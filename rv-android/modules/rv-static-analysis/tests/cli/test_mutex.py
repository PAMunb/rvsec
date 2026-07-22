"""
INV-ANA-33 — CLI mutex between ``--mop-dir`` and ``--targets-file``.

Argparse with ``add_mutually_exclusive_group`` accepts (a) only one or
(b) neither (Pydantic enforces "neither is invalid" later, so the CLI
should ONLY error on "both"). These tests cover four cases:

  (a) only ``--mop-dir``        -> argparse accepts
  (b) only ``--targets-file``   -> argparse accepts
  (c) both                       -> argparse exits 2 with mutex error
  (d) neither                    -> argparse accepts (Pydantic catches downstream)

Argparse exits the process on error, so we capture ``SystemExit`` with a
``pytest.raises`` context.
"""

import argparse

import pytest

from rv_static_analysis.__main__ import setup_argument_parser


def _parse(args: list[str]) -> argparse.Namespace:
    parser = setup_argument_parser()
    return parser.parse_args(args)


_BASE = ["analyze", "--apk", "/tmp/x.apk", "--output", "/tmp/out"]


def test_only_mop_dir_accepted() -> None:
    ns = _parse(_BASE + ["--mop-dir", "/tmp/jca"])
    assert ns.mop_dir == "/tmp/jca"
    assert ns.targets_file is None


def test_only_targets_file_accepted() -> None:
    ns = _parse(_BASE + ["--targets-file", "/tmp/sigs.txt"])
    assert ns.targets_file == "/tmp/sigs.txt"
    assert ns.mop_dir is None


def test_both_rejected_with_exit_code_2() -> None:
    with pytest.raises(SystemExit) as exc:
        _parse(_BASE + ["--mop-dir", "/tmp/jca", "--targets-file", "/tmp/sigs.txt"])
    assert exc.value.code == 2


def test_neither_accepted_at_cli_layer() -> None:
    # The CLI's mutex group is not `required=True` — defaults from rvsec_root
    # layout fill mop_dir in Pydantic. The "neither" failure mode lives at
    # _validate_mop_directory when no defaults are available either.
    ns = _parse(_BASE)
    assert ns.mop_dir is None
    assert ns.targets_file is None
