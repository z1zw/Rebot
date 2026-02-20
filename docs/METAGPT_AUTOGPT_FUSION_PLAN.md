# MetaGPT + AutoGPT Fusion Plan

## Scope
This document maps concrete mechanisms from local `MetaGPT` and `AutoGPT` repos into Rebot's current multi-agent stack.

Targets:
- stronger fail -> auto-rework loop
- lower technical debt in quality gates
- production-grade one-sentence delivery quality

## Current State Snapshot
- DeepSeek request path is already wired:
  - `rebot/models/openai_compatible.py`
  - `rebot/models/providers.py`
  - `backend/app/core/capabilities.py`
  - `backend/app/worker.py`
  - `desktop/flutter_agentgpt/lib/app_state.dart`
- Multi-agent rework loop exists in:
  - `backend/app/orchestration/multi_agent_scheduler.py`
  - Reviewer + self-check + bounded auto-rework are active.

## Borrow From MetaGPT
Source references:
- `MetaGPT/metagpt/actions/action_node.py`
- `MetaGPT/metagpt/actions/design_api_review.py`
- `MetaGPT/config/config2.example.yaml` (`repair_llm_output`)

Reusable patterns:
1. Structured review + revise as first-class stages (`auto_review`, `auto_revise`).
2. Prompt/schema repair retry when model output is malformed.
3. Requirement-vs-design explicit review (PRD conformance check).

Fusion actions for Rebot:
1. Add dedicated `prd_conformance` score to reviewer schema and gate logic.
2. Add parse-repair fallback before failing reviewer response.
3. Add stage-level "review -> revise -> review" traces in event stream.

## Borrow From AutoGPT
Source reference:
- `AutoGPT/autogpt_platform/backend/backend/blocks/llm.py`

Reusable patterns:
1. Structured JSON output with explicit retry count.
2. Parseable/validation-specific retry prompts.
3. Return retry telemetry (`llm_call_count`, `llm_retry_count`).

Fusion actions for Rebot:
1. Wrap role LLM calls with structured-output helper for planner/reviewer.
2. Emit per-stage retry metrics into run result and `ExecutionStore.metrics`.
3. Differentiate parse failure vs schema failure vs quality failure.

## Gaps To Close (Short Board)
1. Runtime validation currently relies too much on static review; compile/run smoke checks should become blocking gates by framework.
2. Review output is mostly free-form; schema should be stricter and versioned.
3. Rework reasons were underexposed; now surfaced via `quality_gate` payload, but should also be dashboarded.
4. Some diagnostics were framework-coupled incorrectly (fixed for JS interactivity check in scheduler).

## Priority Backlog
1. P0: Framework smoke checks with auto-repair retry
   - Flutter: `flutter analyze` + optional `flutter test`
   - Web: build or lint command if `package.json` exists
   - Python: `python -m py_compile` for project files
2. P0: Structured role-output helper
   - Shared parser/retry utility for planner/reviewer/coder repair prompts
3. P1: PRD conformance score and gating
   - Add rubric field to reviewer and benchmark scripts
4. P1: Telemetry dashboard fields
   - quality gate cycles, rework count, parse retries, schema retries
5. P2: Golden benchmark batch in CI
   - run `scripts/score_prd_benchmark.py --manifest ...` per release

## Acceptance Criteria
1. No run ends as `completed` when framework smoke check hard-fails.
2. Reviewer malformed JSON no longer ends immediately; repair retry occurs first.
3. Batch benchmark average >= 85 and no `fail` case.
4. Result payload always includes structured `quality_gate` details.
