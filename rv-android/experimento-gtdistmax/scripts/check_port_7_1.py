"""Task 7.1: the aperv-tool code before this change against the code after it.

Usage: python check_port_7_1.py <pin_dir> <document.json> [<document.json> ...]

<pin_dir> holds old_derive_mop_artifact.py and old_tool.py, written by
`git show 99572bc0:rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/<file>`.
They are loaded under other module names beside the installed (new) modules.

Check 1: on every document, the old derive() and the new derive() at cut 3 serialise to the
same bytes (serialize_canonical), with the same source_file/source_digest arguments.
Check 2: for every variant of get_variants() (none carries a ladder override), the old and the
new _push_properties write the same ape.properties, with and without the artifact line, except
the difference EXPECTED_REMOVED names: after the k removal (task 7.3, design D15) the new code
no longer writes the ledger line of the four MOP variants, and adds no line anywhere.
Prints the per-line difference of each comparison and exits 1 if any differs from the expected.
"""

import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

from aperv_tool.tools.aperv import derive_mop_artifact as new_derive
from aperv_tool.tools.aperv.tool import ApeRVTool as NewTool


# The lines the old tool.py writes and the new one does not, per variant (design D15).
LEDGER_LINE = "ape.mopCoinLedgerMaxInteractions=2"
EXPECTED_REMOVED = {
    variant: [LEDGER_LINE] for variant in ("mop", "as_mop", "as_mop_llm", "mop_nolaunch")
}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _properties(tool, artifact_pushed):
    captured = {}

    def fake_push(local_path, device_path, device_serial, trace_file_path):
        with open(local_path) as handle:
            captured["properties"] = handle.read()

    tool._push_file_to_device = fake_push
    with tempfile.NamedTemporaryFile(suffix=".trace", delete=False) as trace:
        trace_path = trace.name
    try:
        tool._push_properties("emulator-5554", trace_path, artifact_pushed)
    finally:
        os.unlink(trace_path)
    return captured["properties"]


def main():
    pin_dir, documents = sys.argv[1], sys.argv[2:]
    old_derive = _load("old_derive_mop_artifact", os.path.join(pin_dir, "old_derive_mop_artifact.py"))
    old_tool = _load("old_aperv_tool", os.path.join(pin_dir, "old_tool.py"))
    failures = 0

    for path in documents:
        with open(path, "rb") as handle:
            raw = handle.read()
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        name = os.path.basename(path)
        document = json.loads(raw)
        old_bytes = old_derive.serialize_canonical(
            old_derive.derive(copy.deepcopy(document), name, digest)
        )
        new_bytes = new_derive.serialize_canonical(
            new_derive.derive(copy.deepcopy(document), name, digest, cut=3)
        )
        same = old_bytes == new_bytes
        failures += not same
        print(
            f"derive cut=3 {'SAME' if same else 'DIFFERENT'} {path} "
            f"artifact_bytes={len(new_bytes)} sha256={hashlib.sha256(new_bytes).hexdigest()[:16]}"
        )

    old_variants = old_tool.ApeRVTool.get_variants()
    new_variants = NewTool.get_variants()
    same_names = sorted(old_variants) == sorted(new_variants)
    failures += not same_names
    print(f"variant names {'SAME' if same_names else 'DIFFERENT'}: {sorted(new_variants)}")
    for variant in sorted(set(old_variants) & set(new_variants)):
        for artifact_pushed in (False, True):
            old = old_tool.ApeRVTool()
            old.configure(copy.deepcopy(old_variants[variant]))
            new = NewTool()
            new.configure(copy.deepcopy(new_variants[variant]))
            old_lines = _properties(old, artifact_pushed).splitlines()
            new_lines = _properties(new, artifact_pushed).splitlines()
            removed = [line for line in old_lines if line not in new_lines]
            added = [line for line in new_lines if line not in old_lines]
            # The surviving lines keep their order: the new file is the old one minus the
            # removed lines.
            in_order = [line for line in old_lines if line not in removed] == new_lines
            expected = removed == EXPECTED_REMOVED.get(variant, []) and not added
            ok = expected and in_order
            failures += not ok
            print(
                f"ape.properties {variant} artifact_pushed={artifact_pushed} "
                f"{'AS EXPECTED' if ok else 'UNEXPECTED'} old_lines={len(old_lines)} "
                f"new_lines={len(new_lines)} removed={removed} added={added}"
            )

    print("RESULT", "PASS" if failures == 0 else f"FAIL ({failures})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
