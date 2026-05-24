#!/usr/bin/env python3
"""Pull public Bluesky posts for personas.

Source entry shape in personas/<id>.yaml:
  - type: bluesky
    handle: "username.bsky.social"
    max_items: 100

Saves: staging/raw/bluesky/<persona_id>.json
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/bluesky")
STAGING.mkdir(parents=True, exist_ok=True)

API_BASE = "https://public.api.bsky.app/xrpc"


def _http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "expert-mind-skill/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_author_feed(handle: str, max_items: int) -> list[dict]:
    """Fetch latest posts from public API (no auth needed for public profiles)."""
    posts = []
    cursor = None
    page_size = 100  # API max
    while len(posts) < max_items:
        params = {
            "actor": handle,
            "limit": min(page_size, max_items - len(posts)),
            "filter": "posts_no_replies",
        }
        if cursor:
            params["cursor"] = cursor
        url = f"{API_BASE}/app.bsky.feed.getAuthorFeed?{urllib.parse.urlencode(params)}"
        data = _http_get(url)
        feed = data.get("feed", [])
        if not feed:
            break
        posts.extend(feed)
        cursor = data.get("cursor")
        if not cursor:
            break
    return posts


def normalize(item: dict) -> dict:
    post = item.get("post", {})
    record = post.get("record", {})
    return {
        "id": post.get("uri", "").split("/")[-1],
        "url": post.get("uri"),
        "date": record.get("createdAt"),
        "text": record.get("text", "").strip(),
        "likes": post.get("likeCount"),
        "reposts": post.get("repostCount"),
        "replies": post.get("replyCount"),
    }


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "bluesky"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        handle = src.get("handle")
        if not handle:
            continue
        targets.append((p["id"], handle, int(src.get("max_items", 100))))

    if not targets:
        print("[done] no Bluesky targets.")
        return

    for persona_id, handle, max_items in targets:
        try:
            posts = fetch_author_feed(handle, max_items)
            out = [normalize(p) for p in posts]
            (STAGING / f"{persona_id}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
            print(f"  [done] {persona_id} ({handle}): {len(out)} posts")
        except Exception as e:
            print(f"  [fail] {persona_id} ({handle}): {e}")


if __name__ == "__main__":
    main()
