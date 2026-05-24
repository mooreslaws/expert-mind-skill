#!/usr/bin/env python3
"""Judge collected excerpts against expert worldview. Saves scored items per persona.

Persona passports are loaded from `personas/*.yaml` in CWD (or, if empty,
from the bundled `cold-start/registry.yaml`). See scripts/persona_loader.py.
"""
import json
import os
import random
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start  # noqa: E402

# Accept either standard or corporate key var
API_KEY = (
    os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("ANTHROPIC_CORPORATE_API_KEY")
    or ""
)
if not API_KEY:
    raise SystemExit("Missing ANTHROPIC_API_KEY (or ANTHROPIC_CORPORATE_API_KEY) in env.")

MODEL = os.environ.get("EXPERT_MIND_JUDGE_MODEL", "claude-sonnet-4-5")

# Adapters write to staging/raw/<source>/<persona_id>.json. Judge auto-discovers
# every subdir under staging/raw/ via collect_excerpts() — no per-adapter wiring.
SCORED = Path("staging/scored")
SCORED.mkdir(parents=True, exist_ok=True)

MIN_TEXT_LEN = 120
MAX_TEXT_LEN = 6000
THREADS = 12


def _load_all_personas() -> dict[str, dict]:
    """Load from personas/, fallback to cold-start. Returns {id: passport}."""
    from_yaml = {p["id"]: p for p in load_personas()}
    if from_yaml:
        return from_yaml
    return load_cold_start()


PERSONAS = _load_all_personas()

JUDGE_PROMPT = """You are a calibration judge for expert mental models.

PERSONA:
  Name: {name}
  Role: {role}
  Expertise: {expertise}
  Voice: {voice}

EXCERPT (from {source}):
{text}

TASK:
Score 0.0-1.0 how strongly this excerpt expresses {name}'s REUSABLE mental model,
framework, principle, or opinion (vs reporting facts, news, status, or merely citing others).

SCORING:
- 0.8-1.0: "if X then Y" rules, named frameworks, dichotomies, strong counter-intuitive claims with mechanism
- 0.6-0.8: opinions backed by mechanism/data, voice-distinctive takes
- 0.4-0.6: borderline (mix of fact and stance)
- 0.0-0.4: news, raw stats, company announcements, polite responses, promo copy, generic motivational

TYPE DEFINITIONS (pick the most specific that fits):
- framework: NAMED mental model with structure. Markers: has a name in quotes/caps (e.g. "Native Agent Proximity", "Millionaire's Mall"), or contains "X vs Y", or lists 2+ named components/stages/ingredients.
- principle: If-then rule or directional claim without explicit name or internal structure. (e.g. "Activation before monetization.")
- opinion: Stance with mechanism, but without rule/framework form. (e.g. "Apple's services revenue is increasingly ads-dependent.")
- case: Specific company/event example illustrating a point. Use only when the case IS the takeaway.
- voice_sample: A memorable aphoristic phrasing in the expert's signature style (short, quotable, punchy).
- prediction: Forward-looking claim about market/tech evolution with mechanism.

WHEN UNSURE between principle and framework: lean framework if there's any named concept, structural dichotomy, or enumerated list. Frameworks are the most reusable artifact in a skill.

OUTPUT strict JSON only (no markdown, no preamble):
{{"score": <float>, "type": "<str>", "principle": "<1-2 sentence distillation OR empty>", "voice_quote": "<single punchy aphoristic phrase from excerpt OR empty>", "reason": "<1 short sentence>"}}
"""


MAX_ATTEMPTS = 6


def call_anthropic(prompt: str, max_tokens: int = 500) -> dict:
    """Call Anthropic with exponential backoff + jitter on transient failures.

    429/5xx: retry up to MAX_ATTEMPTS, honor Retry-After if present.
    Connection errors: same.
    Hard 4xx (other): no retry, return error result.
    """
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    last_err = "unknown"
    for attempt in range(MAX_ATTEMPTS):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body, method="POST"
        )
        req.add_header("x-api-key", API_KEY)
        req.add_header("anthropic-version", "2023-06-01")
        req.add_header("content-type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            txt = d["content"][0]["text"].strip()
            if txt.startswith("```"):
                txt = txt.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(txt)
        except urllib.error.HTTPError as e:
            err_body = (e.read().decode() or "")[:500]
            # Keep the full 500 chars so messages like "credit balance too low"
            # don't get truncated at "credit b". 500 fits a typical Anthropic
            # error envelope including suggested remediation.
            last_err = f"HTTP {e.code}: {err_body}"
            if e.code in (429, 500, 502, 503, 504, 529):
                retry_after = e.headers.get("Retry-After") if hasattr(e, "headers") else None
                if retry_after and retry_after.isdigit():
                    delay = min(int(retry_after), 60)
                else:
                    delay = min(2 ** attempt, 30) + random.uniform(0, 1.5)
                time.sleep(delay)
                continue
            return {"score": 0.0, "type": "error", "principle": "", "voice_quote": "", "reason": last_err}
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last_err = str(e)[:120]
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1.5))
                continue
        except Exception as e:
            last_err = str(e)[:120]
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1.5))
                continue
    return {"score": 0.0, "type": "error", "principle": "", "voice_quote": "", "reason": f"exhausted: {last_err}"}


def judge_excerpt(persona_id: str, persona: dict, source: str, source_id: str, source_url: str, date: str, text: str) -> dict:
    if not text or len(text) < MIN_TEXT_LEN:
        return None
    truncated = text[:MAX_TEXT_LEN]
    prompt = JUDGE_PROMPT.format(
        name=persona["name"],
        role=persona["role"],
        expertise=", ".join(persona["expertise"]),
        voice=persona["voice"],
        source=source,
        text=truncated,
    )
    result = call_anthropic(prompt)
    return {
        "persona_id": persona_id,
        "source": source,
        "source_id": source_id,
        "source_url": source_url,
        "date": date,
        "text": text,
        "score": result.get("score", 0.0),
        "type": result.get("type", ""),
        "principle": result.get("principle", ""),
        "voice_quote": result.get("voice_quote", ""),
        "reason": result.get("reason", ""),
    }


def collect_excerpts(persona_id: str):
    """Collect from all sources for one persona.

    Auto-discovers any directory under `staging/raw/*/` containing a
    `<persona_id>.json` — this means new adapters work automatically without
    judge.py code changes. LinkedIn keeps a special handler because its JSON
    shape (`content` + `linkedinUrl`) differs from the generic `{text, url, date, id}` pattern.
    """
    excerpts = []
    staging_root = Path("staging/raw")

    # LinkedIn (special shape: posts have `content` key + `linkedinUrl`)
    lin_path = staging_root / "linkedin" / f"{persona_id}.json"
    if lin_path.exists():
        for p in json.loads(lin_path.read_text()):
            content = p.get("content") or ""
            if len(content) < MIN_TEXT_LEN:
                continue
            excerpts.append({
                "source": "linkedin",
                "source_id": p.get("id", ""),
                "source_url": p.get("linkedinUrl", ""),
                "date": p.get("postedAt", {}).get("date", ""),
                "text": content,
            })

    # Generic-shape sources — auto-discover every other subdir of staging/raw/
    if staging_root.exists():
        for sub in sorted(staging_root.iterdir()):
            if not sub.is_dir() or sub.name in ("linkedin",):
                continue
            path = sub / f"{persona_id}.json"
            if not path.exists():
                continue
            for it in json.loads(path.read_text()):
                t = it.get("text") or ""
                if len(t) < MIN_TEXT_LEN:
                    continue
                excerpts.append({
                    "source": sub.name,
                    "source_id": str(it.get("id", "")),
                    "source_url": it.get("url") or it.get("link", ""),
                    "date": it.get("date", ""),
                    "text": t,
                })

    return excerpts


def run_for_persona(persona_id: str):
    persona = PERSONAS.get(persona_id)
    if not persona:
        print(f"  [skip] no persona config: {persona_id}", flush=True)
        return
    excerpts = collect_excerpts(persona_id)
    if not excerpts:
        print(f"  [skip] no excerpts: {persona_id}", flush=True)
        return

    out = SCORED / f"{persona_id}.jsonl"
    print(f"\n=== {persona_id}: {len(excerpts)} excerpts to judge ===", flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {
            ex.submit(
                judge_excerpt, persona_id, persona,
                e["source"], e["source_id"], e["source_url"], e["date"], e["text"]
            ): i
            for i, e in enumerate(excerpts)
        }
        done = 0
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)
            done += 1
            if done % 25 == 0:
                print(f"  {persona_id}: {done}/{len(excerpts)} judged", flush=True)

    # Sort by score desc
    results.sort(key=lambda x: x["score"], reverse=True)
    # ensure_ascii=True escapes Unicode line-separators (U+2028, U+2029, NEL),
    # which would otherwise survive into the output and break naive
    # splitlines()-based readers downstream.
    with out.open("w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    # Summary
    errors = [r for r in results if r.get("type") == "error"]
    real = [r for r in results if r.get("type") != "error"]
    scores = [r["score"] for r in real]
    high = sum(1 for s in scores if s >= 0.7)
    mid = sum(1 for s in scores if 0.5 <= s < 0.7)
    low = sum(1 for s in scores if s < 0.5)
    err_marker = f" ⚠️  ERRORS={len(errors)}" if errors else ""
    print(f"  [done] {persona_id}: high={high} mid={mid} low={low} "
          f"(total real={len(real)}){err_marker}", flush=True)
    if errors:
        # Surface the first error reason so the user can see WHY (auth, credits,
        # rate-limit, etc.) rather than silently counting them as low scores.
        print(f"    first error: {errors[0].get('reason', '?')[:160]}", flush=True)


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PERSONAS.keys())
    targets = [t for t in targets if t in PERSONAS]
    for pid in targets:
        run_for_persona(pid)
    print("\n[all done]")


if __name__ == "__main__":
    main()
