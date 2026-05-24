#!/usr/bin/env python3
"""Pull public Mastodon statuses for personas.

Source entry shape in personas/<id>.yaml:
  - type: mastodon
    instance: "mastodon.social"     # or "hachyderm.io", "fosstodon.org", etc.
    handle: "username"
    max_items: 100                  # optional, default 100

Saves: staging/raw/mastodon/<persona_id>.json
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/mastodon")
STAGING.mkdir(parents=True, exist_ok=True)


class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buf = []

    def handle_data(self, d):
        self.buf.append(d)


def strip_html(s: str) -> str:
    if not s:
        return ""
    p = _Stripper()
    p.feed(s)
    return re.sub(r"\s+", " ", "".join(p.buf)).strip()


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "expert-mind-skill/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch_account_statuses(instance: str, handle: str, max_items: int) -> list[dict]:
    instance = instance.strip().rstrip("/").replace("https://", "").replace("http://", "")
    handle = handle.strip().lstrip("@")

    # Step 1 — look up account id
    lookup_url = f"https://{instance}/api/v1/accounts/lookup?{urllib.parse.urlencode({'acct': handle})}"
    account = json.loads(_http_get(lookup_url))
    if "id" not in account:
        raise RuntimeError(f"could not resolve account @{handle}@{instance}: {account}")

    # Step 2 — fetch statuses (paginate)
    statuses = []
    max_id = None
    page_size = 40  # Mastodon API max
    while len(statuses) < max_items:
        params = {"limit": min(page_size, max_items - len(statuses))}
        if max_id:
            params["max_id"] = max_id
        url = f"https://{instance}/api/v1/accounts/{account['id']}/statuses?{urllib.parse.urlencode(params)}"
        page = json.loads(_http_get(url))
        if not page:
            break
        statuses.extend(page)
        max_id = page[-1]["id"]
    return statuses


def normalize(status: dict, instance: str) -> dict:
    return {
        "id": status.get("id"),
        "url": status.get("url"),
        "date": status.get("created_at"),
        "text": strip_html(status.get("content", "")),
        "reblogs_count": status.get("reblogs_count"),
        "favourites_count": status.get("favourites_count"),
        "instance": instance,
    }


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "mastodon"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        instance = src.get("instance")
        handle = src.get("handle")
        if not instance or not handle:
            print(f"  [skip] {p['id']}: mastodon source missing instance/handle")
            continue
        targets.append((p["id"], instance, handle, int(src.get("max_items", 100))))

    if not targets:
        print("[done] no Mastodon targets.")
        return

    for persona_id, instance, handle, max_items in targets:
        try:
            statuses = fetch_account_statuses(instance, handle, max_items)
            out = [normalize(s, instance) for s in statuses if not s.get("reblog")]
            (STAGING / f"{persona_id}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
            print(f"  [done] {persona_id} (@{handle}@{instance}): {len(out)} statuses")
        except Exception as e:
            print(f"  [fail] {persona_id} (@{handle}@{instance}): {e}")


if __name__ == "__main__":
    main()
