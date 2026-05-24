#!/usr/bin/env python3
"""Import manually-provided text content for personas.

For personas with `type: manual_text` sources, this script reads pre-collected
content from the user's `staging/raw/manual/<persona_id>/` directory. The user
puts text files there themselves — anything from "I copy-pasted 10 of his
posts" to "I exported my Snipd JSON and turned it into .txt files".

Source entry shape in personas/<id>.yaml:
  - type: manual_text
    path: "staging/raw/manual/<persona_id>/"   # optional override
    pattern: "*.txt"                            # optional, default *.txt
    source_url_prefix: "https://example.com/"   # optional, used in attribution

Saves: staging/raw/manual/<persona_id>.json (consolidated)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

OUT = Path("staging/raw/manual")
OUT.mkdir(parents=True, exist_ok=True)


def import_for_persona(persona_id: str, src: dict) -> int:
    path = Path(src.get("path") or f"staging/raw/manual/{persona_id}/")
    pattern = src.get("pattern", "*.txt")
    prefix = src.get("source_url_prefix", "")

    if not path.exists():
        print(f"  [empty] {persona_id}: {path} does not exist — create it and drop .txt files inside")
        return 0

    items = []
    for f in sorted(path.glob(pattern)):
        if not f.is_file():
            continue
        text = f.read_text().strip()
        if not text:
            continue
        items.append({
            "id": f.stem,
            "url": prefix + f.name if prefix else "",
            "date": "",
            "text": text,
            "filename": f.name,
        })

    out_file = OUT / f"{persona_id}.json"
    out_file.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    print(f"  [done] {persona_id}: imported {len(items)} files from {path}")
    return len(items)


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    pairs = [(p, s) for p, s in sources_of_type(personas, "manual_text")
             if not cli_filter or p["id"] in cli_filter]
    if not pairs:
        print("[done] no manual_text sources.")
        return
    total = sum(import_for_persona(p["id"], s) for p, s in pairs)
    print(f"\n[total] {total} items imported across {len(pairs)} personas")


if __name__ == "__main__":
    main()
