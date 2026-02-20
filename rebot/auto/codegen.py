"""AI-driven code generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Callable

from pydantic import BaseModel, Field

from rebot.agents.vector_memory import VectorMemory
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.tools.fs_tools import WriteFileTool, ReadFileTool, ListFilesTool
from rebot.tools.command_tool import RunTestsTool
from rebot.auto.anomaly_memory import AnomalyMemory


class FileSpec(BaseModel):
    path: str
    content: str


class CodegenSchema(BaseModel):
    summary: str
    stack: list[str] = Field(default_factory=list)
    files: list[FileSpec] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)


class FilePlanItem(BaseModel):
    path: str
    purpose: str = ""


class FilePlanSchema(BaseModel):
    summary: str
    stack: list[str] = Field(default_factory=list)
    files: list[FilePlanItem] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)


class FileChunkSchema(BaseModel):
    path: str
    content_chunk: str
    done: bool = False

class MetaPolicy(BaseModel):
    goals: list[str] = Field(default_factory=list)
    architecture_rules: list[str] = Field(default_factory=list)
    ui_rules: list[str] = Field(default_factory=list)
    quality_rules: list[str] = Field(default_factory=list)
    perspective_rules: list[str] = Field(default_factory=list)


class DefectMap(BaseModel):
    root_causes: list[str] = Field(default_factory=list)
    risk_hotspots: list[str] = Field(default_factory=list)
    structural_fixes: list[str] = Field(default_factory=list)


class AnomalyItem(BaseModel):
    name: str
    severity: float
    evidence: str


class AnomalyReport(BaseModel):
    score: float
    items: list[AnomalyItem] = Field(default_factory=list)
    attention: dict[str, float] = Field(default_factory=dict)
    clusters: dict[str, list[str]] = Field(default_factory=dict)
    scaled_attention: dict[str, float] = Field(default_factory=dict)
    perspective_missing: list[str] = Field(default_factory=list)
    perspective_tasks: list[str] = Field(default_factory=list)


@dataclass
class CodegenConfig:
    workspace: str
    language: str
    platforms: list[str]
    quality_targets: list[str] = field(
        default_factory=lambda: [
            "production_ready",
            "clean_architecture",
            "security_hardened",
            "fast_build",
        ]
    )
    domain_targets: list[str] = field(default_factory=list)
    max_files: int = 24
    validate_commands: list[str] = field(default_factory=list)
    enable_validation: bool = True
    anomaly_threshold: float = 0.35
    max_refine_rounds: int = 2
    memory_path: str | None = None
    attention_scale: float = 1.0
    attention_curves: dict[str, float] = field(
        default_factory=lambda: {
            "frontend": 1.0,
            "backend": 1.0,
            "mobile": 1.0,
            "validation": 1.2,
            "missing_files": 1.1,
            "general": 1.0,
        }
    )
    max_file_chunks: int = 4
    vector_memory_path: str | None = None
    on_file: Callable[[str], None] | None = None
    on_file_start: Callable[[str], None] | None = None
    on_file_chunk: Callable[[str, int], None] | None = None
    on_file_done: Callable[[str], None] | None = None
    max_codegen_workers: int = 2


@dataclass
class CodegenPipeline:
    model: ChatModel

    def build_policy(
        self,
        *,
        spec: dict[str, Any],
        arch: dict[str, Any],
        plan: dict[str, Any],
        perspective: dict[str, Any] | None = None,
    ) -> MetaPolicy:
        prompt = (
            "Derive a high-level generation policy. Focus on structure, UI layout rules, "
            "and quality constraints. Return JSON only."
        )
        payload = {"spec": spec, "arch": arch, "plan": plan, "perspective": perspective or {}}
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "MetaPolicy",
                    "schema": MetaPolicy.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, MetaPolicy, msg.content, prompt, payload)
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, MetaPolicy, msg.content, prompt, payload)

    def generate(
        self,
        *,
        spec: dict[str, Any],
        arch: dict[str, Any],
        plan: dict[str, Any],
        config: CodegenConfig,
        policy: MetaPolicy | None = None,
    ) -> CodegenSchema:
        return self._generate_incremental(
            spec=spec,
            arch=arch,
            plan=plan,
            config=config,
            policy=policy,
        )

    def _generate_incremental(
        self,
        *,
        spec: dict[str, Any],
        arch: dict[str, Any],
        plan: dict[str, Any],
        config: CodegenConfig,
        policy: MetaPolicy | None,
    ) -> CodegenSchema:
        retrieved = self._retrieve_vector_context(spec=spec, config=config)
        workspace_snapshot = self.summarize_workspace(root=config.workspace)
        plan_prompt = (
            "Create a compact file plan for implementation. "
            "Return JSON only with summary, stack, files[{path,purpose}], commands. "
            "Keep file count practical and runnable."
        )
        plan_payload = {
            "spec": spec,
            "arch": arch,
            "plan": plan,
            "workspace": workspace_snapshot,
            "language": config.language,
            "platforms": config.platforms,
            "quality_targets": config.quality_targets,
            "domain_targets": config.domain_targets,
            "max_files": config.max_files,
            "attention_scale": config.attention_scale,
            "policy": policy.model_dump() if policy else {},
            "retrieved_context": retrieved,
        }
        file_plan = self._build_file_plan(plan_prompt, plan_payload, config)

        generated_files: list[FileSpec] = []
        to_generate = file_plan.files[: config.max_files]
        immediate: list[FileSpec] = []
        delayed: list[FilePlanItem] = []
        for item in to_generate:
            p_lower = item.path.lower()
            if p_lower.endswith("readme.md") or "/docs/" in p_lower or p_lower.startswith("docs/"):
                immediate.append(FileSpec(path=item.path, content=_fallback_file_content(item.path, spec)))
            else:
                delayed.append(item)
        generated_files.extend(immediate)

        max_workers = max(1, min(config.max_codegen_workers, len(delayed) if delayed else 1))
        if delayed and max_workers > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                fut_map = {
                    pool.submit(
                        self._generate_one_file_safe,
                        item=item,
                        spec=spec,
                        arch=arch,
                        plan=plan,
                        policy=policy,
                        config=config,
                        workspace_snapshot=workspace_snapshot,
                        retrieved=retrieved,
                    ): item
                    for item in delayed
                }
                for fut in as_completed(fut_map):
                    generated_files.append(fut.result())
        else:
            for item in delayed:
                generated_files.append(
                    self._generate_one_file_safe(
                        item=item,
                        spec=spec,
                        arch=arch,
                        plan=plan,
                        policy=policy,
                        config=config,
                        workspace_snapshot=workspace_snapshot,
                        retrieved=retrieved,
                    )
                )

        result = CodegenSchema(
            summary=file_plan.summary or "Generated runnable project code.",
            stack=file_plan.stack,
            files=generated_files,
            commands=file_plan.commands,
        )
        self._update_vector_memory(spec=spec, code=result, config=config)
        return result

    def _generate_one_file_safe(
        self,
        *,
        item: FilePlanItem,
        spec: dict[str, Any],
        arch: dict[str, Any],
        plan: dict[str, Any],
        policy: MetaPolicy | None,
        config: CodegenConfig,
        workspace_snapshot: str,
        retrieved: list[dict[str, Any]],
    ) -> FileSpec:
        if config.on_file is not None:
            try:
                config.on_file(item.path)
            except Exception:
                pass
        if config.on_file_start is not None:
            try:
                config.on_file_start(item.path)
            except Exception:
                pass
        print(f"Codegen: generating file {item.path}")
        content = self._generate_single_file(
            path=item.path,
            purpose=item.purpose,
            spec=spec,
            arch=arch,
            plan=plan,
            policy=policy,
            config=config,
            workspace_snapshot=workspace_snapshot,
            retrieved=retrieved,
        )
        if config.on_file_done is not None:
            try:
                config.on_file_done(item.path)
            except Exception:
                pass
        return FileSpec(path=item.path, content=content)

    def _build_file_plan(
        self,
        prompt: str,
        payload: dict[str, Any],
        config: CodegenConfig,
    ) -> FilePlanSchema:
        try:
            if getattr(self.model, "supports_response_format", False):
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "FilePlanSchema",
                        "schema": FilePlanSchema.model_json_schema(),
                    },
                }
                msg = self.model.invoke(
                    [Message(role="user", content=f"{prompt}\n\n{payload}")],
                    tools=[],
                    response_format=response_format,
                )
                parsed = _parse_schema_with_repair(self.model, FilePlanSchema, msg.content, prompt, payload)
            else:
                msg = self.model.invoke(
                    [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
                    tools=[],
                )
                parsed = _parse_schema_with_repair(self.model, FilePlanSchema, msg.content, prompt, payload)
        except Exception:
            return _fallback_file_plan(config=config, workspace=config.workspace)
        parsed = _normalize_file_plan_for_platform(parsed, config)
        if not parsed.files:
            return _fallback_file_plan(config=config, workspace=config.workspace)
        return parsed

    def _generate_single_file(
        self,
        *,
        path: str,
        purpose: str,
        spec: dict[str, Any],
        arch: dict[str, Any],
        plan: dict[str, Any],
        policy: MetaPolicy | None,
        config: CodegenConfig,
        workspace_snapshot: str,
        retrieved: list[dict[str, Any]],
    ) -> str:
        chunks: list[str] = []
        cursor = 0
        spec_compact = _compact_spec(spec)
        arch_compact = _compact_arch(arch)
        plan_compact = _compact_plan(plan)
        for _ in range(config.max_file_chunks):
            prompt = (
                "Generate code for a single file in chunks. "
                "Return JSON only with {path, content_chunk, done}. "
                "If file is not finished, set done=false and continue naturally in next call."
            )
            payload = {
                "path": path,
                "purpose": purpose,
                "language": config.language,
                "platforms": config.platforms,
                "spec": spec_compact,
                "arch": arch_compact,
                "plan": plan_compact,
                "policy": policy.model_dump() if policy else {},
                "workspace": workspace_snapshot,
                "retrieved_context": retrieved,
                "generated_chars": cursor,
                "existing_content": "".join(chunks)[-8000:],
            }
            if getattr(self.model, "supports_response_format", False):
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "FileChunkSchema",
                        "schema": FileChunkSchema.model_json_schema(),
                    },
                }
                msg = self.model.invoke(
                    [Message(role="user", content=f"{prompt}\n\n{payload}")],
                    tools=[],
                    response_format=response_format,
                )
                try:
                    piece = _parse_schema_with_repair(self.model, FileChunkSchema, msg.content, prompt, payload)
                except Exception:
                    piece = FileChunkSchema(path=path, content_chunk=_fallback_file_content(path, spec), done=True)
            else:
                msg = self.model.invoke(
                    [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
                    tools=[],
                )
                try:
                    piece = _parse_schema_with_repair(self.model, FileChunkSchema, msg.content, prompt, payload)
                except Exception:
                    piece = FileChunkSchema(path=path, content_chunk=_fallback_file_content(path, spec), done=True)
            if piece.content_chunk:
                chunks.append(piece.content_chunk)
                cursor += len(piece.content_chunk)
                if config.on_file_chunk is not None:
                    try:
                        config.on_file_chunk(path, len(chunks))
                    except Exception:
                        pass
            if piece.done or not piece.content_chunk:
                break
        content = "".join(chunks).strip()
        if not content:
            return _fallback_file_content(path, spec)
        return content

    def _retrieve_vector_context(self, *, spec: dict[str, Any], config: CodegenConfig) -> list[dict[str, Any]]:
        path = Path(config.vector_memory_path) if config.vector_memory_path else Path(config.workspace) / "docs" / "vector_memory.json"
        memory = VectorMemory(path=path)
        memory.load()
        query = _build_spec_query(spec)
        return memory.search(query, top_k=6)

    def _update_vector_memory(self, *, spec: dict[str, Any], code: CodegenSchema, config: CodegenConfig) -> None:
        path = Path(config.vector_memory_path) if config.vector_memory_path else Path(config.workspace) / "docs" / "vector_memory.json"
        memory = VectorMemory(path=path)
        memory.load()
        artifact = {
            "product": spec.get("product"),
            "stack": code.stack[:8],
            "files": [f.path for f in code.files[:40]],
            "summary": code.summary[:800],
        }
        memory.add(json.dumps(artifact, ensure_ascii=False), metadata={"kind": "codegen"})
        memory.save()

    def apply(self, code: CodegenSchema, *, root: str) -> None:
        writer = WriteFileTool(root=_path(root))
        for fs in code.files:
            writer.run({"path": fs.path, "content": fs.content})

    def validate(self, *, root: str, commands: list[str]) -> list[str]:
        if not commands:
            return []
        runner = RunTestsTool(root=_path(root))
        outputs: list[str] = []
        for cmd in commands:
            outputs.append(runner.run({"command": cmd}))
        return outputs

    def summarize_workspace(self, *, root: str, max_depth: int = 4) -> str:
        lister = ListFilesTool()
        return lister.run({"path": root, "max_depth": max_depth})

    def detect_anomalies(
        self,
        *,
        root: str,
        platforms: list[str],
        validation_outputs: list[str],
        memory: AnomalyMemory | None = None,
        attention_scale: float = 1.0,
        attention_curves: dict[str, float] | None = None,
        perspective: dict[str, Any] | None = None,
    ) -> AnomalyReport:
        issues: list[AnomalyItem] = []
        attention: dict[str, float] = {}
        files = self._list_files(root)

        def add(name: str, severity: float, evidence: str, focus: str) -> None:
            issues.append(AnomalyItem(name=name, severity=severity, evidence=evidence))
            attention[focus] = max(attention.get(focus, 0.0), severity)

        if "frontend/package.json" not in files:
            add("missing_frontend", 0.6, "frontend/package.json not found", "frontend")
        if "frontend/src/App.jsx" not in files and "frontend/src/App.tsx" not in files:
            add("missing_frontend_entry", 0.55, "App entry missing", "frontend")
        if "backend/app.py" not in files and "backend/index.ts" not in files:
            add("missing_backend_entry", 0.5, "backend entry missing", "backend")

        platform_set = {p.lower() for p in platforms}
        if "ios" in platform_set and "mobile/ios/HomeView.swift" not in files:
            add("missing_ios_ui", 0.45, "SwiftUI HomeView missing", "mobile")
        if "web" in platform_set and "frontend/index.html" not in files:
            add("missing_web_index", 0.4, "frontend/index.html missing", "frontend")

        for out in validation_outputs:
            lowered = out.lower()
            if "error" in lowered or "failed" in lowered or "traceback" in lowered:
                add("validation_failed", 0.8, out[-800:], "quality")
                break

        perspective_missing: list[str] = []
        perspective_tasks: list[str] = []
        if perspective:
            missing_views = perspective.get("missing_views") or []
            if missing_views:
                perspective_missing = list(missing_views)
                perspective_tasks = [
                    f"Add perspective coverage for: {view}" for view in perspective_missing
                ]
                add(
                    "perspective_missing",
                    0.5,
                    "Missing views: " + ", ".join(perspective_missing),
                    "general",
                )

        score = 0.0
        if issues:
            score = min(1.0, sum(i.severity for i in issues) / max(len(issues), 1))
        if memory:
            boost = memory.attention_boost()
            for key, weight in boost.items():
                attention[key] = max(attention.get(key, 0.0), weight)
            freq = memory.frequency_boost()
            for name, bump in freq.items():
                cluster = memory._cluster_key(name)
                attention[cluster] = max(attention.get(cluster, 0.0), bump)
        clusters = memory.clusters if memory else {}
        severity_boost = 1.0
        if issues:
            max_sev = max(i.severity for i in issues)
            severity_boost = 1.0 + max_sev * 0.6
        curve_map = attention_curves or {}
        scaled = {
            k: min(
                1.0,
                v * max(0.1, attention_scale) * severity_boost * curve_map.get(k, 1.0),
            )
            for k, v in attention.items()
        }
        return AnomalyReport(
            score=score,
            items=issues,
            attention=attention,
            clusters=clusters,
            scaled_attention=scaled,
            perspective_missing=perspective_missing,
            perspective_tasks=perspective_tasks,
        )

    def refine_with_anomalies(
        self,
        *,
        root: str,
        report: AnomalyReport,
        summary: str,
        stack: list[str],
        defect_map: DefectMap | None = None,
        policy: MetaPolicy | None = None,
    ) -> CodegenSchema:
        prompt = (
            "You must fix the anomalies with priority based on attention weights. "
            "Return JSON with files[{path,content}] for ONLY changed files. "
            "Avoid overfitting: fix severe anomalies, tolerate minor stylistic variance."
        )
        payload = {
            "summary": summary,
            "stack": stack,
            "anomaly_score": report.score,
            "anomalies": [i.model_dump() for i in report.items],
            "attention": report.attention,
            "attention_clusters": report.clusters,
            "attention_scaled": report.scaled_attention,
            "perspective_missing": report.perspective_missing,
            "perspective_tasks": report.perspective_tasks,
            "policy": policy.model_dump() if policy else {},
            "defect_map": defect_map.model_dump() if defect_map else {},
            "workspace": self.summarize_workspace(root=root),
        }
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "CodegenSchema",
                    "schema": CodegenSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, CodegenSchema, msg.content, prompt, payload)
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, CodegenSchema, msg.content, prompt, payload)

    def build_defect_map(
        self,
        *,
        report: AnomalyReport,
        spec: dict[str, Any],
        arch: dict[str, Any],
    ) -> DefectMap:
        prompt = (
            "Analyze anomalies and derive structural root causes and fixes. "
            "Return JSON with root_causes, risk_hotspots, structural_fixes."
        )
        payload = {"anomalies": [i.model_dump() for i in report.items], "spec": spec, "arch": arch}
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "DefectMap",
                    "schema": DefectMap.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, DefectMap, msg.content, prompt, payload)
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, DefectMap, msg.content, prompt, payload)

    def refine(
        self,
        *,
        root: str,
        issues: list[str],
        summary: str,
        stack: list[str],
    ) -> CodegenSchema:
        prompt = (
            "Refine the codebase to fix the issues. "
            "Return JSON with files[{path,content}] containing ONLY files that must be changed. "
            "Do NOT include unchanged files."
        )
        payload = {
            "summary": summary,
            "stack": stack,
            "issues": issues,
            "workspace": self.summarize_workspace(root=root),
        }
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "CodegenSchema",
                    "schema": CodegenSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, CodegenSchema, msg.content, prompt, payload)
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, CodegenSchema, msg.content, prompt, payload)

    def _list_files(self, root: str, max_depth: int = 6) -> set[str]:
        lister = ListFilesTool()
        content = lister.run({"path": root, "max_depth": max_depth})
        return {line.strip() for line in content.splitlines() if line.strip()}


def _path(raw: str):
    from pathlib import Path

    return Path(raw)


def _parse_schema_with_repair(
    model: ChatModel,
    schema: type[BaseModel],
    raw: str,
    prompt: str,
    payload: dict[str, Any],
):
    attempts: list[dict[str, Any]] = []
    is_file_chunk = schema is FileChunkSchema or getattr(schema, "__name__", "") == "FileChunkSchema"

    def _try_parse(candidate: str):
        try:
            return schema.model_validate_json(candidate)
        except Exception:
            extracted = _extract_json_object(candidate)
            if extracted:
                try:
                    data = json.loads(extracted)
                    normalized = _normalize_payload(schema, data)
                    return schema.model_validate(normalized)
                except Exception:
                    return None
            return None

    attempts.append({"stage": "initial", "content": raw})
    parsed = _try_parse(raw)
    if parsed is not None:
        return parsed

    response_format = {
        "type": "json_schema",
        "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
    }
    candidate = raw
    for i in range(3):
        clipped = candidate[-6000:] if candidate else ""
        repair_prompt = (
            f"{prompt}\n\n"
            "Return STRICT valid JSON only, no markdown fences, no comments.\n"
            "Close all strings and braces correctly.\n"
            f"Schema fields: {list(schema.model_fields.keys())}\n\n"
            f"Input context:\n{payload}\n\n"
            f"Broken JSON candidate:\n{clipped}"
        )
        repaired = model.invoke(
            [Message(role="user", content=repair_prompt)],
            tools=[],
            response_format=response_format if getattr(model, "supports_response_format", False) else None,
        )
        candidate = repaired.content
        attempts.append({"stage": f"repair_{i + 1}", "content": candidate})
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed
    if is_file_chunk:
        heuristic = _heuristic_file_chunk(candidate, fallback_path=str(payload.get("path") or "unknown.txt"))
        if heuristic is not None:
            try:
                return schema.model_validate(heuristic)
            except Exception:
                pass
        # Last-resort fallback so a single bad chunk never aborts the whole generation.
        fallback_path = _coerce_to_text(payload.get("path", "unknown.txt"))
        return FileChunkSchema(path=fallback_path, content_chunk="", done=True)
    dump_path = _dump_codegen_debug(schema=schema.__name__, payload=payload, attempts=attempts)
    snippet = (candidate or "")[:400].replace("\n", "\\n")
    raise ValueError(
        f"{schema.__name__} JSON parsing failed after retries. debug_file={dump_path} last_snippet={snippet}"
    )


def _normalize_payload(schema: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if schema is FilePlanSchema:
        normalized["summary"] = _coerce_to_text(normalized.get("summary", "Implementation file plan"))
        normalized["stack"] = _normalize_list(normalized.get("stack", []))
        normalized["commands"] = _normalize_list(normalized.get("commands", []))
        files = normalized.get("files", [])
        if not isinstance(files, list):
            files = [files]
        fixed: list[dict[str, str]] = []
        for item in files:
            if isinstance(item, dict):
                fixed.append(
                    {
                        "path": _coerce_to_text(item.get("path", "src/main.txt")),
                        "purpose": _coerce_to_text(item.get("purpose", "")),
                    }
                )
            else:
                fixed.append({"path": _coerce_to_text(item), "purpose": ""})
        normalized["files"] = fixed
        return normalized
    if schema is FileChunkSchema:
        normalized["path"] = _coerce_to_text(normalized.get("path", "unknown.txt"))
        normalized["content_chunk"] = _coerce_to_text(normalized.get("content_chunk", ""))
        done_raw = normalized.get("done", False)
        if isinstance(done_raw, bool):
            done = done_raw
        elif isinstance(done_raw, (int, float)):
            done = bool(done_raw)
        elif isinstance(done_raw, str):
            done = done_raw.strip().lower() in {"1", "true", "yes", "done", "finished"}
        else:
            done = False
        normalized["done"] = done
        return normalized
    if schema is CodegenSchema:
        normalized["summary"] = _coerce_to_text(normalized.get("summary", "Generated code changes"))
        normalized["stack"] = _normalize_list(normalized.get("stack", []))
        normalized["commands"] = _normalize_list(normalized.get("commands", []))
        files = normalized.get("files", [])
        if not isinstance(files, list):
            files = [files]
        fixed_files: list[dict[str, str]] = []
        for item in files:
            if isinstance(item, dict):
                fixed_files.append(
                    {
                        "path": _coerce_to_text(item.get("path", "unknown.txt")),
                        "content": _coerce_to_text(item.get("content", "")),
                    }
                )
            else:
                fixed_files.append({"path": "unknown.txt", "content": _coerce_to_text(item)})
        normalized["files"] = fixed_files
        return normalized
    if schema is MetaPolicy:
        for key in (
            "goals",
            "architecture_rules",
            "ui_rules",
            "quality_rules",
            "perspective_rules",
        ):
            normalized[key] = _normalize_list(normalized.get(key, []))
        return normalized
    if schema is DefectMap:
        for key in ("root_causes", "risk_hotspots", "structural_fixes"):
            normalized[key] = _normalize_list(normalized.get(key, []))
        return normalized
    return normalized


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_coerce_to_text(v) for v in value if v is not None]
    if isinstance(value, dict):
        return [_coerce_to_text(v) for v in value.values() if v is not None] or [
            _coerce_to_text(value)
        ]
    return [_coerce_to_text(value)]


def _coerce_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        parts: list[str] = []
        for k, v in value.items():
            if v is None:
                continue
            parts.append(f"{k}: {_coerce_to_text(v)}")
        return " | ".join(parts) if parts else json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(_coerce_to_text(v) for v in value)
    return str(value)


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def _dump_codegen_debug(*, schema: str, payload: dict[str, Any], attempts: list[dict[str, Any]]) -> str:
    root = Path(tempfile.gettempdir()) / "rebot_codegen_debug"
    root.mkdir(parents=True, exist_ok=True)
    idx = len(list(root.glob("codegen_debug_*.json"))) + 1
    path = root / f"codegen_debug_{idx}.json"
    path.write_text(
        json.dumps({"schema": schema, "payload": payload, "attempts": attempts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def _heuristic_file_chunk(candidate: str, *, fallback_path: str) -> dict[str, Any] | None:
    if not candidate:
        return None
    path_match = re.search(r'"path"\s*:\s*"([^"]+)"', candidate)
    path = path_match.group(1).strip() if path_match else fallback_path

    done = False
    done_match = re.search(r'"done"\s*:\s*(true|false)', candidate, flags=re.IGNORECASE)
    if done_match:
        done = done_match.group(1).lower() == "true"

    content = ""
    marker = re.search(r'"content_chunk"\s*:\s*"', candidate)
    if marker:
        s = candidate[marker.end() :]
        buf: list[str] = []
        esc = False
        for ch in s:
            if esc:
                buf.append(ch)
                esc = False
                continue
            if ch == "\\":
                buf.append(ch)
                esc = True
                continue
            if ch == '"':
                break
            buf.append(ch)
        raw = "".join(buf)
        if raw:
            try:
                content = bytes(raw, "utf-8").decode("unicode_escape")
            except Exception:
                content = raw.replace("\\n", "\n").replace('\\"', '"')
    if not content.strip():
        if "```" in candidate:
            parts = candidate.split("```")
            if len(parts) >= 2:
                content = parts[1]
        elif "content_chunk" not in candidate:
            content = candidate
    if not content.strip():
        return None
    return {"path": path, "content_chunk": content, "done": done}


def _build_spec_query(spec: dict[str, Any]) -> str:
    product = _coerce_to_text(spec.get("product", ""))
    goals = " ".join(_normalize_list(spec.get("goals", [])))
    features = " ".join(_normalize_list(spec.get("features", [])))
    return f"{product} {goals} {features}".strip()


def _compact_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "product": _coerce_to_text(spec.get("product", "")),
        "platforms": _normalize_list(spec.get("platforms", []))[:6],
        "features": _normalize_list(spec.get("features", []))[:10],
        "constraints": _normalize_list(spec.get("constraints", []))[:8],
    }


def _compact_arch(arch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(arch, dict):
        return {"summary": _coerce_to_text(arch)}
    out: dict[str, Any] = {}
    for key in ("architecture", "components", "interfaces", "notes", "stack"):
        if key in arch:
            out[key] = arch[key]
    if not out:
        out = {"summary": _coerce_to_text(arch)}
    return out


def _compact_plan(plan: dict[str, Any]) -> dict[str, Any]:
    tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
    task_names: list[str] = []
    if isinstance(tasks, list):
        for t in tasks[:12]:
            if isinstance(t, dict):
                task_names.append(_coerce_to_text(t.get("task", t)))
            else:
                task_names.append(_coerce_to_text(t))
    milestones = plan.get("milestones", []) if isinstance(plan, dict) else []
    return {"tasks": task_names, "milestones": _normalize_list(milestones)[:8]}


def _fallback_file_plan(*, config: CodegenConfig, workspace: str) -> FilePlanSchema:
    existing = _fallback_files_from_workspace(workspace)
    if existing:
        files = [FilePlanItem(path=p, purpose="Implement and complete this file.") for p in existing]
        return FilePlanSchema(
            summary="Fallback file plan from workspace scan.",
            stack=[config.language],
            files=files,
            commands=config.validate_commands,
        )
    default_files = [
        FilePlanItem(path="frontend/index.html", purpose="Main web entry and app mount."),
        FilePlanItem(path="frontend/src/main.js", purpose="Core interaction and game logic."),
        FilePlanItem(path="frontend/src/styles.css", purpose="UI style and layout."),
        FilePlanItem(path="README.md", purpose="Run and usage instructions."),
    ]
    return FilePlanSchema(
        summary="Fallback default plan.",
        stack=[config.language],
        files=default_files,
        commands=config.validate_commands,
    )


def _normalize_file_plan_for_platform(plan: FilePlanSchema, config: CodegenConfig) -> FilePlanSchema:
    platforms = {p.lower() for p in (config.platforms or [])}
    if "web" not in platforms and "html" not in platforms and "react" not in platforms and "nextjs" not in platforms:
        return plan
    normalized: list[FilePlanItem] = []
    seen: set[str] = set()

    def map_path(raw: str) -> str:
        p = raw.replace("\\", "/").strip().lstrip("/")
        name = p.split("/")[-1].lower()
        if name in {"index.html"}:
            return "frontend/index.html"
        if name in {"style.css", "styles.css"}:
            return "frontend/src/styles.css"
        if name.endswith(".js") or name.endswith(".ts") or name.endswith(".tsx"):
            return f"frontend/src/{name}"
        if "/" not in p and name.endswith(".md"):
            return name
        if "/" not in p and name.endswith(".json"):
            return f"frontend/{name}"
        if "/" not in p:
            return f"frontend/{p}"
        return p

    for item in plan.files:
        mapped = map_path(item.path)
        if mapped in seen:
            continue
        seen.add(mapped)
        normalized.append(FilePlanItem(path=mapped, purpose=item.purpose))

    required = [
        FilePlanItem(path="frontend/index.html", purpose="Main web entry and app mount."),
        FilePlanItem(path="frontend/src/main.js", purpose="Core interaction and game logic."),
        FilePlanItem(path="frontend/src/styles.css", purpose="UI style and layout."),
    ]
    for req in required:
        if req.path not in seen:
            normalized.insert(0, req)
            seen.add(req.path)

    if "README.md" not in seen:
        normalized.append(FilePlanItem(path="README.md", purpose="Run and usage instructions."))

    if len(normalized) > config.max_files:
        normalized = normalized[: config.max_files]

    return FilePlanSchema(
        summary=plan.summary,
        stack=plan.stack,
        files=normalized,
        commands=plan.commands,
    )


def _fallback_files_from_workspace(workspace: str) -> list[str]:
    root = Path(workspace)
    if not root.exists():
        return []
    chosen: list[str] = []
    exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".dart", ".json"}
    for path in root.rglob("*"):
        if len(chosen) >= 30:
            break
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if "node_modules" in path.parts or ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.suffix.lower() not in exts:
            continue
        chosen.append(str(path.relative_to(root)).replace("\\", "/"))
    return chosen


def _fallback_file_content(path: str, spec: dict[str, Any]) -> str:
    p = path.lower()
    product = _coerce_to_text(spec.get("product", "Generated App")).lower()
    if p.endswith("index.html"):
        title = _coerce_to_text(spec.get("product", "Generated App"))
        return (
            "<!doctype html>\n"
            "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title><link rel='stylesheet' href='./src/styles.css'></head>"
            "<body><div id='root'></div><script type='module' src='./src/main.js'></script></body></html>\n"
        )
    if p.endswith("styles.css"):
        return (
            "body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#f5f7fb;}\n"
            "#root{max-width:960px;margin:0 auto;}\n"
            ".game{max-width:420px;background:#faf8ef;border-radius:14px;padding:16px;box-shadow:0 8px 24px rgba(0,0,0,.08);}\n"
            ".toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}\n"
            ".grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;background:#bbada0;padding:8px;border-radius:8px;}\n"
            ".cell{height:84px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:28px;background:#cdc1b4;color:#776e65;}\n"
            ".v2{background:#eee4da}.v4{background:#ede0c8}.v8{background:#f2b179;color:#f9f6f2}.v16{background:#f59563;color:#f9f6f2}.v32{background:#f67c5f;color:#f9f6f2}.v64{background:#f65e3b;color:#f9f6f2}.v128,.v256,.v512,.v1024,.v2048{background:#edcf72;color:#f9f6f2}\n"
        )
    if p.endswith(".js") or p.endswith(".ts"):
        if "2048" in product:
            return (
                "const root = document.getElementById('root');\n"
                "let score = 0;\n"
                "let board = Array.from({length:4},()=>Array(4).fill(0));\n"
                "function addRandom(){const e=[];for(let r=0;r<4;r++)for(let c=0;c<4;c++)if(!board[r][c])e.push([r,c]);if(!e.length)return;const [r,c]=e[Math.floor(Math.random()*e.length)];board[r][c]=Math.random()<0.9?2:4;}\n"
                "function reset(){score=0;board=Array.from({length:4},()=>Array(4).fill(0));addRandom();addRandom();render();}\n"
                "function slide(row){const a=row.filter(Boolean);for(let i=0;i<a.length-1;i++){if(a[i]===a[i+1]){a[i]*=2;score+=a[i];a[i+1]=0;}}const b=a.filter(Boolean);while(b.length<4)b.push(0);return b;}\n"
                "function move(dir){let moved=false;const clone=board.map(r=>[...r]);const rot=(m)=>m[0].map((_,i)=>m.map(r=>r[i]).reverse());const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);let b=board.map(r=>[...r]);if(dir==='up')b=rot(b);if(dir==='right')b=rot(rot(b));if(dir==='down')b=rot(rot(rot(b)));b=b.map(r=>slide(r));if(dir==='down')b=rot(b);if(dir==='right')b=rot(rot(b));if(dir==='up')b=rot(rot(rot(b)));board=b;moved=!eq(clone,board);if(moved)addRandom();render();}\n"
                "function cls(v){return v?`cell v${v}`:'cell';}\n"
                "function render(){root.innerHTML=`<div class='game'><div class='toolbar'><h2>2048</h2><div>Score: ${score}</div><button id='reset'>Restart</button></div><div class='grid'>${board.flat().map(v=>`<div class='${cls(v)}'>${v||''}</div>`).join('')}</div></div>`;document.getElementById('reset').onclick=reset;}\n"
                "window.addEventListener('keydown',(e)=>{const k=e.key;if(k==='ArrowLeft')move('left');if(k==='ArrowRight')move('right');if(k==='ArrowUp')move('up');if(k==='ArrowDown')move('down');});\n"
                "reset();\n"
            )
        return "document.getElementById('root').textContent = 'Generated fallback app is ready.';\n"
    if p.endswith("readme.md"):
        return (
            "# Generated Project\n\n"
            "## Quick Start\n"
            "- open `frontend/index.html` directly, or\n"
            "- run a static server in `frontend/`.\n"
        )
    return ""
