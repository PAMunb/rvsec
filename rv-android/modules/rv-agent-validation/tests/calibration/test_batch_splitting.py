"""
Tests for APK batch splitting logic (T9-T14).

Validates the round-robin distribution used by baseline_docker.py to split
APKs evenly across Docker containers.
"""

import sys
from pathlib import Path

# Add scripts/ to sys.path so we can import from standalone scripts
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from baseline_docker import split_apks_round_robin


def test_even_split():
    """T9: 12 APKs / 6 batches = 2 APKs per batch."""
    apks = [f"app_{i}.apk" for i in range(12)]
    batches = split_apks_round_robin(apks, 6)

    assert len(batches) == 6
    for batch in batches:
        assert len(batch) == 2


def test_uneven_split():
    """T10: 105 APKs / 6 batches = 3 batches of 18, 3 batches of 17."""
    apks = [f"app_{i}.apk" for i in range(105)]
    batches = split_apks_round_robin(apks, 6)

    assert len(batches) == 6
    sizes = sorted([len(b) for b in batches])
    assert sizes == [17, 17, 17, 18, 18, 18]
    assert sum(sizes) == 105


def test_single_container():
    """T11: All APKs go to one container."""
    apks = [f"app_{i}.apk" for i in range(10)]
    batches = split_apks_round_robin(apks, 1)

    assert len(batches) == 1
    assert len(batches[0]) == 10


def test_more_containers_than_apks():
    """T12: 3 APKs / 6 batches = 3 with 1 APK, 3 empty."""
    apks = [f"app_{i}.apk" for i in range(3)]
    batches = split_apks_round_robin(apks, 6)

    assert len(batches) == 6
    non_empty = [b for b in batches if b]
    assert len(non_empty) == 3
    for b in non_empty:
        assert len(b) == 1


def test_all_apks_present():
    """T13: No duplicates, no omissions after splitting."""
    apks = [f"app_{i}.apk" for i in range(105)]
    batches = split_apks_round_robin(apks, 6)

    flat = [apk for batch in batches for apk in batch]
    assert set(flat) == set(apks)
    assert len(flat) == len(apks)


def test_round_robin_order():
    """T14: APKs are distributed round-robin."""
    apks = ["a", "b", "c", "d"]
    batches = split_apks_round_robin(apks, 2)

    assert batches[0] == ["a", "c"]
    assert batches[1] == ["b", "d"]
