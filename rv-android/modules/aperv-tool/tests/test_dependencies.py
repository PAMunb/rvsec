"""Dependency declaration of the analysis layer.

Two facts are asserted here, and they pull in opposite directions.

The first is that ``statsmodels`` is installed at all. It carries the
negative-binomial GLM the campaign analysis leans on, and it is the one
dependency of this module that is neither a workspace sibling nor already
present through ``rv-android-core``. If the declaration in ``pyproject.toml``
is ever dropped, every count-model test would fail with an import error whose
cause is three layers away from its symptom; this test names the cause.

The second is that importing a *reader* must not drag ``statsmodels`` in.
The three shipped readers run over traces, dumps and logcats and have nothing
to do with estimation; ``statsmodels`` costs roughly a second of import time
and pulls ``patsy`` and a large ``scipy`` surface with it. ``count_glm``
therefore imports it inside the function that fits, and this test is what keeps
that discipline honest — a module-level ``import statsmodels`` added later
would still pass every functional test and would silently tax every reader.

The check runs in a subprocess because ``sys.modules`` is process-global: by
the time pytest reaches this file some other test may legitimately have
imported ``statsmodels``, and asking about the current process would measure
test ordering rather than the readers.
"""

from __future__ import annotations

import subprocess
import sys


def test_statsmodels_importable() -> None:
    """``statsmodels`` is declared and installed in the shared environment."""
    import statsmodels.api as sm

    assert hasattr(sm, "NegativeBinomial")


def test_statsmodels_not_loaded_by_readers() -> None:
    """The three shipped readers import without pulling ``statsmodels`` in."""
    probe = (
        "import sys;"
        "import aperv_tool.analysis.trace_ndjson;"
        "import aperv_tool.analysis.coverage_dump;"
        "import aperv_tool.analysis.clock_logcat_join;"
        "loaded=[m for m in sys.modules if m.split('.')[0] "
        "in ('statsmodels','patsy')];"
        "print(','.join(sorted(loaded)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", (
        "importing the shipped readers loaded an estimation dependency: "
        f"{result.stdout.strip()}"
    )
