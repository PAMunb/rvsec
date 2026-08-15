"""The only way a number leaves the library, and the type it has to leave in.

``emit`` consumes ``Envelope`` and nothing else. Handing it a bare float raises
``TypeError`` naming the type, which is a deliberately blunt refusal: the whole
point of the envelope is that a number is not publishable without its
denominator, its convention and its exclusions, and an emitter that accepted a
float would let every one of those be forgotten at the last step, where nobody
is looking any more.

The table is written as CSV with a fixed column set and one column per estimate
field, ``estimate.``-prefixed so an estimator naming a field ``n`` cannot
collide with the envelope's own ``n``. Both denominators occupy their own
columns rather than being folded into a rendered fraction (INV-CAN-09), and the
exclusions are rendered by identity, because a table that reported only how many
units were dropped would leave a reader unable to tell an incidental loss from a
systematic one.

The figure counterpart performs the same refusal and then hands the validated
envelopes to a rendering function the caller supplies. Which plotting library
draws a figure is a decision for the caller — this module owns the refusal, not
the chart — and none is a declared dependency of the analysis path.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Sequence

from aperv_tool.analysis.envelope import Envelope

# The envelope's own fields, in the order they are written. Estimate fields are
# appended after these, prefixed and sorted, so a table of mixed estimands has a
# stable column set rather than one that depends on row order.
_FIXED_COLUMNS = (
    "estimand",
    "n",
    "reachable",
    "analysed",
    "denominator_reason",
)
_TRAILING_COLUMNS = (
    "ci_low",
    "ci_high",
    "convention",
    "exclusions",
    "provenance_ref",
)


def table(envelopes: Sequence[Envelope], dest: Path | str) -> Path:
    """Write envelopes to a CSV table at ``dest``.

    Args:
        envelopes: The results to emit. Every element must be an ``Envelope``.
        dest: Where to write. Parent directories are created; nothing else on
            the filesystem is touched, and no input is ever written to.

    Returns:
        The path written.

    Raises:
        TypeError: Any element — or the argument itself — is not an
            ``Envelope``.
    """
    rows = _validated(envelopes)
    estimate_columns = sorted({key for row in rows for key in row.estimate})
    header = (
        list(_FIXED_COLUMNS)
        + [f"estimate.{key}" for key in estimate_columns]
        + list(_TRAILING_COLUMNS)
    )

    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow(_render(row, estimate_columns))
    return path


def figure(
    envelopes: Sequence[Envelope],
    dest: Path | str,
    *,
    render: Callable[[Sequence[Envelope], Path], None],
) -> Path:
    """Draw a figure from envelopes, through a caller-supplied renderer.

    Args:
        envelopes: The results to draw. Every element must be an ``Envelope``.
        dest: Where the renderer writes.
        render: The drawing function, called with the validated envelopes and
            the destination path. It receives envelopes rather than plain
            numbers so that a caption or an axis label can still reach the
            convention and the denominator the figure was drawn under.

    Returns:
        The path handed to the renderer.

    Raises:
        TypeError: Any element — or the argument itself — is not an
            ``Envelope``.
    """
    rows = _validated(envelopes)
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    render(rows, path)
    return path


def _validated(envelopes: Sequence[Envelope]) -> tuple[Envelope, ...]:
    """Every element as an ``Envelope``, or ``TypeError`` naming the type.

    A non-sequence argument — the bare float this refusal exists for — fails
    here too, and with the same message, because ``emit.table(0.4472, dest)`` is
    the call that actually gets written.
    """
    if isinstance(envelopes, Envelope):
        raise TypeError(
            "emit requires a sequence of Envelope, not a single Envelope; "
            "wrap it in a list"
        )
    try:
        items = list(envelopes)
    except TypeError:
        raise TypeError(
            f"emit requires a sequence of Envelope, got "
            f"{type(envelopes).__name__}: a number cannot be emitted without "
            "its denominator, convention and exclusions"
        ) from None

    for position, item in enumerate(items):
        if not isinstance(item, Envelope):
            raise TypeError(
                f"emit requires Envelope, got {type(item).__name__} at position "
                f"{position}: a number cannot be emitted without its "
                "denominator, convention and exclusions"
            )
    return tuple(items)


def _render(envelope: Envelope, estimate_columns: Sequence[str]) -> list[str]:
    """One envelope as a row of strings, with absent estimate fields left empty."""
    values: list[str] = [
        envelope.estimand,
        str(envelope.n),
        str(envelope.denominator.reachable),
        str(envelope.denominator.analysed),
        envelope.denominator.reason,
    ]
    values += [
        "" if key not in envelope.estimate else str(envelope.estimate[key])
        for key in estimate_columns
    ]
    low, high = (
        ("", "") if envelope.ci is None else (str(envelope.ci[0]), str(envelope.ci[1]))
    )
    values += [
        low,
        high,
        "; ".join(
            f"{key}={envelope.convention[key]}" for key in sorted(envelope.convention)
        ),
        "; ".join(f"{item.identity}: {item.reason}" for item in envelope.exclusions),
        envelope.provenance_ref,
    ]
    return values
