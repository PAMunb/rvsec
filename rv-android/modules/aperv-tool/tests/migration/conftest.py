"""Shared access to the ape source checkout for the migration tier.

The stage-2 tables live in the ape repository, not here, so every test in this directory
needs a checkout that carries them. `$APE_REPO` must point at one — `$RVSEC_HOME/ape` is
tried as a fallback but in practice holds only `target/`, so it rarely resolves.

When no checkout resolves, the tier **skips** rather than fails. It is one-time migration
tooling and CI has no ape checkout; failing there would break an unrelated build for
everyone. The skip carries the command that makes it run, so a skipped tier reads as
"not wired up here", never as "checked and fine".
"""

import pytest

from .jar_tables import JarTableError, resolve_ape_repo

_SKIP_REASON = (
    "no stage-2 ape checkout: run with "
    "APE_REPO=<checkout carrying rearch-02-runspec> to execute the migration tier"
)


@pytest.fixture(scope="session")
def ape_repo():
    """Path to an ape checkout carrying `Presets.java` / `KeyOwnership.java`."""
    try:
        return resolve_ape_repo()
    except JarTableError:
        pytest.skip(_SKIP_REASON)
