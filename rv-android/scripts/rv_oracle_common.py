"""Shared pieces of the L3-b and L3-c oracle derivations.

Both derivations read a campaign CSV, reduce it to unique misuses, and write one
oracle per APK with a trace pair the comparator can read. The parts that must be
identical between them live here, because a divergence would not announce
itself: two oracles keyed differently, or two traces written in different
shapes, would still load, still score, and still produce a verdict — a wrong
one.

The unit of analysis
--------------------
`(apk, class, method, spec)` — one *unique misuse*, as defined at
`results-rq1.tex:41` and implemented by the article's own
`repair_summary_outcome.py:53`. Not `(spec, errorType)`: that key merges two
different misuses of one specification into one row, and not the raw event,
which counts a misuse once per line it was reported at.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# The producer's rule, copied from `ErrorDescription.FRAME_SUFFIX` in
# rvsec-core. Two properties matter and both are deliberate: the group contains
# no nested parenthesis, and it ends in `:<digits>`. Everything else about it is
# unconstrained, which is what lets it recognise `(Unknown Source:1)` and
# `(r8-map-id-…:17)` as source positions.
FRAME_SUFFIX = re.compile(r"\(([^()]+:\d+)\)$")


def split_frame(value: str) -> tuple[str, str, str] | None:
    """Recover `(class, method, location)` from a whole stack frame, or None.

    Mirrors `ErrorDescription.createErrorSummary`: strip the trailing position
    group, then split the remainder at its **last** dot. The class part is a
    dotted path and a method name never contains a dot, so the last dot is the
    separator whatever the name is made of — no guess about what a method looks
    like is needed, and none is made.
    """
    if not value:
        return None
    m = FRAME_SUFFIX.search(value)
    if not m:
        return None
    remainder = value[: m.start()]
    last_dot = remainder.rfind(".")
    if last_dot == -1:
        return None
    return remainder[:last_dot], remainder[last_dot + 1 :], m.group(1)


def repair_frame_form(row: dict) -> bool:
    """Repair one row in place if its class/method hold a whole stack frame.

    When `ErrorDescription`'s split fails upstream, its fallback leaves the
    entire frame — source position included — in *both* the class and the method
    field. The line number then silently joins the key, and one misuse is
    counted once per line it occurs at. Recovering from either field yields the
    same triple; the method is tried first because that is the field the
    upstream regex is documented to reject.

    Returns True when a repair was applied.
    """
    recovered = split_frame(row.get("method", "")) or split_frame(row.get("class", ""))
    if not recovered:
        return False
    row["class"], row["method"], row["location"] = recovered
    return True


#: `unique_msg` is seven `:::`-joined parts, in this order. Named rather than
#: indexed at the call sites: `parts[3]` and `parts[4]` were the error type and the
#: message under the five-part key, and after gh104 `parts[4]` is the violation code
#: — a reader that kept the old index would have gone on producing a column labelled
#: "message" holding a code, with nothing raising.
UNIQUE_MSG_PARTS = ("class", "method", "spec", "error_type", "code", "event", "message")


def unique_msg_parts(unique_msg: str) -> dict[str, str] | None:
    """The seven named parts of a `unique_msg`, or None when it does not have seven.

    A part count other than seven means either a key of the five-part identity era —
    the published dataset and every campaign consolidated before gh104 — or a
    `message` carrying the `:::` the envelope grammar forbids. Neither is reinterpreted
    by taking the parts positionally anyway: the two eras are not comparable, and a key
    with a separator inside a part is unreadable to every consumer that splits on it.
    """
    parts = unique_msg.split(":::")
    if len(parts) != len(UNIQUE_MSG_PARTS):
        return None
    return dict(zip(UNIQUE_MSG_PARTS, parts))


def error_type(unique_msg: str) -> str:
    """The `error_type` part, or `Unknown` for a key that is not seven parts."""
    parts = unique_msg_parts(unique_msg)
    return parts["error_type"] if parts else "Unknown"


def code(unique_msg: str) -> str:
    """The `code` part — the stable violation code of the message envelope."""
    parts = unique_msg_parts(unique_msg)
    return parts["code"] if parts else ""


def event(unique_msg: str) -> str:
    """The `event` part — the automaton event that failed."""
    parts = unique_msg_parts(unique_msg)
    return parts["event"] if parts else ""


def message(unique_msg: str) -> str:
    """The `message` part — the whole envelope, or the free text before it."""
    parts = unique_msg_parts(unique_msg)
    return parts["message"] if parts else ""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def apk_base_name(apk: str) -> str:
    """`app.pwhs.blockads_45.apk` -> `app.pwhs.blockads`.

    The inverse of `TraceComparator.resolveOracleForApk`, which strips `.apk`
    and a trailing `_<digits>` version suffix before looking for
    `<base>-oracle.yaml`. Deriving a name any other way produces an oracle that
    resolves for no APK — the defect that made the pooled files inert in batch
    mode.
    """
    base = apk[:-4] if apk.endswith(".apk") else apk
    us = base.rfind("_")
    if 0 < us < len(base) - 1 and base[us + 1 :].isdigit():
        base = base[:us]
    return base


def short_class(qualified: str) -> str:
    """The short form `ErrorSummary.className()` would have written.

    It returns `classQualifiedName` unchanged today — the `$`-stripping branch
    is commented out in the Java — so this is deliberately the identity, not a
    last-segment split. Writing a *different* short form here would make traces
    that no producer could have emitted, and the comparator accepts either form
    anyway.
    """
    return qualified


def violation_line(spec: str, qualified: str, method: str, location: str,
                   etype: str, expecting: str) -> str:
    """One line in the on-device collector's format.

    `ErrorSummary.toString()` writes
    `spec,classQualifiedName,className,methodName,location,error` and
    `ErrorCollector:37` appends `"," + expecting`. The tag is padded exactly as
    logcat's `threadtime` format renders it, so these traces exercise the same
    parsing path a real recording does. Newlines are stripped from `expecting`
    because a line break would split one event into two.
    """
    expecting = (expecting or "unknown").replace("\n", " ").replace("\r", " ").strip()
    fields = ",".join([spec, qualified, short_class(qualified), method,
                       location or "Unknown Source:1", etype, expecting])
    return f"08-06 00:00:00.000  1000  1000 V RVSEC   : {fields}"


def write_trace(path: Path, misuses) -> None:
    """Write one side's trace: one violation line per unique misuse.

    Presence, not multiplicity. Occurrence counts are not comparable across the
    two variants — each side was driven by its own GUI exploration, so a
    category firing 1,675 times against 40 says which screens were reached, not
    what either weaver emits — and `countFalsePositives` counts per occurrence,
    so raw multiplicities would let exploration depth decide the verdict.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        violation_line(m["spec"], m["class"], m["method"], m["location"],
                       m["error_type"], m["message"])
        for m in sorted(misuses, key=lambda m: (m["spec"], m["class"],
                                                m["method"], m["error_type"]))
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def oracle_events_block(misuses) -> list[str]:
    """The `expected_events:` block, one entry per unique misuse."""
    lines = ["expected_events:"]
    ordered = sorted(misuses, key=lambda m: (m["spec"], m["class"],
                                             m["method"], m["error_type"]))
    for i, m in enumerate(ordered, start=1):
        lines += [
            f"  - id: {i}",
            f"    spec: {m['spec']}",
            f"    error_type: {m['error_type']}",
            f"    location: {{ class: {m['class']}, method: {m['method']} }}",
            # Left null deliberately. The `expecting` text is generated by the
            # specification and names the offending parameter, so it would
            # discriminate two misuses of one method — but it is also the field
            # most likely to move when a .mop set is edited, and issue #101 is
            # editing those sets in parallel.
            "    expected_message_substring: null",
        ]
    return lines
