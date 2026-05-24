---
description: Run the full pipeline (ingest → judge → distill) for one persona or all. Optional persona id as argument.
---

# Run the pipeline

Trigger the full refresh cycle for one persona or all enabled personas.

## Steps

### 1. Check pipeline readiness

First run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wizard_state.py --json` and
read `_pipeline_ready`. If False, show `_blockers` and stop — point user at
`/expert-mind-skill:init` to resolve them.

### 2. Parse arguments

If invoked as `/expert-mind-skill:run`, run for all enabled personas.

If invoked as `/expert-mind-skill:run <persona-id>` (or multiple ids),
restrict to those.

### 3. Confirm

Show a one-line summary of what's about to happen:
```
Running pipeline:
  <N> personas: <ids joined>
  <M> sources enabled
```

AskUserQuestion: **Run now** / **Cancel**.

### 4. Execute

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py [persona-ids...]
```

Stream stdout to the chat. The orchestrator handles dispatch to each adapter
script, then judge, then distill.

### 5. Summarize

After completion, read `output/_evaluation.json` and show the per-persona
table:
```
persona             accepted/judged  fullness    applicability
<id>                <a>/<b>          <f>         <app>
...
```

Flag any persona that:
- Dropped to `low` fullness (regression vs last run, if logs exist)
- Has 0 frameworks or 0 voice_samples
- Hit `hard_cap_tokens`

## Flags (pass to orchestrator)

- `--force` — re-scrape even if staging files exist
- `--skip-ingest` — only judge + distill on existing staging data
- `--skip-judge` — only distill on existing scored data
- `--skip-distill` — ingest + judge only, no rewrite of skill files
