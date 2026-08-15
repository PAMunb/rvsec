"""Where a question meets the library, and the only place either one names it.

Everything under ``analysis/`` computes estimates and does not know what they are
for. That is enforced, not merely intended: a test greps every module for a
research-question identifier and this package is its single exception
(INV-CAN-22). The coupling has to live *somewhere* — a question is answered by a
particular outcome built a particular way and handed to a particular estimator
with particular knobs — and putting all of it in one directory, most of it in one
data file, is what keeps the library reusable by the next campaign instead of
becoming this campaign's script with a package around it.

## The catalogue is data

``rq_map.toml`` maps an entry id to a builder, an estimator, a caller module and
the parameters. It is TOML rather than Python for one reason that matters: a
reviewer reading the pre-registration can diff it against the catalogue and see
every decided knob in one screen, without reading code. A parameter that moved
into a call site would be invisible to that reading, so the callers below take
*nothing* from their own source — every value comes through ``Entry``.

## Nothing has a default

``Entry.parameter`` raises rather than returning a fallback, because the failure
this package exists to prevent is a number produced under a knob nobody decided.
That is the freeze-item rule of INV-CAN-11 applied to the configuration boundary
as well as to the function boundary: an omitted parameter is an error, and an
explicitly empty one is a decision. TOML has no null, so a knob whose decided
value *is* "none" — no offset, no reference level — is written as the empty
string and read back through ``Entry.optional``. ``offset_column = ""`` says out
loud that there is no offset; omitting the key says nothing at all, and is
refused.

## An entry with no caller is a visible hole

The catalogue is written first, from the pre-registration, and the callers arrive
after. So the state "declared but not yet wired" is normal and must be legible:
``coverage`` reports it rather than letting a silently missing caller read as a
question nobody asked.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from aperv_tool.analysis.corpus import FreezeItemUnset

#: The catalogue. One file, beside the callers it drives.
RQ_MAP = Path(__file__).resolve().parent / "rq_map.toml"

#: How TOML says "the decided value is none". TOML has no null literal, and the
#: alternatives are worse: a missing key is indistinguishable from an oversight,
#: and a magic string like ``"none"`` collides with a column or an arm that could
#: legitimately be called that. The empty string can name neither.
NONE_IN_TOML = ""

#: The table every entry sits under, so the file can grow other top-level tables
#: (a campaign's arm roster, say) without either one having to know about it.
_ENTRY_TABLE = "entry"


class UnknownEntry(KeyError):
    """An entry id absent from the catalogue.

    Raised rather than resolved loosely. A caller invoked for an id the
    catalogue does not carry is either a typo or a stale reference, and both are
    worth stopping on: the alternative is an analysis that runs and reports
    against parameters nobody wrote down.
    """


@dataclass(frozen=True, slots=True)
class Entry:
    """One catalogue row: a question, what answers it, and under which knobs.

    Attributes:
        entry_id: The catalogue key — the one string in this library allowed to
            name a research question.
        question: The question in prose, as the pre-registration states it. Kept
            beside the wiring so a reviewer reads both together.
        builder: Dotted path of the outcome builder, for the record. Documentary
            rather than dispatched on: a caller imports what it uses, and a
            string that pretended to select it would be a second, weaker seat
            for the same decision.
        estimator: Dotted path of the estimator, on the same terms.
        caller: ``module:function`` under this package, or ``None`` when the
            entry is declared and not yet wired.
        parameters: The decided knobs. Consulted through ``parameter`` and
            ``optional``, never read directly, so an omission raises.
    """

    entry_id: str
    question: str
    builder: str
    estimator: str
    caller: str | None
    parameters: Mapping[str, Any]

    def parameter(self, name: str) -> Any:
        """The declared value of ``name``.

        Args:
            name: The parameter, as the catalogue spells it.

        Returns:
            The value, whatever TOML made of it.

        Raises:
            FreezeItemUnset: The catalogue does not declare it. Every parameter
                is a freeze item here — the library supplies no defaults, and a
                caller that invented one would be deciding on the author's
                behalf.
        """
        try:
            return self.parameters[name]
        except KeyError:
            declared = ", ".join(sorted(self.parameters)) or "<none>"
            raise FreezeItemUnset(
                f"{self.entry_id}: parameter {name!r} is not declared in the "
                f"catalogue and has no default; declared parameters are {declared}"
            ) from None

    def optional(self, name: str) -> Any | None:
        """``parameter``, with the empty string read as an explicit "none".

        Args:
            name: The parameter, as the catalogue spells it.

        Returns:
            The value, or ``None`` when the catalogue declares it empty.

        Raises:
            FreezeItemUnset: The catalogue does not declare it. Saying "none"
                and saying nothing remain different statements.
        """
        value = self.parameter(name)
        return None if value == NONE_IN_TOML else value


def load(path: Path | str = RQ_MAP) -> dict[str, Entry]:
    """The whole catalogue, keyed by entry id.

    Args:
        path: The catalogue file. Defaults to the one shipped beside this
            module; a campaign that keeps its own passes it here.

    Returns:
        Entry id → ``Entry``, in file order.

    Raises:
        FileNotFoundError: The catalogue is not there.
        ValueError: An entry omits ``question``, ``builder`` or ``estimator`` —
            the three fields that make a row readable without running it.
    """
    document = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    entries: dict[str, Entry] = {}
    for entry_id, row in document.get(_ENTRY_TABLE, {}).items():
        missing = [
            key for key in ("question", "builder", "estimator") if key not in row
        ]
        if missing:
            raise ValueError(
                f"catalogue entry {entry_id!r} omits {', '.join(missing)}; an entry "
                "that cannot be read without running it is not a catalogue entry"
            )
        entries[entry_id] = Entry(
            entry_id=entry_id,
            question=row["question"],
            builder=row["builder"],
            estimator=row["estimator"],
            caller=row.get("caller") or None,
            parameters=dict(row.get("parameters", {})),
        )
    return entries


def entry(entry_id: str, *, path: Path | str = RQ_MAP) -> Entry:
    """One catalogue row.

    Args:
        entry_id: The catalogue key.
        path: The catalogue file.

    Returns:
        The ``Entry``.

    Raises:
        UnknownEntry: No such id, with the known ids named — a typo is the
            common cause and the list is what resolves it.
    """
    entries = load(path)
    try:
        return entries[entry_id]
    except KeyError:
        known = ", ".join(sorted(entries)) or "<empty catalogue>"
        raise UnknownEntry(
            f"no catalogue entry {entry_id!r}; declared entries are {known}"
        ) from None
