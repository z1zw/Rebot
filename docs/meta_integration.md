# MetaGPT Integration Notes

## Summary
Rebot now embeds key MetaGPT helper layers to align the scheduler with the planner/coder/reviewer philosophy from `MetaGPT`:

1. **Prompt scaffolding** – Imported `STRUCTURAL_CONTEXT`/`PLAN_STATUS` templates plus `TaskTypeGuidance` so planner prompts include repo map, memory hints, and task-specific guidance.
2. **Review flow** – Added `AskReviewHelper` and review constants, enabling `_review_plan` to auto-review each plan and emit structured `plan_review` SSE events.
3. **Plan visibility** – Scheduler now emits `plan_summary` events (with file list + summary) that feed the UI console, and retries planning when review feedback marks the plan insufficient.
4. **Guardrails alignment** – Coders, self-check, and guardrail builders now receive the inferred `TaskTypeGuidance`, ensuring Flutter/React/Uniapp/Python plans inherit the intended instructions.

## Frontend handling
- `AppState` listens for `plan_summary`/`plan_review`, stores the summary/files, and logs the review confirmation status so the UI shows MetaGPT-style progress.
- `_consumeDesignPlanMessage` now prepopulates `generatedFiles` with placeholders, keeping the explorer in sync with the plan.

## Run verification
1. Start backend and use the Flutter desktop app to submit a requirement.
2. Observe SSE `plan_summary`/`plan_review` events in the console log and confirm the plan files list updates.
3. Build (`flutter build windows`) to ensure the UI compiles with the new events enabled.

With this integration we keep the existing Rebot workflows but now benefit from MetaGPT-level prompts and review scaffolding.
