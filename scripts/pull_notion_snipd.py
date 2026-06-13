#!/usr/bin/env python3
"""Pull Snipd-derived snippets from a Notion database.

Snipd → email → Readwise → Notion is a common pipeline: a podcast snippet
the user marks on Snipd lands as a page in their Notion "Knowledge Items"
database with `Source Type = Newsletter`, `Author = Snipd | AI Podcast
Player`, and a structured body (Key Theses / Key Facts / Conclusion). For
recurring podcast guests (Lemkin, Rory, etc.) this gives a user-curated
stream of framework-dense content — much higher signal than scraping all
20VC episodes blindly.

Source entry shape in personas/<id>.yaml:
  - type: notion_snipd
    title_contains: "20VC"               # substring of page title to match
    database_id: <your-notion-database-id>   # or set EXPERT_MIND_NOTION_SNIPD_DB
    max_pages: 100                       # optional, default 100

Why title_contains rather than guest_name? Snipd export pages are titled by
episode, not by guest ("✨ Your snips for: The Twenty Minute VC - 20VC:
Anthropic Raises $30BN..."). For recurring podcast guests (Lemkin on 20VC,
Eric Seufert on Mobile Dev Memo), the right filter is the SHOW name. The
LLM judge downstream then filters non-guest content via voice description.

Saves: staging/raw/notion-snipd/<persona_id>.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

NOTION_TOKEN = (
    os.environ.get("NOTION_TOKEN")
    or os.environ.get("NOTION_READER_TOKEN")
    or ""
)
if not NOTION_TOKEN:
    raise SystemExit(
        "Missing NOTION_TOKEN or NOTION_READER_TOKEN.\n"
        "Create an internal integration at https://www.notion.so/profile/integrations\n"
        "then share your snipd-source database with that integration."
    )

# The database that holds your Snipd→Readwise→Notion pages. Set this via the
# EXPERT_MIND_NOTION_SNIPD_DB env var, or per-source with `database_id:` in
# personas/<id>.yaml.
#
# NOTE: Notion exposes two related IDs — `database` and `data-source`/`collection`.
# The /databases/{id}/query API wants the DATABASE id, not the collection id.
# Find it in your DB's URL: notion.so/<workspace>/<DATABASE_ID>?v=<view_id>.
DEFAULT_DB = os.environ.get("EXPERT_MIND_NOTION_SNIPD_DB", "")

STAGING = Path("staging/raw/notion-snipd")
STAGING.mkdir(parents=True, exist_ok=True)

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"  # stable Notion API version

# ---- HTTP helpers ----------------------------------------------------------


def _api(method: str, path: str, body: dict | None = None) -> dict:
    """Call Notion API with auth + retries on 429/5xx."""
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "expert-mind-skill/0.2",
    }
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # Notion rate limit: 429 with Retry-After. 5xx: backoff.
            if e.code in (429, 500, 502, 503, 504):
                delay = int(e.headers.get("Retry-After") or 2 ** attempt)
                time.sleep(min(delay, 30))
                continue
            err_body = (e.read().decode(errors="replace") or "")[:300]
            raise RuntimeError(f"Notion API {e.code} on {method} {path}: {err_body}") from e
    raise RuntimeError(f"Notion API exhausted retries on {method} {path}")


# ---- DB query --------------------------------------------------------------


def query_database(db_id: str, title_contains: str, max_pages: int) -> list[dict]:
    """Paginate a database query, returning up to `max_pages` matching pages.

    Filter is `Name title contains <title_contains>` — sorted newest first.
    """
    pages: list[dict] = []
    cursor: str | None = None
    while len(pages) < max_pages:
        body: dict = {
            "filter": {"property": "Name", "title": {"contains": title_contains}},
            "page_size": min(100, max_pages - len(pages)),
            "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        }
        if cursor:
            body["start_cursor"] = cursor
        resp = _api("POST", f"/databases/{db_id}/query", body)
        pages.extend(resp.get("results", []))
        cursor = resp.get("next_cursor")
        if not resp.get("has_more") or not cursor:
            break
    return pages[:max_pages]


# ---- Page content extraction ----------------------------------------------


def _rich_text_to_string(rt_list: list[dict]) -> str:
    """Notion rich_text arrays → plain string."""
    return "".join((rt.get("plain_text") or "") for rt in (rt_list or []))


def _block_text(block: dict) -> str:
    """Best-effort text extraction across common Notion block types."""
    t = block.get("type", "")
    payload = block.get(t, {}) or {}
    rt = payload.get("rich_text") or []
    text = _rich_text_to_string(rt)
    # Heading prefix so the structure survives into the judge prompt
    if t == "heading_1":
        return f"\n# {text}\n"
    if t == "heading_2":
        return f"\n## {text}\n"
    if t == "heading_3":
        return f"\n### {text}\n"
    if t == "bulleted_list_item":
        return f"- {text}\n"
    if t == "numbered_list_item":
        return f"1. {text}\n"
    if t == "quote":
        return f"> {text}\n"
    if t == "code":
        return f"```\n{text}\n```\n"
    if t == "divider":
        return "\n---\n"
    return text + "\n" if text else ""


def fetch_page_text(page_id: str) -> str:
    """Walk a page's blocks (paginated) and concatenate plain text."""
    chunks: list[str] = []
    cursor: str | None = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        resp = _api("GET", path)
        for block in resp.get("results", []):
            chunks.append(_block_text(block))
        cursor = resp.get("next_cursor")
        if not resp.get("has_more") or not cursor:
            break
    return "".join(chunks).strip()


# ---- Normalize page → judge-ready record ----------------------------------


def normalize(page: dict, body_text: str) -> dict:
    """Notion page → {id, url, date, text} same shape as other adapters."""
    props = page.get("properties", {})
    # Title: usually under "Name" property
    title_rt = props.get("Name", {}).get("title", []) if isinstance(props.get("Name"), dict) else []
    title = _rich_text_to_string(title_rt) or page.get("id", "")
    # Date: prefer page-level "Source Date" property if present, else created_time
    date = (
        props.get("Source Date", {}).get("date", {}).get("start", "")
        if isinstance(props.get("Source Date"), dict) else ""
    ) or page.get("created_time", "")
    return {
        "id": page.get("id", ""),
        "url": page.get("url", ""),
        "date": date,
        "title": title,
        "text": f"{title}\n\n{body_text}".strip(),
    }


# ---- Main driver ----------------------------------------------------------


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "notion_snipd"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        targets.append((
            p["id"],
            src.get("title_contains") or src.get("guest_name_match") or p["name"],
            src.get("database_id") or DEFAULT_DB,
            int(src.get("max_pages", 100)),
        ))

    if not targets:
        print("[done] no notion_snipd sources.")
        return

    for persona_id, title_contains, db_id, max_pages in targets:
        if not db_id:
            print(f"  [skip] {persona_id}: no Notion database configured. "
                  f"Set EXPERT_MIND_NOTION_SNIPD_DB env var, or add `database_id:` "
                  f"to the notion_snipd source in personas/{persona_id}.yaml")
            continue
        try:
            pages = query_database(db_id, title_contains, max_pages)
            print(f"  [match] {persona_id}: {len(pages)} pages with title containing '{title_contains}'")
            items = []
            for page in pages:
                body = fetch_page_text(page["id"])
                if not body:
                    continue
                items.append(normalize(page, body))
            (STAGING / f"{persona_id}.json").write_text(
                json.dumps(items, indent=2, ensure_ascii=False)
            )
            print(f"  [done] {persona_id}: {len(items)} pages saved")
        except Exception as e:
            print(f"  [fail] {persona_id}: {e}")


if __name__ == "__main__":
    main()
