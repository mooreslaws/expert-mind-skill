# Contributing

Thanks for considering a contribution. Two paths are most valuable:

1. **Add a new persona** to the `cold-start/registry.yaml` so other users can
   one-click import a starter passport for a known expert.
2. **Add a new source adapter** so personas can be fed from a new platform.

Both are documented below. PRs welcome.

---

## Adding a persona to the cold-start registry

The registry ships pre-filled passports. Users see them in `/init` Step 2 and
can multi-pick which to activate. Adding a new persona requires no code.

1. Fork the repo.
2. Open `cold-start/registry.yaml`.
3. Add a new entry following the schema:

```yaml
<persona-id>:                   # kebab-case, e.g. naval-ravikant
  name: <Display Name>
  role: <one-line role>
  expertise: [<tag>, <tag>, ...]    # used in skill description for activation
  voice: |
    2-3 sentences describing this author's distinctive speech.
    The judge uses this to filter relevant content from noise.
  groups: [<category>, ...]         # one or more from: marketing, product,
                                    # strategy, ai, finance, leadership,
                                    # design, sales
  recommended_sources:
    - type: rss                     # free, always recommend if author has a blog
      url: https://example.com/feed
      auth: none
      cost_note: free
    - type: linkedin_apify          # needs APIFY_TOKEN
      handle: example-handle
      auth: APIFY_TOKEN
      cost_note: "~$0.002/post"
    # ... add more source types as appropriate
```

4. (Optional but recommended) Generate a sample SKILL.md by running the
   pipeline against your own data, then commit
   `skills/<persona-id>/SKILL.md`. This pre-fills the skill for users who
   want to use this persona without running the pipeline themselves.

5. Open a PR with subject `Add <name> to cold-start registry`.

### Picking a good `voice` description

This is the single highest-leverage field. The LLM judge uses it to decide
which content qualifies as "this author's actual lens" vs noise. Two tips:

- **Be specific about syntax and topics.** "Likes data-driven examples" is
  too vague. "Anchors abstractions in concrete dollar amounts; cites own
  prior essays; uses Galbraith-style historical framing" is good.
- **Pick distinctive features.** What does this person say that no one else
  would say? That's the voice.

---

## Adding a new source adapter

Each adapter is a single Python file in `scripts/` named `pull_<source>.py`
or `scrape_<source>.py`. Existing examples: `pull_rss.py` (free, simplest),
`pull_mastodon.py` (free, uses public API), `scrape_linkedin.py` (paid, uses
Apify).

### Protocol

The adapter reads from `personas/*.yaml`, finds sources with matching `type`,
fetches content, normalises it, and writes to
`staging/raw/<adapter_dir>/<persona_id>.json`.

Output format (consumed by `judge.py`):

```json
[
  {
    "id": "unique-string",
    "url": "https://...",
    "date": "2026-05-17T...",
    "text": "the actual content to judge",
    "...other fields": "are kept but not used by judge"
  },
  ...
]
```

### Boilerplate

```python
#!/usr/bin/env python3
"""Pull <SOURCE> for personas.

Source entry shape in personas/<id>.yaml:
  - type: <source-type>
    <required fields>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type

STAGING = Path("staging/raw/<adapter-dir>")
STAGING.mkdir(parents=True, exist_ok=True)


def fetch_for_persona(persona_id: str, src: dict) -> list[dict]:
    # ... your fetch logic ...
    return []


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    for p, src in sources_of_type(personas, "<source-type>"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        items = fetch_for_persona(p["id"], src)
        out = STAGING / f"{p['id']}.json"
        out.write_text(json.dumps(items, indent=2, ensure_ascii=False))
        print(f"  [done] {p['id']}: {len(items)} items")


if __name__ == "__main__":
    main()
```

### Register the adapter in orchestrator.py

In `scripts/orchestrator.py`, add to the `INGEST_DISPATCH` list:

```python
INGEST_DISPATCH = [
    # ...existing entries...
    ("<source-type>", "pull_<source>.py", "<ENV_VAR or None>"),
]
```

### Register the adapter type in wizard_state.py

In `scripts/wizard_state.py`, add to `SOURCE_AUTH_MAP`:

```python
SOURCE_AUTH_MAP = {
    # ...existing entries...
    "<source-type>": "<ENV_VAR or None>",
}
```

### Update README

Add a row to the "Supported source types" table in `README.md`. Be honest
about auth requirements, costs, and reliability.

### Test

Run `python tests/test_smoke.py` — `test_all_adapters_import` should pass.

---

## Development setup

```bash
git clone https://github.com/mooreslaws/expert-mind-skill
cd expert-mind-skill
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff

# Run the smoke tests
python tests/test_smoke.py

# Lint
ruff check scripts/ tests/
```

---

## Reporting bugs

Open an issue with:
- What you tried (the command or wizard step)
- What you expected
- What happened (paste the output of `/expert-mind-skill:status` if relevant)
- Versions: Python (`python --version`), this plugin's version (from `.claude-plugin/plugin.json`)

---

## Code style

- No external dependencies beyond `pyyaml` and what's already in
  `requirements.txt`. New adapters should use stdlib when possible.
- Each adapter is a self-contained script — no shared state.
- Tests should not make real API calls unless explicitly marked as
  integration tests.
