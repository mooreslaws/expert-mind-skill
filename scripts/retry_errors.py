#!/usr/bin/env python3
"""Retry items in scored/<persona>.jsonl that have type='error'.

Lower concurrency (4 threads) to avoid rate limits.
"""
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from judge import PERSONAS, judge_excerpt

SCORED = Path("staging/scored")
THREADS = 4


def main():
    for jsonl in sorted(SCORED.glob("*.jsonl")):
        if jsonl.name.startswith("_"):
            continue
        persona_id = jsonl.stem
        if persona_id not in PERSONAS:
            continue
        items = [json.loads(ln) for ln in jsonl.read_text().splitlines() if ln.strip()]
        errors = [(i, it) for i, it in enumerate(items) if it.get("type") == "error"]
        if not errors:
            continue
        persona = PERSONAS[persona_id]
        print(f"  {persona_id}: retrying {len(errors)} errors", flush=True)

        with ThreadPoolExecutor(max_workers=THREADS) as ex:
            futures = {
                ex.submit(
                    judge_excerpt,
                    persona_id, persona,
                    it["source"], it["source_id"], it["source_url"], it.get("date", ""), it["text"]
                ): i
                for i, it in errors
            }
            recovered = 0
            for fut in as_completed(futures):
                i = futures[fut]
                r = fut.result()
                if r and r.get("type") != "error":
                    items[i] = r
                    recovered += 1
            print(f"    recovered {recovered}/{len(errors)}", flush=True)

        # Re-sort by score and write back
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        with jsonl.open("w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
