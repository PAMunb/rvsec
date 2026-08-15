"""Which catalogue entries have a caller, and which are still holes.

The catalogue is written from the pre-registration before any of it is wired, so
"declared but not yet answered" is the normal state of a fresh entry rather than
a defect. What would be a defect is that state going unnoticed: an entry whose
caller quietly never arrived looks, from the outside, exactly like a question
nobody asked. This module makes the difference printable.

It distinguishes two ways of not being covered, because they need different
actions. An entry that **declares no caller** is waiting for someone to write
one. An entry whose declared caller **does not resolve** is a broken reference —
a renamed module, a typo, a function that moved — and it is the more urgent of
the two precisely because the catalogue claims it is wired.

Resolution is by import, and a caller is not called here. The report is safe to
run on a machine with no data.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from aperv_tool.analysis.callers import RQ_MAP, Entry, load

#: The three states an entry can be in. ``covered`` means the declared caller
#: imported and the attribute is callable — nothing weaker, because a name that
#: resolves to a module or a constant would satisfy a mere ``hasattr``.
State = Literal["covered", "undeclared", "unresolved"]


@dataclass(frozen=True, slots=True)
class Coverage:
    """One entry's wiring state, with the reason spelled out.

    Attributes:
        entry_id: The catalogue key.
        state: ``covered``, ``undeclared`` or ``unresolved``.
        detail: What was found — the resolved target, or the import error's own
            message. A coverage report whose failures say only "unresolved"
            sends the reader back to the file to guess.
    """

    entry_id: str
    state: State
    detail: str

    @property
    def covered(self) -> bool:
        """True only for a caller that actually resolved to something callable."""
        return self.state == "covered"


def resolve(entry: Entry) -> Callable[..., object]:
    """Import an entry's caller and return the function.

    Args:
        entry: The catalogue row, whose ``caller`` is ``module:function``
            relative to this package.

    Returns:
        The caller.

    Raises:
        ValueError: The entry declares no caller, or declares one in a form
            that is not ``module:function``.
        ModuleNotFoundError: The module does not exist.
        AttributeError: The module exists and the function does not.
        TypeError: The name resolved to something that cannot be called.
    """
    if not entry.caller:
        raise ValueError(f"{entry.entry_id}: no caller declared")
    if entry.caller.count(":") != 1:
        raise ValueError(
            f"{entry.entry_id}: caller {entry.caller!r} is not 'module:function'"
        )
    module_name, function_name = entry.caller.split(":")
    module = importlib.import_module(f"{__package__}.{module_name}")
    target = getattr(module, function_name)
    if not callable(target):
        raise TypeError(
            f"{entry.entry_id}: caller {entry.caller!r} resolved to a "
            f"{type(target).__name__}, which cannot be called"
        )
    return target


def survey(path: Path | str = RQ_MAP) -> tuple[Coverage, ...]:
    """Every entry's wiring state, catalogue order.

    Args:
        path: The catalogue file.

    Returns:
        One ``Coverage`` per entry.
    """
    states: list[Coverage] = []
    for entry in load(path).values():
        if not entry.caller:
            states.append(
                Coverage(
                    entry_id=entry.entry_id,
                    state="undeclared",
                    detail="no caller declared",
                )
            )
            continue
        try:
            resolve(entry)
        except Exception as error:  # noqa: BLE001 — the message is the report
            states.append(
                Coverage(
                    entry_id=entry.entry_id,
                    state="unresolved",
                    detail=f"{entry.caller}: {type(error).__name__}: {error}",
                )
            )
        else:
            states.append(
                Coverage(entry_id=entry.entry_id, state="covered", detail=entry.caller)
            )
    return tuple(states)


def uncovered(path: Path | str = RQ_MAP) -> tuple[Coverage, ...]:
    """The entries with no working caller, both kinds, catalogue order.

    Args:
        path: The catalogue file.

    Returns:
        The ``Coverage`` rows that are not ``covered``. Empty means every
        declared entry is wired.
    """
    return tuple(state for state in survey(path) if not state.covered)


def report(path: Path | str = RQ_MAP) -> str:
    """The survey as text, uncovered entries last and named.

    Args:
        path: The catalogue file.

    Returns:
        The report. The counts come first so a reader who stops after one line
        still knows whether to keep reading.
    """
    states = survey(path)
    holes = [state for state in states if not state.covered]
    lines = [
        f"catalogue: {len(states)} entries, {len(states) - len(holes)} covered, "
        f"{len(holes)} uncovered",
    ]
    for state in states:
        if state.covered:
            lines.append(f"  [covered]    {state.entry_id} -> {state.detail}")
    for state in holes:
        lines.append(f"  [{state.state}] {state.entry_id}: {state.detail}")
    return "\n".join(lines)
