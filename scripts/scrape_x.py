#!/usr/bin/env python3
"""Scrape X/Twitter posts for personas via Apify (apidojo actor).

Persona-driven: iterates personas/*.yaml (falls back to cold-start registry),
finds `x_apify` sources, scrapes each handle.

Saves: staging/raw/x/<persona_id>.json
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

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise SystemExit("Missing APIFY_TOKEN in env. Get one at https://apify.com/sign-up")

# Reliable, no-cookies X/Twitter scraper. Cheaper than the original Twitter API.
ACTOR = "apidojo~twitter-scraper-lite"
STAGING = Path("staging/raw/x")
STAGING.mkdir(parents=True, exist_ok=True)

MAX_TWEETS = int(os.environ.get("EXPERT_MIND_X_MAX_TWEETS", "500"))


def _api(method, path, data=None, params=None):
    url = f"https://api.apify.com/v2{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {APIFY_TOKEN}")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def start_run(handle: str, max_tweets: int) -> str:
    """Trigger an X scrape for one handle."""
    payload = {
        "twitterHandles": [handle.lstrip("@")],
        "maxItems": max_tweets,
        "sort": "Latest",
    }
    r = _api("POST", f"/acts/{ACTOR}/runs", data=payload)
    return r["data"]["id"]


def run_status(run_id: str):
    r = _api("GET", f"/actor-runs/{run_id}")
    return r["data"]["status"], r["data"].get("defaultDatasetId")


def fetch_dataset(dataset_id: str) -> list:
    r = _api("GET", f"/datasets/{dataset_id}/items",
             params={"clean": "true", "format": "json"})
    return r if isinstance(r, list) else r.get("items", [])


def _gather_targets() -> list[tuple[str, str]]:
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for persona, src in sources_of_type(personas, "x_apify"):
        handle = src.get("handle")
        if not handle:
            continue
        targets.append((persona["id"], handle.lstrip("@")))
    return targets


def main():
    cli_filter = set(a for a in sys.argv[1:] if not a.startswith("--"))
    force = "--force" in sys.argv

    targets = _gather_targets()
    if cli_filter:
        targets = [t for t in targets if t[0] in cli_filter]
    if not targets:
        print("[done] no X targets to scrape.")
        return

    print(f"[start] launching {len(targets)} Apify X runs, max {MAX_TWEETS} tweets each", flush=True)
    runs = []
    for persona_id, handle in targets:
        out = STAGING / f"{persona_id}.json"
        if out.exists() and out.stat().st_size > 50 and not force:
            print(f"  [skip] {persona_id} already scraped", flush=True)
            continue
        try:
            run_id = start_run(handle, MAX_TWEETS)
            print(f"  [start] {persona_id} (@{handle}): run={run_id}", flush=True)
            runs.append((persona_id, run_id))
        except Exception as e:
            print(f"  [fail-to-start] {persona_id}: {e}", flush=True)

    pending = {p: rid for p, rid in runs}
    poll = 0
    while pending:
        time.sleep(15)
        poll += 1
        finished = []
        for persona_id, run_id in list(pending.items()):
            try:
                status, dataset_id = run_status(run_id)
            except Exception as e:
                print(f"  [poll-err] {persona_id}: {e}", flush=True)
                continue
            if status == "SUCCEEDED":
                items = fetch_dataset(dataset_id)
                out = STAGING / f"{persona_id}.json"
                out.write_text(json.dumps(items, indent=2))
                print(f"  [done] {persona_id}: {len(items)} tweets saved", flush=True)
                finished.append(persona_id)
            elif status in ("FAILED", "ABORTED", "TIMED-OUT", "TIMED_OUT"):
                print(f"  [{status}] {persona_id}: run={run_id}", flush=True)
                finished.append(persona_id)
        for p in finished:
            del pending[p]
        if pending and poll % 4 == 0:
            print(f"  [waiting tick={poll}] still pending: {sorted(pending)}", flush=True)

    print("\n[done] all X runs complete.", flush=True)


if __name__ == "__main__":
    main()
