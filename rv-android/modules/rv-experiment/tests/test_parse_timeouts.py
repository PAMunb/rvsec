"""Unit tests for `_parse_timeouts` (CLI boundary parsing, INV-EXP-33).

The helper turns the `--timeouts` / `RV_TIMEOUTS` CSV string into a list of
positive integers, preserving order and rejecting empty/invalid/non-positive
input with `click.BadParameter` before any experiment setup.
"""

from __future__ import annotations

import click
import pytest
from rv_experiment.__main__ import _parse_timeouts


def test_single_value():
    assert _parse_timeouts("300") == [300]


def test_list_values_order_preserved():
    assert _parse_timeouts("60,300,600") == [60, 300, 600]


def test_whitespace_trimmed():
    assert _parse_timeouts(" 60 , 300 ") == [60, 300]


def test_trailing_comma_ignored():
    assert _parse_timeouts("60,300,") == [60, 300]


def test_duplicates_preserved():
    # No dedup at the parser: resume skips identity-colliding tasks (INV-EXP-33).
    assert _parse_timeouts("60,60") == [60, 60]


def test_invalid_token_raises():
    with pytest.raises(click.BadParameter):
        _parse_timeouts("60,abc")


def test_empty_string_raises():
    with pytest.raises(click.BadParameter):
        _parse_timeouts("")


def test_only_commas_raises():
    with pytest.raises(click.BadParameter):
        _parse_timeouts(",,")


def test_zero_raises():
    with pytest.raises(click.BadParameter):
        _parse_timeouts("0")


def test_negative_raises():
    with pytest.raises(click.BadParameter):
        _parse_timeouts("300,-5")
