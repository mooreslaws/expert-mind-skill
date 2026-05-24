# Expert Mind Skill — Specification v1

> Open-source toolkit that ingests sources (Telegram, RSS, podcasts, X, LinkedIn, web, ...) about specific experts and incrementally enriches Claude Skills representing each expert's worldview. Stays small, signal-dense, and IDE-agnostic.

---

## 1. Vision

A non-developer or a developer can:
1. Drop a YAML "persona passport" describing an expert (Eric Seufert, Naval, your favourite blogger).
2. Connect sources where that expert publishes (Telegram channel, RSS, X handle, LinkedIn, podcast, ...).
3. Hit a single command (or let cron do it) — system extracts only the mental models / frameworks / opinions and writes them into a compact Claude Skill that fits inside the model's attention budget.

The skill grows up to a soft cap, then starts replacing weaker principles with stronger newer ones rather than ballooning forever.

---

## 2. Non-goals

- **Not a content scraper.** We discard 95%+ of input (news, status, factual updates).
- **Not a knowledge base.** We don't build a queryable archive — just compact skill files.
- **Not multi-language at v1.** English-only output.
- **Not Cursor-native at v1.** Skills are Claude-native; Cursor users get them by pointing at the same `output/skills/` directory.
- **Not a UI.** CLI + git + files only. GUI is a documented extension point for contributors.
- **Not a telemetry system.** No usage tracking of which skills get loaded.

---

## 3. Architecture

Two layers, one repository:

```
                         ┌─────────────────────────────────┐
                         │   Claude Code Plugin layer      │
                         │   (slash commands + wizard)     │
                         │   /expert-mind-skill:init       │
                         │   /expert-mind-skill:add-persona│
                         │   /expert-mind-skill:status     │
                         │   /expert-mind-skill:run        │
                         └────────────┬────────────────────┘
                                      │ shells out to
                                      ▼
┌───────────────────────────────────────────────────────────┐
│                     Python CLI / Engine                   │
│                                                           │
│  personas/  →  sources/  →  pipeline/  →  output/         │
│   (yaml)      (adapters)    (3 stages)    (.md skills)    │
│                                                           │
│                    ↓ external LLM API                     │
│         Anthropic / OpenAI / Ollama (configurable)        │
└───────────────────────────────────────────────────────────┘
```

The CLI works standalone (cron / GH Actions / manual). The plugin is sugar on top — it's the easy-install path for Claude Code users.

---

## 4. Repository structure

```
expert-mind-skill/
├── .claude-plugin/
│   ├── plugin.json
│   ├── commands/
│   │   ├── init.md           # setup wizard
│   │   ├── add-persona.md    # interactive persona creator
│   │   ├── status.md         # health + last run
│   │   └── run.md            # force a sync cycle
│   └── skills/
│       └── (none in v1; plugin = commands only)
│
├── personas/                 # user-owned passports
│   ├── eric-seufert.yaml
│   ├── naval.yaml
│   └── ...
│
├── output/
│   ├── skills/               # LEAN: load into Claude/Cursor
│   │   ├── eric-seufert.md
│   │   └── ...
│   └── deep/                 # full archive (audit / reference)
│       ├── eric-seufert-deep.md
│       └── ...
│
├── logs/
│   ├── eric-seufert.jsonl    # append-only attribution log
│   ├── _review-queue.md      # borderline items awaiting manual review
│   └── _run-history.jsonl    # one row per pipeline run
│
├── sources/                  # adapters (Python, one file each)
│   ├── base.py               # SourceAdapter protocol
│   ├── rss.py                # ─┐
│   ├── substack.py           #  │  Tier 1 — built-in v1
│   ├── medium.py             #  │
│   ├── telegram_public.py    #  │
│   ├── youtube.py            #  │
│   ├── linkedin_apify.py     #  │
│   ├── x_apify.py            #  │
│   ├── readwise_reader.py    #  │
│   ├── readwise_highlights.py#  │
│   ├── webfeed.py            #  │  generic HTML→text
│   ├── email_forward.py      # ─┘
│   ├── mastodon.py           # ─┐
│   ├── bluesky.py            #  │  Tier 2 — built-in v1
│   ├── reddit_user.py        #  │
│   ├── hackernews.py         #  │
│   ├── arxiv.py              #  │
│   ├── snipd_import.py       # ─┘
│   ├── podcast_rss.py        # ─┐  Tier 3 — stretch v1
│   ├── notion_kb.py          #  │
│   └── gdrive_folder.py      # ─┘
│
├── cold-start/
│   └── registry.yaml         # known experts with pre-curated sources
│
├── judge/
│   ├── prompt.md             # canonical judge prompt
│   ├── calibration_seed.md   # labeled examples (50+)
│   └── config.yaml           # threshold, model tier
│
├── pipeline/
│   ├── ingest.py             # adapter → dedupe → raw store
│   ├── judge.py              # raw → scored
│   ├── distill.py            # scored → skill (with eviction)
│   └── orchestrator.py       # ties stages, handles concurrency
│
├── cli/
│   └── main.py               # `expert-mind-skill run|init|add-persona|status`
│
├── deploy/
│   ├── github-actions.yml    # default cron via GH Actions
│   ├── cron-launchd.plist    # macOS local
│   ├── cron-systemd.service  # Linux local
│   └── docker-compose.yml    # VPS
│
├── .env.example
├── pyproject.toml            # uv tool install expert-mind-skill
├── README.md
└── LICENSE                   # MIT
```

---

## 5. Persona passport (`personas/<id>.yaml`)

The single file the user edits.

```yaml
id: eric-seufert
name: Eric Seufert
role: Founder of Mobile Dev Memo; advisor on mobile growth, advertising, attribution
expertise: [mobile_advertising, attribution, app_growth, ad_economics, AI_distribution]
voice: |
  Analytical, dense, prone to historical/economic framing (Galbraith, Malthus).
  Strong opinions, supported by quoted prior writing.
  Uses concrete dollar examples to anchor abstractions.
languages: [en]
domain: marketing                        # optional, freeform tag
groups: [marketing, strategy, ai]        # activation tags (see §11.3)
activation_phrases:                      # extra triggers beyond expertise
  - "mobile growth expert"
  - "ad attribution"
  - "AppLovin or Meta ad analysis"

sources:
  - type: rss
    url: https://mobiledevmemo.com/feed/
    enabled: true
  - type: podcast_rss
    url: https://feeds.simplecast.com/...
    transcribe: true
  - type: x_apify
    handle: "@eric_seufert"
    enabled: false
  - type: linkedin_apify
    handle: "ericseufert"
    enabled: false
  - type: readwise_reader
    tag: "mdm"
    enabled: true

cadence: weekly                          # weekly | daily | manual
size_limit_tokens: 4000                  # soft cap for lean skill
hard_cap_tokens: 8000                    # forced distillation above this
review_mode: auto                        # auto | pr | manual
include_sources_in_lean: false           # toggle: keep source URLs in lean skill or only in logs/deep
attribution_log: logs/eric-seufert.jsonl
```

**Notes:**
- `voice` is freeform — used by the judge to recognise content that matches the expert's style.
- `groups` is critical for activation (see §11.3) — semantic groupings used when user says "use my strategy experts".
- `include_sources_in_lean` set per persona, default at init. `false` = pristine skill (sources only in `deep/` + `.jsonl`); `true` = footnote-style attribution under each principle.
- `enabled: false` lets you park a source.
- `review_mode: pr` opens a PR for human review instead of auto-commit.

---

## 6. Source adapters

20 built-in adapters at v1, organised by complexity/cost:

### Tier 1 — core (always shipped, well-tested)

| Adapter | What it pulls | Auth | Cost |
|---|---|---|---|
| `rss` | Any RSS/Atom feed | none | free |
| `substack` | Substack pubs (RSS + metadata enrichment) | none | free |
| `medium` | Medium author feed (RSS-based) | none | free |
| `telegram_public` | Public TG channels via Telethon | API ID/hash | free |
| `youtube` | Channel videos + transcripts | API key (optional, fallback to scrape) | free or $5/mo |
| `linkedin_apify` | LinkedIn posts + articles | Apify token | ~$0.01/post |
| `x_apify` | X/Twitter feed | Apify token | ~$0.01/tweet |
| `readwise_reader` | Saved articles by tag | Readwise token | $8/mo (user already pays) |
| `readwise_highlights` | Highlights by author tag | Readwise token | same |
| `webfeed` | Generic blog → text (Readability port) | none | free |
| `email_forward` | IMAP folder for forwarded newsletters | IMAP creds | free |

### Tier 2 — common (shipped, lighter testing)

| Adapter | What it pulls | Auth | Cost |
|---|---|---|---|
| `mastodon` | Public timeline by handle | none | free |
| `bluesky` | Author feed | none | free |
| `reddit_user` | Author posts + comments via PRAW | reddit OAuth | free |
| `hackernews` | Author submissions via Firebase API | none | free |
| `arxiv` | Author papers + abstracts | none | free |
| `snipd_import` | Snipd JSON export | none | free |

### Tier 3 — stretch v1 / v2

| Adapter | Status | Notes |
|---|---|---|
| `podcast_rss` | stretch v1 | RSS + Whisper transcription if no transcript provided |
| `notion_kb` | stretch v1 | for users who curate notes about an expert in Notion |
| `gdrive_folder` | v2 | folder of PDFs/docs |
| `farcaster` | v2 | growing crypto-native audience |
| `stack_overflow` | v2 | for tech experts |
| `mirror_xyz` | v2 | Web3 long-form |

**Each adapter is one file. Adding a new one = community contribution.** README documents the protocol.

### Adapter protocol

```python
# sources/base.py

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Protocol

@dataclass
class RawItem:
    source_id: str          # globally unique
    source_url: str
    author_handle: str
    published_at: datetime | None
    title: str | None
    text: str
    raw_metadata: dict

class SourceAdapter(Protocol):
    type: str

    def validate_config(self, source_config: dict) -> None:
        """Raise on invalid config. Used by /add-persona wizard."""

    def fetch(
        self,
        source_config: dict,
        since: datetime | None,
    ) -> Iterator[RawItem]:
        """Yield items newer than `since`. Caller handles dedup."""
```

---

## 7. Pipeline

Three sequential stages. Each writes its output to disk so failures don't lose state.

### 7.1 Ingest (`pipeline/ingest.py`)

```
for each enabled persona:
    for each enabled source:
        adapter = load_adapter(source.type)
        for item in adapter.fetch(source.config, since=last_sync):
            if hash(item.source_id) in seen:
                continue
            if semantic_dedup(item.text, recent_items_by_author):
                continue                          # already seen from another source
            write_to(staging/raw/<persona>/<item_id>.json)
```

Semantic dedup uses cheap embedding (Haiku or local sentence-transformers). Cosine > 0.92 against author's recent N items = drop.

### 7.2 Judge (`pipeline/judge.py`)

```
for each raw item in staging/raw/<persona>/:
    score, principle, type, conflicts, evolves = judge_llm(
        persona = persona.yaml,
        excerpt = item.text,
    )
    write_to(staging/scored/<persona>/<item_id>.json)
    if score < threshold_low:
        archive(item)
    elif score < threshold_high:
        append_to(logs/_review-queue.md)
    else:
        mark_for_distill(item)
```

**Judge output schema (strict JSON):**

```json
{
  "score": 0.83,
  "type": "framework",
  "extracted_principle": "Digital ads route existing demand rather than create it. Targeting shifts the value distribution so a few high-value users justify spend.",
  "reason": "Named mental model with economic mechanism, originally argued by expert across multiple pieces.",
  "conflicts_with": null,
  "evolves": null
}
```

`type ∈ { principle, framework, opinion, case, voice_sample, prediction }`.

### 7.3 Distill (`pipeline/distill.py`)

```
load current_skill = output/skills/<persona>.md
load incoming = [items where score ≥ threshold_high]

for each incoming:
    if evolves_existing_principle(incoming, current_skill):
        append "evolved" entry, retain original with date marker
    elif conflicts_with_another_persona(incoming):
        add to skill's "## Conflicts" section with explicit attribution
    else:
        append to relevant section

if estimated_tokens(skill) > size_limit:
    run distillation_pass(skill):
        - cluster principles by semantic similarity
        - within cluster: keep strongest + most recent
        - rewrite cluster as 1-2 tighter principles

if estimated_tokens(skill) > hard_cap:
    force distillation, retry; if still over, block lean writes

always append every accepted item (full quote + URL + date) to logs/<persona>.jsonl
```

**Eviction policy:** never delete from `logs/` or `deep/`. Lean replaces freely.

---

## 8. Judge

### 8.1 Prompt skeleton (`judge/prompt.md`)

```
You are a calibration judge for expert mental models.

PERSONA:
  Name: {persona.name}
  Role: {persona.role}
  Expertise: {persona.expertise}
  Voice: {persona.voice}

EXCERPT:
  {item.text}

CONTEXT:
  Source: {item.source_url}
  Author handle on source: {item.author_handle}
  Published: {item.published_at}

YOUR TASK:
Score 0.0-1.0 how strongly this excerpt expresses {persona.name}'s reusable
mental model, framework, principle, or opinion (vs reporting facts, news,
status, or merely citing others).

RULES:
- "if X then Y" rules, named frameworks, dichotomies → HIGH (0.8-1.0)
- Opinions backed by mechanism / data → MEDIUM-HIGH (0.6-0.8)
- Company- or time-specific facts and stats → LOW (0.0-0.3)
- Bare predictions without mechanism → LOW-MEDIUM (0.3-0.5)
- Citations of external thinkers → SCORE based on whether {persona.name}
  uses that thinker as load-bearing scaffold (then HIGH) or merely names them (then LOW)
- Voice / style samples → 0.5-0.7, type="voice_sample"

OUTPUT (strict JSON):
  { score, type, extracted_principle, reason,
    conflicts_with: null | string,
    evolves: null | string }
```

### 8.2 Calibration

Live file: `judge/calibration_seed.md` (already drafted with 50 examples).

CI / pre-merge gate: run judge over calibration set, require ≥90% label agreement.

### 8.3 Threshold

`judge/config.yaml`:
```yaml
threshold_low: 0.5
threshold_high: 0.7
model_tier:
  default: anthropic/claude-sonnet-4-6
  ingest_dedup: anthropic/claude-haiku-4-5
  distill: anthropic/claude-opus-4-7
```

---

## 9. Skill output format

### 9.1 Lean (`output/skills/<persona>.md`)

What gets loaded into Claude / Cursor.

```markdown
---
name: eric-seufert
description: |
  Eric Seufert — mobile growth, ad economics, attribution.
  Triggers: mobile UA, paid acquisition strategy, AppLovin/Meta/Google
  ad platform analysis, AI-distribution debates, marketing experts,
  strategy experts.
type: persona
groups: [marketing, strategy, ai]
generated_by: expert-mind-skill@v1.0.0
last_updated: 2026-05-16
revision: 14
size_tokens: 3247
---

# Eric Seufert

## Core thesis
- AI shifts the binding economic constraint from production to distribution. Personalized advertising platforms become critical infrastructure.

## Frameworks
- **Millionaire's Mall** — ad campaign economics are fat-tailed; campaigns are won by identifying rare high-LTV users, not persuading the median.

## Principles
- Bid against true LTV. The platform absorbs wasted-impression risk if you give it your real value-per-objective.
- Generative AI is deflationary for production, inflationary for distribution.

## Predictions
- (2026-05) Meta's location fees are partly geopolitical — passing DSTs to advertisers creates visible tax pressure on US-EU negotiations.

## Voice samples
- > "The Millionaire's Mall only requires the presence of one billionaire."

## Evolution (when principles change)
- *(none yet)*

## Conflicts with other personas
- *(none yet)*

---
*Generated from <N> items over <date range>. Full attribution: `logs/eric-seufert.jsonl`.*
```

If `include_sources_in_lean: true`, each principle gets a `[¹]` footnote with URL at the bottom.

### 9.2 Deep (`output/deep/<persona>-deep.md`)

All quotes, all dates, all source URLs. Never loaded into Claude.

### 9.3 Attribution log (`logs/<persona>.jsonl`)

Append-only, one row per accepted excerpt.

---

## 10. Evolution & conflict

### 10.1 Evolution

```markdown
## Principles
- ~~Old: Run reach campaigns to fix Meta's over-targeting~~ *(2026-03-21)*
- **Evolved (2026-05-08):** Reach + value rules together; reach alone over-counts low-intent youth.
```

### 10.2 Conflicts between personas

```markdown
## Conflicts with other personas
- **vs naval-ravikant on _leverage_:** Naval says leverage = code + media + capital. Seufert implicitly disagrees: distribution leverage (ad platforms) dominates everything else in the digital economy.
```

User can suppress with `conflicts_track: false`.

---

## 11. Setup wizard, activation, and cold-start

### 11.1 `/expert-mind-skill:init`

1. "Where do you want skills saved?" → default: current repo `output/skills/`
2. "Pick LLM provider for the judge:" → Anthropic / OpenAI / Ollama
3. "Paste your API key:" → `.env`
4. "How do you want to run cron?" → GH Actions / local / manual
5. **"Include source URLs inside lean skills?"** → yes (footnotes) / no (only in logs/deep). Default: no.
6. "Add your first persona now?" → if yes, invokes `add-persona`. If no, offer cold-start registry.

### 11.2 `/expert-mind-skill:add-persona`

1. Name, role, expertise, voice (or pick from cold-start registry — see §11.4).
2. **Groups** (multi-select from existing groups + free-form add): `marketing`, `strategy`, `finance`, `ai`, `product`, `design`, etc.
3. **Activation phrases** (optional, beyond expertise tags): "give me mobile growth experts", "ad attribution lens".
4. Add sources — loop:
   - Pick adapter from §6 list
   - Adapter-specific prompts (`validate_config` runs here)
   - Test fetch shows 1-3 sample items
5. Save passport, optionally trigger first run.

### 11.3 Skill activation strategy

When the user types "give me strategy experts" or "use my financial skills", Claude's skill loader matches based on:

- **`description:` field** in the skill frontmatter — primary trigger
- **`groups:` field** — secondary (registers "strategy experts" → all skills with `strategy` in groups)
- **`activation_phrases:` field** — explicit user-defined phrases

The pipeline auto-generates `description:` from the passport:

```
{name} — {role short}. Triggers: {expertise joined}, {groups joined}, {activation_phrases joined}.
```

README will teach users:
- "Add `strategy` to groups → activates on 'use strategy experts', 'strategy lens', etc."
- "Use activation_phrases for unusual triggers ('ad bear case', 'naval-mode')."
- "Avoid generic descriptions — they cause conflicts when 20+ skills are installed."

This works in Claude Code, Cursor (with skill loader), and any IDE that respects the skill frontmatter.

### 11.4 Cold-start registry (`cold-start/registry.yaml`)

Pre-curated passports + source lists for well-known experts. User picks from menu during `add-persona`:

```yaml
naval-ravikant:
  name: Naval Ravikant
  role: Investor, founder of AngelList, philosopher of leverage
  groups: [strategy, career, ai]
  sources:
    - type: rss
      url: https://nav.al/feed
    - type: x_apify
      handle: "@naval"
    - type: youtube
      channel: "UCAhYL8I3DCWZbnAxLLO5n_g"
    - type: linkedin_apify
      handle: "navalravikant"

eric-seufert:
  name: Eric Seufert
  role: Mobile growth, ad economics, attribution
  groups: [marketing, strategy, ai]
  sources:
    - type: rss
      url: https://mobiledevmemo.com/feed/
    - type: linkedin_apify
      handle: "ericseufert"
    - type: youtube
      channel: "UCxsJ..."

lenny-rachitsky:
  name: Lenny Rachitsky
  role: Product growth, PM advice
  groups: [product, strategy, growth]
  sources:
    - type: substack
      url: https://www.lennysnewsletter.com/
    - type: linkedin_apify
      handle: "lennyrachitsky"
    - type: youtube
      channel: "UCa_X..."

april-dunford:
  name: April Dunford
  role: Positioning expert, author of "Obviously Awesome"
  groups: [marketing, strategy, positioning]
  sources:
    - type: linkedin_apify
      handle: "aprildunford"
    - type: rss
      url: https://www.aprildunford.com/feed/
    - type: youtube
      channel: "..."

andrej-karpathy:
  name: Andrej Karpathy
  role: AI/ML research, neural networks, education
  groups: [ai, ml, strategy]
  sources:
    - type: x_apify
      handle: "@karpathy"
    - type: youtube
      channel: "UCPk8m_r6fkUSYmvgCBwq-sw"
    - type: github
      user: "karpathy"

# ~30 more: Patrick Collison, Brian Chesky, Pieter Levels, Sam Altman,
# Reid Hoffman, Dharmesh Shah, Sahil Lavingia, Andrew Chen, Steve Jobs,
# David Ogilvy, Naval ↑, Igor Ryabenkiy, Ilya Krasinsky, Bayram Annakov,
# Paul Graham, Marc Andreessen, Ben Thompson, Stratechery, ...
```

Registry shipped with repo. Updated by community PRs.

---

## 12. Deployment modes

### 12.1 GitHub Actions (default)

```yaml
name: expert-mind-skill
on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:
jobs:
  enrich:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv tool install expert-mind-skill
      - run: expert-mind-skill run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "expert-mind-skill weekly run"
```

### 12.2 Local cron (macOS launchd / Linux systemd)

Generated by `init` wizard.

### 12.3 VPS via docker-compose

For persistent infra.

### 12.4 What we do NOT support

- `claude_code background process` — dies with session.
- claude.ai/code (web) — no scheduled execution.

---

## 13. Cost model

Default: Sonnet 4.6 for judge, Haiku for dedup, Opus for distill cycles.

For **20 personas, ~1.5 items/day, weekly cadence:**

| Stage | Calls/week | Cost/week |
|---|---|---|
| Dedup (Haiku) | ~210 | $0.05 |
| Judge (Sonnet) | ~210 | $1.05 |
| Distill (Opus, occasional) | ~5 | $0.40 |
| **Total** | | **~$1.50/week** |

Three tiers in `judge/config.yaml`:
- `budget` (Haiku everywhere) → $0.20/week
- `balanced` (default) → $1.50/week
- `quality` (Sonnet + Opus more often) → $5/week

Adapter costs add separately:
- LinkedIn / X via Apify: ~$0.01/post × ~14 posts/week × 20 personas ≈ $2.80/week
- Readwise: user's existing subscription
- Others: free

**Worst-case total (20 personas, all paid adapters on): ~$5/week.**

---

## 14. Configuration files

### 14.1 `.env`

```env
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=

TELEGRAM_API_ID=
TELEGRAM_API_HASH=
APIFY_TOKEN=
READWISE_TOKEN=
YOUTUBE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
IMAP_HOST=
IMAP_USER=
IMAP_PASS=

EXPERT_MIND_SKILL_LOG_LEVEL=info
```

### 14.2 `judge/config.yaml`

```yaml
threshold_low: 0.5
threshold_high: 0.7
model_tier:
  default: anthropic/claude-sonnet-4-6
  ingest_dedup: anthropic/claude-haiku-4-5
  distill: anthropic/claude-opus-4-7
embedding_model: anthropic/claude-haiku-4-5
semantic_dedup_threshold: 0.92
distillation_trigger_tokens: 6000
hard_cap_tokens: 8000
```

---

## 15. v1 MVP scope

**IN v1:**
- CLI: `init`, `add-persona`, `status`, `run`
- 17 adapters (Tier 1 + Tier 2)
- Pipeline: ingest → judge → distill, with attribution log
- Output: lean + deep + jsonl, with optional source-link footnotes
- Three LLM providers (Anthropic primary, OpenAI alt, Ollama escape hatch)
- GH Actions + local cron + docker deploy templates
- Claude Code plugin with 4 commands
- Cost estimator script
- Calibration set (50 labeled examples, already drafted)
- Cold-start registry with ≥30 well-known experts
- Group-based activation (groups + activation_phrases fields)

**OUT of v1, documented as v2:**
- Tier 3 adapters (podcast transcription, Farcaster, SO, Mirror, Google Drive)
- Cursor-native install
- A/B eval
- GUI (review queue dashboard)
- Telemetry
- Audio transcription for podcasts without transcripts
- Private Telegram / paid Substack
- Cross-persona conflict auto-detection beyond ~20 personas

---

## 16. README outline

1. **What it is** — 2 sentences + GIF of init wizard
2. **Quickstart** — fork → `/plugin install` → `/expert-mind-skill:init` → done
3. **Three install paths** — GH Actions (recommended) / local / VPS
4. **Adding a persona** — example passport + wizard screenshot, link to cold-start registry
5. **Adding a source** — current adapter list (Tier 1/2/3) + how to write a new one
6. **Activating skills by context** — groups + activation_phrases mechanic explained
7. **Cost** — table from §13 + estimator script
8. **How the judge works** — short version of §8 with link to calibration set
9. **Editing skills by hand** — manual edits always win; cron only appends
10. **Ideas for contributors** — GUI dashboard, Cursor-native install, more adapters, audio transcription, A/B eval
11. **License (MIT) + acknowledgements**

---

## 17. Open questions (remaining after r2)

1. **Skill loading order in Claude when 20+ personas.** §11.3 documents the mechanism (description + groups + activation_phrases). Open question: how aggressive should the pipeline be in *normalizing* descriptions to avoid collisions? (e.g. enforce no two personas share >70% of their trigger keywords)
2. **Cold-start registry maintenance.** PRs from community? CI check that all listed sources are still alive?
3. **What happens if the user's LLM provider is unreachable mid-run?** Retry/backoff strategy. Probably: 3 retries with exponential backoff, then skip persona and log error.

---

*End of SPEC v1.1. Review, push back, then we start coding.*
