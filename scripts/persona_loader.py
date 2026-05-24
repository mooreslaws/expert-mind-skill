"""Persona loading utility.

Reads `personas/*.yaml` from CWD by default. Falls back to the bundled
`cold-start/registry.yaml` (located alongside the scripts/) when CWD's
personas/ is empty — useful for testing or for users who haven't run /init.

Schema (per passport):
  id, name, role, expertise (list), voice (str), groups (list),
  sources (list of {type, ...adapter-specific..., enabled, auth, cost_note}),
  cadence (weekly|daily|manual), size_limit_tokens, hard_cap_tokens,
  review_mode (auto|pr|manual), include_sources_in_lean (bool).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except ImportError as e:
    raise SystemExit(
        "PyYAML not installed. Run: pip install pyyaml"
    ) from e


def _plugin_root() -> Path:
    """Locate the plugin root (where cold-start/ lives) regardless of CWD.

    Priority:
      1. EXPERT_MIND_PLUGIN_ROOT env var (explicit override)
      2. CLAUDE_PLUGIN_ROOT env var (set by Claude Code when invoking commands)
      3. The directory containing this file's parent (scripts/.. → plugin root)
    """
    for var in ("EXPERT_MIND_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        if os.environ.get(var):
            return Path(os.environ[var])
    return Path(__file__).resolve().parent.parent


def _default_cold_start_path() -> Path:
    return _plugin_root() / "cold-start" / "registry.yaml"


def _load_yaml_file(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML must be a dict, got {type(data).__name__}")
    return data


def _normalize(persona_id: str, body: dict) -> dict:
    """Ensure required fields and apply sensible defaults."""
    body = dict(body)
    body.setdefault("id", persona_id)
    body.setdefault("expertise", [])
    body.setdefault("groups", [])
    body.setdefault("voice", "")
    body.setdefault("languages", ["en"])
    body.setdefault("sources", body.get("recommended_sources", []))  # cold-start uses recommended_sources
    body.setdefault("cadence", "weekly")
    body.setdefault("size_limit_tokens", 4000)
    body.setdefault("hard_cap_tokens", 8000)
    body.setdefault("review_mode", "auto")
    body.setdefault("include_sources_in_lean", False)
    # Each source may have `enabled: true|false`; default true
    body["sources"] = [
        {"enabled": True, **src} for src in body["sources"]
    ]
    return body


def load_personas(personas_dir: Path | str = "personas") -> list[dict]:
    """Load all personas/*.yaml. Returns list of normalised passport dicts."""
    p = Path(personas_dir)
    if not p.exists():
        return []
    out = []
    for f in sorted(p.glob("*.yaml")):
        try:
            body = _load_yaml_file(f)
        except Exception as e:
            print(f"[warn] could not load {f}: {e}")
            continue
        out.append(_normalize(f.stem, body))
    return out


def load_cold_start(registry_path: Path | str | None = None) -> dict[str, dict]:
    """Load the cold-start registry. Returns {id: passport}.

    If `registry_path` is None, looks for `cold-start/registry.yaml` in:
      1. CWD (so a user can override with their own local registry)
      2. The plugin root (the bundled default)
    """
    if registry_path is not None:
        p = Path(registry_path)
    else:
        cwd_candidate = Path("cold-start/registry.yaml")
        bundled = _default_cold_start_path()
        p = cwd_candidate if cwd_candidate.exists() else bundled
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: must be a dict of {{id: passport}}")
    return {pid: _normalize(pid, body) for pid, body in raw.items()}


def get_persona(persona_id: str, *, fallback_to_cold_start: bool = True) -> dict | None:
    """Look up a single persona. First checks personas/, then cold-start if allowed."""
    for p in load_personas():
        if p["id"] == persona_id:
            return p
    if fallback_to_cold_start:
        return load_cold_start().get(persona_id)
    return None


def sources_of_type(personas: Iterable[dict], source_type: str) -> list[tuple[dict, dict]]:
    """For all (persona, source) pairs where source.type == source_type and source.enabled.

    Returns: [(persona_dict, source_dict), ...]
    """
    out = []
    for p in personas:
        for src in p.get("sources", []):
            if src.get("type") == source_type and src.get("enabled", True):
                out.append((p, src))
    return out


if __name__ == "__main__":
    import json
    import sys
    personas = load_personas()
    if not personas:
        print("[info] personas/ is empty, showing cold-start registry instead")
        personas = list(load_cold_start().values())
    if "--json" in sys.argv:
        print(json.dumps(personas, indent=2))
    else:
        for p in personas:
            print(f"  {p['id']:30s} ({len(p.get('sources', []))} sources)")
