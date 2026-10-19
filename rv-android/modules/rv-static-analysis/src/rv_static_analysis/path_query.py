"""
Print the call paths behind one method's target distances.

A document GATOR wrote with `-clientParam distancePaths=true` carries, besides the
`[i, d]` pairs of every method, the path each distance search followed: a
top-level table `pathMethods` of method signatures and a top-level list
`distancePaths` of steps `[i, v, n]` ("towards target `i`, method `v` calls method
`n`"), indices into `distanceTargets` and `pathMethods`. For every written pair
`[i, d]` on a method `m`, following the steps from `m` reaches `distanceTargets[i]`
in exactly `d` steps (INV-ANA-91). `query_paths()` follows them for one method and
returns the chains as text, which is what `rv-static-analysis path` prints
(INV-ANA-98).

### Architectural Decisions:

- The document is read in one `ijson` event pass of its own, not through
  `read_analysis_document`, because that reader drops the path members for the
  campaign readers (INV-ANA-97) and widening its contract for a stand-alone tool
  would touch the parser and the `aperv-tool` derive. The pass builds only
  `distanceTargets`, `pathMethods`, `distancePaths` and the `targetDistances` of
  the requested method; every other value streams past unbuilt. It stops as soon
  as it holds all four, so `windows` and `transitions` are not read.
- A method entry's `targetDistances` is built when its `signature` either equals
  the requested one or has not been read yet, and kept only if the signature
  matches when the entry closes. GATOR writes `signature` first, so in practice
  only the requested method's pairs are built, while a document with the other
  member order still answers correctly.
- Steps are indexed by `(i, v)`. A chain is followed for exactly `d` steps and
  must end on the target's signature, so a missing or misdirected step is
  reported as a document that breaks INV-ANA-91 instead of printing a short
  chain.
- A document cut by a killed producer is read up to the cut, as the campaign
  reader does (INV-ANA-81): the members complete before it are used, and the
  refusals name the truncation when a needed member is missing.

### Role in the System:

- Called by the `rv-static-analysis path DOC METHOD [--target I]` subcommand
  (`__main__.handle_path_command`).
- Stand-alone use of the analyser only; no campaign reader calls it.

### Integration Points:

- Input: a static-analysis document written by `RvsecAnalysisClient` with
  `distancePaths=true`, compact or full, a method's Soot signature and optionally
  a target index.
- Output: for each pair, sorted by target index, the header
  `[i] d=<d> <target signature>` and the `d + 1` signatures of the chain from the
  method to the target, each indented by two spaces.
- Dependencies: `ijson` (backend `yajl2_c`).
"""

from collections.abc import Iterator
from typing import Any

import ijson
from rv_static_analysis.parser.static.static_analysis_parser import _JK

# The C backend is required: the pure-Python backend reads multi-gigabyte
# documents tens of times slower. `get_backend` raises ImportError without it.
_ijson = ijson.get_backend("yajl2_c")

# ijson prefix of an entry of `reachability[].methods[]`.
_METHOD_PREFIX = f"{_JK.reachability}.item.{_JK.methods}.item"

# Top-level members the query builds.
_KEPT_MEMBERS = frozenset((_JK.distance_targets, _JK.path_methods, _JK.distance_paths))

# Indentation of a chain's signatures under its header line.
_CHAIN_INDENT = "  "

_Event = tuple[str, str, Any]


class PathQueryRefused(Exception):
    """A query the document cannot answer.

    Raised by `query_paths` with one line naming the document and the reason.
    """


def query_paths(doc: str, method: str, target: int | None = None) -> list[str]:
    """Return the output lines of the chains from `method` to its targets.

    For each pair `[i, d]` of `method`, sorted by `(i, d)`, or only the pairs with
    `i == target` when `target` is given, the lines are the header
    `[i] d=<d> <signature of distanceTargets[i]>` followed by the chain's `d + 1`
    signatures, from `method` to the target, each indented by two spaces.

    Args:
        doc: Path of a document written with `distancePaths=true`.
        method: Soot signature of an app method, as in `reachability`.
        target: Index into `distanceTargets` to restrict the output to, or None for
            every pair of the method.

    Returns:
        The lines, without newlines. Empty when the method has no pair, which means
        it reaches no target within GATOR's distance bound.

    Raises:
        PathQueryRefused: The document carries no `distancePaths`; `method` has no
            entry in `reachability`; `target` is given and `method` has no pair
            for it; or a chain breaks (INV-ANA-91 does not hold).
        OSError: The document cannot be opened or read.
    """
    members, found, pairs, truncated = _read(doc, method)
    cut = " (the document is truncated)" if truncated else ""

    if _JK.distance_paths not in members:
        raise PathQueryRefused(
            f"{doc}: the document carries no distancePaths{cut}; GATOR writes them "
            "with -clientParam distancePaths=true"
        )
    if not found:
        raise PathQueryRefused(
            f"{doc}: the method {method} has no entry in reachability{cut}"
        )

    pairs = sorted(pairs)
    if target is not None:
        pairs = [pair for pair in pairs if pair[0] == target]
        if not pairs:
            raise PathQueryRefused(
                f"{doc}: the method {method} carries no pair for target {target}"
            )

    targets = members.get(_JK.distance_targets) or []
    methods: list[str] = members.get(_JK.path_methods) or []
    steps = {(i, v): n for i, v, n in members[_JK.distance_paths]}
    position = {signature: index for index, signature in enumerate(methods)}

    lines: list[str] = []
    for index, distance in pairs:
        if not 0 <= index < len(targets):
            raise PathQueryRefused(
                f"{doc}: target {index} of the method {method} is not in "
                "distanceTargets"
            )
        target_signature = targets[index][_JK.signature]
        chain = _follow(
            doc, method, index, distance, target_signature, steps, position, methods
        )
        lines.append(f"[{index}] d={distance} {target_signature}")
        lines.extend(f"{_CHAIN_INDENT}{signature}" for signature in chain)
    return lines


def _follow(
    doc: str,
    method: str,
    index: int,
    distance: int,
    target_signature: str,
    steps: dict[tuple[int, int], int],
    position: dict[str, int],
    methods: list[str],
) -> list[str]:
    """Follow `distance` steps towards target `index` from `method`.

    Args:
        doc: Path of the document, named in the refusal.
        method: Soot signature the chain starts from.
        index: Index into `distanceTargets` of the target being followed.
        distance: The pair's distance, the number of steps to follow.
        target_signature: Signature the chain must end on.
        steps: The next method's `pathMethods` index, by `(target index,
            current method's pathMethods index)`.
        position: Index of each signature in `pathMethods`.
        methods: The `pathMethods` table.

    Returns:
        The chain's `distance + 1` signatures, from `method` to the target.

    Raises:
        PathQueryRefused: A step is missing or points outside `pathMethods`, or the
            chain does not end on the target after `distance` steps.
    """
    chain = [method]
    current = position.get(method)
    for _ in range(distance):
        following = steps.get((index, current)) if current is not None else None
        if following is None or not 0 <= following < len(methods):
            raise PathQueryRefused(
                f"{doc}: the chain of {method} towards target {index} breaks after "
                f"{chain[-1]}: no step for it (INV-ANA-91)"
            )
        chain.append(methods[following])
        current = following
    if chain[-1] != target_signature:
        raise PathQueryRefused(
            f"{doc}: the chain of {method} towards target {index} ends on {chain[-1]} "
            f"after {distance} steps, not on {target_signature} (INV-ANA-91)"
        )
    return chain


def _read(doc: str, method: str) -> tuple[dict, bool, list, bool]:
    """Read the members the query needs in one event pass.

    Args:
        doc: Path of the static-analysis document.
        method: Soot signature of the method whose `targetDistances` to build.

    Returns:
        `(members, found, pairs, truncated)`: the complete top-level members among
        `_KEPT_MEMBERS`; whether `method` has an entry in `reachability`; that
        entry's `targetDistances` (empty when it has none); and whether the input
        ended or stopped being JSON before the pass had everything.

    Raises:
        OSError: The document cannot be opened or read.
    """
    members: dict[str, Any] = {}
    found = False
    pairs: list = []
    # The method entry being read: its signature once met, and its pairs when
    # they were built.
    signature: str | None = None
    entry_pairs: list | None = None

    with open(doc, "rb") as handle:
        events = _ijson.parse(handle, use_float=True)
        try:
            for prefix, event, value in events:
                if event == "map_key" and prefix == "" and value in _KEPT_MEMBERS:
                    members[value] = _build(events)
                    if found and _KEPT_MEMBERS <= members.keys():
                        return members, found, pairs, False
                elif prefix == _METHOD_PREFIX and not found:
                    if event == "start_map":
                        signature, entry_pairs = None, None
                    elif event == "map_key" and value == _JK.signature:
                        signature = _build(events)
                    elif event == "map_key" and value == _JK.target_distances:
                        # A signature not read yet may still be the requested
                        # one; the pairs are built and the `end_map` branch
                        # keeps them only on a match.
                        if signature is None or signature == method:
                            entry_pairs = _build(events)
                    elif event == "end_map" and signature == method:
                        found = True
                        pairs = entry_pairs if isinstance(entry_pairs, list) else []
        except ijson.JSONError:
            # A producer killed mid-write leaves a cut document (INV-ANA-81):
            # keep what was complete before the cut and let the caller name
            # the truncation if a needed member is missing.
            return members, found, pairs, True
    return members, found, pairs, False


def _build(events: Iterator[_Event]) -> Any:
    """Build the next value of the stream, consuming exactly its events.

    The caller's own iterator is passed in, so its loop resumes on the event
    after the value.

    Raises:
        ijson.IncompleteJSONError: The input ends inside the value.
    """
    builder = ijson.ObjectBuilder()
    depth = 0
    for _, event, value in events:
        builder.event(event, value)
        if event == "start_map" or event == "start_array":
            depth += 1
        elif event == "end_map" or event == "end_array":
            depth -= 1
        if depth == 0:
            return builder.value
    raise ijson.IncompleteJSONError("input ended inside a value")
