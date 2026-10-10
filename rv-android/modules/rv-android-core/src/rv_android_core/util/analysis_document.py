"""
Read the static-analysis document as a stream of JSON events.

The document GATOR writes (`<apk_name>.json`) carries, for every app method, its
call-graph distance to every monitored target:
`reachability[].methods[].targetDistances`, `[i, d]` pairs indexing the top-level
`distanceTargets` list. Those pairs make the document 100 to 400 times larger than the
rest of it (2.16 GB for a 39,950-method app, 9.34 GB for the largest of the Study 03
corpus), and a `json.loads` of it materialises every pair as a Python list. Its readers
keep few or none of them: `StaticAnalysisParser` keeps none, and the MOP-artifact
derivation of `aperv-tool` keeps the pairs within three calls and each method's three
nearest.

`read_analysis_document()` walks the file once with `ijson` and builds every value
as `json.loads` would, except the distance members, which the caller's
`PairPolicy` either drops without building or folds into per-target minima as the
events arrive.

Where yajl and `json.loads` disagree, the reader follows yajl. A lone surrogate escape
(`"\\ud800"`) comes back as `'?'` with no truncation reported, and an integer beyond
64 bits or a number beyond double range stops the read as if the input had ended
there. GATOR writes neither.

### Architectural Decisions:

- One event pass rather than one `ijson.items` pass per section. The C `items`
  builder is about twice as fast per byte, but a section-per-pass read needs four
  or more passes and cannot tell, in a truncated file, which section was the last
  one written in full. In one pass a top-level member is complete exactly when its
  closing event was read (INV-ANA-81).
- The reader lives here because both readers need it and `aperv-tool` does not
  depend on `rv-static-analysis`. Two copies of an event builder would drift on the
  edge cases that matter here: truncation and skipped subtrees.
- `digest_of_file()` lives beside it because the parsed-copy cache of
  `rv-static-analysis` and the MOP-artifact cache of `aperv-tool` key on the same
  digest of the same file.
- The C backend is required at import. The pure-Python backend reads tens of times
  slower, which on a 9 GB document turns a two-minute read into an hour inside a
  task's setup; an environment without the wheel fails here instead.
- Numbers are read with `use_float=True`, so integers are `int` and every other
  number is `float`, as `json.loads` returns them.

### Role in the System:

- `rv_static_analysis.parser.static.static_analysis_parser` reads with
  `PairPolicy.DROP`, and caches the result keyed by `digest_of_file()`.
- `aperv_tool.tools.aperv.tool.ApeRVTool._derive_mop_artifact` reads with
  `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)` and passes the dict to `derive()`.

### Integration Points:

- Input: the path of a static-analysis document, any size, possibly truncated by a
  producer killed mid-write.
- Output: `(dict, truncated)`; the dict has the shape `json.loads` would give,
  minus or with reduced distance members.
- Dependencies: `ijson` (backend `yajl2_c`).
"""

import hashlib
from dataclasses import dataclass
from typing import Any, ClassVar, Iterator

import ijson

if ijson.backend != "yajl2_c":
    raise ImportError(
        f"ijson backend is {ijson.backend!r}, not 'yajl2_c': the C extension is "
        "missing, and the pure-Python backend is too slow for multi-gigabyte "
        "static-analysis documents"
    )

# === DOCUMENT LAYOUT ===

# The two distance members, named as GATOR's JsonSchema.Keys names them.
DISTANCE_TARGETS_KEY = "distanceTargets"
TARGET_DISTANCES_KEY = "targetDistances"
REACHABILITY_KEY = "reachability"

# ijson prefix of an entry of `reachability[].methods[]`: the object whose
# `targetDistances` member the policy applies to. A member of that name anywhere
# else in the document is an ordinary member.
_METHOD_PREFIX = "reachability.item.methods.item"

DIGEST_ALGORITHM = "sha256"

_Event = tuple[str, str, Any]


@dataclass(frozen=True)
class PairPolicy:
    """What the reader does with the distance members.

    Attributes:
        drop: When True, `distanceTargets` and every method's `targetDistances`
            are consumed without building a value and are absent from the result.
            When False, `distanceTargets` is built and each `targetDistances` is
            reduced (see `reduce`).
        weighed_max: Under reduction, every pair at a distance up to this value is
            kept.
        k: Under reduction, the `k` nearest pairs by `(d, i)` are kept whatever
            their distance.
        DROP: The shared `PairPolicy(drop=True)` instance.
    """

    drop: bool
    weighed_max: int = 0
    k: int = 0

    DROP: ClassVar["PairPolicy"]

    @staticmethod
    def reduce(weighed_max: int, k: int) -> "PairPolicy":
        """Keep, per method, the pairs at `d <= weighed_max` and the `k` nearest.

        The pairs are first merged by the minimum distance per target index, as the
        MOP derivation merges them, so "nearest" ranks targets rather than raw
        entries. For a consumer that merges by the minimum and then cuts its lists
        at `d <= weighed_max` or at its `k` nearest, the reduction is exact: a
        dropped pair has `k` targets ahead of it in its own method, and they stay
        ahead of it after any merge.

        Args:
            weighed_max: Largest distance kept unconditionally.
            k: Number of nearest targets kept per method beyond that cut.

        Returns:
            A reducing policy (`drop=False`).
        """
        return PairPolicy(drop=False, weighed_max=weighed_max, k=k)


PairPolicy.DROP = PairPolicy(drop=True)


def read_analysis_document(path: str, pairs: PairPolicy) -> tuple[dict, bool]:
    """Read a static-analysis document in one pass of JSON events.

    Every member is built as `json.loads` would build it — same values, same types,
    same key order, the last of duplicate keys winning — except `distanceTargets`
    (absent under `PairPolicy.DROP`) and the `targetDistances` member of every
    `reachability[].methods[]` entry (absent under `DROP`, reduced otherwise). The
    file's text is never held in memory, nor any dropped pair.

    Truncation is reported rather than raised. A top-level member enters the
    result only once its value was read in full, so a document cut by a killed
    producer yields the members written before the cut and none of the one being
    written. A top-level number needs a byte after it: when the input ends on a
    digit, `12` may be the start of `123`, and the number is dropped. The check reads
    the file's last byte, so when the read stops earlier on bytes that are not JSON, a
    complete top-level number just before them is dropped too.

    Bytes after the root object closes are not read.

    Args:
        path: Path of the document.
        pairs: What to do with the distance members.

    Returns:
        `(document, truncated)`. `truncated` is True iff the input ended, or stopped
        being JSON, after the root object opened and before it closed.

    Raises:
        OSError: The file cannot be opened or read.
        ValueError: The file is empty, its first token is not JSON, or its root is not
            an object. Bytes that stop being JSON after the root opened return
            `({}, True)` or the members completed before them.
    """
    with open(path, "rb") as handle:
        events = ijson.parse(handle, use_float=True)
        try:
            _, event, _ = next(events)
        except (ijson.JSONError, StopIteration) as error:
            raise ValueError(f"{path} is not a JSON document: {error}") from error
        if event != "start_map":
            raise ValueError(f"{path}: the root of the document is not an object")

        document: dict = {}
        # A top-level number is held back until the next event proves it ended.
        pending: tuple[str, Any] | None = None
        try:
            for _, event, key in events:
                if pending is not None:
                    document[pending[0]] = pending[1]
                    pending = None
                if event == "end_map":
                    return document, False
                # Every other event at this level is a member's key.
                if key == DISTANCE_TARGETS_KEY and pairs.drop:
                    _skip_value(events)
                    continue
                hook = None
                if key == REACHABILITY_KEY:
                    hook = _distance_hook(pairs, _target_bound(document))
                event, value = _build_value(events, hook)
                if event == "number":
                    pending = (key, value)
                else:
                    document[key] = value
        except (ijson.JSONError, StopIteration):
            if pending is not None and not _ends_inside_number(path):
                document[pending[0]] = pending[1]
            return document, True
    # ijson raises before its events run out on any input that does not close the
    # root, so this is reached only on a backend that stops quietly.
    return document, True


def digest_of_file(path: str) -> str:
    """Compute the digest a cache records to name its source document.

    The file is hashed as stored on disk — not a re-encoded parse, which would not
    round-trip — and streamed in chunks by `hashlib.file_digest`, so the digest of a
    multi-gigabyte document holds no copy of it in memory and a cache hit costs one
    sequential read.

    Args:
        path: Path of the file.

    Returns:
        The digest as `"<algorithm>:<hex>"`, e.g. `"sha256:9f86d0…"`.

    Raises:
        OSError: The file cannot be opened or read.
    """
    with open(path, "rb") as source_file:
        digest = hashlib.file_digest(source_file, DIGEST_ALGORITHM)
    return f"{DIGEST_ALGORITHM}:{digest.hexdigest()}"


# Bytes that can continue a JSON number.
_NUMBER_BYTES = frozenset(b"0123456789+-.eE")


def _ends_inside_number(path: str) -> bool:
    """Check whether the file's last byte could belong to an unfinished number.

    yajl reports a number that the end of input cut, so a truncated document whose
    last member is a number cannot tell `12` from the start of `123` by its events.
    Any byte after the number (a space, a comma, the next key) ends it.
    """
    with open(path, "rb") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            return False
        handle.seek(-1, 2)
        return handle.read(1)[0] in _NUMBER_BYTES


# === VALUE BUILDING ===

# Returned by a hook whose member must be left out of the method.
_DROPPED = object()


def _build_value(events: Iterator[_Event], hook=None) -> tuple[str, Any]:
    """Build the next value of the stream.

    Containers are linked into their parent when they open, so the stack holds
    only the open path. `hook`, when given, is called on every `targetDistances`
    key of a method entry and consumes that member's value itself.

    Args:
        events: The `ijson.parse` stream, positioned before the value's first event.
        hook: Handler from `_distance_hook`, or None to build every member.

    Returns:
        The value's first event name and the value.

    Raises:
        ijson.IncompleteJSONError: The input ends inside the value.
    """
    _, event, value = next(events)
    if event == "start_map":
        root: Any = {}
    elif event == "start_array":
        root = []
    else:
        return event, value

    stack: list[Any] = [root]
    keys: list[Any] = [None]
    for prefix, event, value in events:
        if event == "map_key":
            if (
                hook is not None
                and value == TARGET_DISTANCES_KEY
                and prefix == _METHOD_PREFIX
            ):
                built = hook(events)
                if built is not _DROPPED:
                    stack[-1][value] = built
                continue
            keys[-1] = value
        elif event == "start_map" or event == "start_array":
            child: Any = {} if event == "start_map" else []
            parent = stack[-1]
            if type(parent) is list:
                parent.append(child)
            else:
                parent[keys[-1]] = child
            stack.append(child)
            keys.append(None)
        elif event == "end_map" or event == "end_array":
            stack.pop()
            keys.pop()
            if not stack:
                return "start_map" if type(root) is dict else "start_array", root
        else:
            parent = stack[-1]
            if type(parent) is list:
                parent.append(value)
            else:
                parent[keys[-1]] = value
    raise ijson.IncompleteJSONError("input ended inside a value")


def _skip_value(events: Iterator[_Event]) -> None:
    """Consume the next value of the stream without building it."""
    depth = 0
    for _, event, _ in events:
        if event == "start_map" or event == "start_array":
            depth += 1
        elif event == "end_map" or event == "end_array":
            depth -= 1
        if depth == 0:
            return
    raise ijson.IncompleteJSONError("input ended inside a skipped value")


# === DISTANCE PAIRS ===


def _target_bound(document: dict) -> int | None:
    """Return the exclusive bound on a pair's target index, as derivation computes it.

    `0` when `distanceTargets` is not a list, so every pair fails the range check.
    `None` when `distanceTargets` has not been read yet. GATOR writes it before
    `reachability`; for a document that does not, the bound is unknown while the
    pairs stream past and the reduction keeps every valid per-target minimum, which
    is still exact, only larger.
    """
    if DISTANCE_TARGETS_KEY not in document:
        return None
    targets = document[DISTANCE_TARGETS_KEY]
    return len(targets) if isinstance(targets, list) else 0


def _distance_hook(pairs: PairPolicy, bound: int | None):
    """Return the `targetDistances` handler `_build_value` calls inside `reachability`.

    The handler consumes the member's value and returns `_DROPPED` under a dropping
    policy, else the reduced pair list.
    """
    if pairs.drop:

        def drop(events: Iterator[_Event]) -> object:
            _skip_value(events)
            return _DROPPED

        return drop

    def reduce(events: Iterator[_Event]) -> list:
        return _reduce_pairs(events, bound, pairs.weighed_max, pairs.k)

    return reduce


def _reduce_pairs(
    events: Iterator[_Event], bound: int | None, weighed_max: int, k: int
) -> list[list[int]]:
    """Fold one `targetDistances` value into the pairs a reduction keeps.

    An entry counts only when the MOP derivation's `_read_pairs` would count it: a
    two-element list of integers `[i, d]`, booleans excluded, with `0 <= i`,
    `d >= 0` and `i < bound`. Anything else is skipped, so producer noise cannot
    take one of the `k` nearest places from a pair the derivation would read. A
    value that is not a list holds no pair.

    Args:
        events: The `ijson.parse` stream, positioned before the member's value.
        bound: Exclusive bound on `i` from `_target_bound`, or None when unknown.
        weighed_max: Largest distance kept unconditionally.
        k: Number of nearest targets kept beyond that cut.

    Returns:
        `[[i, d], …]` ordered by `(d, i)`: every per-target minimum when `bound` is
        unknown, else those at `d <= weighed_max` and the `k` nearest.

    Raises:
        ijson.IncompleteJSONError: The input ends inside the value.
    """
    _, event, _ = next(events)
    if event != "start_array":
        if event == "start_map":
            _skip_rest(events)
        return []

    minima: dict[int, int] = {}
    for _, event, value in events:
        if event == "end_array":
            break
        if event == "start_array":
            entry = _read_entry(events)
        else:
            if event == "start_map":
                _skip_rest(events)
            continue
        if entry is None:
            continue
        index, distance = entry
        if index < 0 or distance < 0 or (bound is not None and index >= bound):
            continue
        previous = minima.get(index)
        if previous is None or distance < previous:
            minima[index] = distance
    else:
        raise ijson.IncompleteJSONError("input ended inside targetDistances")

    ordered = sorted((distance, index) for index, distance in minima.items())
    if bound is None:
        return [[index, distance] for distance, index in ordered]
    return [
        [index, distance]
        for rank, (distance, index) in enumerate(ordered)
        if distance <= weighed_max or rank < k
    ]


def _skip_rest(events: Iterator[_Event]) -> None:
    """Consume the rest of a container whose opening event was already read."""
    depth = 1
    for _, event, _ in events:
        if event == "start_map" or event == "start_array":
            depth += 1
        elif event == "end_map" or event == "end_array":
            depth -= 1
            if depth == 0:
                return
    raise ijson.IncompleteJSONError("input ended inside a skipped value")


def _read_entry(events: Iterator[_Event]) -> tuple[int, int] | None:
    """Read one pair entry whose opening `[` was already read.

    Returns:
        `(i, d)` when the entry is exactly two integers, else None. The entry is
        consumed to its closing `]` either way.
    """
    items: list[Any] = []
    well_formed = True
    for _, event, value in events:
        if event == "end_array":
            break
        if event == "start_map" or event == "start_array":
            _skip_rest(events)
            well_formed = False
        # Booleans arrive as `boolean` events, and under `use_float=True` a number
        # with a fraction or exponent is a float, so only JSON integers pass here.
        elif event == "number" and type(value) is int:
            items.append(value)
        else:
            well_formed = False
    else:
        raise ijson.IncompleteJSONError("input ended inside a pair")
    if not well_formed or len(items) != 2:
        return None
    return items[0], items[1]
