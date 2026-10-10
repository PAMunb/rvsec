"""
Convert a full-mode static-analysis document to the compact form GATOR writes.

GATOR writes the analysis document in one of two modes. In full mode
(`-clientParam fullOutput=true`) it indents by two spaces and gives every app
method its `[i, d]` pair to every target within `DIST_MAX` calls. In compact
mode, the default, it writes no whitespace, keeps per method only the pairs at
`d <= COMPACT_WEIGHED_MAX` and the `COMPACT_K` nearest by `(d, i)`, and records
that reduction in a top-level `distancePairs` member (INV-ANA-85, INV-ANA-86).
`compact_document()` turns a full document into the compact document GATOR
would have written for the same analysis, byte for byte (INV-ANA-87).

The converter exists because GATOR is expensive and the full documents already
exist: re-analysing the Study 03 corpus to get compact documents would cost days
of machine time (57.5 h of wall clock in September 2026), while the conversion is
one streaming pass per document.

### Architectural Decisions:

- The input is read by `read_analysis_document` with
  `PairPolicy.reduce(COMPACT_WEIGHED_MAX, COMPACT_K)`, the reader the parser and
  the `aperv-tool` derive already use, so the input's text and the dropped pairs
  are never held in memory. The reduced document is held whole and serialised
  at once. Its size follows the sections the reduction leaves alone, not the
  input: on the E6 corpus the peak was 1.9 GiB of RSS for
  `org.fossify.calendar_20` (406 MB in, 269 MB out, almost all `windows`) and
  674 MiB for the 9.3 GB sdmse document (55 MB out). Streaming it out would
  need a second state machine for the member order.
- The reader reduces a method's pairs only once it knows the target count,
  which it learns from `distanceTargets`. GATOR writes `distanceTargets` before
  `reachability` whenever it writes any pair, so every document GATOR wrote is
  reduced; a hand-made document with the two members in the other order would
  keep its pairs whole under the marker.
- The reduction is the one the MOP derive applies, so it loses nothing the derive
  reads: a dropped pair has `COMPACT_K` targets ahead of it in its own method.
- The serialiser reproduces Gson's `JsonWriter` with no indent and HTML-safe
  escaping off. `json.dumps(ensure_ascii=False)` escapes strings the same way
  except for U+2028 and U+2029, which Gson escapes and `json.dumps` leaves as
  they are; those two are escaped after encoding. Only integers are accepted as
  numbers: GATOR writes no other kind, and Gson's formatting of a double is not
  reproduced.
- Every refusal is decided before the output file exists, and the output is
  written to a temporary file in its own directory and renamed onto it, so a
  refused or interrupted conversion leaves no file or the previous one.

### Role in the System:

- Called by the `rv-static-analysis compact INPUT OUTPUT` subcommand
  (`__main__.handle_compact_command`).
- `COMPACT_WEIGHED_MAX` and `COMPACT_K` are compared by a parity test with
  `TargetDistances` (Java) and with `aperv-tool`'s `DIST_WEIGHED_MAX`/`DIST_K`
  (INV-ANA-88).

### Integration Points:

- Input: a full-mode document (`<apk_name>.json`) written by
  `RvsecAnalysisClient` and closed, with or without the `complete` sentinel.
- Output: the compact document, UTF-8, no trailing newline.
- Dependencies: `rv_android_core.util.analysis_document` (streaming reader).
"""

import json
import os
import shutil
import tempfile
from typing import Any

from rv_android_core.util.analysis_document import PairPolicy, read_analysis_document
from rv_static_analysis.parser.static.static_analysis_parser import _JK

# Largest distance kept unconditionally, and number of nearest targets kept
# beyond it, per method. They are the derive's DIST_WEIGHED_MAX and DIST_K: the
# MOP-artifact jar weighs a pair only up to d = 3, and activityDist keeps the 3
# nearest targets.
COMPACT_WEIGHED_MAX = 3
COMPACT_K = 3

# Top-level members GATOR writes after `distancePairs`, in its write order. The
# marker goes before the first of them the document holds, which is
# `distanceTargets`, or `components` when the distance pass failed. It thereby
# lands right after the scope members, where `JsonReportWriter` writes it.
_MEMBERS_AFTER_MARKER = (
    _JK.distance_targets,
    _JK.components,
    _JK.reachability,
    _JK.windows,
    _JK.transitions,
    _JK.complete,
)

# The values a document GATOR writes can hold. bool is listed apart from int
# because the check compares exact types.
_JSON_VALUE_TYPES = frozenset((str, int, bool, type(None)))

# Gson escapes the two Unicode line terminators, which `json.dumps` writes raw.
_LINE_TERMINATOR_ESCAPES = (("\u2028", "\\u2028"), ("\u2029", "\\u2029"))

# Suffix of the temporary file the output is written to; its prefix is the
# output's name, hidden, so a leftover file says which output it was.
_TEMP_SUFFIX = ".tmp"


class CompactRefused(Exception):
    """A document that cannot be converted.

    Raised by `compact_document` with a message naming the input and the reason.
    """


def dumps_gson_compact(value: Any) -> str:
    """Serialise a JSON value as Gson's `JsonWriter` writes it with no indent.

    No whitespace is written between tokens. Strings are escaped as Gson
    escapes them with HTML-safe escaping off: `"` and `\\` with a backslash;
    `\\t`, `\\b`, `\\n`, `\\r` and `\\f` in short form; the other code points
    below U+0020, and U+2028 and U+2029, as lowercase `\\uxxxx`; every other
    character, U+007F and non-ASCII included, as itself.

    Args:
        value: A `dict` with `str` keys, `list`, `str`, `int`, `bool` or `None`,
            nested to any depth.

    Returns:
        The serialised text, without a trailing newline.

    Raises:
        CompactRefused: The value holds anything else, such as a `float`.
    """
    stack = [value]
    while stack:
        item = stack.pop()
        kind = type(item)
        if kind is dict:
            stack.extend(item.values())
        elif kind is list:
            stack.extend(item)
        elif kind not in _JSON_VALUE_TYPES:
            raise CompactRefused(
                f"the document holds {item!r}, a {kind.__name__}; GATOR writes "
                "only integers, strings, booleans and null, and Gson's form of "
                "any other value is not reproduced"
            )
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    # A raw U+2028/U+2029 in the encoded text can only sit inside a string, so
    # replacing it in the whole text escapes exactly the characters Gson escapes.
    for character, escape in _LINE_TERMINATOR_ESCAPES:
        text = text.replace(character, escape)
    return text


def compact_document(src: str, dst: str) -> None:
    """Write the compact form of the full document `src` to `dst` (INV-ANA-87).

    The members, their order and their values stay as read, except that each
    `reachability[].methods[].targetDistances` keeps the pairs at
    `d <= COMPACT_WEIGHED_MAX` and the `COMPACT_K` nearest by `(d, i)`, sorted by
    `i`, and `distancePairs: {"weighedMax": COMPACT_WEIGHED_MAX, "k": COMPACT_K}`
    is inserted where GATOR writes it. `dst` takes the permission bits of `src`.

    A document without the `complete` sentinel but closed (the pre-WTG write of a
    run killed during WTG construction) is converted like any other: GATOR's
    compact pre-WTG write is the same document in compact form.

    Args:
        src: Path of a closed full-mode document.
        dst: Path of the compact document; replaced atomically when it exists.

    Raises:
        CompactRefused: `dst` is `src` itself; the read of `src` reports
            truncation; `src` already carries `distancePairs`; or `src` holds a
            value other than an integer, string, boolean or null. `dst` is left
            as it was.
        ValueError: `src` is empty, not JSON, or its root is not an object.
        OSError: `src` cannot be read or `dst` cannot be written.
    """
    # Checked before the read: writing onto the input would destroy the only
    # full copy of the analysis.
    if os.path.exists(dst) and os.path.samefile(src, dst):
        raise CompactRefused(f"{src}: the output {dst} is the input file itself")

    document, truncated = read_analysis_document(
        src, PairPolicy.reduce(COMPACT_WEIGHED_MAX, COMPACT_K)
    )
    if truncated:
        raise CompactRefused(
            f"{src}: the document is truncated, so it is not a document GATOR "
            "wrote in full and has no compact form"
        )
    if _JK.distance_pairs in document:
        raise CompactRefused(f"{src}: the document is already compact")

    _sort_pairs_by_target(document)
    try:
        text = dumps_gson_compact(_with_marker(document))
    except CompactRefused as error:
        raise CompactRefused(f"{src}: {error}") from error
    _write_atomically(src, dst, text)


def _sort_pairs_by_target(document: dict) -> None:
    """Sort each method's reduced `targetDistances` by target index, in place.

    The reader returns the kept pairs ordered by `(d, i)`, while GATOR writes them
    ordered by `i`. The reader merges a method's pairs by target, so a list holds
    one pair per target and sorting the `[i, d]` lists sorts by `i`.
    """
    reachability = document.get(_JK.reachability)
    for entry in reachability if isinstance(reachability, list) else ():
        methods = entry.get(_JK.methods) if isinstance(entry, dict) else None
        for method in methods if isinstance(methods, list) else ():
            pairs = (
                method.get(_JK.target_distances) if isinstance(method, dict) else None
            )
            if isinstance(pairs, list):
                pairs.sort()


def _with_marker(document: dict) -> dict:
    """Return the document with `distancePairs` inserted where GATOR writes it.

    The marker goes right before the first member GATOR writes after it. A
    document holding none of them gets the marker last, after its scope members.
    """
    marker = {_JK.weighed_max: COMPACT_WEIGHED_MAX, _JK.k: COMPACT_K}
    anchor = next((key for key in document if key in _MEMBERS_AFTER_MARKER), None)
    compacted: dict = {}
    for key, value in document.items():
        if key == anchor:
            compacted[_JK.distance_pairs] = marker
        compacted[key] = value
    if anchor is None:
        compacted[_JK.distance_pairs] = marker
    return compacted


def _write_atomically(src: str, dst: str, text: str) -> None:
    """Write `text` to `dst` through a temporary file in the same directory.

    The temporary file is flushed to disk before the rename, as GATOR syncs its
    own output, so a crash leaves either the previous `dst` or the new one. It
    takes `src`'s permission bits, because `tempfile` creates it readable by its
    owner only. On any failure it is removed.

    Args:
        src: The input document, read here only for its permission bits.
        dst: Path the output is renamed onto.
        text: The serialised compact document.
    """
    directory = os.path.dirname(os.path.abspath(dst))
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=directory,
        prefix=f".{os.path.basename(dst)}.",
        suffix=_TEMP_SUFFIX,
        delete=False,
    )
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copymode(src, handle.name)
        os.replace(handle.name, dst)
    except BaseException:
        try:
            os.remove(handle.name)
        except FileNotFoundError:
            pass
        raise
