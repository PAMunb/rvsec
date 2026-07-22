"""CLI parsing for `rv-platform run --timeouts` (INV-PLT-22).

Mirrors the rv-experiment `_parse_timeouts` rules (comma split, whitespace trim,
positive integers only, order preserved, no dedup) with the argparse-native
error path: wired as the argument's ``type=``, an invalid value aborts in
``parse_args()`` with a usage error (exit 2) before any ``PlatformConfig`` is
constructed.
"""

from __future__ import annotations

import argparse

import pytest
from rv_platform.__main__ import _create_config_from_cli, _parse_timeouts, create_parser

# --- _parse_timeouts unit cases (mirror of rv-experiment) ---


def test_single_value():
    assert _parse_timeouts("300") == [300]


def test_list_values_order_preserved():
    assert _parse_timeouts("60,300,600") == [60, 300, 600]


def test_whitespace_trimmed():
    assert _parse_timeouts(" 60 , 300 ") == [60, 300]


def test_duplicates_preserved():
    assert _parse_timeouts("60,60") == [60, 60]


def test_invalid_token_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_timeouts("60,abc")


def test_empty_string_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_timeouts("")


def test_zero_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_timeouts("0")


def test_negative_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_timeouts("300,-5")


# --- Parser-level: type= converts the CSV token to a list during parse_args ---


def test_parser_default_is_single_element_list():
    args = create_parser().parse_args(["run", "--tools", "monkey"])
    assert args.timeouts == [300]


def test_parser_parses_list():
    args = create_parser().parse_args(
        ["run", "--tools", "monkey", "--timeouts", "60,300"]
    )
    assert args.timeouts == [60, 300]


def test_parser_rejects_invalid_with_exit_2():
    with pytest.raises(SystemExit) as exc:
        create_parser().parse_args(["run", "--tools", "monkey", "--timeouts", "300,-5"])
    assert exc.value.code == 2


def test_parser_rejects_old_scalar_flag():
    with pytest.raises(SystemExit) as exc:
        create_parser().parse_args(["run", "--tools", "monkey", "--timeout", "300"])
    assert exc.value.code == 2


# --- _create_config_from_cli wiring: parsed list flows into PlatformConfig ---


def test_create_config_wires_timeouts_list(tmp_path):
    apks = tmp_path / "apks"
    apks.mkdir()
    args = create_parser().parse_args(
        [
            "run",
            "--tools",
            "monkey",
            "--timeouts",
            "60,300",
            "--apks-dir",
            str(apks),
        ]
    )
    config = _create_config_from_cli(args)
    assert config.timeouts == [60, 300]
