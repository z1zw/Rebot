from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Any
import asyncio
import ast
import json
import os
import re
from pathlib import Path
import time

from app.orchestration.metagpt_helpers import (
    AskReviewHelper,
    ReviewConst,
    TaskTypeGuidance,
    build_product_prd_contract,
    build_plan_status,
    build_structural_context,
)
from app.orchestration.ui_presets import choose_ui_preset


LlmCall = Callable[[str, str], Awaitable[str]]
RoleLlmCall = Callable[[str, str, str], Awaitable[str]]
Emit = Callable[[str, Any], Awaitable[None]]


@dataclass
class GeneratedArtifact:
    path: str
    description: str
    content: str


@dataclass
class PlannedFile:
    path: str
    description: str
    deps: list[str]


@dataclass
class BudgetSnapshot:
    estimated_tokens: int = 0
    estimated_cost: float = 0.0
    calls: int = 0


@dataclass
class ReviewReport:
    status: str
    notes: str
    scores: dict[str, int]
    blocking_issues: list[str]


class MultiAgentScheduler:
    def __init__(
        self,
        *,
        llm_call: LlmCall,
        emit: Emit,
        role_llm_call: RoleLlmCall | None = None,
        max_workers: int = 3,
        retries: int = 2,
        max_token_budget: int | None = None,
        max_cost_budget: float | None = None,
        checkpoint_dir: Path | None = None,
        run_id: str | None = None,
    ) -> None:
        self.llm_call = llm_call
        self.role_llm_call = role_llm_call
        self.emit = emit
        self.max_workers = max(1, max_workers)
        self.retries = max(0, retries)
        self.max_token_budget = (
            max(1, int(max_token_budget)) if max_token_budget is not None else None
        )
        self.max_cost_budget = (
            max(0.0, float(max_cost_budget)) if max_cost_budget is not None else None
        )
        self.checkpoint_dir = checkpoint_dir
        self.run_id = run_id or f"run-{int(time.time())}"
        self.budget = BudgetSnapshot()
        self._last_quality_gate: dict[str, Any] = {}
        self.llm_call_timeout_s = max(
            30.0,
            float(os.getenv("REBOT_LLM_CALL_TIMEOUT_S", "120")),
        )
        self.planner_collab_enabled = os.getenv(
            "REBOT_PLANNER_COLLAB_ENABLED",
            "true",
        ).strip().lower() in {"1", "true", "yes", "on"}

    async def run(
        self,
        *,
        task: str,
        repo_map: str,
        ast_context: str,
        memory_hints: list[str],
        framework: str | None = None,  # user-selected framework, overrides inference
    ) -> dict[str, Any]:
        await self.emit("console_log", {"text": f"[scheduler] RUN START - framework param: {framework!r}", "level": "info"})
        await self._emit_bus(
            role="scheduler",
            cause_by="run_start",
            content=f"run_id={self.run_id} framework={framework or 'auto'}",
            send_to="all",
        )
        await self.emit("run_stage", {"stage": "plan", "message": "Planner is creating file plan..."})
        task_guidance = TaskTypeGuidance.infer(task)
        plan = await self._planner(
            task=task,
            repo_map=repo_map,
            ast_context=ast_context,
            memory_hints=memory_hints,
            framework=framework,
        )
        plan, ast_dep_stats = self._apply_ast_dependencies(plan=plan, ast_context=ast_context)
        if ast_dep_stats.get("added_links", 0) > 0:
            await self.emit(
                "console_log",
                {
                    "text": (
                        f"[ast_deps] added_links={ast_dep_stats.get('added_links')} "
                        f"touched_files={ast_dep_stats.get('touched_files')}"
                    ),
                    "level": "default",
                },
            )
        await self.emit(
            "plan_ast_deps",
            {
                "added_links": int(ast_dep_stats.get("added_links", 0)),
                "touched_files": int(ast_dep_stats.get("touched_files", 0)),
                "added_edges": list(ast_dep_stats.get("added_edges", [])),
                "total_edges": self._count_plan_edges(plan),
                "attempt": 0,
            },
        )
        plan_summary = self._plan_summary(plan)
        structural_context = build_structural_context(
            user_requirement=task,
            repo_map=repo_map or "No repo map available.",
            plan_summary=plan_summary,
            context="\n---\n".join(memory_hints[:3]) or "No memory hints.",
        )
        plan_status = build_plan_status(
            plan_summary=plan_summary,
            current_task=plan[0].description if plan else task,
            guidance=task_guidance.guidance,
        )
        await self.emit(
            "plan_summary",
            {
                "summary": plan_summary,
                "files": [p.__dict__ for p in plan],
            },
        )
        await self._save_checkpoint(
            stage="plan",
            payload={
                "framework": framework,
                "plan_summary": plan_summary,
                "plan": [p.__dict__ for p in plan],
            },
        )
        await self.emit(
            "structural_context",
            {
                "text": structural_context,
                "plan_summary": plan_summary,
                "task": task,
            },
        )
        await self.emit(
            "plan_status",
            {
                "status": plan_status,
                "current_task": plan[0].description if plan else task,
            },
        )
        attempt = 0
        plan_confirmed, plan_notes = await self._review_plan(
            task=task, plan=plan, repo_map=repo_map, guidance=task_guidance
        )
        while not plan_confirmed and attempt < self.retries:
            await self.emit(
                "console_log",
                {
                    "text": "[plan_review] auto retrying plan after review flagged issues",
                    "level": "warning",
                },
            )
            plan = await self._planner(
                task=task,
                repo_map=repo_map,
                ast_context=ast_context,
                memory_hints=memory_hints,
                framework=framework,
            )
            plan, ast_dep_stats = self._apply_ast_dependencies(plan=plan, ast_context=ast_context)
            if ast_dep_stats.get("added_links", 0) > 0:
                await self.emit(
                    "console_log",
                    {
                        "text": (
                            f"[ast_deps] retry added_links={ast_dep_stats.get('added_links')} "
                            f"touched_files={ast_dep_stats.get('touched_files')}"
                        ),
                        "level": "default",
                    },
                )
            await self.emit(
                "plan_ast_deps",
                {
                    "added_links": int(ast_dep_stats.get("added_links", 0)),
                    "touched_files": int(ast_dep_stats.get("touched_files", 0)),
                    "added_edges": list(ast_dep_stats.get("added_edges", [])),
                    "total_edges": self._count_plan_edges(plan),
                    "attempt": attempt + 1,
                },
            )
            plan_summary = self._plan_summary(plan)
            plan_confirmed, plan_notes = await self._review_plan(
                task=task, plan=plan, repo_map=repo_map, guidance=task_guidance
            )
            attempt += 1
        await self.emit("plan_summary", {"summary": plan_summary, "files": [p.__dict__ for p in plan]})
        await self.emit("console_log", {"text": f"[plan_review] confirmed={plan_confirmed} notes={plan_notes}", "level": "default"})
        await self.emit(
            "plan_review",
            {
                "confirmed": plan_confirmed,
                "notes": plan_notes,
                "summary": plan_summary,
            },
        )
        await self.emit("run_stage", {"stage": "plan_review", "message": "Planner review confirms task alignment."})
        # Framework enforcement: only "general" allows model inference, others are mandatory
        if framework and framework.strip().lower() not in {"general", ""}:
            inferred_framework = framework.strip().lower()
            await self.emit(
                "console_log",
                {"text": f"[framework] ENFORCED: {inferred_framework} (user selected)", "level": "default"},
            )
        else:
            inferred_framework = self._infer_framework(task=task, plan=plan)
            await self.emit(
                "console_log",
                {"text": f"[framework] INFERRED: {inferred_framework} (general mode)", "level": "default"},
            )
        ui_preset = choose_ui_preset(task, inferred_framework)
        await self.emit(
            "console_log",
            {
                "text": f"[preset] selected={ui_preset.get('name')} framework={inferred_framework}",
                "level": "default",
            },
        )

        await self.emit("run_stage", {"stage": "implement", "message": "Coder agents are generating files..."})
        artifacts = await self._coder(
            task=task,
            plan=plan,
            repo_map=repo_map,
            ast_context=ast_context,
            memory_hints=memory_hints,
            framework=inferred_framework,
            ui_preset=ui_preset,
            task_guidance=task_guidance,
        )
        await self._save_checkpoint(
            stage="implement",
            payload={
                "plan": [p.__dict__ for p in plan],
                "framework": inferred_framework,
                "ui_preset": ui_preset.get("name"),
                "artifacts": [a.__dict__ for a in artifacts],
            },
        )

        await self.emit("run_stage", {"stage": "verify", "message": "Verifier agent is running delivery self-check..."})
        artifacts, verify_summary = await self._self_check_and_repair(
            task=task,
            artifacts=artifacts,
            framework=inferred_framework,
            ui_preset=ui_preset,
            task_guidance=task_guidance,
        )
        await self.emit("console_log", {"text": f"[self_check] {verify_summary}", "level": "default"})
        await self._save_checkpoint(
            stage="verify",
            payload={
                "plan": [p.__dict__ for p in plan],
                "framework": inferred_framework,
                "ui_preset": ui_preset.get("name"),
                "artifacts": [a.__dict__ for a in artifacts],
                "self_check": verify_summary,
            },
        )

        review_report, artifacts = await self._review_with_auto_rework(
            task=task,
            artifacts=artifacts,
            repo_map=repo_map,
            ast_context=ast_context,
            framework=inferred_framework,
            ui_preset=ui_preset,
            task_guidance=task_guidance,
            plan=plan,
        )
        review = review_report.notes
        review_status = review_report.status
        integration = self._validate_integration(plan=plan, artifacts=artifacts)
        prd_score = self._score_prd_delivery(
            framework=inferred_framework,
            plan=plan,
            artifacts=artifacts,
        )
        await self.emit("console_log", {"text": f"[integration] {integration}", "level": "default"})
        await self.emit(
            "prd_score",
            {
                "total": prd_score.get("total"),
                "verdict": prd_score.get("verdict"),
                "scores": prd_score.get("scores"),
            },
        )
        await self._save_checkpoint(
            stage="review",
            payload={
                "plan": [p.__dict__ for p in plan],
                "framework": inferred_framework,
                "ui_preset": ui_preset.get("name"),
                "artifacts": [a.__dict__ for a in artifacts],
                "review": review,
                "review_status": review_status,
                "integration": integration,
                "self_check": verify_summary,
                "prd_score": prd_score,
            },
        )

        return {
            "plan": [p.__dict__ for p in plan],
            "artifacts": [a.__dict__ for a in artifacts],
            "review": review,
            "integration": integration,
            "framework": inferred_framework,
            "ui_preset": ui_preset.get("name"),
            "self_check": verify_summary,
            "quality_gate": dict(self._last_quality_gate),
            "prd_score": prd_score,
            "ast_context_used": bool((ast_context or "").strip()),
            "ast_dep_links_added": int(ast_dep_stats.get("added_links", 0)),
            "budget": {
                "estimated_tokens": self.budget.estimated_tokens,
                "estimated_cost": round(self.budget.estimated_cost, 6),
                "calls": self.budget.calls,
                "max_token_budget": self.max_token_budget,
                "max_cost_budget": self.max_cost_budget,
            },
        }

    async def run_from_checkpoint(
        self,
        *,
        task: str,
        repo_map: str,
        ast_context: str,
        memory_hints: list[str],
        checkpoint: dict[str, Any],
        framework: str | None = None,
    ) -> dict[str, Any]:
        stage = self._normalize_checkpoint_stage(checkpoint.get("stage"))
        payload = checkpoint.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        self._restore_budget(checkpoint.get("budget"))

        plan = self._checkpoint_plan(payload.get("plan"))
        artifacts = self._checkpoint_artifacts(payload.get("artifacts"))
        if not plan and stage != "plan":
            await self.emit(
                "console_log",
                {"text": "[checkpoint] missing plan in checkpoint, falling back to full run", "level": "warning"},
            )
            return await self.run(
                task=task,
                repo_map=repo_map,
                ast_context=ast_context,
                memory_hints=memory_hints,
                framework=framework,
            )

        if framework and framework.strip().lower() not in {"", "general"}:
            inferred_framework = framework.strip().lower()
        else:
            inferred_framework = str(payload.get("framework") or "").strip().lower()
            if not inferred_framework:
                inferred_framework = self._infer_framework(task=task, plan=plan) if plan else "general"
        ui_preset = choose_ui_preset(task, inferred_framework)
        task_guidance = TaskTypeGuidance.infer(task)

        await self.emit(
            "console_log",
            {"text": f"[checkpoint] resuming from stage={stage}", "level": "info"},
        )
        await self.emit(
            "run_stage",
            {"stage": stage, "message": f"Resuming from checkpoint stage: {stage}"},
        )

        if stage == "plan":
            plan = await self._planner(
                task=task,
                repo_map=repo_map,
                ast_context=ast_context,
                memory_hints=memory_hints,
                framework=inferred_framework,
            )
            plan, _ = self._apply_ast_dependencies(plan=plan, ast_context=ast_context)
            await self._save_checkpoint(
                stage="plan",
                payload={
                    "framework": inferred_framework,
                    "plan_summary": self._plan_summary(plan),
                    "plan": [p.__dict__ for p in plan],
                },
            )

        if stage in {"plan", "implement"}:
            if not artifacts:
                await self.emit("run_stage", {"stage": "implement", "message": "Coder agents are generating files..."})
                artifacts = await self._coder(
                    task=task,
                    plan=plan,
                    repo_map=repo_map,
                    ast_context=ast_context,
                    memory_hints=memory_hints,
                    framework=inferred_framework,
                    ui_preset=ui_preset,
                    task_guidance=task_guidance,
                )
                await self._save_checkpoint(
                    stage="implement",
                    payload={
                        "plan": [p.__dict__ for p in plan],
                        "framework": inferred_framework,
                        "ui_preset": ui_preset.get("name"),
                        "artifacts": [a.__dict__ for a in artifacts],
                    },
                )

        verify_summary = str(payload.get("self_check") or "")
        if stage in {"plan", "implement", "verify"}:
            await self.emit("run_stage", {"stage": "verify", "message": "Verifier agent is running delivery self-check..."})
            artifacts, verify_summary = await self._self_check_and_repair(
                task=task,
                artifacts=artifacts,
                framework=inferred_framework,
                ui_preset=ui_preset,
                task_guidance=task_guidance,
            )
            await self._save_checkpoint(
                stage="verify",
                payload={
                    "plan": [p.__dict__ for p in plan],
                    "framework": inferred_framework,
                    "ui_preset": ui_preset.get("name"),
                    "artifacts": [a.__dict__ for a in artifacts],
                    "self_check": verify_summary,
                },
            )

        review_report, artifacts = await self._review_with_auto_rework(
            task=task,
            artifacts=artifacts,
            repo_map=repo_map,
            ast_context=ast_context,
            framework=inferred_framework,
            ui_preset=ui_preset,
            task_guidance=task_guidance,
            plan=plan,
        )
        review = review_report.notes
        review_status = review_report.status
        integration = self._validate_integration(plan=plan, artifacts=artifacts)
        prd_score = self._score_prd_delivery(
            framework=inferred_framework,
            plan=plan,
            artifacts=artifacts,
        )
        await self.emit(
            "prd_score",
            {
                "total": prd_score.get("total"),
                "verdict": prd_score.get("verdict"),
                "scores": prd_score.get("scores"),
            },
        )
        await self._save_checkpoint(
            stage="review",
            payload={
                "plan": [p.__dict__ for p in plan],
                "framework": inferred_framework,
                "ui_preset": ui_preset.get("name"),
                "artifacts": [a.__dict__ for a in artifacts],
                "review": review,
                "review_status": review_status,
                "integration": integration,
                "self_check": verify_summary,
                "prd_score": prd_score,
            },
        )
        return {
            "plan": [p.__dict__ for p in plan],
            "artifacts": [a.__dict__ for a in artifacts],
            "review": review,
            "integration": integration,
            "framework": inferred_framework,
            "ui_preset": ui_preset.get("name"),
            "self_check": verify_summary,
            "quality_gate": dict(self._last_quality_gate),
            "prd_score": prd_score,
            "ast_context_used": bool((ast_context or "").strip()),
            "ast_dep_links_added": 0,
            "budget": {
                "estimated_tokens": self.budget.estimated_tokens,
                "estimated_cost": round(self.budget.estimated_cost, 6),
                "calls": self.budget.calls,
                "max_token_budget": self.max_token_budget,
                "max_cost_budget": self.max_cost_budget,
            },
        }

    async def _planner(
        self,
        *,
        task: str,
        repo_map: str,
        ast_context: str,
        memory_hints: list[str],
        framework: str | None = None,
    ) -> list[PlannedFile]:
        task_guidance = TaskTypeGuidance.infer(task)
        fw = (framework or "general").strip().lower()
        is_general = fw in {"general", ""}
        
        # Log framework decision for debugging
        await self.emit("console_log", {"text": f"[planner] raw framework={framework}, normalized={fw}, is_general={is_general}", "level": "info"})
        
        if is_general:
            # General mode: let model decide the best framework
            framework_rules = (
                "GENERAL MODE: You decide the best technology stack.\n"
                "Choose the most appropriate framework based on the task requirements.\n"
                "Options: flutter (for mobile/desktop apps), react/vue (for web apps), "
                "python (for CLI/backend/games with pygame), html (for simple web pages)."
            )
            framework_header = "FRAMEWORK: Model's choice (general mode)"
        else:
            # Enforced framework: strict compliance required
            framework_rules = self._get_framework_plan_rules(fw)
            framework_header = f"MANDATORY FRAMEWORK: {fw.upper()} - ALL generated files MUST be for {fw} framework. DO NOT generate files for other frameworks."
        
        system = (
            "You are Planner Agent.\n"
            "Return JSON only.\n"
            "Schema: {\"prd\":{\"product_goal\":\"...\",\"target_user\":\"...\",\"core_user_journey\":[\"...\"],\"functional_scope\":[\"...\"],\"interaction_spec\":[\"...\"],\"state_model\":[\"...\"]},\"files\":[{\"path\":\"...\",\"description\":\"...\",\"deps\":[\"...\"]}],\"graph\":{\"path\":[\"dep1\",\"dep2\"]}}.\n"
            f"{framework_header}\n"
            f"{framework_rules}\n"
            "Rules:\n"
            "- must include runnable entry files and startup-critical files.\n"
            "- must ensure generated project is executable without asking user for extra choices.\n"
            "- deps are project-internal dependencies (path strings).\n"
            "- keep deps empty for independent files to maximize parallelism.\n"
            "- for games: MUST plan files for game logic, state management, input handling, and rendering.\n"
            "- for apps: MUST plan files for business logic, state management, and user interactions.\n"
            "- NEVER plan only static UI files - always include logic/interaction files.\n"
            "No markdown."
        )
        memory_context = "\n---\n".join(memory_hints[:4]).strip() or "No relevant memory."
        user = (
            build_structural_context(
                user_requirement=task,
                repo_map=repo_map,
                plan_summary="List project files and their dependencies.",
                context=memory_context,
            )
            + "\nAST_CONTEXT\n"
            + (ast_context or "No AST context.")
            + "\nGUIDANCE\n"
            + (
                "General requirement: runnable startup + responsive UI + no TODO placeholders + FULL INTERACTIVITY.\n"
                "For games: must include game state, input handling, game loop, win/lose conditions, score system.\n"
                "For apps: must include state management, event handlers, complete user flows.\n"
                f"Task guidance: {task_guidance.guidance}"
            )
            + "\n\n"
            + build_product_prd_contract(task=task, guidance=task_guidance.guidance)
        )
        raw = await self._planner_with_collaboration(system=system, user=user)
        parsed = self._parse_json_object(raw)
        out = self._to_plan_items(parsed)
        if not out:
            out = [PlannedFile(path="README.md", description="Project overview and run instructions.", deps=[])]
        return out

    async def _planner_with_collaboration(self, *, system: str, user: str) -> str:
        if not self.planner_collab_enabled:
            return await self._call_with_retry(system, user, tag="planner", role="planner")
        if self.role_llm_call is None:
            return await self._call_with_retry(system, user, tag="planner", role="planner")

        await self.emit(
            "console_log",
            {"text": "[planner] collaborative mode: planner + reviewer + merge", "level": "info"},
        )
        reviewer_system = (
            "You are Architecture Reviewer.\n"
            "Review the planner intent for production readiness and implementation risks.\n"
            "Return concise plain text with:\n"
            "- missing files\n"
            "- dependency/cycle risks\n"
            "- runtime and interaction gaps\n"
            "- concrete fixes\n"
            "No markdown."
        )
        planner_task = asyncio.create_task(
            self._call_with_retry(system, user, tag="planner.primary", role="planner")
        )
        reviewer_task = asyncio.create_task(
            self._call_with_retry(reviewer_system, user, tag="planner.reviewer", role="reviewer")
        )
        planner_res, reviewer_res = await asyncio.gather(
            planner_task,
            reviewer_task,
            return_exceptions=True,
        )
        if isinstance(planner_res, Exception):
            raise RuntimeError(f"planner.primary failed: {planner_res}")
        primary_raw = str(planner_res)
        reviewer_feedback = "" if isinstance(reviewer_res, Exception) else str(reviewer_res)
        if not reviewer_feedback.strip():
            return primary_raw

        merge_user = (
            "ORIGINAL_USER_CONTEXT:\n"
            f"{user}\n\n"
            "PRIMARY_PLANNER_OUTPUT:\n"
            f"{primary_raw}\n\n"
            "REVIEWER_FEEDBACK:\n"
            f"{reviewer_feedback}\n\n"
            "Produce FINAL planner JSON that strictly follows required schema."
        )
        return await self._call_with_retry(system, merge_user, tag="planner.merge", role="planner")

    def _to_plan_items(self, parsed: dict[str, Any]) -> list[PlannedFile]:
        files = parsed.get("files") if isinstance(parsed, dict) else None
        graph = parsed.get("graph") if isinstance(parsed, dict) else None
        graph_map: dict[str, list[str]] = {}
        if isinstance(graph, dict):
            for k, v in graph.items():
                p = str(k or "").strip().replace("\\", "/")
                if not p:
                    continue
                deps: list[str] = []
                if isinstance(v, list):
                    for d in v:
                        ds = str(d or "").strip().replace("\\", "/")
                        if ds:
                            deps.append(ds)
                graph_map[p] = deps
        out: list[PlannedFile] = []
        seen: set[str] = set()
        if isinstance(files, list):
            for item in files:
                if not isinstance(item, dict):
                    continue
                p = str(item.get("path", "")).strip().replace("\\", "/")
                d = str(item.get("description", "")).strip()
                deps: list[str] = []
                raw_deps = item.get("deps")
                if isinstance(raw_deps, list):
                    for dep in raw_deps:
                        ds = str(dep or "").strip().replace("\\", "/")
                        if ds:
                            deps.append(ds)
                if p in graph_map:
                    deps = graph_map[p]
                if p and p not in seen:
                    out.append(PlannedFile(path=p, description=d, deps=deps))
                    seen.add(p)
        return out

    def _plan_summary(self, plan: list[PlannedFile]) -> str:
        return "\n".join(f"{idx+1}. {p.path}: {p.description or 'No description'}" for idx, p in enumerate(plan))

    def _apply_ast_dependencies(self, *, plan: list[PlannedFile], ast_context: str) -> tuple[list[PlannedFile], dict[str, Any]]:
        if not plan or not (ast_context or "").strip():
            return plan, {"added_links": 0, "touched_files": 0, "added_edges": []}
        defs_by_name, refs_by_path = self._parse_ast_context(ast_context)
        if not defs_by_name or not refs_by_path:
            return plan, {"added_links": 0, "touched_files": 0, "added_edges": []}

        plan_paths = {self._norm_path(p.path) for p in plan if p.path}
        dep_map: dict[str, set[str]] = {
            self._norm_path(p.path): {self._norm_path(d) for d in p.deps if d}
            for p in plan
            if p.path
        }

        added_links = 0
        touched_files = 0
        added_edges: list[str] = []
        out: list[PlannedFile] = []
        for item in plan:
            pth = self._norm_path(item.path)
            if not pth:
                out.append(item)
                continue
            refs = refs_by_path.get(pth, set())
            existing = set(dep_map.get(pth, set()))
            next_deps = list(item.deps)
            changed = False
            for name in refs:
                defs = defs_by_name.get(name, set())
                for dep in defs:
                    if dep == pth or dep not in plan_paths:
                        continue
                    if dep in existing:
                        continue
                    # Skip direct two-node cycles: A->B if B already depends on A.
                    if pth in dep_map.get(dep, set()):
                        continue
                    existing.add(dep)
                    next_deps.append(dep)
                    added_links += 1
                    added_edges.append(f"{pth}->{dep}")
                    changed = True
            if changed:
                touched_files += 1
            out.append(PlannedFile(path=item.path, description=item.description, deps=next_deps))
        return out, {"added_links": added_links, "touched_files": touched_files, "added_edges": added_edges}

    def _parse_ast_context(self, ast_context: str) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        text = ast_context or ""
        if "<ast_index" not in text:
            return {}, {}
        sym_re = re.compile(
            r'<symbol\s+path="([^"]+)"[^>]*>([^<]+)</symbol>',
            flags=re.IGNORECASE,
        )
        ref_re = re.compile(
            r'<ref\s+path="([^"]+)"[^>]*>([^<]+)</ref>',
            flags=re.IGNORECASE,
        )
        defs_by_name: dict[str, set[str]] = {}
        refs_by_path: dict[str, set[str]] = {}
        for m in sym_re.finditer(text):
            path = self._norm_path(m.group(1))
            name = (m.group(2) or "").strip()
            if not path or not name:
                continue
            defs_by_name.setdefault(name, set()).add(path)
        for m in ref_re.finditer(text):
            path = self._norm_path(m.group(1))
            name = (m.group(2) or "").strip()
            if not path or not name:
                continue
            refs_by_path.setdefault(path, set()).add(name)
        return defs_by_name, refs_by_path

    def _norm_path(self, path: str) -> str:
        return str(path or "").strip().replace("\\", "/").lstrip("./")

    def _count_plan_edges(self, plan: list[PlannedFile]) -> int:
        total = 0
        for item in plan:
            total += len([d for d in item.deps if str(d or "").strip()])
        return total

    async def _coder(
        self,
        *,
        task: str,
        plan: list[PlannedFile],
        repo_map: str,
        ast_context: str,
        memory_hints: list[str],
        framework: str,
        ui_preset: dict[str, Any],
        task_guidance: "TaskTypeGuidance",
    ) -> list[GeneratedArtifact]:
        sem = asyncio.Semaphore(self.max_workers)
        results: dict[str, GeneratedArtifact] = {}
        lock = asyncio.Lock()
        guardrails = self._runtime_guardrails(framework=framework, ui_preset=ui_preset, task_guidance=task_guidance)
        is_general = framework in {"general", ""}

        async def _one(item: PlannedFile) -> None:
            path = str(item.path or "").strip()
            if not path:
                return
            await self.emit("file_generating", {"path": path, "status": "writing"})
            async with sem:
                if is_general:
                    framework_instruction = "GENERAL MODE: Generate code using the most appropriate technology for this file."
                else:
                    framework_instruction = f"MANDATORY FRAMEWORK: {framework.upper()} - You MUST generate {framework} code ONLY. Do NOT use any other framework."
                system = (
                    "You are Coder Agent.\n"
                    f"{framework_instruction}\n"
                    f"{build_product_prd_contract(task=task, guidance=task_guidance.guidance)}\n"
                    "Generate complete file content only.\n"
                    "The output must be runnable and functionally working.\n"
                    "Do not ask user to choose options.\n"
                    "CRITICAL REQUIREMENTS:\n"
                    "- For games: implement COMPLETE game logic (game loop, input handling, state, win/lose, score, restart).\n"
                    "- For apps: implement COMPLETE business logic (state management, event handlers, user flows).\n"
                    "- NEVER generate static UI without interaction handlers.\n"
                    "- Every button/touch target MUST have a working handler.\n"
                    "- The result must be immediately playable/usable, not a mockup.\n"
                    "No markdown code fences."
                )
                user = (
                    f"TASK:\n{task}\n\n"
                    f"TARGET_FILE: {path}\n"
                    f"DESCRIPTION: {item.description}\n"
                    f"DEPENDENCIES: {', '.join(item.deps) if item.deps else 'none'}\n\n"
                    f"RUNTIME_GUARDRAILS:\n{guardrails}\n\n"
                    f"REPO_MAP:\n{repo_map}\n\n"
                    f"AST_CONTEXT:\n{ast_context or 'No AST context.'}\n\n"
                    f"MEMORY_HINTS:\n" + "\n---\n".join(memory_hints[:4])
                )
                content = await self._call_with_retry(system, user, tag=f"coder:{path}", role="coder")
                content = self._strip_code_fences(content)
                artifact = GeneratedArtifact(path=path, description=item.description, content=content)
                lint_ok, lint_msg = self._lint_artifact(artifact)
                await self.emit(
                    "console_log",
                    {
                        "text": f"[lint] {path}: {lint_msg}",
                        "level": "success" if lint_ok else "warning",
                    },
                )
                await self.emit("file_done", {"path": path, "status": "done", "content": content})
                async with lock:
                    results[path] = artifact
                    done_count = len(results)
                    pending_count = max(0, total - done_count)
                    current_wave = wave
                    generated_paths = sorted(results.keys())[:400]
                await self.emit(
                    "run_progress",
                    (
                        f"Coder file done ({path}): "
                        f"completed={done_count}/{total}, pending={pending_count}, wave={current_wave}"
                    ),
                )
                await self._save_checkpoint(
                    stage="implement",
                    payload={
                        "coder_wave": current_wave,
                        "coder_completed": done_count,
                        "coder_total": total,
                        "coder_pending": pending_count,
                        "last_completed_file": path,
                        "generated_paths": generated_paths,
                    },
                )

        pending: dict[str, PlannedFile] = {p.path: p for p in plan if p.path}
        completed: set[str] = set()
        wave = 0
        total = len(pending)

        while pending:
            wave += 1
            ready: list[PlannedFile] = []
            for pth, item in list(pending.items()):
                deps = {d for d in item.deps if d in pending or d in completed}
                if deps.issubset(completed):
                    ready.append(item)
            if not ready:
                cycle_break = next(iter(pending.values()))
                await self.emit(
                    "console_log",
                    {"text": f"[deps] cycle or unresolved deps detected, forcing: {cycle_break.path}", "level": "warning"},
                )
                ready = [cycle_break]
            await self.emit(
                "run_progress",
                f"Coder wave {wave} starting: ready={len(ready)}, completed={len(completed)}, pending={len(pending)}",
            )
            await asyncio.gather(*(_one(i) for i in ready))
            for item in ready:
                completed.add(item.path)
                pending.pop(item.path, None)
            await self.emit(
                "run_progress",
                f"Coder wave {wave} done: completed={len(completed)}/{total}, pending={len(pending)}",
            )
            await self._save_checkpoint(
                stage="implement",
                payload={
                    "coder_wave": wave,
                    "coder_completed": len(completed),
                    "coder_total": total,
                    "coder_pending": len(pending),
                    "generated_paths": sorted(results.keys())[:400],
                },
            )

        ordered: list[GeneratedArtifact] = []
        for p in plan:
            art = results.get(p.path)
            if art is not None:
                ordered.append(art)
        return ordered

    async def _review_plan(
        self,
        *,
        task: str,
        plan: list[PlannedFile],
        repo_map: str,
        guidance: TaskTypeGuidance,
    ) -> tuple[bool, str]:
        plan_summary = self._plan_summary(plan)
        current_task = plan[0].description if plan else task
        plan_status = build_plan_status(
            plan_summary=plan_summary,
            current_task=current_task,
            guidance=guidance.guidance,
            current_task_code=(plan[0].description if plan else ""),
            current_task_result="pending",
        )
        review_text, confirmed = await AskReviewHelper.run(
            context=plan_status,
            plan_summary=plan_summary,
            trigger=ReviewConst.TASK_REVIEW_TRIGGER,
        )
        return confirmed, review_text

    async def _reviewer(
        self,
        *,
        task: str,
        artifacts: list[GeneratedArtifact],
        repo_map: str,
        ast_context: str,
        framework: str,
        ui_preset: dict[str, Any],
    ) -> ReviewReport:
        summary = "\n".join(f"- {a.path} ({len(a.content)} chars)" for a in artifacts[:80])
        system = (
            "You are Reviewer Agent.\n"
            "Review executable readiness, responsive adaptation quality, and UI consistency.\n"
            "Return JSON only.\n"
            "Schema: {\"status\":\"ok|warn|fail\",\"scores\":{\"executable\":0-100,\"responsive\":0-100,\"ui_consistency\":0-100,\"interaction\":0-100},\"summary\":\"...\",\"notes\":\"...\",\"blocking_issues\":[\"...\"]}.\n"
            "Set status=fail when executable score < 70 or blocking issues exist."
        )
        user = (
            f"TASK:\n{task}\n\n"
            f"FRAMEWORK:{framework}\n"
            f"UI_PRESET:{ui_preset.get('name')}\n\n"
            f"FILES:\n{summary}\n\nREPO_MAP:\n{repo_map}\n"
            f"\nAST_CONTEXT:\n{ast_context or 'No AST context.'}\n"
            f"\n{build_product_prd_contract(task=task, guidance='review for product readiness')}\n"
        )
        raw = await self._call_with_retry(system, user, tag="reviewer", role="reviewer")
        parsed = self._parse_json_object(raw)
        if not parsed:
            return ReviewReport(
                status="fail",
                notes="reviewer_response_not_json",
                scores={},
                blocking_issues=["reviewer did not return valid JSON"],
            )
        status = str(parsed.get("status", "ok")).strip().lower()
        summary = str(parsed.get("summary", "")).strip()
        notes = str(parsed.get("notes", "")).strip() or summary
        scores_raw = parsed.get("scores")
        scores: dict[str, int] = {}
        if isinstance(scores_raw, dict):
            for k, v in scores_raw.items():
                try:
                    scores[str(k)] = int(v)
                except Exception:
                    continue
        blocking_raw = parsed.get("blocking_issues")
        blocking_issues = []
        if isinstance(blocking_raw, list):
            blocking_issues = [str(x).strip() for x in blocking_raw if str(x).strip()]
        if scores:
            notes = f"scores={scores} | {notes}"
        if not status:
            status = "ok"
        return ReviewReport(
            status=status,
            notes=notes or raw,
            scores=scores,
            blocking_issues=blocking_issues,
        )

    async def _review_with_auto_rework(
        self,
        *,
        task: str,
        artifacts: list[GeneratedArtifact],
        repo_map: str,
        ast_context: str,
        framework: str,
        ui_preset: dict[str, Any],
        task_guidance: TaskTypeGuidance,
        plan: list[PlannedFile],
    ) -> tuple[ReviewReport, list[GeneratedArtifact]]:
        current = artifacts
        await self.emit("run_stage", {"stage": "review", "message": "Reviewer agent is checking outputs..."})
        report = await self._reviewer(
            task=task,
            artifacts=current,
            repo_map=repo_map,
            ast_context=ast_context,
            framework=framework,
            ui_preset=ui_preset,
        )

        max_cycles = max(1, min(self.retries + 1, 3))
        auto_reworks = 0
        triggers: list[str] = []
        last_integration = "unknown"
        history: list[dict[str, Any]] = []
        for cycle in range(max_cycles):
            integration = self._validate_integration(plan=plan, artifacts=current)
            last_integration = integration
            needs_rework, reasons = self._needs_rework(report, integration)
            history.append(
                {
                    "cycle": cycle + 1,
                    "status": report.status,
                    "integration": integration,
                    "reasons": reasons,
                }
            )
            if not needs_rework:
                self._last_quality_gate = {
                    "cycles": cycle + 1,
                    "auto_reworks": auto_reworks,
                    "final_status": report.status,
                    "final_integration": integration,
                    "triggers": triggers,
                    "history": history,
                }
                await self.emit("quality_gate_report", dict(self._last_quality_gate))
                return report, current

            await self.emit(
                "console_log",
                {
                    "text": (
                        f"[quality_gate] cycle={cycle + 1}/{max_cycles} status={report.status} "
                        f"integration={integration}. Auto rework triggered."
                    ),
                    "level": "warning",
                },
            )
            auto_reworks += 1
            triggers.extend([f"cycle{cycle + 1}:{r}" for r in reasons])
            current, verify_summary = await self._self_check_and_repair(
                task=task,
                artifacts=current,
                framework=framework,
                ui_preset=ui_preset,
                task_guidance=task_guidance,
            )
            await self.emit("console_log", {"text": f"[quality_gate] repair={verify_summary}", "level": "default"})
            report = await self._reviewer(
                task=task,
                artifacts=current,
                repo_map=repo_map,
                ast_context=ast_context,
                framework=framework,
                ui_preset=ui_preset,
            )

        await self.emit(
            "console_log",
            {
                "text": f"[quality_gate] exhausted auto rework cycles; final_status={report.status}",
                "level": "warning",
            },
        )
        self._last_quality_gate = {
            "cycles": max_cycles,
            "auto_reworks": auto_reworks,
            "final_status": report.status,
            "final_integration": last_integration,
            "triggers": triggers,
            "history": history,
        }
        await self.emit("quality_gate_report", dict(self._last_quality_gate))
        return report, current

    def _needs_rework(self, report: ReviewReport, integration: str) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if report.status == "fail":
            reasons.append("review_status_fail")
        if report.blocking_issues:
            reasons.append("blocking_issues_present")
        if report.scores.get("executable", 100) < 70:
            reasons.append("score_executable_lt_70")
        if report.scores.get("interaction", 100) < 65:
            reasons.append("score_interaction_lt_65")
        if report.status == "warn" and report.scores.get("responsive", 100) < 60:
            reasons.append("score_responsive_lt_60_on_warn")
        if not integration.startswith("ok "):
            reasons.append("integration_not_ok")
        return (len(reasons) > 0, reasons)

    async def _self_check_and_repair(
        self,
        *,
        task: str,
        artifacts: list[GeneratedArtifact],
        framework: str,
        ui_preset: dict[str, Any],
        task_guidance: TaskTypeGuidance,
    ) -> tuple[list[GeneratedArtifact], str]:
        issues = self._diagnose_artifacts(
            artifacts=artifacts,
            framework=framework,
            task_guidance=task_guidance,
        )
        if not issues:
            return artifacts, "pass:0_issue"

        await self.emit("console_log", {"text": f"[self_check] detected {len(issues)} issue(s)", "level": "warning"})
        by_path: dict[str, GeneratedArtifact] = {a.path: a for a in artifacts}
        for issue in issues:
            path = issue.get("path")
            if not path or path not in by_path:
                continue
            target = by_path[path]
            patched = await self._repair_single_artifact(
                task=task,
                framework=framework,
                ui_preset=ui_preset,
                artifact=target,
                issue=issue,
                all_artifacts=by_path,
            )
            by_path[path] = patched
            await self.emit("file_done", {"path": patched.path, "status": "done", "content": patched.content})

        repaired = [by_path[a.path] for a in artifacts if a.path in by_path]
        remain = self._diagnose_artifacts(artifacts=repaired, framework=framework)
        if remain:
            return repaired, f"warn:remain={len(remain)} repaired={len(issues)-len(remain)}"
        return repaired, f"pass:repaired={len(issues)}"

    async def _repair_single_artifact(
        self,
        *,
        task: str,
        framework: str,
        ui_preset: dict[str, Any],
        artifact: GeneratedArtifact,
        issue: dict[str, str],
        all_artifacts: dict[str, GeneratedArtifact],
    ) -> GeneratedArtifact:
        # Build context from related files for cross-file issues
        related_context = ""
        issue_reason = issue.get("reason", "")
        if "undefined type" in issue_reason or "undefined parameter" in issue_reason or "widget" in issue_reason:
            # Include other dart files for context
            for path, art in all_artifacts.items():
                if path != artifact.path and path.lower().endswith(".dart"):
                    # Truncate content to avoid context overflow
                    content_preview = art.content[:2000] if art.content else ""
                    related_context += f"\n--- FILE: {path} ---\n{content_preview}\n"
            if len(related_context) > 8000:
                related_context = related_context[:8000] + "\n... (truncated)"
        
        system = (
            "You are Fix Agent.\n"
            "Rewrite the full file content so the issue is fixed.\n"
            "If the issue is about an undefined type or widget, you may need to:\n"
            "  1. Define the missing class in this file, OR\n"
            "  2. Add the correct import statement, OR\n"
            "  3. Fix the type annotation to match an existing class\n"
            "If the issue is about widget parameters, check the widget definition and fix the call.\n"
            "Keep behavior correct and executable.\n"
            "No markdown code fences."
        )
        user = (
            f"TASK:\n{task}\n\n"
            f"FRAMEWORK:{framework}\n"
            f"UI_PRESET:{ui_preset.get('name')}\n"
            f"TARGET_FILE:{artifact.path}\n"
            f"ISSUE:{issue_reason}\n"
            f"ALL_PROJECT_FILES:{list(all_artifacts.keys())[:100]}\n\n"
            f"RELATED_FILES:\n{related_context}\n\n"
            f"CURRENT_CONTENT:\n{artifact.content}\n"
        )
        fixed = await self._call_with_retry(system, user, tag=f"fix:{artifact.path}", role="fixer")
        fixed = self._strip_code_fences(fixed)
        return GeneratedArtifact(path=artifact.path, description=artifact.description, content=fixed)

    async def _call_with_retry(self, system: str, user: str, *, tag: str, role: str) -> str:
        last = ""
        for attempt in range(self.retries + 1):
            try:
                await self._emit_bus(
                    role=role,
                    cause_by=f"{tag}:attempt:{attempt + 1}",
                    content="starting llm call",
                    send_to="llm",
                )
                text = await asyncio.wait_for(
                    self._invoke_llm(role=role, system=system, user=user),
                    timeout=self.llm_call_timeout_s,
                )
                await self._emit_bus(
                    role=role,
                    cause_by=f"{tag}:success",
                    content=f"response_chars={len(text)}",
                    send_to="scheduler",
                )
                return text
            except asyncio.TimeoutError:
                last = f"timeout after {int(self.llm_call_timeout_s)}s"
                await self.emit("console_log", {"text": f"[{tag}] timeout: {last}", "level": "warning"})
                await self._emit_bus(
                    role=role,
                    cause_by=f"{tag}:timeout",
                    content=last,
                    send_to="scheduler",
                )
            except Exception as exc:
                last = str(exc)
                await self.emit("console_log", {"text": f"[{tag}] retry {attempt + 1} failed: {last}", "level": "warning"})
                await self._emit_bus(
                    role=role,
                    cause_by=f"{tag}:error",
                    content=last[:240],
                    send_to="scheduler",
                )
                await asyncio.sleep(min(1.2 * (attempt + 1), 4.0))
        raise RuntimeError(f"{tag} failed after retries: {last}")

    async def _invoke_llm(self, *, role: str, system: str, user: str) -> str:
        if self.role_llm_call is not None:
            text = await self.role_llm_call(role, system, user)
        else:
            text = await self.llm_call(system, user)
        self._consume_budget(system=system, user=user, output=text)
        return text

    def _consume_budget(self, *, system: str, user: str, output: str) -> None:
        in_tokens = max(1, (len(system) + len(user)) // 4)
        out_tokens = max(1, len(output) // 4)
        total = in_tokens + out_tokens
        self.budget.estimated_tokens += total
        self.budget.calls += 1
        # Coarse cost estimate for guardrail only.
        self.budget.estimated_cost += (in_tokens * 0.5 + out_tokens * 1.5) / 1_000_000
        if self.max_token_budget is not None and self.budget.estimated_tokens > self.max_token_budget:
            raise RuntimeError(
                f"token_budget_exceeded:{self.budget.estimated_tokens}>{self.max_token_budget}"
            )
        if self.max_cost_budget is not None and self.budget.estimated_cost > self.max_cost_budget:
            raise RuntimeError(
                f"cost_budget_exceeded:{self.budget.estimated_cost:.6f}>{self.max_cost_budget:.6f}"
            )

    async def _emit_bus(
        self,
        *,
        role: str,
        cause_by: str,
        content: str,
        send_to: str,
    ) -> None:
        payload = {
            "run_id": self.run_id,
            "role": role,
            "cause_by": cause_by,
            "send_to": send_to,
            "content": content,
            "ts": time.time(),
        }
        await self.emit("agent_bus", payload)

    async def _save_checkpoint(self, *, stage: str, payload: dict[str, Any]) -> None:
        if self.checkpoint_dir is None:
            return
        try:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            target = self.checkpoint_dir / f"{self.run_id}.json"
            snap = {
                "run_id": self.run_id,
                "stage": stage,
                "updated_at": time.time(),
                "budget": {
                    "estimated_tokens": self.budget.estimated_tokens,
                    "estimated_cost": self.budget.estimated_cost,
                    "calls": self.budget.calls,
                },
                "payload": payload,
            }
            target.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
            await self.emit("checkpoint_saved", {"stage": stage, "path": str(target)})
        except Exception as exc:
            await self.emit("console_log", {"text": f"[checkpoint] save failed: {exc}", "level": "warning"})

    def _normalize_checkpoint_stage(self, stage: Any) -> str:
        value = str(stage or "").strip().lower()
        if value in {"plan", "implement", "verify", "review"}:
            return value
        return "plan"

    def _checkpoint_plan(self, raw: Any) -> list[PlannedFile]:
        out: list[PlannedFile] = []
        if not isinstance(raw, list):
            return out
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip().replace("\\", "/")
            if not path:
                continue
            desc = str(item.get("description") or "")
            deps: list[str] = []
            raw_deps = item.get("deps")
            if isinstance(raw_deps, list):
                for dep in raw_deps:
                    d = str(dep or "").strip().replace("\\", "/")
                    if d:
                        deps.append(d)
            out.append(PlannedFile(path=path, description=desc, deps=deps))
        return out

    def _checkpoint_artifacts(self, raw: Any) -> list[GeneratedArtifact]:
        out: list[GeneratedArtifact] = []
        if not isinstance(raw, list):
            return out
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip().replace("\\", "/")
            if not path:
                continue
            out.append(
                GeneratedArtifact(
                    path=path,
                    description=str(item.get("description") or ""),
                    content=str(item.get("content") or ""),
                )
            )
        return out

    def _restore_budget(self, raw: Any) -> None:
        if not isinstance(raw, dict):
            return
        try:
            self.budget.estimated_tokens = max(0, int(raw.get("estimated_tokens") or 0))
        except Exception:
            self.budget.estimated_tokens = 0
        try:
            self.budget.estimated_cost = max(0.0, float(raw.get("estimated_cost") or 0.0))
        except Exception:
            self.budget.estimated_cost = 0.0
        try:
            self.budget.calls = max(0, int(raw.get("calls") or 0))
        except Exception:
            self.budget.calls = 0

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        raw = self._strip_code_fences(text).strip()
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        return {}

    def _strip_code_fences(self, text: str) -> str:
        raw = (text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return raw.strip()

    def _lint_artifact(self, artifact: GeneratedArtifact) -> tuple[bool, str]:
        path = artifact.path.lower()
        content = artifact.content or ""
        if not content.strip():
            return False, "empty content"
        try:
            if path.endswith(".json"):
                json.loads(content)
                return True, "json ok"
            if path.endswith(".py"):
                ast.parse(content)
                return True, "python ast ok"
            if path.endswith(".md") or path.endswith(".txt"):
                return True, "text file"
            return True, "basic check ok"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _validate_integration(self, *, plan: list[PlannedFile], artifacts: list[GeneratedArtifact]) -> str:
        generated = {a.path for a in artifacts}
        missing = [p.path for p in plan if p.path not in generated]
        bad_deps: list[str] = []
        for p in plan:
            for d in p.deps:
                if d not in generated:
                    bad_deps.append(f"{p.path}->{d}")
        if missing or bad_deps:
            return f"missing_files={len(missing)}, unresolved_deps={len(bad_deps)}"
        return f"ok files={len(generated)}"

    def _score_prd_delivery(
        self,
        *,
        framework: str,
        plan: list[PlannedFile],
        artifacts: list[GeneratedArtifact],
    ) -> dict[str, Any]:
        planned_paths = {p.path.strip().replace("\\", "/") for p in plan if p.path.strip()}
        generated_paths = {a.path.strip().replace("\\", "/") for a in artifacts if a.path.strip()}
        if not planned_paths:
            file_cov = 100.0 if generated_paths else 0.0
        else:
            file_cov = (len(planned_paths & generated_paths) / max(len(planned_paths), 1)) * 100.0

        names = {Path(p).name.lower() for p in generated_paths}
        entry_required = {
            "flutter": {"pubspec.yaml", "main.dart"},
            "react": {"package.json", "index.html"},
            "nextjs": {"package.json"},
            "python": {"main.py"},
            "html": {"index.html"},
        }.get((framework or "").strip().lower(), set())
        if not entry_required:
            entry_score = 100.0
        else:
            hit = 0
            for req in entry_required:
                if req in names:
                    hit += 1
            entry_score = (hit / max(len(entry_required), 1)) * 100.0

        corpus = "\n".join((a.content or "").lower() for a in artifacts[:200])
        interaction_signals = ("onclick", "ontap", "onpressed", "addEventListener", "gesturedetector", "setstate")
        responsive_signals = ("layoutbuilder", "mediaquery", "@media", "breakpoint", "responsive", "flex", "grid")
        visual_signals = ("theme", "color", "typography", "spacing", "radius", "boxshadow")
        placeholder_signals = ("todo", "tbd", "placeholder", "coming soon", "mock data")

        interaction = 100.0 if any(s.lower() in corpus for s in interaction_signals) else 45.0
        responsive = 100.0 if any(s.lower() in corpus for s in responsive_signals) else 55.0
        visual = 100.0 if any(s.lower() in corpus for s in visual_signals) else 55.0
        placeholder_hits = sum(corpus.count(s) for s in placeholder_signals)
        hygiene = max(0.0, 100.0 - min(float(placeholder_hits * 8), 72.0))

        total = (
            file_cov * 0.30
            + entry_score * 0.20
            + interaction * 0.20
            + (0.6 * responsive + 0.4 * visual) * 0.15
            + hygiene * 0.15
        )
        verdict = "pass" if total >= 80 else ("warn" if total >= 65 else "fail")
        return {
            "scores": {
                "file_coverage": round(file_cov, 2),
                "runtime_entry": round(entry_score, 2),
                "interaction": round(interaction, 2),
                "ux_design": round((0.6 * responsive + 0.4 * visual), 2),
                "hygiene": round(hygiene, 2),
            },
            "placeholder_hits": int(placeholder_hits),
            "total": round(total, 2),
            "verdict": verdict,
        }

    def _get_framework_plan_rules(self, framework: str) -> str:
        """Return framework-specific planning rules to ensure correct file structure."""
        rules: dict[str, str] = {
            "flutter": (
                "FLUTTER PROJECT REQUIREMENTS:\n"
                "- MUST include pubspec.yaml with flutter dependency\n"
                "- MUST include lib/main.dart as entry point\n"
                "- All UI code MUST be in .dart files under lib/\n"
                "- Use StatefulWidget for interactive components\n"
                "- CRITICAL: Plan ALL model/logic classes as separate files (e.g., lib/models/game_logic.dart)\n"
                "- Every custom class used must have a corresponding file that defines it\n"
                "- For games: plan files for game_logic.dart, game_state.dart in lib/models/\n"
                "- NEVER generate HTML/CSS/JS files for Flutter projects"
            ),
            "react": (
                "REACT PROJECT REQUIREMENTS:\n"
                "- MUST include package.json with react dependency\n"
                "- MUST include src/index.js or src/index.tsx as entry point\n"
                "- MUST include public/index.html for mounting React app\n"
                "- Use .jsx/.tsx files for React components"
            ),
            "vue": (
                "VUE PROJECT REQUIREMENTS:\n"
                "- MUST include package.json with vue dependency\n"
                "- MUST include src/main.js and src/App.vue\n"
                "- Use .vue files for Vue components"
            ),
            "python": (
                "PYTHON PROJECT REQUIREMENTS:\n"
                "- MUST include main.py or __main__.py as entry point\n"
                "- For games: use pygame or similar library\n"
                "- Include requirements.txt for dependencies"
            ),
            "uniapp": (
                "UNIAPP PROJECT REQUIREMENTS:\n"
                "- MUST include pages.json for page configuration\n"
                "- MUST include manifest.json for app config\n"
                "- Use .vue files for pages under pages/"
            ),
            "miniprogram": (
                "MINIPROGRAM PROJECT REQUIREMENTS:\n"
                "- MUST include app.json, app.js, app.wxss\n"
                "- Each page needs .wxml, .wxss, .js, .json files\n"
                "- Use pages/ directory for page components"
            ),
            "html": (
                "HTML/CSS/JS PROJECT REQUIREMENTS:\n"
                "- MUST include index.html as entry point\n"
                "- Include .css for styles, .js for logic\n"
                "- Ensure all paths are relative"
            ),
        }
        return rules.get(framework, rules["html"])

    def _infer_framework(self, *, task: str, plan: list[PlannedFile]) -> str:
        text = (task or "").lower()
        paths = [p.path.lower() for p in plan]
        names = {Path(p).name.lower() for p in paths}
        if "pubspec.yaml" in names or any(p.endswith("/main.dart") for p in paths):
            return "flutter"
        if "next.config.js" in names or "nextjs" in text or "next.js" in text:
            return "nextjs"
        if "pages.json" in names or "manifest.json" in names or "uniapp" in text:
            return "uniapp"
        if "package.json" in names or "react" in text or "vue" in text:
            return "react"
        if "html" in text or "css" in text or "javascript" in text:
            return "html"
        return "html"

    def _runtime_guardrails(self, *, framework: str, ui_preset: dict[str, Any], task_guidance: TaskTypeGuidance) -> str:
        common = [
            "Generated code must run successfully after write.",
            "No TODO/TBD placeholders in final content.",
            "Do not leave undefined identifiers or missing imports.",
            "If web UI is generated, prefer responsive units (%, rem, vw, vh, clamp) over fixed px.",
            "Support desktop/mobile/tablet layout adaptation.",
            "All interactive elements MUST have working event handlers - never leave empty stubs.",
            "For games: must include complete game logic, win/lose conditions, score tracking, and restart capability.",
            "For apps: must include complete state management and user interaction flows.",
        ]
        fw_rules: list[str] = []
        if framework in {"html", "react", "nextjs", "uniapp"}:
            fw_rules = [
                "Must include valid runnable entrypoint (index.html or package.json scripts).",
                "Ensure script/style paths are relative and loadable.",
                "CSS must include responsive breakpoints or flexible layout (flex/grid + relative units).",
                "JavaScript must include event listeners (addEventListener) for all interactive elements.",
                "For games: use requestAnimationFrame for game loop, implement keyboard/mouse/touch input handling.",
                "Never generate static HTML mockups - all UI must respond to user input.",
            ]
        elif framework == "flutter":
            fw_rules = [
                "Must include lib/main.dart and runnable widget tree.",
                "All custom classes/models referenced must be DEFINED in project files or IMPORTED correctly.",
                "CRITICAL: If you use a type like 'GameLogic', you MUST either define it or import it.",
                "Use LayoutBuilder/MediaQuery/Flexible/Expanded for adaptation.",
                "Avoid hard-coded fixed dimensions where not necessary.",
                "Use StatefulWidget with setState for interactive state changes.",
                "Widget constructor named parameters must match usage (if you call Widget(label: x), the Widget must have 'label' param).",
                "Include GestureDetector/InkWell for tap/swipe handling.",
                "For games: use Timer.periodic or AnimationController for game loop, implement touch input handling.",
                "Never generate static UI - all interactive elements must have onTap/onPressed handlers.",
            ]
        elif framework == "python":
            fw_rules = [
                "Must include runnable entry script (main.py or __main__.py).",
                "For games: use pygame or similar with event loop, keyboard/mouse handling, and rendering.",
                "For CLI: implement argparse and interactive prompts where appropriate.",
            ]
        elif framework in {"general", ""}:
            fw_rules = [
                "GENERAL MODE: Choose the most appropriate technology stack.",
                "Ensure the chosen framework has proper entry points.",
                "All code must be runnable without additional configuration.",
            ]
        preset_rules = [str(x) for x in (ui_preset.get("rules") or [])]
        guidance_rule = f"Task-specific guidance: {task_guidance.guidance}" if task_guidance else ""
        return "\n".join(
            f"- {r}"
            for r in [*common, *fw_rules, *preset_rules, guidance_rule]
            if r
        )

    def _diagnose_artifacts(
        self,
        *,
        artifacts: list[GeneratedArtifact],
        framework: str,
        task_guidance: TaskTypeGuidance | None = None,
    ) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        by_path = {a.path.lower(): a for a in artifacts}
        names = {Path(p).name.lower() for p in by_path}

        if framework in {"html", "react", "nextjs", "uniapp"}:
            if "index.html" not in names and "package.json" not in names:
                issues.append({"path": "", "reason": "missing runnable web entrypoint (index.html or package.json)"})
        if framework == "flutter":
            if "pubspec.yaml" not in names and "main.dart" not in names:
                issues.append({"path": "", "reason": "missing flutter entrypoint (pubspec.yaml/lib/main.dart)"})

        placeholder_re = re.compile(r"\b(TODO|TBD|placeholder|lorem ipsum)\b", re.IGNORECASE)
        px_re = re.compile(r"(?<![a-zA-Z0-9_])\d+(?:\.\d+)?px\b")
        rel_re = re.compile(r"\d+(?:\.\d+)?(?:vw|vh|vmin|vmax|rem|em|%)\b")

        for a in artifacts:
            p = a.path.lower()
            c = a.content or ""
            if not c.strip():
                issues.append({"path": a.path, "reason": "empty content"})
                continue
            if placeholder_re.search(c):
                issues.append({"path": a.path, "reason": "contains unfinished placeholder markers"})
            if p.endswith(".css"):
                px_count = len(px_re.findall(c))
                rel_count = len(rel_re.findall(c))
                if px_count >= 10 and rel_count == 0:
                    issues.append({"path": a.path, "reason": "css uses too many fixed px without relative units"})
            if p.endswith(".html"):
                if "<script" in c and "defer" not in c:
                    issues.append({"path": a.path, "reason": "script tag missing defer, may break DOM binding"})
            if p.endswith(".dart") and framework == "flutter":
                if "MediaQuery" not in c and "LayoutBuilder" not in c and "Flexible" not in c and "Expanded" not in c:
                    issues.append({"path": a.path, "reason": "flutter layout lacks adaptation primitives"})
                # Check for interactivity in Flutter
                if "main.dart" in p:
                    has_gesture = any(kw in c for kw in ["GestureDetector", "InkWell", "onTap", "onPressed", "onPanUpdate"])
                    has_state = "setState" in c or "StatefulWidget" in c
                    if not has_gesture and not has_state:
                        issues.append({"path": a.path, "reason": "flutter main lacks interaction handlers (GestureDetector/onTap/setState)"})
        
        # Flutter cross-file reference validation
        if framework == "flutter":
            cross_issues = self._check_flutter_cross_references(artifacts)
            issues.extend(cross_issues)

        # Check for interactivity in game-related JS files.
        for a in artifacts:
            p = a.path.lower()
            c = a.content or ""
            if p.endswith(".js") and framework in {"html", "react", "nextjs"}:
                has_events = any(kw in c for kw in ["addEventListener", "onclick", "onkeydown", "onClick", "onTouchStart"])
                has_state = any(kw in c for kw in ["useState", "state", "setState", "let ", "const "])
                if not has_events and "game" in p and has_state:
                    issues.append({"path": a.path, "reason": "game js file lacks event listeners"})

        return issues

    def _check_flutter_cross_references(self, artifacts: list[GeneratedArtifact]) -> list[dict[str, str]]:
        """Check Flutter/Dart files for unresolved cross-file references."""
        issues: list[dict[str, str]] = []
        
        # Collect all defined classes and widgets from all dart files
        class_def_re = re.compile(r"class\s+(\w+)")
        widget_named_params_re = re.compile(r"const\s+(\w+)\s*\(\s*\{([^}]*)\}")
        
        defined_classes: set[str] = set()
        widget_params: dict[str, set[str]] = {}  # widget name -> set of named params
        
        dart_artifacts = [a for a in artifacts if a.path.lower().endswith(".dart")]
        
        # First pass: collect definitions
        for a in dart_artifacts:
            content = a.content or ""
            # Find class definitions
            for m in class_def_re.finditer(content):
                defined_classes.add(m.group(1))
            # Find widget constructor named parameters
            for m in widget_named_params_re.finditer(content):
                widget_name = m.group(1)
                params_text = m.group(2)
                # Extract named parameter names
                param_names: set[str] = set()
                for param in params_text.split(","):
                    # Match patterns like "required this.label" or "this.value" or "String? name"
                    param = param.strip()
                    if "this." in param:
                        idx = param.find("this.") + 5
                        rest = param[idx:]
                        name_match = re.match(r"(\w+)", rest)
                        if name_match:
                            param_names.add(name_match.group(1))
                    else:
                        # Match "Type paramName" or "required Type paramName"
                        parts = param.split()
                        if parts:
                            name_match = re.match(r"(\w+)", parts[-1])
                            if name_match:
                                param_names.add(name_match.group(1))
                widget_params[widget_name] = param_names
        
        # Built-in Flutter classes we don't need to check
        flutter_builtin = {
            "StatelessWidget", "StatefulWidget", "State", "Widget", "BuildContext",
            "Key", "Color", "Colors", "Container", "Text", "Column", "Row", "Scaffold",
            "AppBar", "Center", "Padding", "EdgeInsets", "SizedBox", "Expanded", "Flexible",
            "ListView", "GridView", "Stack", "Positioned", "Align", "GestureDetector",
            "InkWell", "ElevatedButton", "TextButton", "Icon", "Icons", "MaterialApp",
            "Theme", "ThemeData", "MediaQuery", "LayoutBuilder", "AnimatedBuilder",
            "AnimatedScale", "AnimatedPositioned", "Animation", "AnimationController",
            "Tween", "Duration", "Timer", "Future", "Stream", "List", "Map", "Set",
            "String", "int", "double", "bool", "dynamic", "void", "Object", "Null",
            "Navigator", "MaterialPageRoute", "AlertDialog", "SnackBar", "ScaffoldMessenger",
            "BoxDecoration", "BorderRadius", "Border", "BoxShadow", "LinearGradient",
            "TextStyle", "FontWeight", "TextAlign", "MainAxisAlignment", "CrossAxisAlignment",
            "Axis", "WrapAlignment", "Card", "CardTheme", "CardThemeData", "FloatingActionButton",
            "Image", "AssetImage", "NetworkImage", "CircleAvatar", "ClipRRect", "ClipOval",
            "Transform", "Matrix4", "Offset", "Size", "Rect", "VoidCallback", "ValueChanged",
            "StateSetter", "ChangeNotifier", "Provider", "Consumer", "ValueNotifier",
        }
        
        # Second pass: check references
        type_usage_re = re.compile(r"(?:final|var|const)?\s*(\w+)\s+\w+\s*=")
        constructor_call_re = re.compile(r"(\w+)\s*\(")
        named_arg_re = re.compile(r"(\w+)\s*:")
        
        for a in dart_artifacts:
            content = a.content or ""
            
            # Find type usages
            for m in type_usage_re.finditer(content):
                type_name = m.group(1)
                if type_name not in defined_classes and type_name not in flutter_builtin:
                    if type_name[0].isupper() and not type_name.startswith("_"):
                        issues.append({
                            "path": a.path,
                            "reason": f"undefined type '{type_name}' - class not found in project files"
                        })
            
            # Check constructor calls for custom widgets
            for m in constructor_call_re.finditer(content):
                widget_name = m.group(1)
                if widget_name in widget_params:
                    # Find the arguments in this call
                    call_start = m.end() - 1
                    # Simple bracket matching
                    depth = 1
                    call_end = call_start + 1
                    while call_end < len(content) and depth > 0:
                        if content[call_end] == "(":
                            depth += 1
                        elif content[call_end] == ")":
                            depth -= 1
                        call_end += 1
                    call_text = content[call_start:call_end]
                    # Find named arguments used
                    used_params = set(named_arg_re.findall(call_text))
                    available_params = widget_params[widget_name]
                    for param in used_params:
                        if param not in available_params and param not in {"key", "child", "children"}:
                            issues.append({
                                "path": a.path,
                                "reason": f"widget '{widget_name}' called with undefined parameter '{param}'"
                            })
        
        return issues
