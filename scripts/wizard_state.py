#!/usr/bin/env python3
"""Inspect the filesystem to determine wizard step completion state.

Reports which setup steps are done, pending, skipped, or blocked. Used by
the /init wizard to show a checklist and pick the next step.

Usage:
  python3 scripts/wizard_state.py            # human-readable checklist
  python3 scripts/wizard_state.py --json     # machine-readable JSON
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from persona_loader import load_personas, load_cold_start  # noqa: E402


# ---- Status enum ----
#
# Note: we don't have a PENDING/blocked status because nothing blocks the
# wizard from exiting. Steps are either DONE, PENDING (not done yet — user
# can return any time), SKIPPED (not applicable to their config), or ERROR.
# A separate `pipeline_ready` flag answers "can /run actually do something
# right now?" — that's what gates the pipeline, not the wizard.

DONE = "done"           # ✅
PENDING = "pending"     # ⚪
SKIPPED = "skipped"     # ➖
ERROR = "error"         # ❌


def _load_dotenv() -> dict:
    """Read CWD/.env without depending on python-dotenv.

    Empty-string env vars are treated as "not set" — some parent processes
    clear vars to "" instead of unsetting, and we don't want that to block
    a real value in `.env`. Matches orchestrator._load_dotenv_into_environ.
    """
    env = dict(os.environ)
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k and not env.get(k):
                env[k] = v.strip().strip('"').strip("'")
    return env


# ---- Per-step checks ----

def check_llm_provider() -> dict:
    env = _load_dotenv()
    anthropic = env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_CORPORATE_API_KEY")
    openai = env.get("OPENAI_API_KEY")
    ollama = env.get("OLLAMA_BASE_URL")
    if anthropic:
        return {"status": DONE, "required": True, "provider": "anthropic",
                "detail": f"key ends in …{anthropic[-4:]}"}
    if openai:
        return {"status": DONE, "required": True, "provider": "openai",
                "detail": f"key ends in …{openai[-4:]}"}
    if ollama:
        return {"status": DONE, "required": True, "provider": "ollama",
                "detail": ollama}
    return {"status": PENDING, "required": True,
            "detail": "no ANTHROPIC_API_KEY / OPENAI_API_KEY / OLLAMA_BASE_URL in .env"}


def check_personas() -> dict:
    personas_dir = Path("personas")
    files = sorted(personas_dir.glob("*.yaml")) if personas_dir.exists() else []
    if files:
        return {"status": DONE, "required": True, "count": len(files),
                "ids": [f.stem for f in files]}
    # No personas yet — but cold-start registry exists?
    cs = load_cold_start()
    if cs:
        return {"status": PENDING, "required": True,
                "detail": f"none active yet; {len(cs)} presets available to import"}
    return {"status": PENDING, "required": True,
            "detail": "personas/ is empty and no cold-start registry found"}


# Map adapter type → env var required (None means no auth)
SOURCE_AUTH_MAP = {
    # Free, no auth
    "rss": None,
    "mastodon": None,
    "bluesky": None,
    "hackernews": None,
    "arxiv": None,
    "youtube": None,             # YOUTUBE_API_KEY is optional for richer metadata
    "webfeed": None,
    "manual_text": None,
    "telegram_public": None,     # uses t.me/s/ HTML scrape, no API needed

    # Sign up + token
    "linkedin_apify": "APIFY_TOKEN",     # only viable path for LinkedIn (no public API)
    "x_apify": "APIFY_TOKEN",            # recommended default for X (cheaper than X API)
    "x_official": "X_BEARER_TOKEN",      # alternative: X API v2, needs Basic+ tier ($100/mo)
    "readwise_reader": "READWISE_TOKEN",
    "readwise_highlights": "READWISE_TOKEN",

    # Advanced
    "email_forward": "IMAP_HOST",    # also needs IMAP_USER + IMAP_PASS — adapter validates at runtime
}


def check_sources() -> dict:
    """Inspect every enabled source across all personas.

    Returns per-persona breakdown and aggregate source readiness.
    A source is "ready" iff it requires no auth, or the required env var is set.
    """
    env = _load_dotenv()
    personas = load_personas()
    if not personas:
        return {"status": SKIPPED, "required": False,
                "detail": "no personas configured yet — sources are per-persona"}

    per_persona = []
    missing_env_vars: set[str] = set()
    total_sources = 0
    total_ready = 0

    for p in personas:
        sources = [s for s in p.get("sources", []) if s.get("enabled", True)]
        per_src = []
        for src in sources:
            t = src.get("type", "?")
            auth_var = SOURCE_AUTH_MAP.get(t, "?unknown")
            if auth_var is None:
                ready = True
            elif auth_var == "?unknown":
                ready = False
            else:
                ready = bool(env.get(auth_var))
                if not ready:
                    missing_env_vars.add(auth_var)
            per_src.append({"type": t, "ready": ready, "auth": auth_var})
            total_sources += 1
            if ready:
                total_ready += 1

        per_persona.append({
            "id": p["id"],
            "name": p.get("name"),
            "sources": per_src,
            "ready": sum(1 for s in per_src if s["ready"]),
            "total": len(per_src),
        })

    if total_sources == 0:
        return {"status": PENDING, "required": True,
                "detail": "personas have no sources yet"}

    status = DONE if total_ready == total_sources else PENDING
    return {
        "status": status,
        "required": True,
        "total_sources": total_sources,
        "ready_sources": total_ready,
        "per_persona": per_persona,
        "missing_env_vars": sorted(missing_env_vars),
        "detail": f"{total_ready}/{total_sources} sources ready"
                  + (f"; needs: {', '.join(sorted(missing_env_vars))}" if missing_env_vars else ""),
    }


def check_cron() -> dict:
    gha = Path(".github/workflows/expert-mind-skill.yml")
    launchd_glob = list(Path.home().glob("Library/LaunchAgents/com.*expert-mind-skill*"))
    systemd_glob = list(Path.home().glob(".config/systemd/user/expert-mind-skill*"))
    if gha.exists():
        return {"status": DONE, "required": False, "mode": "github-actions",
                "detail": str(gha)}
    if launchd_glob:
        return {"status": DONE, "required": False, "mode": "launchd",
                "detail": str(launchd_glob[0])}
    if systemd_glob:
        return {"status": DONE, "required": False, "mode": "systemd",
                "detail": str(systemd_glob[0])}
    return {"status": PENDING, "required": False,
            "detail": "no automated schedule — runs only when you invoke /run"}


def _skill_path_for(persona_id: str) -> Path | None:
    """Return the path to a skill output for this persona, or None.

    Supports both the new directory layout (output/skills/<id>/SKILL.md) and the
    legacy flat layout (output/skills/<id>.md) for back-compat with old runs.
    """
    dir_form = Path("output/skills") / persona_id / "SKILL.md"
    if dir_form.exists():
        return dir_form
    flat_form = Path("output/skills") / f"{persona_id}.md"
    if flat_form.exists():
        return flat_form
    return None


def check_first_run() -> dict:
    """Has the pipeline run for the CURRENT persona set?

    "First run done" doesn't just mean *some* output exists — it means every
    configured persona has a skill output, and those outputs aren't older than
    their persona files (otherwise the config has drifted and a re-run is due).
    """
    personas_dir = Path("personas")
    persona_files = sorted(personas_dir.glob("*.yaml")) if personas_dir.exists() else []
    if not persona_files:
        return {"status": PENDING, "required": False,
                "detail": "pipeline has not run yet (no personas configured)"}

    covered = []
    missing = []
    stale = []
    for pf in persona_files:
        pid = pf.stem
        skill = _skill_path_for(pid)
        if skill is None:
            missing.append(pid)
            continue
        if skill.stat().st_mtime < pf.stat().st_mtime:
            stale.append(pid)
        else:
            covered.append(pid)

    total = len(persona_files)
    if not covered and not stale:
        return {"status": PENDING, "required": False,
                "detail": f"pipeline has not run yet (0/{total} personas have output)",
                "covered": [], "missing": missing, "stale": []}

    if missing or stale:
        bits = []
        if missing:
            bits.append(f"{len(missing)} missing output")
        if stale:
            bits.append(f"{len(stale)} stale (persona edited after last run)")
        return {"status": PENDING, "required": False,
                "detail": f"partial run: {len(covered)}/{total} fresh; " + ", ".join(bits),
                "covered": covered, "missing": missing, "stale": stale}

    return {"status": DONE, "required": False,
            "detail": f"all {total} personas have fresh skill outputs",
            "covered": covered, "missing": [], "stale": []}


def is_pipeline_ready(state: dict) -> tuple[bool, list[str]]:
    """Can `expert-mind-skill run` actually do something useful right now?

    Returns (ready, blockers). blockers is a list of human-readable reasons
    why pipeline cannot run yet. ready==True iff blockers is empty.
    """
    blockers = []
    if state["llm_provider"]["status"] != DONE:
        blockers.append("no LLM provider key (need ANTHROPIC_API_KEY or similar)")
    if state["personas"]["status"] != DONE:
        blockers.append("no personas configured yet (add at least one)")
    src = state["sources"]
    if src["status"] not in (DONE, SKIPPED):
        missing = src.get("missing_env_vars") or []
        if missing:
            blockers.append(f"sources missing credentials: {', '.join(missing)}")
        else:
            blockers.append("personas have no sources attached")
    return (not blockers, blockers)


def inspect() -> dict:
    state = {
        "llm_provider": check_llm_provider(),
        "personas": check_personas(),
        "sources": check_sources(),
        "cron": check_cron(),
        "first_run": check_first_run(),
    }
    ready, blockers = is_pipeline_ready(state)
    state["_pipeline_ready"] = ready
    state["_blockers"] = blockers
    return state


# ---- Reporting ----

ICONS = {DONE: "✅", PENDING: "⚪", SKIPPED: "➖", ERROR: "❌"}


def _fmt_step(label: str, step: dict) -> str:
    icon = ICONS.get(step["status"], "?")
    # `required` here means "needed for the pipeline to run"; the wizard
    # itself never blocks on this.
    flag = "needed for /run" if step.get("required") else "optional"
    detail = step.get("detail", "")
    extras = []
    for k in ("provider", "count", "mode"):
        if k in step:
            extras.append(f"{k}={step[k]}")
    extras_s = f" [{', '.join(extras)}]" if extras else ""
    return f"  {icon} {label:20s} {step['status']:8s} ({flag}){extras_s}  {detail}"


def report(state: dict) -> str:
    out = ["Setup state:", ""]
    out.append(_fmt_step("LLM provider", state["llm_provider"]))
    out.append(_fmt_step("Personas", state["personas"]))
    out.append(_fmt_step("Sources", state["sources"]))
    out.append(_fmt_step("Cron schedule", state["cron"]))
    out.append(_fmt_step("First run", state["first_run"]))

    # Optional per-persona source breakdown when there are unready sources
    sources = state["sources"]
    if sources.get("status") == PENDING and sources.get("per_persona"):
        out.append("")
        out.append("  Sources per persona:")
        for pp in sources["per_persona"]:
            ready_marker = "✅" if pp["ready"] == pp["total"] and pp["total"] > 0 else "⚪"
            bits = []
            for s in pp["sources"]:
                mark = "✅" if s["ready"] else "⚠️ "
                auth = f" (needs {s['auth']})" if (not s["ready"] and s["auth"] not in (None, "?unknown")) else ""
                bits.append(f"{mark}{s['type']}{auth}")
            out.append(f"    {ready_marker} {pp['id']:25s} {pp['ready']}/{pp['total']}  {'; '.join(bits)}")
    out.append("")

    fr = state["first_run"]
    if fr.get("missing") or fr.get("stale"):
        bits = []
        if fr.get("missing"):
            bits.append(f"  missing: {', '.join(fr['missing'])}")
        if fr.get("stale"):
            bits.append(f"  stale:   {', '.join(fr['stale'])}")
        out.append("")
        out.append("  First-run coverage:")
        out.extend(bits)

    if state["_pipeline_ready"]:
        if state["first_run"]["status"] == DONE:
            out.append("")
            out.append("✅ All set. Pipeline has run; skills are live.")
        else:
            out.append("")
            out.append("✅ Ready to run. Try /expert-mind-skill:run.")
    else:
        out.append("⚪ Pipeline not yet runnable. Blockers:")
        for b in state["_blockers"]:
            out.append(f"   - {b}")
        out.append("")
        out.append("You can exit the wizard anytime — these can be filled in later.")

    return "\n".join(out)


def main():
    state = inspect()
    if "--json" in sys.argv:
        print(json.dumps(state, indent=2))
    else:
        print(report(state))


if __name__ == "__main__":
    main()
