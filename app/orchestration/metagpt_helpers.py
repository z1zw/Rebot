# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

STRUCTURAL_CONTEXT = """
## User Requirement
{user_requirement}
## Context
{context}
## Repo Map
{repo_map}
## Current Plan Summary
{plan_summary}
"""

PLAN_STATUS = """
## Finished Tasks
### code
```python
{code_written}
```

### execution result
{task_results}

## Current Task
{current_task}

## Finished Section of Current Task
### code
```python
{current_task_code}
```

### execution result
{current_task_result}

## Task Guidance
Write code for the incomplete sections of 'Current Task'. Avoid duplicating code already produced above.
Specifically, {guidance}
"""


class ReviewConst:
    TASK_REVIEW_TRIGGER = "task"
    CODE_REVIEW_TRIGGER = "code"
    CONTINUE_WORDS = ["confirm", "continue", "c", "yes", "y"]
    CHANGE_WORDS = ["change"]
    EXIT_WORDS = ["exit"]
    TASK_REVIEW_INSTRUCTION = (
        f"If you want to change any task, say '{CHANGE_WORDS[0]} task task_id or current task, ...'. "
        f"If you confirm the output, say: {CONTINUE_WORDS[0]} or {CONTINUE_WORDS[1]}."
    )
    CODE_REVIEW_INSTRUCTION = (
        f"If you want code rewritten, say '{CHANGE_WORDS[0]} ...'. "
        f"If you want to keep it, say {CONTINUE_WORDS[0]} or {CONTINUE_WORDS[1]}."
    )
    EXIT_INSTRUCTION = f"If you want to stop, say {EXIT_WORDS[0]}."


@dataclass(frozen=True)
class TaskTypeDef:
    name: str
    desc: str
    guidance: str


class TaskTypeGuidance(Enum):
    FLUTTER = TaskTypeDef(
        name="flutter",
        desc="Flutter UI or Dart-based desktop/mobile work",
        guidance=(
            "Focus on responsive widgets, MediaQuery, safe areas, and avoid platform-specific blockers. "
            "For games: implement complete game logic with state management (setState/StatefulWidget), "
            "user input handling (GestureDetector, onTap, onPanUpdate), game loop with animations (AnimationController, Timer), "
            "win/lose conditions, score tracking, and visual feedback. Never generate static UI without interaction handlers."
        ),
    )
    WEB = TaskTypeDef(
        name="web",
        desc="HTML/CSS/JS web application",
        guidance=(
            "Prioritize responsive layouts (flex/grid), relative units (%, rem, vw/vh), and clean entry points. "
            "For games: implement full game logic with event listeners (keydown, click, touch), "
            "game state management, requestAnimationFrame for game loops, collision detection, "
            "score tracking, win/lose conditions, and restart functionality. Never generate static mockups."
        ),
    )
    UNIAPP = TaskTypeDef(
        name="uniapp",
        desc="UniApp/Vue-based multi-platform app",
        guidance=(
            "Make sure manifests describe the pages and styles adapt to the platform through relative units. "
            "Include reactive data binding, event handlers (@click, @tap), and complete business logic. "
            "For interactive apps: implement Vue reactivity, state management, and user input handling."
        ),
    )
    PYTHON = TaskTypeDef(
        name="python",
        desc="Python scripts/services",
        guidance=(
            "Keep dependencies minimal, focus on entrypoint and script execution, and avoid placeholders. "
            "For games: use pygame or similar with complete game loop, event handling, rendering, "
            "and game state. For CLI apps: implement complete command parsing and interactive prompts."
        ),
    )
    GENERAL = TaskTypeDef(
        name="general",
        desc="Fallback generic software task",
        guidance=(
            "Ensure the workspace is runnable, includes instructions, and uses best practices for the implied stack. "
            "All interactive elements must have working event handlers. Never leave interaction stubs or placeholders."
        ),
    )

    @classmethod
    def infer(cls, text: str) -> TaskTypeDef:
        lowered = (text or "").lower()
        if "flutter" in lowered:
            return cls.FLUTTER.value
        if any(keyword in lowered for keyword in ("react", "vue", "html", "web", "vite")):
            return cls.WEB.value
        if "uniapp" in lowered:
            return cls.UNIAPP.value
        if any(keyword in lowered for keyword in ("python", "django", "flask")):
            return cls.PYTHON.value
        return cls.GENERAL.value


def build_structural_context(
    *,
    user_requirement: str,
    repo_map: str,
    plan_summary: str,
    context: str,
) -> str:
    return STRUCTURAL_CONTEXT.format(
        user_requirement=user_requirement,
        context=context,
        repo_map=repo_map,
        plan_summary=plan_summary,
    )


def build_plan_status(
    *,
    plan_summary: str,
    current_task: str,
    guidance: str,
    code_written: str = "",
    task_results: str = "",
    current_task_code: str = "",
    current_task_result: str = "",
) -> str:
    return PLAN_STATUS.format(
        code_written=code_written or plan_summary,
        task_results=task_results or "N/A",
        current_task=current_task or "N/A",
        current_task_code=current_task_code or plan_summary,
        current_task_result=current_task_result or "N/A",
        guidance=guidance or "Focus on delivering working features.",
    )


class AskReviewHelper:
    @staticmethod
    async def run(
        context: str,
        plan_summary: str,
        trigger: str = ReviewConst.TASK_REVIEW_TRIGGER,
    ) -> Tuple[str, bool]:
        logger.debug("Review context: %s", context)
        if "requires revision" in (context or "").lower():
            return ("Review flagged: requires revision before proceeding.", False)
        review_note = f"Auto-review ({trigger}): confirmed {plan_summary.splitlines()[:1]}"
        confirmed = True
        return review_note, confirmed
