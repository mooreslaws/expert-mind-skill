#!/usr/bin/env python3
"""Pull a single web URL → plain text. Naive readability heuristic.

Source entry shape in personas/<id>.yaml:
  - type: webfeed
    url: https://example.com/page
    title: "Optional human label"   # informational only

Saves: staging/raw/web/<persona_id>.json
One persona can have multiple `webfeed` sources — each becomes one item.
"""
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/web")
STAGING.mkdir(parents=True, exist_ok=True)


class _Extractor(HTMLParser):
    """Collect text from semantically content-ish tags; drop nav/script/style/etc.

    This is intentionally simple — no `readability` dependency. Works adequately
    on most personal blogs. For sites it mangles, the user has the option to
    pull via RSS instead.
    """
    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "header",
                 "aside", "form", "iframe"}
    KEEP_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote",
                 "pre", "td", "dd", "dt", "figcaption"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.cur = []
        self.skip_depth = 0
        self.keep_depth = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif tag in self.KEEP_TAGS:
            self.keep_depth += 1
            self.cur = []
        elif tag == "br" and self.keep_depth > 0:
            self.cur.append("\n")
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in self.KEEP_TAGS:
            self.keep_depth = max(0, self.keep_depth - 1)
            text = "".join(self.cur).strip()
            if text:
                self.parts.append(text)
            self.cur = []
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.in_title:
            self.title += data
        if self.keep_depth > 0:
            self.cur.append(data)


def fetch_url(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 expert-mind-skill/0.2"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="ignore")
    parser = _Extractor()
    try:
        parser.feed(raw)
    except Exception:
        pass  # html.parser can be brittle on malformed HTML; keep partial output
    text = "\n\n".join(parser.parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {"title": parser.title.strip(), "text": text}


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    by_persona: dict[str, list[dict]] = {}
    for p, src in sources_of_type(personas, "webfeed"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        url = src.get("url")
        if not url:
            continue
        try:
            doc = fetch_url(url)
            by_persona.setdefault(p["id"], []).append({
                "id": url,
                "url": url,
                "date": "",
                "title": doc["title"] or src.get("title", ""),
                "text": doc["text"],
            })
            print(f"  [done] {p['id']}: {url} ({len(doc['text'])} chars)")
        except Exception as e:
            print(f"  [fail] {p['id']} ({url}): {e}")

    if not by_persona:
        print("[done] no webfeed sources.")
        return

    for persona_id, items in by_persona.items():
        (STAGING / f"{persona_id}.json").write_text(
            json.dumps(items, indent=2, ensure_ascii=False)
        )


if __name__ == "__main__":
    main()
