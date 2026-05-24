#!/usr/bin/env python3
"""Pull YouTube video metadata + transcripts for personas.

No API key required. We use two unauthenticated sources:
  1. The public channel RSS feed (`youtube.com/feeds/videos.xml?channel_id=...`)
     for video listings — gives title, date, URL, description.
  2. `youtube-transcript-api` (optional install) for transcripts — it talks to
     YouTube's internal player endpoints (the same ones the website uses to
     render captions) and doesn't need credentials.

YouTube Data API v3 exists and has a free quota, but for our purposes —
metadata + transcripts of public videos — it's strictly less convenient. If
you ever need richer metadata (subscriber counts, comment counts, etc.), set
`YOUTUBE_API_KEY` and extend this adapter; we don't read it currently.

Source entry shape in personas/<id>.yaml:
  - type: youtube
    channel: "@MobileDevMemo"          # @handle, or channel-id like UCxxx
    max_videos: 20

If `youtube-transcript-api` isn't installed, the adapter still saves metadata
(title, description, URL) — judge works on the description alone, which is
often enough for richly-described content.

Saves: staging/raw/youtube/<persona_id>.json
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

STAGING = Path("staging/raw/youtube")
STAGING.mkdir(parents=True, exist_ok=True)

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    HAVE_TRANSCRIPT_API = True
except ImportError:
    HAVE_TRANSCRIPT_API = False


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "expert-mind-skill/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def resolve_channel_id(channel_ref: str) -> str:
    """Resolve @handle or channel-name to channel-id (UCxxx...)."""
    ref = channel_ref.strip()
    if ref.startswith("UC") and len(ref) >= 22:
        return ref
    # For @handles, fetch the channel page and look for the canonical id
    if ref.startswith("@"):
        url = f"https://www.youtube.com/{ref}"
    else:
        url = f"https://www.youtube.com/@{ref}" if not ref.startswith("http") else ref
    html = _http_get(url).decode("utf-8", errors="ignore")
    m = re.search(r'"channelId":"(UC[\w-]{22})"', html)
    if not m:
        m = re.search(r'<meta itemprop="identifier" content="(UC[\w-]{22})"', html)
    if not m:
        raise RuntimeError(f"could not resolve channel id for {ref}")
    return m.group(1)


def fetch_channel_videos(channel_id: str, max_videos: int) -> list[dict]:
    """Read public RSS feed for the channel — no API key needed."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?{urllib.parse.urlencode({'channel_id': channel_id})}"
    xml_bytes = _http_get(rss_url)
    root = ET.fromstring(xml_bytes)
    ns = {"a": "http://www.w3.org/2005/Atom",
          "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    videos = []
    for entry in root.findall("a:entry", ns)[:max_videos]:
        vid = entry.findtext("yt:videoId", default="", namespaces=ns)
        title = entry.findtext("a:title", default="", namespaces=ns) or ""
        published = entry.findtext("a:published", default="", namespaces=ns) or ""
        link_el = entry.find("a:link", ns)
        url = link_el.attrib.get("href", "") if link_el is not None else ""
        desc = entry.find("media:group/media:description", ns)
        description = (desc.text or "") if desc is not None else ""
        videos.append({
            "id": vid,
            "title": title.strip(),
            "url": url,
            "date": published,
            "description": description.strip(),
            "transcript": "",
        })
    return videos


def fetch_transcript(video_id: str) -> str:
    """Pull transcript via youtube-transcript-api if available, else empty."""
    if not HAVE_TRANSCRIPT_API:
        return ""
    try:
        chunks = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return " ".join(c["text"] for c in chunks)
    except Exception:
        return ""


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "youtube"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        ref = src.get("channel") or src.get("handle")
        if not ref:
            continue
        targets.append((p["id"], ref, int(src.get("max_videos", 20))))

    if not targets:
        print("[done] no YouTube targets.")
        return

    if not HAVE_TRANSCRIPT_API:
        print("[note] `youtube-transcript-api` not installed — saving metadata only.")
        print("       Install with `pip install youtube-transcript-api` for richer content.")

    for persona_id, channel_ref, max_videos in targets:
        try:
            channel_id = resolve_channel_id(channel_ref)
            videos = fetch_channel_videos(channel_id, max_videos)
            for v in videos:
                v["transcript"] = fetch_transcript(v["id"])
                # judge consumes `text` field — merge title + description + transcript
                v["text"] = "\n\n".join(filter(None, [v["title"], v["description"], v["transcript"]]))
            (STAGING / f"{persona_id}.json").write_text(json.dumps(videos, indent=2, ensure_ascii=False))
            with_transcripts = sum(1 for v in videos if v["transcript"])
            print(f"  [done] {persona_id} ({channel_ref}): {len(videos)} videos, {with_transcripts} with transcripts")
        except Exception as e:
            print(f"  [fail] {persona_id} ({channel_ref}): {e}")


if __name__ == "__main__":
    main()
