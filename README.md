# Expert Mind Skill

> **Alexey Vorobey's experimental expert circle for Claude Code.**
> A rotating set of 16 named professionals (Eric Seufert, Andrew Chen,
> Elena Verna, …) distilled into compact mental models. The circle is
> **always growing** — new experts are added when the work warrants it,
> and existing skills auto-refresh on cadence as sources publish new material.

Three ways to activate:

```
> "Use Eric Seufert — what's your take on cohort financing for mobile apps?"
  → loads eric-seufert lens

> "What do mobile UA experts think about Apple Search Ads in 2026?"
  → loads eric-seufert + jacob-rushfinn + janvoss93 lenses

> "Through the lens of growth experts — should we launch a referral program?"
  → loads elena-verna + andrew-chen lenses
```

The circle ships installable on day one — fork to make it yours, add your own
experts via the wizard, or just install and use as-is.

---

## Install (3 commands)

Inside Claude Code:

```bash
# 1. Add the marketplace
/plugin marketplace add github:mooreslaws/expert-mind-skill

# 2. Install the plugin
/plugin install expert-mind-skill@expert-mind-skill

# 3. (Optional) Run the setup wizard
/expert-mind-skill:init
```

After step 2, all 16 bundled skills are available. The wizard in step 3 is
only needed if you want to **add new authors** or **refresh existing ones
with your own data sources**.

---

## What's in the box

16 ready-to-use skills, each ~2-3k tokens with frameworks + principles + voice samples:

| ID | Persona | Domain |
|---|---|---|
| `eric-seufert` | Eric Seufert | Mobile ad economics, ATT, AI distribution |
| `elena-verna` | Elena Verna | PLG, growth loops, retention |
| `andrew-chen` | Andrew Chen | Growth marketing, network effects |
| `anish-acharya` | Anish Acharya | Consumer fintech, AI investing |
| `rory-odriscoll` | Rory O'Driscoll | SaaS economics, public markets |
| `toddgardner1` | Todd Gardner | Bootstrapped SaaS, dev-tools marketing |
| `prestonr` | Preston Rutherford | DTC brand, anti-ROAS-only |
| `marcusburke` | Marcus Burke | Meta ads, value rules |
| `jacob-rushfinn` | Jacob Rushfinn | Mobile UA, creatives |
| `janvoss93` | Jan Voss | Paid UA, ASO |
| `dangjr` | Dan G Jr | Mobile growth |
| `sylvaingauchet` | Sylvain Gauchet | Growth Gems curation |
| `fazlurshah` | Fazlur Shah | Subscription apps |
| `dawidprokopowicz` | Dawid Prokopowicz | Mobile growth |
| `vkalmykov` | V. Kalmykov | Mobile growth |
| `mikolajbarczentewicz` | Mikolaj Barczentewicz | Mobile growth + product |

---

## How to invoke an expert

Three patterns — pick whichever fits how you're thinking.

### 1. By name (single expert)

> "Use Eric Seufert — what's your take on cohort financing?"

Loads exactly one persona (`eric-seufert`). Claude responds through their
frameworks, principles, and voice samples.

### 2. By domain / expertise (2-4 experts)

> "What do **mobile UA experts** think about Apple Search Ads in 2026?"
> "Through the **subscription economics** lens, is freemium-first or trial-first better?"

Activates every persona whose `expertise` tags match the domain. The judge's
description triggers do the routing — no manual list needed.

### 3. By group (a thematic cluster)

> "Through the lens of **growth experts** — should we launch a referral program?"
> "What would **marketing experts** say about this positioning?"

Available groups: `marketing`, `product`, `strategy`, `ai`, `finance`,
`leadership`, `design`, `sales`. Each persona is tagged with 1-3 groups in
their YAML.

### Asking for parallel responses

The patterns above route context to my single answer (I synthesize). To get
genuinely **parallel, side-by-side** voices, ask explicitly:

> "Give me **3 expert perspectives** on X — each in their own section."
> "Don't synthesize — let each expert answer separately."

---

## Adding your own expert

Run `/expert-mind-skill:init` (or `/expert-mind-skill:add-persona` once
already set up). The wizard asks:

1. **Identity** — name, role, voice description, expertise tags
2. **Groups** — for activation by category ("strategy experts", "ai experts")
3. **Sources** — attach as many as you want, any combination:

### Supported source types

All adapters below are **implemented**. Each is a single Python file in
`scripts/` — see `CONTRIBUTING.md` to add a new one.

| Type | Auth | Cost | Notes |
|---|---|---|---|
| `rss` | none | free | Any RSS or Atom feed (Substack, WordPress, Ghost) |
| `linkedin_apify` | `APIFY_TOKEN` | ~$0.002/post | **Only viable path for LinkedIn** — no public API exists |
| `x_apify` | `APIFY_TOKEN` | ~$0.003/tweet | X/Twitter via Apify (recommended — cheap, no monthly fee) |
| `x_official` | `X_BEARER_TOKEN` | $100/mo Basic tier | X API v2 — for users who already pay for Basic+ tier. Free tier blocks reading others' tweets |
| `youtube` | none | free | Public videos via channel RSS + transcripts via scraping. No API key needed; install `pip install youtube-transcript-api` for richer transcript content |
| `telegram_public` | none | free | Public TG channels via `t.me/s/` HTML scrape, no API needed |
| `mastodon` | none | free | Public Mastodon timelines |
| `bluesky` | none | free | Public Bluesky feeds |
| `readwise_reader` | `READWISE_TOKEN` | $8/mo subscription | Your saved Reader articles, filtered by tag |
| `email_forward` | `IMAP_HOST` + `IMAP_USER` + `IMAP_PASS` | free | IMAP folder of forwarded newsletters |
| `webfeed` | none | free | Single web URL → plain text (naive readability) |
| `manual_text` | none | free | Drop `.txt` files in `staging/raw/manual/<persona_id>/` — adapter consolidates them |

**Planned for v1.2** (contributions welcome — see CONTRIBUTING.md):
`reddit_user`, `hackernews`, `arxiv`, `readwise_highlights`, podcast RSS with Whisper transcription, Farcaster.

Get keys at:
- Anthropic: <https://console.anthropic.com/settings/keys>
- Apify: <https://apify.com/sign-up> → Settings → Integrations → API token
- Readwise: <https://readwise.io/access_token>
- Telegram: <https://my.telegram.org/apps>

---

## How the pipeline works

Every cadence cycle (default: weekly):

1. **Ingest** — pulls latest content from each persona's enabled sources
2. **Judge** — Claude scores each excerpt 0-1: is this a reusable principle,
   or just news/noise? Only items ≥0.7 are kept.
3. **Distill** — accepted items are bucketed by type (framework / principle /
   opinion / voice sample), deduplicated semantically, and written to a
   compact `SKILL.md` (target: 2-4k tokens, hard cap: 8k).
4. **Commit** — `git add output/skills/ && git commit` (when running in CI)

Skills auto-update without overwriting your manual edits — manual changes
between markers are preserved, only the auto-generated sections refresh.

---

## How to write a good persona passport

Quality of the skill depends on quality of metadata. Three rules:

### Rule 1 — Voice description is the judge's filter

The `voice` field in `personas/<id>.yaml` is what the judge uses to recognise
"this excerpt sounds like our author" vs "this is generic noise".

**Bad** — generic:
```yaml
voice: "Speaks about marketing topics."
```

**Good** — distinctive:
```yaml
voice: |
  Brand-first contrarian. Argues against pure-performance ROAS optimization.
  Uses concrete examples (Chubbies, Liquid Death) to anchor frameworks.
  Sentences are short and assertive — almost manifesto-style.
```

### Rule 2 — Multiple sources beat single source

A LinkedIn-only persona produces a thin skill (LinkedIn is full of reposts).
A persona with LinkedIn + their newsletter RSS + their podcast appearances
produces a rich skill (3x signal).

Recommended minimum: 2 sources per persona.

### Rule 3 — Don't bloat the skill

Hard cap: 8k tokens. Soft cap: 4k. The judge already filters, and distill
deduplicates. If your skill is hitting 8k:

- Tighten the `expertise` tags (too broad → judge accepts too much)
- Sharpen the `voice` description (too generic → false positives)
- Cap `max_per_section` in `judge/config.yaml`

---

## Cadence and scheduling

Three options for the cron:

### GitHub Actions (recommended)
Copy `deploy/github-actions.yml.template` to `.github/workflows/expert-mind-skill.yml`.
Add secrets in repo settings. Free for public repos, generous for private.

### Local launchd (macOS) / systemd (Linux)
`/expert-mind-skill:init` will generate the unit file and install it. Updates
happen on YOUR machine, no cloud.

### Manual
Run `/expert-mind-skill:run` (or `python scripts/orchestrator.py`) whenever you want.

---

## Cost

Default (Sonnet judge, 16 personas, ~1.5 items/day each, weekly cadence):

| Component | Cost/week |
|---|---|
| Apify (LinkedIn + X) | ~$1.50 |
| Anthropic (judge) | ~$1.00 |
| Anthropic (distill finalize) | ~$0.30 |
| Other adapters (RSS, YouTube, Mastodon, etc.) | $0 |
| **Total** | **~$2.80/week** |

Bootstrap (initial pull with 100 posts/persona): ~$15 one-time.

Switch to Haiku for lower cost — set `EXPERT_MIND_JUDGE_MODEL=claude-haiku-4-5`
to bring weekly cost to ~$0.30.

---

## Plugin layout

```
expert-mind-skill/
├── .claude-plugin/plugin.json    # plugin manifest
├── commands/                     # slash commands
│   ├── init.md                   # /expert-mind-skill:init
│   ├── add-persona.md            # /expert-mind-skill:add-persona
│   ├── status.md                 # /expert-mind-skill:status
│   └── run.md                    # /expert-mind-skill:run
├── skills/                       # 16 bundled expert skills (read-only)
│   ├── eric-seufert/SKILL.md
│   └── …
├── scripts/                      # pipeline (Python)
│   ├── orchestrator.py           # main entry — ingest → judge → distill
│   ├── persona_loader.py         # reads personas/*.yaml
│   ├── scrape_linkedin.py        # Apify-driven LinkedIn ingester
│   ├── pull_rss.py               # RSS/Atom ingester
│   ├── judge.py                  # LLM-as-judge scoring
│   ├── distill.py                # bucket + dedup + voice extraction
│   └── retry_errors.py           # rate-limit recovery helper
├── cold-start/registry.yaml      # 16 pre-curated persona templates
├── hooks/hooks.json              # SessionStart welcome
├── deploy/
│   └── github-actions.yml.template
└── README.md
```

After installation, the user creates these in their working directory:
```
your-project/
├── personas/<id>.yaml            # one file per expert YOU added
├── .env                          # API keys (gitignored)
├── output/skills/                # YOUR custom skills (separate from bundled)
├── logs/<id>.jsonl               # attribution log per persona
└── staging/                      # cache (gitignored)
```

---

## Spec, evaluation, and architecture

- **[SPEC.md](SPEC.md)** — full system specification (v1.1)
- **[output/EVALUATION_REPORT.md](output/EVALUATION_REPORT.md)** — quality report on the 16 bundled skills (16/16 with usable applicability, avg 2,503 tokens)
- **[calibration_seed.md](calibration_seed.md)** — 50 labeled examples used to calibrate the LLM judge

---

## License

MIT. Forks welcome. PRs to expand `cold-start/registry.yaml` with new authors very welcome.

---

## Contributing a new expert to the cold-start registry

1. Fork this repo
2. Add an entry to `cold-start/registry.yaml`:
   ```yaml
   <persona-id>:
     name: ...
     role: ...
     expertise: [...]
     voice: |
       2-3 sentences describing distinctive speech patterns
     groups: [...]
     recommended_sources:
       - type: rss
         url: ...
       - type: linkedin_apify
         handle: ...
   ```
3. (Optional) Generate the SKILL.md by running the pipeline against your own
   sources, commit the resulting file to `skills/<persona-id>/SKILL.md`
4. Open a PR
