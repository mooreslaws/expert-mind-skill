#!/usr/bin/env python3
"""Pull public Telegram channel messages via the `t.me/s/<channel>` HTML view.

This is a no-auth HTML scrape. No Telethon, no API ID/hash, no phone code.
Limitation: the public preview shows the most recent ~20 messages per page.
For a weekly cadence that's plenty; for first-load you may want to run
multiple times or use a richer adapter (out of scope here).

Source entry shape in personas/<id>.yaml:
  - type: telegram_public
    channel: "mobiledevmemo"     # username without @
    max_items: 50                # optional, default 50

Saves: staging/raw/telegram/<persona_id>.json
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/telegram")
STAGING.mkdir(parents=True, exist_ok=True)


# Each Telegram channel preview page is HTML with one .tgme_widget_message_wrap
# block per post. We extract three fields with regex (stable across years of t.me).
MSG_BLOCK_RE = re.compile(
    r'data-post="([^"]+)"[\s\S]*?'                                       # post id
    r'(?:datetime="([^"]+)"[\s\S]*?)?'                                    # date (optional)
    r'<div\s+class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)</div>'  # body
)


def _strip_tags(html: str) -> str:
    # Replace <br> with newlines first (Telegram uses these as separators)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    # Convert links to plain text (keep link href in trailing parens for context)
    html = re.sub(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: f"{m.group(2)} ({m.group(1)})" if m.group(2).strip() != m.group(1) else m.group(1),
        html, flags=re.I | re.DOTALL,
    )
    # Strip any remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode HTML entities (just common ones, no full table)
    text = (text.replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_html(html: str, max_items: int) -> list[dict]:
    messages = []
    for m in MSG_BLOCK_RE.finditer(html):
        post_id, date, body_html = m.group(1), m.group(2) or "", m.group(3)
        text = _strip_tags(body_html)
        if not text:
            continue
        messages.append({
            "id": post_id,
            "url": f"https://t.me/{post_id}",
            "date": date,
            "text": text,
        })
        if len(messages) >= max_items:
            break
    return messages


def fetch_channel(channel: str, max_items: int) -> list[dict]:
    channel = channel.strip().lstrip("@").lstrip("https://t.me/").lstrip("t.me/").strip("/")
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 expert-mind-skill/0.2"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="ignore")
    if "tgme_widget_message" not in html:
        raise RuntimeError(f"channel '{channel}' has no public preview (private or doesn't exist?)")
    return parse_html(html, max_items)


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "telegram_public"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        channel = src.get("channel") or src.get("handle")
        if not channel:
            continue
        targets.append((p["id"], channel, int(src.get("max_items", 50))))

    if not targets:
        print("[done] no telegram_public sources.")
        return

    for persona_id, channel, max_items in targets:
        try:
            items = fetch_channel(channel, max_items)
            (STAGING / f"{persona_id}.json").write_text(
                json.dumps(items, indent=2, ensure_ascii=False)
            )
            print(f"  [done] {persona_id} (@{channel}): {len(items)} messages")
        except Exception as e:
            print(f"  [fail] {persona_id} (@{channel}): {e}")


if __name__ == "__main__":
    main()
