#!/usr/bin/env python3
"""Pull emails from an IMAP folder.

Used for forwarded newsletters. Set up a Gmail/Fastmail rule that forwards
specific senders to a dedicated label/folder; this adapter reads that folder.

Source entry shape in personas/<id>.yaml:
  - type: email_forward
    folder: "Newsletters/EricSeufert"            # IMAP folder name
    sender_filter: "newsletter@example.com"      # optional, narrows by sender
    since_days: 30                                # optional, default 30

Env vars required:
  IMAP_HOST   e.g. imap.gmail.com (Gmail) or imap.fastmail.com
  IMAP_USER   your full address
  IMAP_PASS   app password (Gmail blocks plain password — generate App Password)
  IMAP_PORT   optional, default 993

Saves: staging/raw/email/<persona_id>.json
"""
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start, sources_of_type  # noqa: E402

IMAP_HOST = os.environ.get("IMAP_HOST")
IMAP_USER = os.environ.get("IMAP_USER")
IMAP_PASS = os.environ.get("IMAP_PASS")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))

if not (IMAP_HOST and IMAP_USER and IMAP_PASS):
    raise SystemExit(
        "Missing IMAP_HOST, IMAP_USER, or IMAP_PASS. "
        "For Gmail, generate an App Password at https://myaccount.google.com/apppasswords"
    )

STAGING = Path("staging/raw/email")
STAGING.mkdir(parents=True, exist_ok=True)


def _decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    buf = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            try:
                buf.append(chunk.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                buf.append(chunk.decode("utf-8", errors="replace"))
        else:
            buf.append(chunk)
    return "".join(buf)


def _extract_body(msg) -> str:
    """Prefer text/plain. Fall back to HTML with naive tag stripping."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:
                    continue
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    return _html_to_text(html)
                except Exception:
                    continue
        return ""
    # Non-multipart
    try:
        body = msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", errors="replace"
        )
        if msg.get_content_type() == "text/html":
            body = _html_to_text(body)
        return body
    except Exception:
        return ""


def _html_to_text(html: str) -> str:
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"<(p|div|h\d|li)[^>]*>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def fetch_folder(folder: str, sender_filter: str | None, since_days: int) -> list[dict]:
    M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    M.login(IMAP_USER, IMAP_PASS)
    try:
        # IMAP folder names with spaces must be quoted
        status, _ = M.select(f'"{folder}"', readonly=True)
        if status != "OK":
            raise RuntimeError(f"could not select folder '{folder}'")
        since_str = (datetime.utcnow() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        criteria = [f'SINCE {since_str}']
        if sender_filter:
            criteria.append(f'FROM "{sender_filter}"')
        criteria_str = "(" + " ".join(criteria) + ")"
        status, data = M.search(None, criteria_str)
        if status != "OK":
            return []
        ids = (data[0] or b"").split()
        items = []
        for msg_id in ids:
            status, msg_data = M.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            items.append({
                "id": msg_id.decode(),
                "url": "",
                "date": msg.get("Date", ""),
                "title": _decode(msg.get("Subject", "")),
                "from": _decode(msg.get("From", "")),
                "text": _extract_body(msg),
            })
        return items
    finally:
        try:
            M.logout()
        except Exception:
            pass


def main():
    cli_filter = set(sys.argv[1:])
    personas = load_personas() or list(load_cold_start().values())
    targets = []
    for p, src in sources_of_type(personas, "email_forward"):
        if cli_filter and p["id"] not in cli_filter:
            continue
        folder = src.get("folder")
        if not folder:
            print(f"  [skip] {p['id']}: email_forward source missing 'folder'")
            continue
        targets.append((
            p["id"],
            folder,
            src.get("sender_filter"),
            int(src.get("since_days", 30)),
        ))

    if not targets:
        print("[done] no email_forward sources.")
        return

    for persona_id, folder, sender, since_days in targets:
        try:
            items = fetch_folder(folder, sender, since_days)
            (STAGING / f"{persona_id}.json").write_text(
                json.dumps(items, indent=2, ensure_ascii=False)
            )
            sender_str = f", from={sender}" if sender else ""
            print(f"  [done] {persona_id} ({folder}{sender_str}): {len(items)} emails")
        except Exception as e:
            print(f"  [fail] {persona_id}: {e}")


if __name__ == "__main__":
    main()
