---
description: Setup wizard — inspect current state, pick what to configure, exit any time
---

# Expert Mind Skill — Setup Wizard

This wizard is **stateful via filesystem inspection** and **never blocks**.
At every step the user can pick "I'm done for now" and walk away — anything
left undone can be filled in by re-running `/expert-mind-skill:init` later.

## Step 0 — Inspect current state

Run **`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wizard_state.py`** (without `--json`)
in the user's CWD. Show the user the output verbatim — it's the dashboard.

Then read JSON form: **`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wizard_state.py --json`**
and parse to drive decisions below. The JSON includes a top-level
`_pipeline_ready` boolean and `_blockers` list — use them to phrase choices.

Example output the user sees:
```
Setup state:

  ✅ LLM provider         done     (needed for /run) [provider=anthropic]
  ⚪ Personas             pending  (needed for /run)  none active yet; 15 presets available
  ✅ Apify token          done     (needed for /run)  token ends in …xxxx
  ➖ readwise creds       skipped  (optional)
  ⚪ Cron schedule        pending  (optional)
  ⚪ First run            pending  (optional)

⚪ Pipeline not yet runnable. Blockers:
   - no personas configured yet (add at least one)

You can exit the wizard anytime — these can be filled in later.
```

**Status legend:**
- `✅ done` — step is complete
- `⚪ pending` — not done; user may fill in now or any time later
- `➖ skipped` — not applicable to this user's config (auto-detected)
- `❌ error` — something is wrong (e.g. invalid API key)

**`(needed for /run)` vs `(optional)`** describes what gates the pipeline,
NOT what the wizard requires. Pipeline running and wizard completing are
different concepts — wizard always lets the user exit.

## Step 0.5 — Ask what to do next

After showing the dashboard, use AskUserQuestion. Phrase the "resume" option
adaptively based on what `_blockers` says (if no blockers, recommend Cron or
First run; if blockers exist, recommend resolving them).

> "What would you like to do?"

Options:
- **Continue setup** — wizard picks the first pending step and walks through it
- **Pick a specific step** — multi-pick from the 5 steps below (any combination, including re-doing a done step)
- **I'm done for now** — exit. If `_pipeline_ready` is True, run `/expert-mind-skill:run` to do the first pull, or wait for cron. If False, the user knows which blockers to fix later
- **Start over** — re-run wizard from Step 1 (existing personas/.env are preserved unless explicitly overwritten)

For each step the user picks, follow the matching section below. After each
step completes, re-run `wizard_state.py` to update the dashboard, then loop
back to Step 0.5. Always include "I'm done for now" as an option in the loop.

---

## Step 1 — LLM provider (needed for /run)

Needed because the judge calls an LLM. Without this, the pipeline cannot
update or build skills. Bundled 15 skills still work without this (they're
static files). User may skip this step and run pipeline later.

If state shows `✅ done` already, skip unless user picked "redo this step".

Use AskUserQuestion:
- **Anthropic Claude** (Recommended)
- **OpenAI**
- **Ollama (local, free)**

Per choice, point user at the relevant signup URL and read their key:

| Provider | Signup URL | Env var |
|---|---|---|
| Anthropic | <https://console.anthropic.com/settings/keys> | `ANTHROPIC_API_KEY` |
| OpenAI | <https://platform.openai.com/api-keys> | `OPENAI_API_KEY` |
| Ollama | local, run `ollama serve` | `OLLAMA_BASE_URL` |

Validate via curl:
```bash
# Anthropic example
curl -s -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,"messages":[{"role":"user","content":"OK"}]}' \
  https://api.anthropic.com/v1/messages
```
Look for `"content"` key in response → ✅. 401/403 → re-prompt.

Append the line `<ENV_VAR>=<value>` to `.env` in CWD (create if missing).
Also ensure `.env` is in `.gitignore`.

---

## Step 2 — Personas (identity only — no sources yet)

This step is **only about identifying authors** (name, voice, expertise).
**Do NOT discuss sources, Apify tokens, or costs here** — that's Step 3's
job. Mixing them confuses users who are still choosing whether they even
want a given author.

Meta-question first (AskUserQuestion):
- **Import from preset pack** — pick from 15 pre-curated experts
- **Add my own from scratch** — define a custom author
- **Both** — presets first, then custom
- **Skip for now** — exit Step 2 without adding anything

### 2a. Preset import (plain-text picker, NOT AskUserQuestion)

AskUserQuestion's 4-option ceiling can't display 15 entries; use plain text.

Read `${CLAUDE_PLUGIN_ROOT}/cold-start/registry.yaml`. Print all entries as a
numbered list with just `<id>` and a one-line role description (one entry per
line). Do **not** mention sources/auth/cost in this listing — keep it about
identity only.

Then ask in plain text:
> "Type the ids you want, comma-separated (or `all`, or `none`):"

For each picked id:
1. Read the entry from registry.yaml
2. Write to `personas/<id>.yaml` (create personas/ if missing)
3. Confirm: "✅ added `<name>`"

### 2b. Custom author (plain prompts in sequence)

1. Persona id (kebab-case)
2. Display name
3. Role (1 line)
4. Expertise tags (comma separated)
5. Voice description (2-3 sentences — what makes them distinctive)
6. Groups (multi-select: marketing, product, strategy, ai, finance, leadership, design, sales)

Write to `personas/<id>.yaml` with **empty `sources: []`** — sources are
configured in Step 3. Confirm and ask "add another custom author?".

### 2c. Skip

Tell user how to add later (`/expert-mind-skill:add-persona`), proceed to
Step 3 only if there are personas to configure sources for.

---

## Step 3 — Sources

Step 3 has two distinct sub-flows depending on how user got to Step 2:

- **Preset-only path** (user imported from registry, no custom personas):
  sources are already attached from the registry entries. Step 3 reduces to
  **auth validation only** — inspect the personas' existing sources, find
  any that need an env var that isn't in `.env`, prompt for each missing
  one. **Do NOT show the catalog or ask "which source types do you want"** —
  the answer was implicitly given when user picked which presets.

- **Custom-personas path** (user defined personas with empty `sources: []`):
  show the full catalog below so user can pick what types to attach.

Detect which sub-flow applies by inspecting `personas/*.yaml`. If every
persona already has ≥1 source, take the auth-only path.

### Catalog (only shown if any persona has empty sources)

Use plain markdown, then AskUserQuestion (multiSelect: true) to capture choices.

> "Which source types do you want to connect? (multi-select)"

### Free, no signup
- `rss` — any RSS or Atom feed (Substack, WordPress, Ghost personal blogs)
- `mastodon` — public Mastodon timeline by handle
- `bluesky` — public Bluesky feed by handle
- `hackernews` — author's HN submissions
- `arxiv` — author's papers
- `youtube` — public channel videos + transcripts (`YOUTUBE_API_KEY` is optional for richer metadata)
- `webfeed` — generic blog page → HTML→text
- `manual_text` — paste content directly (no fetch)

### Sign up + API token

- `linkedin_apify` — LinkedIn profile posts via Apify (~$0.002/post). **This is the only viable path** for LinkedIn — they don't have a public API. Sign up at <https://apify.com/sign-up> → Settings → Integrations → API token. We just need their `APIFY_TOKEN`.

- `x_apify` — X/Twitter timeline via the same Apify account (~$0.003/tweet). Same `APIFY_TOKEN`. **Recommended for X** — no monthly subscription, just pay-per-use.

- `x_official` — X API v2 via Bearer token from <https://developer.x.com/portal/dashboard>. Only useful if you **already pay** for X API Basic tier ($100/mo) or higher — the free tier blocks reading other users' tweets. For most users, `x_apify` is far cheaper.

- `readwise_reader` — your saved Readwise Reader articles by tag. Get a token at <https://readwise.io/access_token>. Saves to `READWISE_TOKEN`.

### Advanced
- `telegram_public` — public Telegram channels. Needs Telegram app credentials from <https://my.telegram.org/apps> → `TELEGRAM_API_ID` + `TELEGRAM_API_HASH`
- `email_forward` — IMAP folder for forwarded newsletters. Needs `IMAP_HOST`/`IMAP_USER`/`IMAP_PASS`

### Per source picked

For each source type the user enabled, **JIT credential prompt**:
1. Check `.env` for the required env var (e.g. `APIFY_TOKEN`)
2. If absent: tell user where to get it (URL above), read pasted token, validate via curl, append to `.env`
3. If present: skip; tell user "✅ already have your `APIFY_TOKEN`"

Apify is just ONE recommended way to get LinkedIn/X. If the user already has
another scraper or pre-collected JSON, they can skip Apify and use
`manual_text` to drop content directly into the pipeline.

### Per persona

Now per-persona, ask which of these chosen source types to attach:

> "For each persona, check which of the chosen source types to attach:"

For each persona × source-type combo the user picks, prompt the handle/URL,
append to the persona's `sources:` list in `personas/<id>.yaml`.

For personas imported from cold-start, the registry already pre-fills
recommended_sources — the wizard shows them with checkboxes and the user
just toggles or leaves defaults.

---

## Step 4 — Cron schedule (optional)

Skip if `wizard_state.cron.status` is `done`. For non-developer users, the
**"Ask me in chat"** option is by far the best default — it requires zero
setup and they're already in Claude Code.

AskUserQuestion (cadence):
- **Weekly** (recommended) — cron `0 6 * * 1`
- **Daily** — cron `0 6 * * *`
- **Manual only** — exit step (they'll refresh on demand)

AskUserQuestion (host):

- **Ask me in chat** (Recommended for non-developers) — no cron at all. User
  just says "refresh my skills" or "обнови Эрика" to Claude Code; the agent
  runs `/expert-mind-skill:run`. Zero setup, very low friction.

- **GitHub Actions** — for users with the plugin checked into a GitHub repo.
  Copy `${CLAUDE_PLUGIN_ROOT}/deploy/github-actions.yml.template` to
  `.github/workflows/expert-mind-skill.yml`. Then list which secrets to set
  in repo settings (only ones that match enabled source types). Auto-commits
  refreshed skills back. Free for public repos.

- **Local launchd (macOS) / systemd (Linux)** — for users who want refresh
  to keep happening even when Claude Code is closed AND their machine stays
  on. Generate the unit file, write to standard location, register via
  `launchctl load` / `systemctl --user enable --now`. Caveat: won't run if
  laptop is closed/sleeping.

- **Walk me through these** — if user is unsure, explain trade-offs and
  re-prompt. Default suggestion: "Ask me in chat" unless they have an
  always-on server or actively-developed git repo.

---

## Step 5 — First run (optional)

Check `wizard_state._pipeline_ready`. If False, show the blockers and offer
to address them via earlier steps, or exit without running. Don't force.

If True, summarise what's about to happen:
```
Ready to run the pipeline.
  Personas: <N>
  Sources:  <M> enabled (<linkedin_count> linkedin, <rss_count> rss, ...)
```

AskUserQuestion:
- **Run now** → run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py` in user's CWD. Stream output.
- **Not yet** → exit.

After completion, show summary from `output/_evaluation.json` (per-persona
accepted count, fullness, applicability).

---

## After every completed step

Re-inspect state with `wizard_state.py` and return to Step 0.5 ("what next?").

## Exit (at any time the user picks "I'm done for now")

```
Done ✅
Current state:
<paste wizard_state.py output>

To continue setup later: /expert-mind-skill:init
To check status anytime: /expert-mind-skill:status
To run the pipeline manually: /expert-mind-skill:run
```

If `_pipeline_ready` is True and `first_run` is pending, gently add:
"Pipeline is ready to run for the first time. Run `/expert-mind-skill:run`
when you want to populate your skills."

If `_pipeline_ready` is False, list the remaining blockers as a reminder.
Don't pressure — these are user's to address whenever.
