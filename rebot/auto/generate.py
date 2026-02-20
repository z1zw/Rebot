"""One-shot software generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import asyncio
import os

from rebot.auto.spec_compiler import SpecCompiler
from rebot.auto.arch_synthesizer import ArchitectureSynthesizer
from rebot.auto.task_planner import TaskPlanner
from rebot.auto.workflow_synthesizer import WorkflowSynthesizer
from rebot.auto.production_builder import ProductionBuilder
from rebot.auto.quality_gate import QualityGate
from rebot.auto.security_gate import SecurityGate
from rebot.auto.ui_designer import UIDesigner
from rebot.models.base import ChatModel
from rebot.auto.codegen import CodegenPipeline, CodegenConfig
from rebot.auto.metagpt_chain import MetaGPTChain
from rebot.auto.perspective import PerspectiveExpander
from rebot.workflows import WorkflowExecutor, ExecutionContext, create_default_registry
from rebot.tools.fs_tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    ReplaceInFileTool,
    ApplyPatchTool,
)
from rebot.tools.command_tool import RunTestsTool


@dataclass
class GeneratorConfig:
    language: str
    platforms: list[str]
    include_ci: bool = True
    include_security: bool = True
    execute_workflow: bool = False
    workflow_inputs: dict[str, Any] = field(default_factory=dict)
    enable_file_tools: bool = True
    enable_command_tools: bool = False
    ai_codegen: bool = True
    validate_commands: list[str] = field(default_factory=list)
    domain_targets: list[str] = field(default_factory=list)
    attention_scale: float = 1.0
    metagpt_chain: bool = True
    metagpt_native: bool = False
    metagpt_native_repo: str | None = None
    metagpt_native_rounds: int = 5
    metagpt_native_investment: float = 3.0
    metagpt_native_only: bool = False
    perspective: bool = True
    max_codegen_workers: int | None = None
    max_files: int | None = None
    max_file_chunks: int | None = None
    max_refine_rounds: int | None = None
    use_reasoning_vector: bool = True
    vector_memory_path: str | None = None


@dataclass
class OneShotGenerator:
    model: ChatModel
    root: Path

    def generate(
        self,
        requirement: str,
        config: GeneratorConfig,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        def emit(stage: str, message: str) -> None:
            if progress_callback is not None:
                progress_callback(stage, message)

        if config.metagpt_native:
            emit("metagpt_native", "Running native MetaGPT multi-agent team...")
            try:
                from rebot.auto.metagpt_native_bridge import run_native_metagpt

                native = run_native_metagpt(
                    requirement=requirement,
                    workspace=str(self.root),
                    api_key=getattr(getattr(self.model, "config", None), "api_key", ""),
                    model=getattr(getattr(self.model, "config", None), "model", ""),
                    base_url=getattr(getattr(self.model, "config", None), "base_url", "")
                    or "https://api.openai.com/v1",
                    repo_path=config.metagpt_native_repo,
                    rounds=config.metagpt_native_rounds,
                    investment=config.metagpt_native_investment,
                )
                emit(
                    "metagpt_native_done",
                    (
                        f"Native MetaGPT done: rounds={native.rounds}, "
                        f"history={native.history_size}, cost={native.total_cost:.4f}"
                    ),
                )
                if config.metagpt_native_only:
                    return
            except Exception as exc:
                emit("metagpt_native_fallback", f"Native MetaGPT failed, fallback to Rebot: {exc}")

        emit("spec", "Compiling requirement into product spec...")
        spec = SpecCompiler(self.model).compile(
            requirement, language=config.language, platforms=config.platforms
        )
        emit("architecture", "Synthesizing architecture...")
        try:
            arch = ArchitectureSynthesizer(self.model).synthesize(spec)
        except Exception:
            arch = _fallback_architecture(spec)
        emit("plan", "Planning implementation tasks...")
        try:
            plan = TaskPlanner(self.model).plan(spec)
        except Exception:
            plan = _fallback_task_plan(spec)
        prd = None
        design = None
        tasks = None
        if config.metagpt_chain:
            emit("metagpt", "Running PRD / Design / Tasks chain...")
            try:
                chain = MetaGPTChain(self.model)
                prd = chain.build_prd(requirement)
                design = chain.build_design(prd)
                tasks = chain.build_tasks(design)
            except Exception:
                prd = None
                design = None
                tasks = None
        emit("workflow", "Building executable workflow...")
        try:
            workflow = WorkflowSynthesizer(self.model).synthesize(
                spec, plan, perspective_tasks=plan.tasks
            )
        except Exception:
            workflow = _fallback_workflow(spec, plan)
        emit("perspective", "Expanding perspective coverage...")
        try:
            perspective = PerspectiveExpander(self.model).expand(
                spec=spec.model_dump(), arch=arch.model_dump()
            )
        except Exception:
            perspective = _fallback_perspective()
        if perspective.missing_views:
            for view in perspective.missing_views:
                plan.tasks.append(f"Add perspective coverage: {view}")
        ui = None
        if "ios" in [p.lower() for p in config.platforms]:
            emit("ui", "Designing iOS UI skeleton...")
            ui = UIDesigner(self.model).design(spec, platform="ios")
        builder = ProductionBuilder(self.root)
        emit("scaffold", "Creating production scaffold...")
        builder.build(
            spec,
            arch,
            language=config.language,
            ui=ui,
            scaffold=not config.ai_codegen,
        )
        emit("scaffold_ready", "Scaffold is ready. Preview can start now.")
        (self.root / "docs" / "PLAN.json").write_text(
            plan.model_dump_json(), encoding="utf-8"
        )
        (self.root / "docs" / "WORKFLOW.json").write_text(
            workflow.model_dump_json(), encoding="utf-8"
        )
        (self.root / "docs" / "PERSPECTIVE.json").write_text(
            perspective.model_dump_json(), encoding="utf-8"
        )
        if prd is not None:
            (self.root / "docs" / "PRD.json").write_text(prd.model_dump_json(), encoding="utf-8")
        if design is not None:
            (self.root / "docs" / "DESIGN.json").write_text(design.model_dump_json(), encoding="utf-8")
        if tasks is not None:
            (self.root / "docs" / "TASKS.json").write_text(tasks.model_dump_json(), encoding="utf-8")
        if config.include_ci:
            emit("ci", "Generating CI workflow...")
            QualityGate(self.root).generate_ci()
        if config.include_security:
            emit("security", "Generating security checks...")
            gate = SecurityGate(self.root)
            gate.write_plan()
            gate.write_runner()
        if config.ai_codegen:
            emit("codegen", "Generating project code...")
            pipeline = CodegenPipeline(self.model)
            speed = _infer_codegen_speed_profile(self.model)
            codegen_cfg = CodegenConfig(
                workspace=str(self.root),
                language=config.language,
                platforms=config.platforms,
                validate_commands=config.validate_commands,
                domain_targets=config.domain_targets,
                memory_path=str(self.root / "docs" / "anomaly_memory.json"),
                attention_scale=config.attention_scale,
                vector_memory_path=(
                    config.vector_memory_path
                    if config.use_reasoning_vector
                    else None
                ),
                on_file=lambda p: emit("codegen_file", p),
                on_file_start=lambda p: emit("codegen_file_start", p),
                on_file_chunk=lambda p, idx: emit("codegen_file_chunk", f"{p}#{idx}"),
                on_file_done=lambda p: emit("codegen_file_done", p),
                max_codegen_workers=config.max_codegen_workers or _infer_codegen_workers(self.model),
                max_files=config.max_files or speed["max_files"],
                max_file_chunks=config.max_file_chunks or speed["max_file_chunks"],
                max_refine_rounds=config.max_refine_rounds or speed["max_refine_rounds"],
            )
            try:
                policy = pipeline.build_policy(
                    spec=spec.model_dump(),
                    arch=arch.model_dump(),
                    plan=plan.model_dump(),
                    perspective=perspective.model_dump(),
                )
            except Exception:
                policy = None
            try:
                code = pipeline.generate(
                    spec=spec.model_dump(),
                    arch=arch.model_dump(),
                    plan=plan.model_dump(),
                    config=codegen_cfg,
                    policy=policy,
                )
                pipeline.apply(code, root=str(self.root))
            except Exception:
                # Keep generation alive: scaffold already exists from ProductionBuilder.
                code = None
            validation_results = []
            if config.validate_commands:
                validation_results = pipeline.validate(
                    root=str(self.root), commands=config.validate_commands
                )
            memory = None
            if codegen_cfg.memory_path:
                from rebot.auto.anomaly_memory import AnomalyMemory

                memory = AnomalyMemory(Path(codegen_cfg.memory_path))
                memory.load()
                memory.decay()
            report = pipeline.detect_anomalies(
                root=str(self.root),
                platforms=config.platforms,
                validation_outputs=validation_results,
                memory=memory,
                attention_scale=codegen_cfg.attention_scale,
                attention_curves=codegen_cfg.attention_curves,
                perspective=perspective.model_dump(),
            )
            if memory:
                memory.update([i.model_dump() for i in report.items])
                memory.save()
            rounds = 0
            while code is not None and report.score >= codegen_cfg.anomaly_threshold and rounds < codegen_cfg.max_refine_rounds:
                try:
                    defect_map = pipeline.build_defect_map(
                        report=report,
                        spec=spec.model_dump(),
                        arch=arch.model_dump(),
                    )
                    refined = pipeline.refine_with_anomalies(
                        root=str(self.root),
                        report=report,
                        summary=code.summary,
                        stack=code.stack,
                        defect_map=defect_map,
                        policy=policy,
                    )
                    pipeline.apply(refined, root=str(self.root))
                    validation_results = []
                    if config.validate_commands:
                        validation_results = pipeline.validate(
                            root=str(self.root), commands=config.validate_commands
                        )
                    report = pipeline.detect_anomalies(
                        root=str(self.root),
                        platforms=config.platforms,
                        validation_outputs=validation_results,
                        memory=memory,
                        attention_scale=codegen_cfg.attention_scale,
                        attention_curves=codegen_cfg.attention_curves,
                        perspective=perspective.model_dump(),
                    )
                    if memory:
                        memory.update([i.model_dump() for i in report.items])
                        memory.save()
                    rounds += 1
                except Exception:
                    break
        if config.execute_workflow:
            self._run_workflow(
                workflow,
                requirement=requirement,
                spec=spec.model_dump(),
                arch=arch.model_dump(),
                inputs=config.workflow_inputs,
                enable_file_tools=config.enable_file_tools,
                enable_command_tools=config.enable_command_tools,
            )

    def _run_workflow(
        self,
        workflow: Any,
        *,
        requirement: str,
        spec: dict[str, Any],
        arch: dict[str, Any],
        inputs: dict[str, Any],
        enable_file_tools: bool,
        enable_command_tools: bool,
    ) -> None:
        async def runner() -> None:
            tools: dict[str, Any] = {}
            if enable_file_tools:
                tools.update(
                    {
                        "list_files": ListFilesTool(),
                        "read_file": ReadFileTool(root=self.root),
                        "write_file": WriteFileTool(root=self.root),
                        "replace_in_file": ReplaceInFileTool(root=self.root),
                        "apply_patch": ApplyPatchTool(root=self.root),
                    }
                )
            if enable_command_tools:
                tools["run_tests"] = RunTestsTool(root=self.root)
            registry = create_default_registry()
            ctx = ExecutionContext(model=self.model, tools=tools)
            executor = WorkflowExecutor(registry=registry, ctx=ctx)
            merged_inputs = {
                "requirement": requirement,
                "spec": spec,
                "arch": arch,
            }
            merged_inputs.update(inputs)
            await executor.run(workflow.workflow, merged_inputs)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(runner())
        else:
            raise RuntimeError(
                "generate() cannot execute workflow inside a running event loop. "
                "Call this from a sync context or add an async wrapper."
            )


def _fallback_architecture(spec):
    from rebot.auto.arch_synthesizer import ArchitectureSchema

    return ArchitectureSchema(
        services=["frontend-app", "game-logic"],
        data_stores=["local-storage"],
        apis=["none"],
        modules=["ui", "engine", "input", "storage"],
        deployment=["static-web"],
    )


def _fallback_task_plan(spec):
    from rebot.auto.task_planner import TaskPlanSchema

    return TaskPlanSchema(
        tasks=[
            "Scaffold project files",
            "Implement core gameplay logic",
            "Implement UI and interactions",
            "Add persistence and restart flow",
            "Validate run and basic quality checks",
        ],
        milestones=["Playable MVP", "Polished UI", "Validation complete"],
    )


def _fallback_workflow(spec, plan):
    from rebot.auto.workflow_synthesizer import WorkflowSchema, _fallback_workflow_schema

    payload = {"tasks": plan.tasks}
    return _fallback_workflow_schema(payload, notes=["workflow_fallback_from_generate=true"])


def _fallback_perspective():
    from rebot.auto.perspective import PerspectiveSchema

    return PerspectiveSchema(
        missing_views=[],
        injected_rules=["Prefer runnable output over verbose docs."],
        priority=["runnable", "previewable"],
    )


def _infer_codegen_workers(model: ChatModel) -> int:
    env_workers = os.getenv("REBOT_CODEGEN_WORKERS")
    if env_workers:
        try:
            return max(1, int(env_workers))
        except Exception:
            pass
    cfg = getattr(model, "config", None)
    base_url = str(getattr(cfg, "base_url", "") or "").lower()
    model_name = str(getattr(cfg, "model", "") or "").lower()
    if "deepseek" in base_url or model_name.startswith("deepseek-"):
        return 2
    return 3


def _infer_codegen_speed_profile(model: ChatModel) -> dict[str, int]:
    profile = {
        "max_files": 24,
        "max_file_chunks": 4,
        "max_refine_rounds": 2,
    }
    cfg = getattr(model, "config", None)
    base_url = str(getattr(cfg, "base_url", "") or "").lower()
    model_name = str(getattr(cfg, "model", "") or "").lower()
    is_slow = (
        "deepseek" in base_url
        or model_name.startswith("deepseek-")
        or "moonshot" in base_url
        or model_name.startswith("moonshot-")
    )
    if is_slow:
        profile["max_files"] = 18
        profile["max_file_chunks"] = 2
        profile["max_refine_rounds"] = 1
    env_files = os.getenv("REBOT_CODEGEN_MAX_FILES")
    env_chunks = os.getenv("REBOT_CODEGEN_MAX_FILE_CHUNKS")
    env_refine = os.getenv("REBOT_CODEGEN_MAX_REFINE_ROUNDS")
    try:
        if env_files:
            profile["max_files"] = max(8, int(env_files))
        if env_chunks:
            profile["max_file_chunks"] = max(1, int(env_chunks))
        if env_refine:
            profile["max_refine_rounds"] = max(0, int(env_refine))
    except Exception:
        pass
    return profile
