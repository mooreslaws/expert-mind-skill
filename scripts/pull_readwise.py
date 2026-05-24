#!/usr/bin/env python3
"""Pull saved articles from Readwise Reader.

Source entry shape in personas/<id>.yaml:
  - type: readwise_reader
    tag: "eric-seufert"          # filter by Reader tag
    location: "shortlist"        # one of: shortlist (default), later, archive, feed
    max_items: 100               # optional, default 100

Saves: staging/raw/readwise/<persona_id>.json

API reference: https://readwise.io/reader_api
Get a token at: https://readwise.io/access_token
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

READWISE_TOKEN = os.environ.get("READWISE_TOKEN")
if not READWISE_TOKEN:
    raise SystemExit(
        "Missing READWISE_TOKEN. Get one at https://readwise.io/access_token"
    )

STAGING = Path("staging/raw/readwise")
STAGING.mkdir(parents=True, exist_ok=True)

API_BASE = "https://readwise.io/api/v3"


def _api_get(path: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Token {READWISE_TOKEN}",
        "User-Agent": "expert-mind-skill/0.2",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_documents(tag: str | None, location: str, max_items: int) -> list[dict]:
    """Paginate through Readwise Reader documents in `location`, filtered by tag."""
    docs = []
    cursor = None
    while len(docs) < max_items:
        params = {"location": location}
        if cursor:
            params["pageCursor"] = cursor
        try:
            page = _api_get("/list/", params)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Readwise API {e.code}: {e.read().decode()[:200]}") from e
        results = page.get("results", [])
        if tag:
            tag_lower = tag.lower()
            results = [
                d for d in results
                if any(t.lower() == tag_lower for t in (d.get("tags") or {}).keys())
            ]
        docs.extend(results)
        cursor = page.get("nextPageCursor")
        if not cursor:
            break
    return docs[:max_items]


def normalize(doc: dict) -> dict:
    text_chunks = [doc.get("summary") or "", doc.get("content") or "", doc.get("clean_html") or ""]
    text = "\n\n".join(t for t in text_chunks if t).strip()
    return {
        "id": doc.get("id", ""),
        "url": doc.get("source_url") or doc.get("url") or "",
        "date": doc.get("saved_at") or doc.get("published_date") or "",
        "title": doc.get("title", ""),
        "text": text,
    }


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "readwise_reader"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        targets.append((
            p["id"],
            src.get("tag"),
            src.get("location", "shortlist"),
            int(src.get("max_items", 100)),
        ))

    if not targets:
        print("[done] no readwise_reader sources.")
        return

    for persona_id, tag, location, max_items in targets:
        try:
            docs = fetch_documents(tag=tag, location=location, max_items=max_items)
            items = [normalize(d) for d in docs]
            (STAGING / f"{persona_id}.json").write_text(
                json.dumps(items, indent=2, ensure_ascii=False)
            )
            label = f"tag={tag}, " if tag else ""
            print(f"  [done] {persona_id} ({label}location={location}): {len(items)} docs")
        except Exception as e:
            print(f"  [fail] {persona_id}: {e}")


if __name__ == "__main__":
    main()
