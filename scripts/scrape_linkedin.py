#!/usr/bin/env python3
"""Scrape LinkedIn posts for personas via Apify (harvestapi actor).

Persona-driven: iterates personas/*.yaml (falls back to cold-start registry),
finds `linkedin_apify` sources, scrapes each handle.

Saves: staging/raw/linkedin/<persona_id>.json
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

ACTOR = "harvestapi~linkedin-profile-posts"
STAGING = Path("staging/raw/linkedin")
STAGING.mkdir(parents=True, exist_ok=True)

MAX_POSTS = int(os.environ.get("EXPERT_MIND_LINKEDIN_MAX_POSTS", "100"))


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


def start_run(target_url: str, max_posts: int) -> str:
    payload = {
        "targetUrls": [target_url],
        "maxPosts": max_posts,
        "includeReposts": False,
        "includeQuotePosts": True,
    }
    r = _api("POST", f"/acts/{ACTOR}/runs", data=payload)
    return r["data"]["id"]


def run_status(run_id: str):
    r = _api("GET", f"/actor-runs/{run_id}")
    return r["data"]["status"], r["data"].get("defaultDatasetId")


def fetch_dataset(dataset_id: str) -> list:
    r = _api("GET", f"/datasets/{dataset_id}/items", params={"clean": "true", "format": "json"})
    return r if isinstance(r, list) else r.get("items", [])


def _handle_to_url(handle: str) -> str:
    handle = handle.strip().lstrip("@")
    if handle.startswith("https://"):
        return handle
    return f"https://www.linkedin.com/in/{handle}/"


def _gather_targets() -> list[tuple[str, str]]:
    """Returns [(persona_id, linkedin_url)] from enabled linkedin_apify sources."""
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for persona, src in sources_of_type(personas, "linkedin_apify"):
        handle = src.get("handle") or src.get("url")
        if not handle:
            print(f"  [skip] {persona['id']}: linkedin_apify source has no handle/url")
            continue
        url = _handle_to_url(handle)
        targets.append((persona["id"], url))
    return targets


def main():
    cli_filter = set(sys.argv[1:])  # optional: only run for these persona ids
    targets = _gather_targets()
    if cli_filter:
        targets = [t for t in targets if t[0] in cli_filter]
    if not targets:
        print("[done] no LinkedIn targets to scrape.")
        return

    print(f"[start] launching {len(targets)} Apify runs, max {MAX_POSTS} posts each", flush=True)
    runs = []
    for persona_id, url in targets:
        out = STAGING / f"{persona_id}.json"
        if out.exists() and out.stat().st_size > 50 and "--force" not in sys.argv:
            print(f"  [skip] {persona_id} already scraped ({out.stat().st_size} bytes)", flush=True)
            continue
        try:
            run_id = start_run(url, MAX_POSTS)
            print(f"  [start] {persona_id}: run={run_id}", flush=True)
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
                print(f"  [done] {persona_id}: {len(items)} posts saved", flush=True)
                finished.append(persona_id)
            elif status in ("FAILED", "ABORTED", "TIMED-OUT", "TIMED_OUT"):
                print(f"  [{status}] {persona_id}: run={run_id}", flush=True)
                finished.append(persona_id)
        for p in finished:
            del pending[p]
        if pending and poll % 4 == 0:
            print(f"  [waiting tick={poll}] still pending: {sorted(pending)}", flush=True)

    print("\n[done] all runs complete.", flush=True)
    total = 0
    for persona_id, _ in targets:
        out = STAGING / f"{persona_id}.json"
        if out.exists():
            data = json.loads(out.read_text())
            total += len(data)
    print(f"[total] {total} posts across {len(targets)} personas", flush=True)


if __name__ == "__main__":
    main()
