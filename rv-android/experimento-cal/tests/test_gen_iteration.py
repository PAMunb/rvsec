"""Unit tests for gen_iteration.py (CONFIG-GEN)."""

from __future__ import annotations

import hashlib
import json

import gen_iteration as gen
import yaml

from aperv_tool.tools.aperv.tool import ApeRVTool


def _write(phase_config, tmp_path, iteration=1, jar=None):
    return gen.write_iteration(phase_config, iteration, jar, tmp_path)


def test_manifest_resolves_from_get_variants(phase_config, tmp_path):
    iter_dir = _write(phase_config, tmp_path)
    manifest = json.loads((iter_dir / "manifest.json").read_text())

    # Arm keys equal get_variants() field-by-field (manifest is a resolved echo, not a
    # re-declaration — INV-CAL-01).
    variants = ApeRVTool.get_variants()
    arms = {a["role"]: a for a in manifest["arms"]}
    assert arms["A1"]["keys"] == variants["cal_a1"]
    assert arms["ANC2"]["keys"] == variants["sata_mop_act_frontier"]
    # ape builtin carries its own tool defaults.
    assert arms["ANC1"]["keys"]["strategy"] == "sata"

    # predicted_identities = arms × |subset| × reps.
    assert manifest["dataset"]["apk_count"] == 4
    assert manifest["predicted_identities"] == 3 * 4 * 2

    # expected_config_ack is derived for the LLM arm, empty for non-LLM arms.
    assert arms["A1"]["expected_config_ack"]["prompt_variant"] == "v13"
    assert arms["A1"]["expected_config_ack"]["llm_percentage"] == 0.7
    assert arms["ANC1"]["expected_config_ack"] == {}
    assert arms["ANC2"]["expected_config_ack"] == {}

    # image ID recorded for preflight docker-inspect verification (INV-CAL-03).
    assert manifest["image"]["id"] == "87744cd58be9"


def test_snapshot_hashes_recorded(phase_config, tmp_path):
    iter_dir = _write(phase_config, tmp_path)
    manifest = json.loads((iter_dir / "manifest.json").read_text())

    snap = iter_dir / "artifacts" / "tool.py"
    assert snap.exists()
    # Snapshot is byte-identical to the worktree tool.py and its hash is in the manifest.
    worktree = gen.TOOL_PY_SOURCE.read_bytes()
    assert snap.read_bytes() == worktree
    assert manifest["artifacts"]["tool.py"] == hashlib.sha256(worktree).hexdigest()

    # Every bind-mount references iterN/artifacts/, never the worktree path (INV-CAL-02).
    compose = yaml.safe_load((iter_dir / "docker-compose.calfix.yml").read_text())
    for name, svc in compose["services"].items():
        if name == "sglang":
            continue
        mounts = [v for v in svc["volumes"] if "tool.py" in v]
        assert mounts == [f"./artifacts/tool.py:{gen.TOOL_PY_MOUNT_TARGET}:ro"]


def test_snapshot_records_jar_hash_with_dummy(phase_config, tmp_path):
    # Phase-B path: a --jar snapshot is hashed and recorded (validated with a dummy file).
    jar = tmp_path / "ape-rv.jar"
    jar.write_bytes(b"dummy-jar-bytes")
    iter_dir = _write(phase_config, tmp_path, jar=jar)
    manifest = json.loads((iter_dir / "manifest.json").read_text())
    assert (iter_dir / "artifacts" / "ape-rv.jar").read_bytes() == b"dummy-jar-bytes"
    assert (
        manifest["artifacts"]["ape-rv.jar"]
        == hashlib.sha256(b"dummy-jar-bytes").hexdigest()
    )


def test_compose_rotation_and_filters(phase_config, tmp_path):
    iter_dir = _write(phase_config, tmp_path)
    manifest = json.loads((iter_dir / "manifest.json").read_text())
    compose = yaml.safe_load((iter_dir / "docker-compose.calfix.yml").read_text())

    tokens = ["ape:default", "aperv:sata_mop_act_frontier", "aperv:cal_a1"]
    # Container 0 starts at index 0, container 1 starts at index 1 (rotation by i mod n).
    c0 = compose["services"]["calfix_00"]["environment"]["RV_TOOLS"].split(",")
    c1 = compose["services"]["calfix_01"]["environment"]["RV_TOOLS"].split(",")
    assert c0 == tokens
    assert c1 == tokens[1:] + tokens[:1]
    # Same arm set in every container, different order.
    assert set(c0) == set(c1) == set(tokens)

    # Filters: one batch per container, union == full subset, disjoint partition.
    b0 = (iter_dir / "filters" / "batch_00.txt").read_text().split()
    b1 = (iter_dir / "filters" / "batch_01.txt").read_text().split()
    assert set(b0) | set(b1) == {
        "app.alpha_1",
        "app.bravo_2",
        "app.charlie_3",
        "app.delta_4",
    }
    assert set(b0).isdisjoint(set(b1))

    # sglang present exactly once and GPU-reserved.
    assert "sglang" in compose["services"]
    assert compose["services"]["sglang"]["deploy"]["resources"]["reservations"][
        "devices"
    ][0]["capabilities"] == ["gpu"]

    # Smoke compose exists with the smoke arm subset and 90s / 1 rep.
    smoke = yaml.safe_load((iter_dir / "docker-compose.smoke.yml").read_text())
    smoke_svcs = [n for n in smoke["services"] if n != "sglang"]
    assert smoke_svcs, "smoke compose has no rvandroid containers"
    first = smoke["services"][smoke_svcs[0]]["environment"]
    assert first["RV_TIMEOUTS"] == "90"
    assert first["RV_REPETITIONS"] == "1"
    assert first["RV_TOOLS"] == "aperv:cal_a1"
    assert manifest["smoke"]["predicted_identities"] == 1 * 2 * 1


def test_refuses_existing_iter(phase_config, tmp_path):
    _write(phase_config, tmp_path, iteration=1)
    # Second generation of the same N must refuse (append-only, INV-CAL-12).
    try:
        _write(phase_config, tmp_path, iteration=1)
        assert False, "expected SystemExit(2) on existing iter dir"
    except SystemExit as exc:
        assert exc.code == 2


def test_expected_config_ack_maps_llm_keys():
    # Field-name mapping is exactly the [APE-LLM-CONFIG] surface (no llm_max_tokens).
    keys = ApeRVTool.get_variants()["cal_a3"]
    ack = gen.expected_config_ack(keys)
    assert ack["on_new_state"] is False
    assert ack["on_stagnation"] is True
    assert ack["llm_percentage"] == 0
    assert "max_tokens" not in ack
