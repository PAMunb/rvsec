"""Tests for preflight.py (PRE-FLIGHT audit).

These build a REAL iteration with `gen_iteration.write_iteration` — the test may import the
producer (it needs a genuine tree to audit); the preflight MODULE may not (INV-CAL-04, proved
by `test_preflight_import_independence`).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import gen_iteration  # producer — imported HERE only, never inside preflight.py
import preflight
import yaml


def _build_iter(phase_config, tmp_path):
    """Generate iter1/ from the fixture phase config and return its path."""
    return gen_iteration.write_iteration(phase_config, 1, None, tmp_path)


def test_clean_iteration_passes(phase_config, tmp_path):
    """A freshly generated iteration passes every non-image check (image ID SKIPped)."""
    iter_dir = _build_iter(phase_config, tmp_path)
    report = preflight.run_preflight(iter_dir, allow_docker=False)
    assert not report.failed, report.render()


def test_preflight_detects_mismatch(phase_config, tmp_path, capsys):
    """Dropping one arm from a container's RV_TOOLS is a FAIL naming container + arm."""
    iter_dir = _build_iter(phase_config, tmp_path)
    compose_path = iter_dir / "docker-compose.calfix.yml"
    compose = yaml.safe_load(compose_path.read_text())

    # Hand-edit calfix_00 to drop the ANC1 arm from RV_TOOLS (simulates config drift).
    env = compose["services"]["calfix_00"]["environment"]
    tokens = env["RV_TOOLS"].split(",")
    dropped = tokens.pop(tokens.index("ape:default"))
    env["RV_TOOLS"] = ",".join(tokens)
    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False))

    rc = preflight.main(["--iter-dir", str(iter_dir), "--skip-image-id"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "calfix_00" in out
    assert dropped in out  # the missing arm token is named
    assert "FAIL" in out


def test_identity_dryrun_counts(phase_config, tmp_path):
    """The identity check re-derives arms × apk_count × reps and distinct (tool,variant)."""
    iter_dir = _build_iter(phase_config, tmp_path)
    manifest = json.loads((iter_dir / "manifest.json").read_text())

    counts = preflight.check_identities(manifest, iter_dir)
    # Fixture: 3 arms, 4 APKs (round-robin over 2 containers), 2 reps.
    assert counts.n_arms == 3
    assert counts.apk_count == 4
    assert counts.reps == 2
    assert counts.total == 3 * 4 * 2 == counts.manifest_total
    # Every arm is a distinct named variant (INV-CAL-05): no identity collisions.
    assert counts.distinct_pairs == 3
    assert counts.ok


def test_artifact_hash_drift_fails(phase_config, tmp_path):
    """A tool.py in artifacts/ that no longer hashes to the manifest FAILs with the
    'generate a new iteration' remediation (spec scenario: worktree drift after snapshot).
    """
    iter_dir = _build_iter(phase_config, tmp_path)
    snap = iter_dir / "artifacts" / "tool.py"
    snap.write_text(snap.read_text() + "\n# tampered after snapshot\n")

    report = preflight.run_preflight(iter_dir, allow_docker=False)
    assert report.failed
    art = [r for r in report.records if "artifact tool.py" in r.label]
    assert art and art[0].status == "FAIL"
    assert "generate a NEW iteration" in art[0].detail


def test_preflight_import_independence():
    """AST proof that preflight.py never imports gen_iteration (INV-CAL-04)."""
    source = Path(preflight.__file__).read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert "gen_iteration" not in imported, f"forbidden import present: {imported}"
