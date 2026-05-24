#!/usr/bin/env python3
"""End-to-end smoke test for the plugin.

Validates that:
1. persona_loader correctly reads YAML from cold-start registry
2. wizard_state inspects filesystem without crashes
3. orchestrator dispatches without errors when no real ingest runs (skip flags)
4. Each adapter module imports cleanly

Does NOT make real API calls — that requires APIFY_TOKEN / ANTHROPIC_API_KEY.
For full e2e with real keys, see `tools/run-e2e.sh`.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS = PROJECT_ROOT / "scripts"
COLD_START = PROJECT_ROOT / "cold-start" / "registry.yaml"

# Ensure scripts/ is on path
sys.path.insert(0, str(SCRIPTS))


def test_cold_start_registry_loads():
    """Registry parses and has expected structure."""
    from persona_loader import load_cold_start
    cs = load_cold_start(COLD_START)
    assert len(cs) >= 10, f"expected at least 10 personas, got {len(cs)}"
    sample = next(iter(cs.values()))
    for field in ("name", "role", "expertise", "voice", "sources"):
        assert field in sample, f"persona missing field: {field}"


def test_each_persona_has_at_least_one_source():
    from persona_loader import load_cold_start
    cs = load_cold_start(COLD_START)
    for pid, persona in cs.items():
        sources = persona.get("sources") or persona.get("recommended_sources") or []
        assert len(sources) > 0, f"{pid} has no sources"


def test_sources_of_type_filters_correctly():
    from persona_loader import load_cold_start, sources_of_type
    cs = list(load_cold_start(COLD_START).values())
    linkedin = sources_of_type(cs, "linkedin_apify")
    rss = sources_of_type(cs, "rss")
    assert len(linkedin) > 0, "expected at least one linkedin_apify source"
    # Every returned pair must be (persona, source) with matching type
    for persona, src in linkedin:
        assert src["type"] == "linkedin_apify"
        assert src.get("enabled", True)


def test_wizard_state_runs_clean():
    """wizard_state.py works against an empty CWD without crashing."""
    with tempfile.TemporaryDirectory() as td:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "wizard_state.py"), "--json"],
            cwd=td,
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ},
        )
        assert result.returncode == 0, f"wizard_state failed: {result.stderr}"
        state = json.loads(result.stdout)
        for key in ("llm_provider", "personas", "sources", "cron", "first_run",
                    "_pipeline_ready", "_blockers"):
            assert key in state, f"missing key in wizard state: {key}"


def test_all_adapters_import():
    """Each adapter module imports without ImportError or env-key crashes.

    Adapters that hard-require an env var at module load time (Apify, Readwise,
    IMAP) are run in a subprocess with fake credentials — module load is what
    we're testing, not real API calls.
    """
    # No-auth adapters: import directly in this process
    no_auth = ("pull_rss", "pull_mastodon", "pull_bluesky", "pull_youtube",
               "import_manual", "pull_telegram", "pull_webfeed")
    for mod_name in no_auth:
        try:
            __import__(mod_name)
        except SystemExit as e:
            raise AssertionError(f"{mod_name} exited at import: {e}")
        except ImportError as e:
            raise AssertionError(f"{mod_name} failed import: {e}")

    # Auth-required adapters: subprocess with fake env
    auth_required = [
        ("scrape_linkedin",  {"APIFY_TOKEN": "fake_token"}),
        ("scrape_x",         {"APIFY_TOKEN": "fake_token"}),
        ("scrape_x_official", {"X_BEARER_TOKEN": "fake_token"}),
        ("pull_readwise",    {"READWISE_TOKEN": "fake_token"}),
        ("pull_email",       {"IMAP_HOST": "imap.example.com",
                              "IMAP_USER": "fake@example.com",
                              "IMAP_PASS": "fake"}),
    ]
    for mod_name, fake_env in auth_required:
        env = {**os.environ, **fake_env}
        result = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{SCRIPTS}'); import {mod_name}; print('ok')"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert "ok" in result.stdout, f"{mod_name} import failed: {result.stderr}"


def test_judge_import_with_fake_key():
    """judge.py loads when an API key env var is set (no real API call)."""
    env = {**os.environ, "ANTHROPIC_API_KEY": "fake_test_key"}
    result = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, '{SCRIPTS}'); import judge; print(len(judge.PERSONAS))"],
        env=env, capture_output=True, text=True, timeout=10,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"judge failed to import: {result.stderr}"
    # In project root, personas/ is empty (only .gitkeep) so falls back to cold-start
    n = int(result.stdout.strip())
    assert n >= 10, f"expected ≥10 personas loaded, got {n}"


def test_orchestrator_dry_run():
    """Orchestrator runs with --skip-* flags without making real API calls."""
    env = {**os.environ,
           "ANTHROPIC_API_KEY": "fake_test_key",
           "APIFY_TOKEN": "fake_test_token"}
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "orchestrator.py"),
         "--skip-ingest", "--skip-judge", "--skip-distill", "eric-seufert"],
        env=env, capture_output=True, text=True, timeout=20,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"orchestrator failed: {result.stderr}"
    assert "eric-seufert" in result.stdout, "expected persona id in output"
    assert "done" in result.stdout.lower()


if __name__ == "__main__":
    # Run all tests when executed directly (no pytest needed)
    test_funcs = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for fn in test_funcs:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(test_funcs) - failed}/{len(test_funcs)} passed")
    sys.exit(1 if failed else 0)
