"""Bucket-classification tests for the two `rv_status.py` copies (gh92, C7).

`ERROR_BUCKETS` classifies a failed task by first-matching regex. Because
`EmulatorError.__str__` embeds the cause's type, every emulator boot failure
used to be swallowed by an earlier generic bucket: a phase-1 boot timeout
matched `("timeout", ...)` and the composite install failure matched
`("install/adb", ...)`, both evaluated before `("emulator/boot", ...)`. The
boot bucket was therefore empty by construction. The fix classifies the boot
signatures literally, ahead of the generic keyword buckets.

The monitoring script is duplicated verbatim under `experimento-20260706/` and
`experimento-20260604/`; a bucket list that is wrong in one copy is wrong in
the other. Both copies are imported by path and the SAME table is run against
each, so any future divergence fails here.

Provenance of the table: every string marked "artifact" below was read from a
stored run — either the `error_message` fields of the 773 `tasks.json` files
in the repo (2163 failed tasks, 7 distinct message forms once task UUIDs are
normalized) or, for the tool timeout, an `ErrorHandler` log line. One entry is
marked "code" instead: the phase-2 boot timeout has never fired in a stored
run, so its string is reproduced from the code that formats it
(`android.py::_wait_for_boot` phase 2).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COPIES = {
    "experimento-20260706": REPO_ROOT
    / "experimento-20260706"
    / "scripts"
    / "rv_status.py",
    "experimento-20260604": REPO_ROOT
    / "experimento-20260604"
    / "scripts"
    / "rv_status.py",
}


def _load_copy(name: str, path: Path):
    module_name = f"_rv_status_{name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MODULES = {name: _load_copy(name, path) for name, path in COPIES.items()}

# (label, error_message, expected_bucket). `label` names the failure mode; the
# message is the exact text a failed task carries in `result.error_message`.
CASES = [
    # artifact — 322 records, e.g. data/validacao_full/results/validacao_full_ajc_1/
    # validacao_full_ajc_1/tasks.json. Phase 1: the boot animation never stopped.
    (
        "phase1_boot_animation",
        "EmulatorError: Failed to start emulator RVSec caused by TimeoutError: "
        "emulator-5554 did not boot within 180s",
        "emulator/boot",
    ),
    # code — android.py::_wait_for_boot phase 2. No stored run has hit it, but it
    # is the other half of the boot gate and must be classifiable when it does.
    (
        "phase2_boot_completed",
        "EmulatorError: Failed to start emulator RVSec caused by TimeoutError: "
        "emulator-5554 sys.boot_completed not set within 300s",
        "emulator/boot",
    ),
    # artifact — 1172 records, e.g. experimento-20260721/results/
    # cmp_llm_20260721_base_07/cmp_llm_20260721_base_07/tasks.json. The composite:
    # a start that reported success and then could not install.
    (
        "composite_start_then_install",
        "EmulatorError: Failed to start emulator RVSec caused by TaskExecutionError: "
        "TaskExecutionError: Failed to install application "
        "(Task ID: 7b2f44c2-6e1d-406d-a40b-0ef0c154a5b1)",
        "emulator/boot",
    ),
    # artifact — 5 records, results/precal_micro/trial_33/trial_33/tasks.json.
    # Legacy phase 3, removed by gh50; the records remain and are boot failures.
    (
        "legacy_phase3_remount",
        "EmulatorError: Failed to start emulator RVSec caused by TimeoutError: "
        "emulator-5554 remount failed within 180s",
        "emulator/boot",
    ),
    # artifact — 3 records, data/results/exp4_09/exp4_09/tasks.json.
    (
        "legacy_phase3_root",
        "EmulatorError: Failed to start emulator RVSec caused by TimeoutError: "
        "emulator-5554 root failed within 180s",
        "emulator/boot",
    ),
    # artifact — data/validacao_ajc_v2/A_dex.log:608, as rendered by ErrorHandler.
    # A genuine APE timeout whose command line names the emulator serial twice.
    # This is why the boot bucket cannot simply be moved to the front of the
    # generic list (design D8): reordering would file this as emulator/boot.
    (
        "genuine_tool_timeout",
        "RVToolTimeoutError: ape execution timed out after 300.0 seconds caused by "
        "RVCommandTimeoutError: RVCommandTimeoutError: Command 'adb -s emulator-5554 "
        "shell CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process "
        "/data/local/tmp/ com.android.commands.monkey.Monkey -p br.unb.cic.cryptoapp "
        "--running-minutes 5 --ape sata' timed out after 300.0 seconds "
        "(Timeout: 300.0s) (Command: adb -s emulator-5554 shell "
        "CLASSPATH=/data/local/tmp/ape.jar /system/bin/app_process /data/local/tmp/ "
        "com.android.commands.monkey.Monkey -p br.unb.cic.cryptoapp "
        "--running-minutes 5 --ape sata) (Tool: ape) (Timeout: 300.0s)",
        "timeout",
    ),
    # artifact — 358 records, data/results/exp4_05/exp4_05/tasks.json. A missing
    # emulator binary is an environment fault, still caught by the generic
    # emulator keyword bucket that the specific signatures sit above.
    (
        "emulator_binary_missing",
        "EmulatorError: Failed to start emulator RVSec caused by CommandNotFoundError: "
        "CommandException[tool=emulator ::: code=-1 ::: "
        "message=The command emulator was not found]",
        "emulator/boot",
    ),
    # artifact — 3 records, data/results/exp4_05/exp4_05/tasks.json. Names adb,
    # so the generic install/adb bucket claims it; the specific signatures above
    # must not steal it.
    (
        "adb_binary_missing",
        "EmulatorError: Failed to start emulator RVSec caused by CommandNotFoundError: "
        "CommandException[tool=adb ::: code=-1 ::: "
        "message=The command adb was not found]",
        "install/adb",
    ),
    # artifact — 300 records, data/validacao_ajc/run_B_ajc/tasks.json. A tool
    # failure relabelled by the same context manager; not a boot signature.
    (
        "tool_component_failure",
        "EmulatorError: Failed to start emulator RVSec caused by TaskExecutionError: "
        "TaskExecutionError: Component ToolExecutionComponent execution failed "
        "(Task ID: 6dfd2e1b-7197-4e39-a8a9-ca07bc7621a6)",
        "emulator/boot",
    ),
]


@pytest.mark.parametrize("copy_name", sorted(COPIES))
@pytest.mark.parametrize(
    "label,message,expected", CASES, ids=[case[0] for case in CASES]
)
def test_error_message_lands_in_expected_bucket(copy_name, label, message, expected):
    """Each stored `error_message` form classifies into its intended bucket."""
    module = MODULES[copy_name]
    assert module.classify_error("ERROR", message) == expected


@pytest.mark.parametrize("copy_name", sorted(COPIES))
def test_boot_signatures_never_fall_into_a_generic_bucket(copy_name):
    """The two boot-gate signatures reach `emulator/boot`, not `timeout`.

    This is the defect C7 corrects: both messages carry the word "timeout" via
    the embedded `TimeoutError` type name, which the generic bucket matched
    first.
    """
    module = MODULES[copy_name]
    boot_signatures = {"phase1_boot_animation", "phase2_boot_completed"}
    messages = [msg for label, msg, _ in CASES if label in boot_signatures]
    assert len(messages) == 2
    for message in messages:
        assert module.classify_error("ERROR", message) == "emulator/boot"


def test_both_copies_declare_the_same_bucket_list():
    """The `ERROR_BUCKETS` block is duplicated; it must stay byte-equivalent."""
    signatures = {
        name: [(label, rx.pattern, rx.flags) for label, rx in module.ERROR_BUCKETS]
        for name, module in MODULES.items()
    }
    first, second = (
        signatures["experimento-20260706"],
        signatures["experimento-20260604"],
    )
    assert first == second


def test_specific_signatures_precede_the_generic_buckets():
    """Ordering is the mechanism: the literal signatures must be evaluated first.

    Guards against a future edit that appends a specific rule below the generic
    keyword buckets, where it could never match.
    """
    for module in MODULES.values():
        labels = [label for label, _ in module.ERROR_BUCKETS]
        generic_start = labels.index("timeout")
        assert generic_start == 2, labels
        assert labels[:2] == ["emulator/boot", "emulator/boot"]
