# Changelog

All notable changes to this project will be documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [Unreleased]

### Added
- 16th bundled persona: `toddgardner1` (Todd Gardner — bootstrapped SaaS, dev-tools marketing)
- 5 new source adapters:
  - `pull_telegram.py` — public Telegram channels via `t.me/s/` HTML scrape (no auth)
  - `pull_readwise.py` — Readwise Reader API (saved articles by tag)
  - `pull_webfeed.py` — single web URL → plain text, naive readability heuristic
  - `pull_email.py` — IMAP folder (for forwarded newsletters)
  - `scrape_x_official.py` — X API v2 alternative for users with Basic tier+ ($100/mo)
- Pre-flight billing/auth checks in `orchestrator.py` — pings Apify and Anthropic
  before launching parallel jobs; aborts with a clear message if 402/credit-low/auth issues
- `youtube-transcript-api` is now a required dependency (richer YouTube ingest)

### Fixed (silent-failure cleanup discovered during production walkthrough)
- `judge.py` — HTTP errors no longer fake-pass as `score=0.0, type=error` rows that
  get counted as `low`. Errors now surface in the summary as `⚠️ ERRORS=N` plus
  the first error reason in stdout
- `judge.py` — JSONL writes use `ensure_ascii=True` to escape U+2028 / NEL chars;
  prevents downstream `splitlines()`-based readers from breaking mid-record
- `judge.py` — HTTP error preview widened from 80 to 500 chars (no more `"Your credit b"` truncation)
- `judge.py` — removed hardcoded "skip Rory / Palmer" exclusion list in `main()`;
  was a forever-TODO that left one persona unjudged
- `distill.py` — reader splits JSONL on `\n` only (not `splitlines()`); skips
  rows where `type == "error"`
- `distill.py` — writes skills as `<id>/SKILL.md` directory layout (matches
  Claude Code skill loader convention)
- `orchestrator.py` + `wizard_state.py` — `.env` loaders treat empty-string env
  vars as "not set" (so `.env` can override `KEY=""` from parent shell)
- `orchestrator.py` — auto-loads `.env` on startup so subprocesses inherit credentials
- `wizard_state.check_first_run()` — per-persona coverage + mtime check (no
  longer reports DONE when stale outputs from previous runs exist)

### Clarified (documentation alignment)
- README reframed as "Alexey Vorobey's experimental expert circle" — rotating
  set that grows over time, refreshes on cadence
- README adds "How to invoke" section with three patterns: by name, by domain,
  by group (and how to ask for parallel responses)
- README adapter table notes that **LinkedIn has no public API**, Apify is the only viable path
- X has two paths documented: `x_apify` (recommended — pay per tweet) and `x_official` (only worthwhile if already on Basic+ tier)
- YouTube adapter clarified: **no API key needed**; we use channel RSS feed + `youtube-transcript-api` scraping. The `YOUTUBE_API_KEY` env var is reserved for future extension but not currently used.
- `tools/publish.sh` — extract a clean stand-alone repo from the development monorepo
- Smoke test suite (`tests/test_smoke.py`) — no external API calls
- GitHub Actions CI template at `deploy/test-workflow.yml.template` (installed by publish.sh)
- CONTRIBUTING.md with adapter contribution guide

### Changed
- `judge.py` `collect_excerpts()` now auto-discovers every `staging/raw/*/` subdir —
  new adapters work automatically without judge.py code changes
- `wizard_state.py` `SOURCE_AUTH_MAP` updated for new adapter env vars:
  `telegram_public` now needs no auth (uses HTML scrape, not Telethon)

## [0.2.0] — 2026-05-18

### Added
- 15 bundled expert skills in `skills/` (Eric Seufert, Andrew Chen, Elena Verna, etc.)
- Cold-start registry (`cold-start/registry.yaml`) — 15 pre-curated passports
- Filesystem-driven wizard state (`scripts/wizard_state.py`)
- 7 source adapters: `rss`, `linkedin_apify`, `x_apify`, `mastodon`, `bluesky`, `youtube`, `manual_text`
- 4 slash commands: `/init`, `/add-persona`, `/status`, `/run`
- SessionStart hook with one-time welcome message
- GitHub Actions template for scheduled refresh
- Comprehensive README with adapter catalog + best practices

### Changed
- `judge.py` no longer hardcodes PERSONAS — reads from `personas/*.yaml` or cold-start
- `scrape_linkedin.py` and `pull_rss.py` are now persona-driven
- Wizard model: no "REQUIRED-but-missing" blocker concept — every step is optional
  for the wizard itself; "needed for /run" is a separate informational flag
- Sources unified into a single Step 3 with full catalog; Apify is just one option

### Removed
- `extract_snipd.py` and `judge_snipd.py` — user-specific, moved to private fork
- Per-source-credential steps in wizard (Apify/Readwise/etc.) — folded into Sources step
- Cost preview in /init — wasn't useful, added friction

## [0.1.0] — 2026-05-17 (internal)

Initial proof-of-concept on 17 sample personas. Dropped Lenny + Palmer after
quality review; 15 remained as bundled set.
