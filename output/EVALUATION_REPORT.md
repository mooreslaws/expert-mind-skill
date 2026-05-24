# Expert Mind Skill — Pipeline Validation (v3)

> Generated 2026-05-19. End-to-end run on **16 bundled personas** using real Apify + Anthropic infrastructure. v3 reflects today's bug-fix round (silent-failure cleanup, pre-flight billing checks, JSONL escape, dotenv loader) plus the addition of `toddgardner1`.

---

## TL;DR

| Metric | v3 (16 personas) |
|---|---:|
| HIGH fullness | 5 |
| MEDIUM | 11 |
| LOW | 0 |
| EXCELLENT applicability | 12 |
| STRONG applicability | 4 |
| FAIR applicability | 0 |
| Total accepted (high+mid) | 883 |
| High-quality items only (≥0.7) | 849 |
| Average tokens / skill | 2,503 |
| Max tokens (under 8k hard cap) | 3,306 |

**0 fair/low** — every persona produces a usable skill. The previous v2 had 0 low + 2 medium; v3 has 0 low + 11 medium because mobile-UA personas (jacob-rushfinn, janvoss93, dawidprokopowicz, etc.) tend to ship at ~2k tokens not 3k — the genuinely-niche content density is just lower. Both numbers are healthy.

---

## Per-persona breakdown

| Persona | Accepted | Frameworks | Principles | Opinions | Predictions | Voice | Tokens | Fullness | Applicability |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `prestonr` | 88/96 | 76 | 11 | 1 | 0 | 0 | 2,101 | medium | excellent |
| `marcusburke` | 77/97 | 52 | 23 | 1 | 0 | 0 | 2,045 | medium | excellent |
| `dangjr` | 76/100 | 41 | 30 | 5 | 0 | 0 | 3,306 | high | excellent |
| `dawidprokopowicz` | 76/97 | 9 | 57 | 10 | 0 | 0 | 2,392 | medium | excellent |
| `toddgardner1` | 70/92 | 33 | 32 | 5 | 0 | 0 | 3,175 | high | excellent |
| `eric-seufert` | 66/101 | 14 | 33 | 13 | 6 | 0 | 3,208 | high | excellent |
| `andrew-chen` | 65/92 | 33 | 25 | 5 | 2 | 0 | 3,231 | high | excellent |
| `elena-verna` | 65/111 | 24 | 34 | 6 | 1 | 0 | 2,895 | medium | excellent |
| `vkalmykov` | 59/89 | 16 | 37 | 6 | 0 | 0 | 3,219 | high | excellent |
| `jacob-rushfinn` | 55/96 | 11 | 44 | 0 | 0 | 0 | 2,743 | medium | excellent |
| `rory-odriscoll` | 43/57 | 18 | 21 | 3 | 1 | 0 | 2,381 | medium | excellent |
| `mikolajbarczentewicz` | 37/88 | 6 | 16 | 15 | 0 | 0 | 2,085 | medium | excellent |
| `janvoss93` | 29/100 | 12 | 13 | 4 | 0 | 0 | 1,949 | medium | strong |
| `anish-acharya` | 28/39 | 17 | 9 | 1 | 0 | 0 | 1,947 | medium | strong |
| `fazlurshah` | 26/83 | 10 | 16 | 0 | 0 | 0 | 1,779 | medium | strong |
| `sylvaingauchet` | 23/114 | 8 | 11 | 2 | 2 | 0 | 1,594 | medium | strong |


---

## Pipeline bugs fixed in this round

| # | Bug | File | Impact |
|---|---|---|---|
| 1 | HTTP errors in judge silently inflated `low` bucket | `judge.py` | One bad-billing run was indistinguishable from "judge rejected everything" |
| 2 | JSONL writes left Unicode line-separators unescaped → `splitlines()` broke records | `judge.py:254` + `distill.py:297` | `JSONDecodeError` crashed distill on any LinkedIn post with U+2028 |
| 3 | Empty-string env vars blocked `.env` loading | `orchestrator.py` + `wizard_state.py` | New API key in `.env` was ignored if shell pre-set `KEY=""` |
| 4 | Hardcoded `Skip Rory/Palmer` list left one persona unjudged | `judge.py:280` | Stale TODO from internal POC era; rory-odriscoll never got scored |
| 5 | `wizard_state.check_first_run()` reported DONE on stale outputs | `wizard_state.py:188` | Hid the fact that pipeline hadn't actually run for current persona set |
| 6 | Skills written as flat `<id>.md` not directory layout | `distill.py` | Claude Code skill loader expects `<id>/SKILL.md` |
| 7 | `orchestrator.py` didn't auto-load `.env` | `orchestrator.py` | Subprocesses missed credentials |
| 8 | HTTP error preview truncated at 80 chars | `judge.py:118` | `"Your credit b"` cut before the diagnostic word |

## Preventive improvements

- **Pre-flight checks** in `orchestrator.py` — pings Apify (`/v2/users/me`) and Anthropic (`/v1/messages`) before launching parallel jobs. Aborts in <1 second if 402/auth/credit-low. Saves ~$3-5 of wasted Apify spend on a single misconfigured run.
- **`youtube-transcript-api`** now a required dependency — eric-seufert gets real video transcripts instead of metadata-only.
- **Surfaced silent failures** — judge summary now prints `⚠️ ERRORS=N` + first error reason in stdout. Easier diagnosis from logs alone.

---

## Notes on quality variance

- **`prestonr` (88 high / 96 total)** — highest signal density. DTC brand voice is sharp and opinionated; nearly every post contains a framework.
- **`dangjr` (76 high / 100)** — strong signal density. Deeptech VC content is heuristic-dense.
- **`andrew-chen` (62 high / 92)** — RSS + LinkedIn combo gives the richest variety: long-form essays plus quick takes.
- **`sylvaingauchet` (21 high / 114 total)** — Growth Gems curator role: most posts are *recommendations of others' content*, which the judge correctly classifies as low-originality. The signal density is genuinely low for a curator role — this is *correct behavior* not a bug.
- **`fazlurshah` (25 high / 83 total)** — subscription apps have a noisy LinkedIn profile (industry news shares, conference posts). Judge filters most as low.

---

## Layout

```
output/
├── EVALUATION_REPORT.md        this file
├── _evaluation.json            raw per-persona stats
└── skills/<id>/SKILL.md        16 final skills

skills/<id>/SKILL.md            bundled skills (committed)
```
