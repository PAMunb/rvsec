"""Tests for smoke_check.py (SMOKE gate).

These craft a tiny smoke results tree by hand (2 arms, hand-written .trace/.logcat/tasks.json)
so the field-by-field config-ack comparison is exercised in isolation, including a deliberate
mismatch. smoke_check.py never imports the producers — it reads only the results tree + manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

import smoke_check

SERVER_MODEL = "Qwen/Qwen3-VL-4B-Instruct"

# The two smoke arms with their expected [APE-LLM-CONFIG] surface (mirrors get_variants()
# cal_a1 = new-state ON at 0.7 budget; cal_a3 = new-state OFF, stagnation-only at 0 budget).
_CAL_A1_ACK = {
    "model": "default",
    "temperature": 0,
    "top_p": 0.6,
    "top_k": 50,
    "timeout_ms": 15000,
    "prompt_variant": "v13",
    "llm_percentage": 0.7,
    "on_new_state": True,
    "on_stagnation": True,
    "url": "http://10.0.2.2:30000/v1",
}
_CAL_A3_ACK = {**_CAL_A1_ACK, "llm_percentage": 0, "on_new_state": False}


def _manifest():
    return {
        "iteration": 1,
        "phase": "calfix",
        "expected_server_model": SERVER_MODEL,
        "arms": [
            {
                "role": "A1",
                "tool": "aperv",
                "variant": "cal_a1",
                "rv_tools_token": "aperv:cal_a1",
                "expected_config_ack": _CAL_A1_ACK,
            },
            {
                "role": "A3",
                "tool": "aperv",
                "variant": "cal_a3",
                "rv_tools_token": "aperv:cal_a3",
                "expected_config_ack": _CAL_A3_ACK,
            },
        ],
    }


def _trace(ack: dict, *, on_new_state: str, ack_server_model: str = SERVER_MODEL) -> str:
    """Render a [APE-LLM-CONFIG] + [APE-LLM-CONFIG-ACK] trace, overriding on_new_state so a
    caller can inject a deliberate field mismatch. `ack_server_model` is the value the ape
    echoes on the ACK line (e.g. the `default` sentinel) — it is informational, never the
    gate's model proof (that is the live /v1/models query)."""
    return (
        "[APE-RV] boot\n"
        f"[APE-LLM-CONFIG] model={ack['model']} temperature={ack['temperature']} "
        f"top_p={ack['top_p']} top_k={ack['top_k']} max_tokens=1024 "
        f"timeout_ms={ack['timeout_ms']} prompt_variant={ack['prompt_variant']} "
        f"llm_percentage={ack['llm_percentage']} on_new_state={on_new_state} "
        f"on_stagnation=true stagnation_threshold=3 url={ack['url']}\n"
        f"[APE-LLM-CONFIG-ACK] server_model={ack_server_model}\n"
    )


def _write_task(task_dir: Path, apk: str, variant: str, trace_text: str):
    """Write one smoke task's tasks.json entry payload + its logcat/trace files."""
    base = f"{apk}__1__90__aperv:{variant}"
    apk_dir = task_dir / apk
    apk_dir.mkdir(parents=True, exist_ok=True)
    (apk_dir / f"{base}.logcat").write_text(
        "07-23 12:00:00.000  1000  1000 I RVSEC-COV: some.method()\n"
    )
    (apk_dir / f"{base}.trace").write_text(trace_text)
    return {
        "config": {
            "apk_name": apk,
            "repetition": 1,
            "timeout": 90,
            "tool_config": {"name": "aperv", "variant": variant},
        },
        "result": {
            "state": "COMPLETED",
            "coverage_metrics": {
                "method_coverage": 12.5,
                "activities_coverage": 10.0,
                "methods_mop_reachable_coverage": 5.0,
                "total_errors": 1,
            },
            "detected_errors_count": 0,
        },
    }


def _build_tree(
    tmp_path: Path, *, a3_on_new_state: str, ack_server_model: str = SERVER_MODEL
) -> Path:
    """Build iter1/ with a manifest + a 2-task smoke results tree.

    `a3_on_new_state` is the raw trace value for cal_a3's on_new_state field: "false" matches
    the manifest, "true" injects the deliberate mismatch. `ack_server_model` is the value the
    ape echoes on the ACK line (informational; the served-model proof is the /v1/models query
    the caller supplies to run_smoke_check).
    """
    iter_dir = tmp_path / "iter1"
    iter_dir.mkdir()
    (iter_dir / "manifest.json").write_text(json.dumps(_manifest()))

    task_dir = iter_dir / "results" / "calfix_smoke_00" / "calfix_smoke_00"
    task_dir.mkdir(parents=True)
    tasks = [
        _write_task(
            task_dir,
            "app.alpha_1",
            "cal_a1",
            _trace(_CAL_A1_ACK, on_new_state="true", ack_server_model=ack_server_model),
        ),
        _write_task(
            task_dir,
            "app.bravo_2",
            "cal_a3",
            _trace(
                _CAL_A3_ACK,
                on_new_state=a3_on_new_state,
                ack_server_model=ack_server_model,
            ),
        ),
    ]
    (task_dir / "tasks.json").write_text(json.dumps({"tasks": tasks}))
    return iter_dir


def test_smoke_all_match_passes(tmp_path, monkeypatch):
    """When every trace matches its manifest arm and the served model matches, the gate
    passes (exit 0, no failures). The served model is supplied directly / via a patched
    /v1/models query so the test needs no docker."""
    iter_dir = _build_tree(tmp_path, a3_on_new_state="false")
    failures = smoke_check.run_smoke_check(iter_dir, SERVER_MODEL)
    assert failures == [], failures
    monkeypatch.setattr(smoke_check, "query_served_model", lambda: SERVER_MODEL)
    assert smoke_check.main(["--iter-dir", str(iter_dir)]) == 0


def test_smoke_config_ack_field_by_field(tmp_path, capsys, monkeypatch):
    """A single field mismatch on cal_a3 fails the gate naming arm + field; cal_a1 passes.
    The served model matches, so the only failure is the injected config field mismatch."""
    iter_dir = _build_tree(tmp_path, a3_on_new_state="true")
    failures = smoke_check.run_smoke_check(iter_dir, SERVER_MODEL)

    # cal_a3's on_new_state is named; cal_a1 is untouched; no served-model failure.
    a3_hits = [f for f in failures if "cal_a3" in f and "on_new_state" in f]
    assert a3_hits, failures
    assert not any("cal_a1" in f for f in failures), failures
    assert not any("served model" in f for f in failures), failures

    monkeypatch.setattr(smoke_check, "query_served_model", lambda: SERVER_MODEL)
    rc = smoke_check.main(["--iter-dir", str(iter_dir)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "aperv:cal_a3" in out
    assert "on_new_state" in out


def test_smoke_served_model_proof(tmp_path, capsys, monkeypatch):
    """The model proof is the live /v1/models query, not the ACK echo: a run whose every
    ACK echoes the `default` sentinel PASSES when the served model matches, and FAILS only
    when the served model actually differs from the manifest."""
    # Every ACK echoes `default` (the real iter0 signature) — must NOT cause a failure.
    iter_dir = _build_tree(tmp_path, a3_on_new_state="false", ack_server_model="default")

    ok = smoke_check.run_smoke_check(iter_dir, SERVER_MODEL)
    assert ok == [], ok  # served model matches → pass despite ACK echoing `default`

    bad = smoke_check.run_smoke_check(iter_dir, "some/other-model")
    assert any("served model" in f for f in bad), bad
    assert not any("[APE-LLM-CONFIG-ACK]" in f for f in bad), bad  # ACK never a failure

    # A failed live query (None) is a mismatch; the ACK echo `default` is reported as info.
    monkeypatch.setattr(smoke_check, "query_served_model", lambda: None)
    rc = smoke_check.main(["--iter-dir", str(iter_dir)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "served model mismatch" in out
    assert "['default']" in out and "informational" in out


def test_tolerant_equal_numeric_and_bool():
    """0 == 0.0 == '0'; booleans compare case-insensitively; strings compare exactly."""
    assert smoke_check.tolerant_equal(0, "0")
    assert smoke_check.tolerant_equal(0, "0.0")
    assert smoke_check.tolerant_equal(0.7, "0.7")
    assert smoke_check.tolerant_equal(True, "true")
    assert smoke_check.tolerant_equal(False, "FALSE")
    assert not smoke_check.tolerant_equal(True, "false")
    assert smoke_check.tolerant_equal("v13", "v13")
    assert not smoke_check.tolerant_equal("v13", "v17")


def test_smoke_verifyerror_fails(tmp_path):
    """A VerifyError in a smoke logcat fails the gate (dex corruption signal)."""
    iter_dir = _build_tree(tmp_path, a3_on_new_state="false")
    logcat = (
        iter_dir
        / "results"
        / "calfix_smoke_00"
        / "calfix_smoke_00"
        / "app.alpha_1"
        / "app.alpha_1__1__90__aperv:cal_a1.logcat"
    )
    logcat.write_text(
        logcat.read_text() + "E AndroidRuntime: java.lang.VerifyError: bad\n"
    )
    failures = smoke_check.run_smoke_check(iter_dir, SERVER_MODEL)
    assert any("VerifyError" in f for f in failures), failures
