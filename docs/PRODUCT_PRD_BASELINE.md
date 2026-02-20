# Product PRD Baseline + Auto Scoring

## 1) Standard PRD Baseline (one-sentence prompt)
Rebot should internally normalize any short prompt into the following fixed product contract:

1. Product Goal
2. Target User
3. Core User Journey
4. Functional Scope (in/out)
5. Interaction Spec
6. State Model (including loading/empty/error)
7. Visual Spec (layout, hierarchy, responsive)
8. Runtime Spec (entrypoint + dependencies + run command)
9. Quality Gates (no placeholders, complete handlers, runnable)

This baseline is now injected into planner/coder/reviewer prompts via:
- `backend/app/orchestration/metagpt_helpers.py`
- `backend/app/orchestration/multi_agent_scheduler.py`

## 2) Benchmark Set
Benchmark cases are defined in:
- `scripts/prd_benchmark_cases.json`

Each case includes:
- one-sentence prompt
- target framework
- expected files
- expected feature keywords

## 3) Auto Scoring
Scoring script:
- `scripts/score_prd_benchmark.py`

### Single case
```bash
python scripts/score_prd_benchmark.py \
  --case-id game_cheese_run_web \
  --workspace backend/Game\ 1
```

### Batch mode
Create a manifest JSON:
```json
{
  "game_cheese_run_web": "backend/Game 1",
  "task_todo_flutter": "backend/flutter_todo"
}
```

Run:
```bash
python scripts/score_prd_benchmark.py --manifest path/to/manifest.json --output score_report.json
```

## 4) Score Rubric (100)
- File coverage: 30
- Runtime entry readiness: 20
- Interaction completeness: 20
- UX/design signals: 15
- Hygiene (placeholder/TODO penalties): 15

Verdict thresholds:
- `pass`: >= 80
- `warn`: >= 65 and < 80
- `fail`: < 65

## 5) Production Target
- Average benchmark score >= 85
- No `fail` cases in batch report
- Reviewer status should not be `fail`
