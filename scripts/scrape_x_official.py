#!/usr/bin/env python3
"""Pull X/Twitter tweets via the official X API v2.

Two paths exist for X content in this plugin:

  - `x_apify`     — Apify scraper (this is the recommended default).
                    Cost: ~$0.003/tweet, no monthly subscription.
                    For 500 tweets × weekly cron: ~$1.50/week per persona.

  - `x_official`  — X API v2 (this adapter). Use ONLY if you already pay for
                    Basic ($100/mo) or higher. Free tier doesn't allow reading
                    other users' tweets — you'd hit 403 immediately.
                    Cost: flat monthly subscription, then no per-tweet cost.
                    Pays off only at thousands of tweets/month.

Source entry shape in personas/<id>.yaml:
  - type: x_official
    handle: "eric_seufert"        # without @
    max_items: 500                # optional, default 500

Env vars required:
  X_BEARER_TOKEN    Bearer token from https://developer.x.com/portal/dashboard
                    (sometimes labelled "App-Only Bearer Token")

Saves: staging/raw/x/<persona_id>.json   (same dir as x_apify — don't enable both)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
if not X_BEARER_TOKEN:
    raise SystemExit(
        "Missing X_BEARER_TOKEN. Get one at https://developer.x.com/portal/dashboard "
        "(needs Basic tier or higher for reading other users' tweets)."
    )

STAGING = Path("staging/raw/x")
STAGING.mkdir(parents=True, exist_ok=True)

API_BASE = "https://api.twitter.com/2"
TWEET_FIELDS = "created_at,public_metrics,referenced_tweets"
USER_FIELDS = "id,username"


def _api_get(path: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {X_BEARER_TOKEN}",
        "User-Agent": "expert-mind-skill/0.2",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        if e.code == 401:
            raise RuntimeError("X API 401 — token invalid or expired") from e
        if e.code == 403:
            raise RuntimeError(
                "X API 403 — your tier doesn't allow reading other users' tweets. "
                "Free tier blocks this. Upgrade to Basic, or use x_apify instead."
            ) from e
        if e.code == 429:
            raise RuntimeError(f"X API rate-limited: {body}") from e
        raise RuntimeError(f"X API {e.code}: {body}") from e


def resolve_user_id(handle: str) -> str:
    handle = handle.lstrip("@")
    data = _api_get(f"/users/by/username/{handle}", {"user.fields": USER_FIELDS})
    if "data" not in data:
        raise RuntimeError(f"could not resolve user @{handle}: {data}")
    return data["data"]["id"]


def fetch_user_tweets(user_id: str, max_items: int) -> list[dict]:
    """Paginate through up to max_items most recent tweets (excluding RTs and replies)."""
    tweets = []
    pagination_token = None
    page_size = min(100, max_items)
    while len(tweets) < max_items:
        params = {
            "tweet.fields": TWEET_FIELDS,
            "max_results": page_size,
            "exclude": "retweets,replies",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        page = _api_get(f"/users/{user_id}/tweets", params)
        data = page.get("data", [])
        if not data:
            break
        tweets.extend(data)
        pagination_token = page.get("meta", {}).get("next_token")
        if not pagination_token:
            break
        # Be polite — X API rate limits are tight
        time.sleep(1)
    return tweets[:max_items]


def normalize(tweet: dict, handle: str) -> dict:
    metrics = tweet.get("public_metrics", {})
    return {
        "id": tweet.get("id", ""),
        "url": f"https://twitter.com/{handle}/status/{tweet.get('id', '')}",
        "date": tweet.get("created_at", ""),
        "text": tweet.get("text", "").strip(),
        "likes": metrics.get("like_count"),
        "retweets": metrics.get("retweet_count"),
        "replies": metrics.get("reply_count"),
    }


def main():
    cli_filter = set(a for a in sys.argv[1:] if not a.startswith("--"))
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "x_official"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        handle = src.get("handle")
        if not handle:
            continue
        targets.append((p["id"], handle.lstrip("@"), int(src.get("max_items", 500))))

    if not targets:
        print("[done] no x_official sources.")
        return

    for persona_id, handle, max_items in targets:
        try:
            user_id = resolve_user_id(handle)
            tweets = fetch_user_tweets(user_id, max_items)
            items = [normalize(t, handle) for t in tweets]
            (STAGING / f"{persona_id}.json").write_text(
                json.dumps(items, indent=2, ensure_ascii=False)
            )
            print(f"  [done] {persona_id} (@{handle}): {len(items)} tweets")
        except Exception as e:
            print(f"  [fail] {persona_id} (@{handle}): {e}")


if __name__ == "__main__":
    main()
