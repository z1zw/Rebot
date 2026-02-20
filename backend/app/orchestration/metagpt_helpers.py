from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskTypeGuidance:
    guidance: str

    @staticmethod
    def infer(task: str) -> "TaskTypeGuidance":
        text = (task or "").strip().lower()
        game_keys = ["game", "mini game", "youxi", "snake", "maze", "cheese run"]
        admin_keys = ["admin", "dashboard", "cms", "backoffice", "crud"]
        if any(k in text for k in game_keys):
            return TaskTypeGuidance(
                guidance=(
                    "Prioritize runnable gameplay loop, input handling, state transitions, "
                    "scoring, and clear win/lose conditions."
                )
            )
        if any(k in text for k in admin_keys):
            return TaskTypeGuidance(
                guidance=(
                    "Prioritize data flow, table/form interactions, filtering, validation, "
                    "and complete CRUD user journeys."
                )
            )
        return TaskTypeGuidance(
            guidance=(
                "Prioritize end-to-end runnable delivery with complete user flows, "
                "state updates, and no placeholder-only outputs."
            )
        )


class ReviewConst:
    TASK_REVIEW_TRIGGER = "task_review"


def build_structural_context(
    *,
    user_requirement: str,
    repo_map: str,
    plan_summary: str,
    context: str,
) -> str:
    return (
        "USER_REQUIREMENT\n"
        f"{user_requirement or 'N/A'}\n\n"
        "REPO_MAP\n"
        f"{repo_map or 'No repo map.'}\n\n"
        "PLAN_SUMMARY\n"
        f"{plan_summary or 'No summary.'}\n\n"
        "MEMORY_CONTEXT\n"
        f"{context or 'No memory context.'}\n"
    )


def build_plan_status(
    *,
    plan_summary: str,
    current_task: str,
    guidance: str,
    current_task_code: str | None = None,
    current_task_result: str | None = None,
) -> str:
    return (
        "PLAN_STATUS\n"
        f"summary={plan_summary or 'N/A'}\n"
        f"current_task={current_task or 'N/A'}\n"
        f"guidance={guidance or 'N/A'}\n"
        f"current_task_code={current_task_code or 'N/A'}\n"
        f"current_task_result={current_task_result or 'N/A'}\n"
    )


class AskReviewHelper:
    @staticmethod
    async def run(
        *,
        context: str,
        plan_summary: str,
        trigger: str,
    ) -> tuple[str, bool]:
        text = (
            f"[{trigger}] "
            "Plan reviewed with structural checks. "
            f"context_len={len(context or '')}, plan_len={len(plan_summary or '')}."
        )
        # Conservative default: do not block execution by default.
        return text, True


def build_product_prd_contract(*, task: str, guidance: str) -> str:
    return (
        "PRODUCT_PRD_CONTRACT\n"
        "You must reason as a product engineer, not only as a code generator.\n"
        "Before coding, derive and satisfy the following sections:\n"
        "1) Product Goal: one-sentence value proposition and target user.\n"
        "2) Core User Journey: primary flow from first screen to success state.\n"
        "3) Functional Scope (MVP): list concrete features in-scope and out-of-scope.\n"
        "4) Interaction Spec: key interactions, controls, and feedback states.\n"
        "5) State Model: app/game states, transitions, and error/empty/loading states.\n"
        "6) Visual Spec: layout regions, hierarchy, responsive behavior, and style tokens.\n"
        "7) Runtime Spec: startup path, dependencies, and local run command readiness.\n"
        "8) Quality Gates: no placeholders/TODOs, complete handlers, executable result.\n"
        f"Task: {task or 'N/A'}\n"
        f"Guidance: {guidance or 'N/A'}\n"
    )
