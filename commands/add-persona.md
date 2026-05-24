---
description: Add a new persona — either copy from cold-start registry, or define a custom author
---

# Add a persona

Quick, focused command for adding one persona without running the full `init`
wizard. Same UX as Step 2 of `init`, just standalone.

## Steps

### 1. Pick mode

AskUserQuestion:
- **Import from cold-start registry** — show the list from `${CLAUDE_PLUGIN_ROOT}/cold-start/registry.yaml`, multi-select
- **Add a custom author** — define from scratch via prompts below

### 2a. Import path

Parse `${CLAUDE_PLUGIN_ROOT}/cold-start/registry.yaml`. Show each entry as a
checkbox option in AskUserQuestion (`multiSelect: true`). Show `name`, `role`
(short), and the persona id.

For each picked id:
1. Read the full entry from registry.yaml
2. Write to `personas/<id>.yaml` in user's CWD (create personas/ if needed)
3. Confirm: "✅ added `<name>` (sources: rss, linkedin_apify, x_apify)"

### 2b. Custom path

Sequential plain-text prompts:
- "Persona id (kebab-case, e.g. `naval-ravikant`):"
- "Display name:"
- "Role (one line):"
- "Expertise tags (comma separated):"
- "Voice — 2-3 sentences. What makes this author recognisable? The judge uses this."
- "Groups (multi-select: marketing, product, strategy, ai, finance, leadership, design, sales):"

Then the sources loop. AskUserQuestion (multiSelect):
- rss / linkedin_apify / x_apify / mastodon / bluesky / youtube / manual_text / telegram_public / readwise_reader / etc.

For each chosen source type, prompt the handle/URL. For types requiring auth
(linkedin_apify, x_apify, readwise_*, telegram_public), check if the env var
is in `.env`. If not, prompt for it, validate, save.

Write the resulting passport to `personas/<id>.yaml`.

### 3. Ask if user wants to run the pipeline for this persona now

If yes → invoke `/expert-mind-skill:run <id>`. Otherwise: "Saved. Run later with
`/expert-mind-skill:run <id>` or wait for next cron tick."

## Note

This command does NOT walk through cron setup or other init steps. For full
onboarding, use `/expert-mind-skill:init`.
