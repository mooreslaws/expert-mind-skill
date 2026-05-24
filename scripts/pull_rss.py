#!/usr/bin/env python3
"""Pull RSS/Atom feeds for personas.

Persona-driven: iterates personas/*.yaml (falls back to cold-start registry),
finds `rss` sources with a non-empty `url`, fetches each.

Saves: staging/raw/rss/<persona_id>.json
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/rss")
STAGING.mkdir(parents=True, exist_ok=True)


class TextStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buf = []

    def handle_data(self, data):
        self.buf.append(data)


def strip_html(s):
    if not s:
        return ""
    p = TextStripper()
    p.feed(s)
    text = "".join(p.buf)
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(xml_bytes):
    """Parse RSS or Atom feed."""
    root = ET.fromstring(xml_bytes)
    items = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        date = (item.findtext("pubDate") or "").strip()
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        content_el = item.find("content:encoded", ns)
        body = content_el.text if content_el is not None else item.findtext("description")
        items.append({
            "title": title,
            "link": link,
            "date": date,
            "text": strip_html(body or ""),
        })
    if items:
        return items

    ns_atom = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns_atom):
        title = (entry.findtext("a:title", default="", namespaces=ns_atom) or "").strip()
        link_el = entry.find("a:link", ns_atom)
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        date = (entry.findtext("a:published", default="", namespaces=ns_atom) or "").strip()
        content_el = entry.find("a:content", ns_atom)
        if content_el is not None:
            body = "".join(content_el.itertext()) if list(content_el) else (content_el.text or "")
        else:
            body = entry.findtext("a:summary", default="", namespaces=ns_atom)
        items.append({
            "title": title,
            "link": link,
            "date": date,
            "text": strip_html(body or ""),
        })
    return items


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "expert-mind-skill/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = sources_of_type(personas, "rss")

    # Filter out empty URLs (cold-start placeholders) + apply CLI filter
    runnable = []
    for persona, src in targets:
        url = (src.get("url") or "").strip()
        if not url:
            continue
        if cli_filter and persona["id"] not in cli_filter:
            continue
        runnable.append((persona["id"], url))

    if not runnable:
        print("[done] no RSS feeds to pull.")
        return

    for persona_id, url in runnable:
        try:
            raw = fetch(url)
            items = parse_feed(raw)
            out = STAGING / f"{persona_id}.json"
            out.write_text(json.dumps(items, indent=2, ensure_ascii=False))
            sizes = [len(it.get("text", "")) for it in items]
            avg = sum(sizes) // max(len(sizes), 1)
            mx = max(sizes) if sizes else 0
            print(f"  [done] {persona_id}: {len(items)} items, avg={avg}c max={mx}c")
        except Exception as e:
            print(f"  [fail] {persona_id} ({url}): {e}")


if __name__ == "__main__":
    main()
