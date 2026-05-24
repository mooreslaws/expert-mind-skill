#!/usr/bin/env python3
"""End-to-end pipeline: ingest -> judge -> distill.

Usage:
  expert-mind-skill run                      # all enabled personas
  expert-mind-skill run eric-seufert         # one persona
  expert-mind-skill run --force              # re-pull even if staging exists
  expert-mind-skill run --skip-ingest        # only judge + distill (use existing staging)
  expert-mind-skill run --skip-distill       # only ingest + judge

Environment:
  ANTHROPIC_API_KEY     required for judge
  APIFY_TOKEN           required if any persona has linkedin_apify / x_apify sources
  EXPERT_MIND_JUDGE_MODEL  override judge model (default claude-sonnet-4-5)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start  # noqa: E402


def _load_dotenv_into_environ() -> None:
    """Load `.env` in CWD into os.environ if not already present.

    Subprocesses inherit os.environ, so doing this at orchestrator startup
    propagates the keys to every adapter. We don't depend on python-dotenv —
    same minimal parser used by wizard_state.py.

    An empty string in os.environ is treated as "not set" — some parent
    processes clear vars to "" rather than unsetting them, and almost no
    workflow actually wants KEY="" to mean "use empty key".
    """
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k and not os.environ.get(k):
            os.environ[k] = v.strip().strip('"').strip("'")


_load_dotenv_into_environ()


def _has_source_type(personas, source_type) -> bool:
    for p in personas:
        for src in p.get("sources", []):
            if src.get("type") == source_type and src.get("enabled", True):
                return True
    return False


def _run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd)


def _preflight_apify() -> tuple[bool, str]:
    """Ping Apify /v2/users/me. Returns (ok, message).

    A live token returns 200 with a JSON body. An exhausted/over-quota account
    returns 402 (Payment Required). An invalid token returns 401. Either way
    we know in <1 second whether 16 parallel actor runs would succeed.
    """
    import urllib.error
    import urllib.request
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        return False, "APIFY_TOKEN not set"
    req = urllib.request.Request("https://api.apify.com/v2/users/me")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()  # discard
        return True, "Apify auth OK"
    except urllib.error.HTTPError as e:
        body = (e.read().decode(errors="replace") or "")[:200]
        if e.code == 402:
            return False, f"Apify HTTP 402 (billing): {body[:160]}"
        if e.code == 401:
            return False, f"Apify HTTP 401 (auth): {body[:160]}"
        return False, f"Apify HTTP {e.code}: {body[:160]}"
    except Exception as e:
        return False, f"Apify check failed: {e}"


def _preflight_anthropic() -> tuple[bool, str]:
    """Ping Anthropic /v1/messages with a 1-token request. Returns (ok, message).

    `credit balance too low` and invalid-key errors come back as HTTP 400 with
    a parseable body, so we catch them here before launching parallel judge
    calls that would each fail identically.
    """
    import urllib.error
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_CORPORATE_API_KEY")
    if not key:
        return False, "no ANTHROPIC_API_KEY / ANTHROPIC_CORPORATE_API_KEY"
    body = json.dumps({
        "model": os.environ.get("EXPERT_MIND_JUDGE_MODEL", "claude-sonnet-4-5"),
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "ok"}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST")
    req.add_header("x-api-key", key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        return True, f"Anthropic auth + balance OK (key …{key[-4:]})"
    except urllib.error.HTTPError as e:
        err = (e.read().decode(errors="replace") or "")[:300]
        if "credit balance" in err.lower():
            return False, f"Anthropic credit balance too low: top up at console.anthropic.com/settings/billing"
        if e.code == 401:
            return False, f"Anthropic HTTP 401 (invalid key): {err[:160]}"
        return False, f"Anthropic HTTP {e.code}: {err[:160]}"
    except Exception as e:
        return False, f"Anthropic check failed: {e}"


def _preflight(personas: list[dict], skip_ingest: bool, skip_judge: bool) -> None:
    """Run cheap auth + balance checks for every paid API we're about to use.

    Aborts the orchestrator with a clear message if any required key is
    missing or its account can't take requests. Saves us from launching
    16 parallel jobs that would all fail identically.
    """
    print("[preflight] checking credentials and balance...", flush=True)
    failures = []

    needs_apify = (not skip_ingest) and (
        _has_source_type(personas, "linkedin_apify") or _has_source_type(personas, "x_apify")
    )
    if needs_apify:
        ok, msg = _preflight_apify()
        print(f"  Apify:    {'✅' if ok else '❌'} {msg}", flush=True)
        if not ok:
            failures.append(msg)

    if not skip_judge:
        ok, msg = _preflight_anthropic()
        print(f"  Anthropic:{'✅' if ok else '❌'} {msg}", flush=True)
        if not ok:
            failures.append(msg)

    if failures:
        print("\n[preflight] aborting — fix the above before re-running:", flush=True)
        for f in failures:
            print(f"  - {f}", flush=True)
        sys.exit(2)


def main():
    args = sys.argv[1:]
    force = "--force" in args
    skip_ingest = "--skip-ingest" in args
    skip_judge = "--skip-judge" in args
    skip_distill = "--skip-distill" in args
    persona_ids = [a for a in args if not a.startswith("--")]

    personas = load_personas() or list(load_cold_start().values())
    if persona_ids:
        personas = [p for p in personas if p["id"] in persona_ids]
        if not personas:
            sys.exit(f"No matching personas for: {persona_ids}")

    script_dir = Path(__file__).parent
    py = sys.executable

    print(f"[orchestrator] {len(personas)} persona(s) selected:")
    for p in personas:
        srcs = [s.get("type") for s in p.get("sources", []) if s.get("enabled", True)]
        print(f"  - {p['id']:30s} sources: {srcs}")

    # Verify auth + balance for each paid API before launching anything.
    _preflight(personas, skip_ingest=skip_ingest, skip_judge=skip_judge)

    # === Stage 1: Ingest — one adapter script per source type ===
    # Each adapter is invoked if at least one persona has that source type enabled.
    INGEST_DISPATCH = [
        ("linkedin_apify",  "scrape_linkedin.py",   "APIFY_TOKEN"),
        ("x_apify",         "scrape_x.py",          "APIFY_TOKEN"),
        ("x_official",      "scrape_x_official.py", "X_BEARER_TOKEN"),
        ("rss",             "pull_rss.py",        None),
        ("mastodon",        "pull_mastodon.py",   None),
        ("bluesky",         "pull_bluesky.py",    None),
        ("youtube",         "pull_youtube.py",    None),
        ("manual_text",     "import_manual.py",   None),
        ("telegram_public", "pull_telegram.py",   None),
        ("readwise_reader", "pull_readwise.py",   "READWISE_TOKEN"),
        ("webfeed",         "pull_webfeed.py",    None),
        ("email_forward",   "pull_email.py",      "IMAP_HOST"),
    ]
    if not skip_ingest:
        for source_type, script_name, required_env in INGEST_DISPATCH:
            if not _has_source_type(personas, source_type):
                continue
            if required_env and not os.environ.get(required_env):
                print(f"[err] {source_type} sources require {required_env} — skipping this adapter")
                continue
            cmd = [py, str(script_dir / script_name), *(p["id"] for p in personas)]
            if force and source_type in ("linkedin_apify", "x_apify"):
                cmd.append("--force")
            if _run(cmd) != 0:
                print(f"[warn] {script_name} returned non-zero")

    # === Stage 2: Judge ===
    if not skip_judge:
        if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_CORPORATE_API_KEY"):
            print("[err] judge requires ANTHROPIC_API_KEY")
            sys.exit(2)
        cmd = [py, str(script_dir / "judge.py"), *(p["id"] for p in personas)]
        if _run(cmd) != 0:
            print("[warn] Judge returned non-zero")

    # === Stage 3: Distill ===
    if not skip_distill:
        cmd = [py, str(script_dir / "distill.py"), *(p["id"] for p in personas)]
        if _run(cmd) != 0:
            print("[warn] Distill returned non-zero")

    print("\n[orchestrator] done.")


if __name__ == "__main__":
    main()
