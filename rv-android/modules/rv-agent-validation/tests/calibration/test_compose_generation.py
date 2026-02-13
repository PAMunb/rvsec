"""
Tests for docker-compose YAML generation (T1-T8).

Validates the pure-function compose generators in both
calibration_orchestrator.py and baseline_docker.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from calibration_orchestrator import generate_calibration_compose
from baseline_docker import generate_baseline_compose


# ---------------------------------------------------------------------------
# Calibration orchestrator compose (T1-T5)
# ---------------------------------------------------------------------------

def _make_calibration_compose(n_trials=4):
    """Helper: generate a calibration compose with n_trials services."""
    batch = [
        (i, f"rvagent:pure_algorithm@mop_direct_score={300 + i}")
        for i in range(n_trials)
    ]
    return generate_calibration_compose(
        batch=batch,
        data_dir="/data/apks",
        filter_file="/data/filter.txt",
        output_dir="/output",
        image="phtcosta/rvandroid:0.8.0",
        cpus=10,
        memory="20g",
        timeout=300,
    )


def test_calibration_compose_structure():
    """T1: Compose has N services with correct image, cpus, memory, devices."""
    compose = _make_calibration_compose(n_trials=4)

    assert "services" in compose
    assert len(compose["services"]) == 4

    svc = compose["services"]["trial_0"]
    assert svc["image"] == "phtcosta/rvandroid:0.8.0"
    assert svc["deploy"]["resources"]["limits"]["cpus"] == "10"
    assert svc["deploy"]["resources"]["limits"]["memory"] == "20g"
    assert "/dev/kvm:/dev/kvm" in svc["devices"]


def test_calibration_compose_env_vars():
    """T2: Each service has correct RV_TOOLS, experiment name, and skip flags."""
    compose = _make_calibration_compose(n_trials=2)

    svc0 = compose["services"]["trial_0"]
    env = svc0["environment"]
    assert "rvagent:pure_algorithm@mop_direct_score=300" in env["RV_TOOLS"]
    assert env["RV_EXPERIMENT_NAME"] == "trial_0"
    assert env["RV_TIMEOUTS"] == "300"
    assert env["RV_NO_WINDOW"] == "true"
    assert env["RV_SKIP_MONITORS"] == "true"
    assert env["RV_SKIP_INSTRUMENT"] == "true"
    assert env["RV_SKIP_STATIC_ANALYSIS"] == "true"

    svc1 = compose["services"]["trial_1"]
    assert "mop_direct_score=301" in svc1["environment"]["RV_TOOLS"]
    assert svc1["environment"]["RV_EXPERIMENT_NAME"] == "trial_1"


def test_calibration_compose_volumes():
    """T3: APK volume (ro), filter mount (ro), and results volume."""
    compose = _make_calibration_compose(n_trials=1)
    volumes = compose["services"]["trial_0"]["volumes"]

    assert "/data/apks:/opt/rvsec/rv-android/apks:ro" in volumes
    assert "/data/filter.txt:/opt/rvsec/rv-android/filters/filter.txt:ro" in volumes
    assert "/output/trial_0:/opt/rvsec/rv-android/results" in volumes


def test_calibration_compose_staggered_delay():
    """T4: RV_DELAY increases by 10s per container (0, 10, 20, 30)."""
    compose = _make_calibration_compose(n_trials=4)

    for i in range(4):
        delay = compose["services"][f"trial_{i}"]["environment"]["RV_DELAY"]
        assert delay == str(i * 10), f"trial_{i} delay should be {i * 10}, got {delay}"


def test_calibration_compose_no_humanoid():
    """T5: No humanoid service or depends_on keys."""
    compose = _make_calibration_compose(n_trials=3)

    assert "humanoid" not in compose["services"]
    for name, svc in compose["services"].items():
        assert "depends_on" not in svc, f"{name} should not have depends_on"


# ---------------------------------------------------------------------------
# Baseline compose (T6-T8)
# ---------------------------------------------------------------------------

def _make_baseline_compose(n_batches=3):
    """Helper: generate a baseline compose with n_batches services."""
    return generate_baseline_compose(
        n_batches=n_batches,
        tools="ape,fastbot,rvagent:pure_algorithm",
        data_dir="/data/apks",
        output_dir="/output",
        image="phtcosta/rvandroid:0.8.0",
        cpus=10,
        memory="20g",
        timeout=300,
        repetitions=3,
    )


def test_baseline_compose_structure():
    """T6: N services, all with same RV_TOOLS, correct image and limits."""
    compose = _make_baseline_compose(n_batches=3)

    assert len(compose["services"]) == 3

    for i in range(3):
        svc = compose["services"][f"batch_{i}"]
        assert svc["image"] == "phtcosta/rvandroid:0.8.0"
        assert svc["environment"]["RV_TOOLS"] == "ape,fastbot,rvagent:pure_algorithm"
        assert svc["deploy"]["resources"]["limits"]["cpus"] == "10"
        assert svc["deploy"]["resources"]["limits"]["memory"] == "20g"
        assert "/dev/kvm:/dev/kvm" in svc["devices"]


def test_baseline_compose_batch_filters():
    """T7: Each batch mounts its own filter file."""
    compose = _make_baseline_compose(n_batches=3)

    for i in range(3):
        svc = compose["services"][f"batch_{i}"]
        env = svc["environment"]
        assert env["RV_APKS_FILTER"] == f"/opt/rvsec/rv-android/filters/batch_{i}_apks.txt"

        # Volume mount for per-batch filter
        filter_mount = [v for v in svc["volumes"] if "batch_{}_apks.txt".format(i) in v]
        assert len(filter_mount) == 1


def test_baseline_compose_repetitions():
    """T8: RV_REPETITIONS env var is set correctly."""
    compose = _make_baseline_compose(n_batches=2)

    for i in range(2):
        env = compose["services"][f"batch_{i}"]["environment"]
        assert env["RV_REPETITIONS"] == "3"
