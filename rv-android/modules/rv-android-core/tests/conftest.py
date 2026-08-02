"""Shared test fixtures for rv-android-core.

The fake clock exists because the boot wait is driven by wall-clock
arithmetic. Patching `time.time` with a counted `side_effect` list couples
each test to the exact number of clock reads the implementation performs, so
an unrelated edit that adds or removes one read breaks tests that have
nothing to do with it. The clock below advances only when the code under test
sleeps, which is how the real loops spend their budget.
"""

import time

import pytest


class FakeClock:
    """Monotonic stand-in for `time.time()` and `time.sleep()`.

    `time()` reports the current instant without advancing it; `sleep()`
    advances it by the number of seconds slept. A loop that polls every
    `BOOT_POLL_INTERVAL_SECONDS` therefore consumes its budget at exactly the
    rate it would in production, and a test controls how long the wait takes
    by choosing the budget rather than by counting clock reads.
    """

    def __init__(self, start: float = 0.0, tick: float = 0.0):
        """Initialize the clock.

        Args:
            start: The instant `time()` reports before anything sleeps.
            tick: Seconds each `time()` call advances the clock. Zero for the
                usual case; set it when a test needs time to pass inside a
                stretch of code that never sleeps.
        """
        self._now = start
        self._tick = tick

    def time(self) -> float:
        """Report the current instant, advancing it by `tick`."""
        self._now += self._tick
        return self._now

    def sleep(self, seconds: float) -> None:
        """Advance the clock by `seconds` without blocking."""
        self._now += seconds

    def advance(self, seconds: float) -> None:
        """Advance the clock explicitly, for setting up a scenario."""
        self._now += seconds


@pytest.fixture
def fake_clock(monkeypatch):
    """Replace `time.time` and `time.sleep` with a monotonic fake clock."""
    clock = FakeClock()
    monkeypatch.setattr(time, "time", clock.time)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock
