---
description: Show installation health — personas configured, sources ready, last run, blockers
---

# Expert Mind Skill — Status

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wizard_state.py` from the user's
working directory and show the output verbatim.

The dashboard tells the user at a glance:
- Which steps are done (`✅`), pending (`⚪`), or skipped (`➖`)
- Whether the pipeline can run right now (`_pipeline_ready` flag)
- A per-persona source breakdown when any source is missing credentials

After showing the dashboard, if there are pending steps, point the user at
`/expert-mind-skill:init` to continue setup. If pipeline is ready but hasn't
run yet, suggest `/expert-mind-skill:run`.

Do NOT walk through configuration — that's `init`'s job. This command is
read-only.
