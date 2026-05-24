#!/usr/bin/env python3
"""Distill scored items into Claude Skills.

Pipeline:
1. Load scored jsonl per persona.
2. Apply regex-based framework promotion (principle → framework when markers present).
3. Optional finalize step: single Claude call per persona to deduplicate near-duplicates
   and extract voice samples from accepted item text.
4. Bucket by type, write lean skill + deep archive + eval report.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

SCORED = Path("staging/scored")
OUTPUT_SKILLS = Path("output/skills")
OUTPUT_DEEP = Path("output/deep")
OUTPUT_SKILLS.mkdir(parents=True, exist_ok=True)
OUTPUT_DEEP.mkdir(parents=True, exist_ok=True)

THRESHOLD = 0.7
MAX_PER_SECTION = {
    "principle": 22,
    "framework": 10,
    "prediction": 8,
    "opinion": 10,
    "voice_sample": 8,
    "case": 5,
}
SECTION_ORDER = ["framework", "principle", "opinion", "prediction", "case", "voice_sample"]
SECTION_TITLES = {
    "framework": "Frameworks",
    "principle": "Principles",
    "opinion": "Opinions",
    "prediction": "Predictions",
    "case": "Case studies",
    "voice_sample": "Voice samples",
}

sys.path.insert(0, str(Path(__file__).parent))
from judge import PERSONAS, call_anthropic  # noqa: E402


# ---- Framework promotion (cheap, regex-only) ----

FRAMEWORK_MARKERS = [
    re.compile(r"\b(?:[A-Z][a-z]+\s+){1,3}(?:Effect|Principle|Theory|Trap|Law|Rule|Test|Framework|Model|Stack|Mall|Proximity|Loop|Funnel|Trajectory|Curve|Equation)\b"),
    re.compile(r"\b\d+\s+(?:routes|paths|ingredients|stages|components|levels|tiers|reasons|pillars|moats|laws)\b", re.I),
    re.compile(r"\b(?:two|three|four|five|six)\s+(?:routes|paths|ingredients|stages|components|levels|tiers|reasons|pillars|moats|laws|categories|types|kinds)\b", re.I),
    re.compile(r"\bvs\.?\s+[A-Z]"),  # "X vs Y" structure
    re.compile(r"['\"][A-Z][^'\"]{3,40}['\"]"),  # quoted named concept
]


def is_framework_like(principle_text: str) -> bool:
    return any(p.search(principle_text) for p in FRAMEWORK_MARKERS)


def promote_frameworks(items: list) -> None:
    """In-place: promote `principle` items that match framework markers."""
    for it in items:
        if it.get("type") == "principle" and is_framework_like(it.get("principle", "")):
            it["type"] = "framework"


# ---- Finalize via Claude (dedup + voice samples) ----

FINALIZE_PROMPT = """You are finalizing a Claude Skill for an expert persona.

PERSONA: {name}
ROLE: {role}
VOICE: {voice}

You are given {n} accepted items, each tagged as framework/principle/opinion/prediction.

Your tasks:
1. DEDUPLICATE near-duplicates. When multiple items express the same idea, merge into one item that captures the strongest formulation. Keep distinct angles separate.
2. RE-CLASSIFY borderline items. A framework has a named concept, structural dichotomy, or enumerated components. A principle is a directional rule.
3. EXTRACT VOICE SAMPLES. Find 4-8 memorable aphoristic phrases from the items' original text (the "text" field), in the expert's signature style. Voice samples should be punchy, quotable, <25 words, with attitude.

RETURN strict JSON only, no markdown:
{{
  "frameworks":   [{{ "text": "...", "source_index": <int from input> }}, ...],     // up to 10
  "principles":   [{{ "text": "...", "source_index": <int from input> }}, ...],     // up to 22
  "opinions":     [{{ "text": "...", "source_index": <int from input> }}, ...],     // up to 10
  "predictions":  [{{ "text": "...", "source_index": <int from input> }}, ...],     // up to 8
  "voice_samples":[{{ "text": "...", "source_index": <int from input> }}, ...]      // 4-8
}}

INPUT ITEMS:
{items}
"""


def finalize_with_claude(persona: dict, by_type: dict) -> dict:
    """One-shot consolidation pass. Returns updated by_type with deduped items
    and a new 'voice_sample' bucket extracted from raw text."""
    all_items = []
    for t, items in by_type.items():
        for it in items:
            all_items.append({**it, "_original_type": t})
    if not all_items:
        return by_type

    # Format compact input
    input_lines = []
    for i, it in enumerate(all_items):
        snippet = (it.get("text") or "")[:600].replace("\n", " ")
        input_lines.append(
            f"[{i}] type={it.get('_original_type', it.get('type'))} score={it.get('score')} "
            f"principle: {it.get('principle','')}\n     text: {snippet}"
        )
    prompt = FINALIZE_PROMPT.format(
        name=persona["name"],
        role=persona["role"],
        voice=persona["voice"],
        n=len(all_items),
        items="\n".join(input_lines),
    )

    result = call_anthropic(prompt, max_tokens=4000)
    if result.get("type") == "error" or "frameworks" not in result:
        print(f"  [warn] finalize failed for {persona['name']}: {result.get('reason', 'no result')}")
        return by_type

    new_by_type = defaultdict(list)
    section_map = {
        "frameworks": "framework",
        "principles": "principle",
        "opinions": "opinion",
        "predictions": "prediction",
        "voice_samples": "voice_sample",
    }
    for key, section_type in section_map.items():
        for entry in result.get(key, []) or []:
            text = entry.get("text", "").strip()
            if not text:
                continue
            src_idx = entry.get("source_index", -1)
            src = all_items[src_idx] if 0 <= src_idx < len(all_items) else {}
            new_by_type[section_type].append({
                "principle": text,
                "score": src.get("score", 0.8),
                "source_url": src.get("source_url", ""),
                "type": section_type,
                "text": src.get("text", ""),
            })
    return new_by_type


# ---- Build skill ----

def estimate_tokens(s: str) -> int:
    return len(s) // 4


def build_skill(persona_id: str, items: list, do_finalize: bool = True) -> tuple[str, dict]:
    persona = PERSONAS[persona_id]
    accepted = [i for i in items if i["score"] >= THRESHOLD and i.get("principle")]
    promote_frameworks(accepted)

    by_type = defaultdict(list)
    for item in accepted:
        t = item.get("type", "principle")
        if t not in MAX_PER_SECTION:
            t = "principle"
        by_type[t].append(item)
    for t in by_type:
        by_type[t].sort(key=lambda x: x["score"], reverse=True)
        by_type[t] = by_type[t][:MAX_PER_SECTION[t] * 2]  # send 2x to finalizer, it'll trim

    if do_finalize:
        by_type = finalize_with_claude(persona, by_type)

    # Trim to final caps
    for t in list(by_type.keys()):
        by_type[t] = by_type[t][:MAX_PER_SECTION.get(t, 20)]

    description = f"{persona['name']} — {persona['role']}. Triggers: {', '.join(persona['expertise'])}."

    lines = [
        "---",
        f"name: {persona_id}",
        "description: |",
        f"  {description}",
        "type: persona",
        "generated_by: expert-mind-skill@v0.2",
        f"last_updated: {date.today().isoformat()}",
        "revision: 2",
        "---",
        "",
        f"# {persona['name']}",
        "",
        f"*{persona['role']}.*",
        "",
        f"**Voice:** {persona['voice']}",
        "",
    ]

    for section_type in SECTION_ORDER:
        items_in = by_type.get(section_type, [])
        if not items_in:
            continue
        lines.append(f"## {SECTION_TITLES[section_type]}")
        lines.append("")
        for it in items_in:
            text = it.get("principle", "").strip()
            if section_type == "voice_sample":
                lines.append(f'- > "{text}"')
            else:
                lines.append(f"- {text}")
        lines.append("")

    total_accepted = sum(len(by_type.get(t, [])) for t in SECTION_ORDER)
    lines.append("---")
    lines.append(
        f"*Generated from {len(items)} items, {total_accepted} kept after dedup. "
        f"Full attribution: `logs/{persona_id}.jsonl`.*"
    )

    skill_md = "\n".join(lines)
    stats = {
        "total": len(items),
        "raw_accepted": len(accepted),
        "accepted": total_accepted,
        "by_type": {t: len(by_type.get(t, [])) for t in SECTION_ORDER},
        "tokens_est": estimate_tokens(skill_md),
    }
    return skill_md, stats


def build_deep(persona_id: str, items: list) -> str:
    persona = PERSONAS[persona_id]
    accepted = [i for i in items if i["score"] >= THRESHOLD]
    accepted.sort(key=lambda x: x["score"], reverse=True)
    lines = [f"# {persona['name']} — Deep archive\n"]
    for it in accepted:
        d = (it.get("date") or "")[:10]
        lines.append(f"### [{it['score']}] {it.get('type','')} — {d}")
        if it.get("principle"):
            lines.append(f"**Principle:** {it['principle']}")
        lines.append(f"**Source:** {it.get('source')} {it.get('source_url','')}")
        lines.append(f"> {(it.get('text') or '').strip()[:1200]}")
        lines.append("")
    return "\n".join(lines)


def evaluate(stats: dict, items: list) -> dict:
    scores = [i["score"] for i in items]
    very_high = sum(1 for s in scores if s >= 0.85)

    accepted = stats["accepted"]
    if accepted >= 30:
        fullness = "high"
    elif accepted >= 15:
        fullness = "medium"
    elif accepted >= 8:
        fullness = "low"
    elif accepted >= 3:
        fullness = "very_low"
    else:
        fullness = "empty"

    has_frameworks = stats["by_type"].get("framework", 0) >= 2
    has_principles = stats["by_type"].get("principle", 0) >= 5
    has_voice = stats["by_type"].get("voice_sample", 0) >= 1
    applicability = sum([has_frameworks * 2, has_principles * 2, has_voice * 1, (very_high >= 3) * 1])
    applicability_label = ["empty", "weak", "weak", "okay", "good", "strong", "excellent"][min(applicability, 6)]

    return {
        "fullness": fullness,
        "applicability": applicability_label,
        "applicability_score": applicability,
        "tokens": stats["tokens_est"],
        "very_high_count": very_high,
    }


def main():
    args = sys.argv[1:]
    do_finalize = "--no-finalize" not in args
    targets = [a for a in args if not a.startswith("--")] or None

    results = {}
    for jsonl in sorted(SCORED.glob("*.jsonl")):
        if jsonl.name.startswith("_"):
            continue
        persona_id = jsonl.stem
        if targets and persona_id not in targets:
            continue
        if persona_id not in PERSONAS:
            continue
        # Split only on '\n' — str.splitlines() also breaks on U+2028, U+2029,
        # NEL, etc., which json.dumps(ensure_ascii=False) leaves unescaped and
        # which appear inside LinkedIn post text. Skip error rows.
        raw_lines = [ln for ln in jsonl.read_text().split("\n") if ln.strip()]
        items = [d for d in (json.loads(ln) for ln in raw_lines) if d.get("type") != "error"]
        print(f"  [distill] {persona_id} ({'with' if do_finalize else 'no'} finalize)...", flush=True)
        skill_md, stats = build_skill(persona_id, items, do_finalize=do_finalize)
        # Claude Code loads skills from `<name>/SKILL.md` directory format —
        # not flat `<name>.md`. Match the bundled-skills layout so user-generated
        # skills are activatable the same way.
        skill_dir = OUTPUT_SKILLS / persona_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_md)
        (OUTPUT_DEEP / f"{persona_id}-deep.md").write_text(build_deep(persona_id, items))
        ev = evaluate(stats, items)
        results[persona_id] = {**stats, **ev}

    print(f"\n{'persona':28s} accepted by_section                            tokens fullness  applicability")
    print("-" * 120)
    for pid, r in sorted(results.items(), key=lambda x: -x[1]["accepted"]):
        bt = r["by_type"]
        by_section = f"F:{bt['framework']:2d} P:{bt['principle']:2d} O:{bt['opinion']:2d} Pr:{bt['prediction']:2d} V:{bt['voice_sample']:2d}"
        print(f"  {pid:26s} {r['accepted']:3d}/{r['total']:3d}  {by_section}  {r['tokens']:5d}  {r['fullness']:9s} {r['applicability']}")

    rep = Path("output/_evaluation.json")
    rep.write_text(json.dumps(results, indent=2))
    print(f"\nWrote evaluation to {rep}")


if __name__ == "__main__":
    main()
