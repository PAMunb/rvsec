"""Shared cache-invalidation helper for the GATOR `LENIENT_OUTPUT` artifact.

Several reachability parity gates (`G_paridade_reachability`,
`G_paridade_targets`, `G_sentinela_complete`) consume the JSON at
`/tmp/gh60_g_subset/lenient.json` — produced by a previous run of
`scripts/check_signature_file_subset.py`. Re-running GATOR on every
pytest invocation would push each test from <1 s to ~40 s, so the gates
deliberately reuse the cached output across runs.

The 2026-05-26 investigation surfaced the danger of that reuse: a stale
cache (e.g. from a `.m2` snapshot of `rvsec-gator-sootandroid` predating
gh51's `cha → spark` default switch) had been silently feeding the gates
for ~2 months. Combined with an equally stale in-tree baseline at
`modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`
(content frozen at `4a8a6342 feat(gh45)` 2026-03-31), the set-equality
check between the two stale artifacts kept passing while the current
build produced a materially different — and intentionally more precise
— output (55 reachable / 32 reachesTarget vs 67 / 61).

This helper centralises the freshness check so the gates cannot drift
back into silently-stale behavior. The rule is intentionally simple:
the cache is valid only when at least as new as the producer jar.

See `openspec/changes/gh60-targets-core/design.md` §D12 for the full
incident analysis.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import NoReturn, Optional

import pytest

# Canonical workspace path used by all gh60 parity gates. Hardcoded so
# the four call sites do not drift; if it ever needs to move, change it
# here only.
LENIENT_OUTPUT: Path = Path("/tmp/gh60_g_subset/lenient.json")


def ensure_fresh_lenient(jar: Path) -> Optional[Path]:
    """Return `LENIENT_OUTPUT` iff the cache is at least as new as `jar`.

    Three possible outcomes:

    - Cache missing or empty → returns `None` (caller regenerates by
      running `scripts/check_signature_file_subset.py`).
    - Cache exists but is older than `jar` → cache is deleted (the
      caller's next freshness check will see it missing and regenerate).
      Returns `None`.
    - Cache exists and `mtime(cache) >= mtime(jar)` → returns the cache
      path; the caller may read it directly.

    The mtime comparison treats equal timestamps as fresh because (a)
    filesystem mtime granularity rounds in unpredictable directions on
    some filesystems and (b) a build that finishes and immediately
    produces a fresh cache on the same wall-clock second is not a stale
    cache by any meaningful definition.

    Args:
        jar: Path to the deployed `rvsec-analysis-client.jar`. If the
            jar itself is absent, the cache is treated as authoritative
            (returned as-is when present) because there is nothing to
            compare against — the caller is responsible for handling
            the missing-jar case at its own layer.

    Returns:
        The `LENIENT_OUTPUT` path when the cache is usable, or `None`
        when the cache needs regeneration.
    """
    if not LENIENT_OUTPUT.exists() or LENIENT_OUTPUT.stat().st_size == 0:
        return None

    if jar.exists():
        cache_mtime = LENIENT_OUTPUT.stat().st_mtime
        jar_mtime = jar.stat().st_mtime
        if cache_mtime < jar_mtime:
            # Stale — producer has been rebuilt since the cache was
            # written. Removing the file (rather than letting the
            # caller re-run with stale data lingering) ensures that any
            # other gate that runs in the same pytest session sees a
            # clean slate.
            LENIENT_OUTPUT.unlink()
            return None

    return LENIENT_OUTPUT


def required_or_skip(reason: str) -> NoReturn:
    """Skip-or-fail dispatcher honoring the ``RV_GATOR_REQUIRED`` contract.

    Pre-2026-05-26 the reachability parity gates all called ``pytest.skip``
    when prerequisites were missing (``RVSEC_HOME`` unset, jar not
    deployed, cryptoapp.apk absent, etc.). That made it possible for a
    CI run to report "passed" while exercising zero gate behavior — the
    very mode that hid the cha/spark mismatch documented in design.md §D12.

    The new contract: when ``RV_GATOR_REQUIRED=1`` is in the environment,
    every gate that would skip MUST fail loudly instead. Pedro's local
    dev and the eventual CI pipeline export the var; bare-minimum
    environments (no Android SDK, no RVSEC_HOME) leave it unset and the
    legacy skip behavior applies.

    Args:
        reason: human-readable description of the missing prerequisite.
            Goes verbatim into both the skip message and the failure
            message so the operator sees the same diagnostic regardless
            of mode.
    """
    if os.environ.get("RV_GATOR_REQUIRED") == "1":
        pytest.fail(f"RV_GATOR_REQUIRED=1 but {reason}")
    pytest.skip(reason)
