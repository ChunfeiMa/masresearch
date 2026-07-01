"""Validate Mermaid diagrams via the Node validator in tools/mermaid-validate.

Mermaid has no Python parser, so we shell out to Node + mermaid's own parser.
If Node or the validator's deps aren't installed, validation is a no-op (every
diagram treated as valid) — the pipeline never breaks over a missing dev tool,
and the UI still degrades gracefully on any invalid diagram that slips through.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from .config import ROOT

VALIDATOR_DIR = ROOT / "tools" / "mermaid-validate"
_SCRIPT = VALIDATOR_DIR / "validate.mjs"


def available() -> bool:
    return (
        shutil.which("node") is not None
        and _SCRIPT.exists()
        and (VALIDATOR_DIR / "node_modules").exists()
    )


def validate(items: list[tuple[str, str]]) -> dict[str, tuple[bool, str]]:
    """Map each (id, mermaid_code) to (is_valid, error_message).

    Returns all-valid if the validator is unavailable or errors out.
    """
    if not items:
        return {}
    if not available():
        return {i: (True, "") for i, _ in items}

    payload = json.dumps([{"id": i, "code": c} for i, c in items])
    try:
        proc = subprocess.run(
            ["node", str(_SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(VALIDATOR_DIR),
        )
        results = json.loads(proc.stdout or "[]")
    except Exception:
        return {i: (True, "") for i, _ in items}

    return {r["id"]: (bool(r.get("valid")), r.get("error", "")) for r in results}
