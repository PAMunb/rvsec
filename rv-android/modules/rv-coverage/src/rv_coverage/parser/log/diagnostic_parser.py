"""
Stateful parser for execution-level diagnostic events in Android logcat.

Assemble crashes (`AndroidRuntime:E` FATAL blocks), class-load `VerifyError`s
(`art`/`dalvikvm:E`), and ANRs (`ActivityManager:W`) into `RvDiagnosticEvent`
objects. Unlike RVSEC/RVSEC-COV records — one line maps to one record, handled by
the stateless `parse_logcat_line` — a crash is multi-line: a header plus N stack
frames, `Caused by:`, and `... N more`, all sharing one `(tag, pid, tid)`.

### Why a separate stateful parser (decision D1 / ADR-001):
`parse_logcat_line` stays a pure 2-tuple function on the RVSEC/COV hot path; this
class carries the multi-line state so that path is untouched (the G1 non-regression
gate holds by construction). Both `parse_logcat_file` (offline / resume) and
`CoverageTracker` (live) feed every line here and register completed events into the
isolated `LogcatRepository.diagnostic_events` collection.

### Contract:
- `feed_line(line)` returns a completed event when the current line closes the
  buffered block (its `(tag, pid, tid)` key changes, or a non-continuation line
  arrives), else None. Lines that are not diagnostic content are skipped.
- `flush()` emits any still-buffered event at end of input; idempotent thereafter.

App attribution comes from the block itself (`Process: <pkg>` for crashes,
`ANR in <pkg>` for ANRs), never from a live PID (decision D6).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from rv_android_core.domain.log import RvDiagnosticEvent

from rv_coverage.parser.log.logcat_parser import (
    _convert_to_datetime,
    _parse_logcat_line,
)

logger = logging.getLogger(__name__)

# Base tag fields (without priority suffix) recognised as diagnostic content.
# Recognition is on the parsed threadtime *tag field*, never a message substring,
# so an `RVSEC-COV` line whose payload contains `isAndroidRuntime()` is ignored
# (INV-ANA-47).
_TAG_ANDROID_RUNTIME = "AndroidRuntime"
_TAG_ART = "art"
_TAG_DALVIKVM = "dalvikvm"
_TAG_ACTIVITY_MANAGER = "ActivityManager"
_DIAGNOSTIC_BASE_TAGS = frozenset(
    {_TAG_ANDROID_RUNTIME, _TAG_ART, _TAG_DALVIKVM, _TAG_ACTIVITY_MANAGER}
)

_CATEGORY_CRASH = "crash"
_CATEGORY_VERIFY_ERROR = "verify_error"
_CATEGORY_ANR = "anr"

# Frame line after threadtime parsing: the leading tab is consumed as whitespace,
# so a frame reads "at <class>.<method>(<File>:<line>)".
_FRAME_RE = re.compile(r"at\s+(.+)\.([^.(]+)\((.*)\)")
_PROCESS_RE = re.compile(r"Process:\s*([^,]+),\s*PID:\s*(\d+)")
_EXCEPTION_RE = re.compile(
    r"((?:[\w$]+\.)*[\w$]+(?:Exception|Error|Throwable))(?::\s*(.*))?$"
)
_REJECTING_CLASS_RE = re.compile(r"Rejecting class\s+([\w.$/]+)")
_ANR_IN_RE = re.compile(r"ANR in\s+([\w.$]+)")
_PROCESS_DIED_RE = re.compile(r"Process\s+([\w.$]+).*has died")


class DiagnosticEventParser:
    """Assemble multi-line diagnostic events from logcat lines, grouped by
    `(tag, pid, tid)`. See module docstring for the contract."""

    def __init__(self) -> None:
        # Buffered parsed lines (each a dict from `_parse_logcat_line`) for the
        # event currently being assembled, plus its grouping key.
        self._buffer: List[Dict[str, Any]] = []
        self._key: Optional[Tuple[str, str, str]] = None

    def feed_line(self, line: str) -> Optional[RvDiagnosticEvent]:
        """Feed one raw logcat line; return a completed event if this line closes
        the buffered block, else None."""
        parsed = _parse_logcat_line(line)

        # Non-threadtime line (e.g. "--------- beginning of crash") — not a
        # continuation, so it closes any open event and is itself skipped
        # (INV-ANA-48).
        if parsed is None:
            return self._close()

        tag = parsed["tag"]
        if tag not in _DIAGNOSTIC_BASE_TAGS:
            # RVSEC / RVSEC-COV / any other tag — closes the current event; the
            # RVSEC/COV hot path is handled separately by parse_logcat_line.
            return self._close()

        key = (tag, parsed["pid"], parsed["tid"])
        is_start, is_cont = self._classify(tag, parsed["message"])

        # Continuation of the open block (same key, e.g. a crash stack frame).
        if self._buffer and key == self._key and is_cont:
            self._buffer.append(parsed)
            return None

        # This line does not continue the current event: close it, then maybe
        # start a new one. At most one completed event is returned per call.
        completed = self._close()
        if is_start:
            self._buffer = [parsed]
            self._key = key
        return completed

    def flush(self) -> Optional[RvDiagnosticEvent]:
        """Emit any still-buffered event at end of input; idempotent thereafter."""
        return self._close()

    @staticmethod
    def _classify(tag: str, message: str) -> Tuple[bool, bool]:
        """Classify a diagnostic line as (is_start, is_continuation).

        - AndroidRuntime: a `FATAL EXCEPTION` header starts a crash; every other
          AndroidRuntime line (Process:, the exception, `\\tat` frames, `Caused
          by:`, `... N more`) continues it.
        - art / dalvikvm: a `Rejecting class` / `Verification error` line is a
          single-line verify_error start; other art lines are ignored.
        - ActivityManager: an `ANR in` / `has died` line is a single-line ANR
          start; other ActivityManager lines are ignored.
        """
        if tag == _TAG_ANDROID_RUNTIME:
            is_start = message.startswith("FATAL EXCEPTION")
            return is_start, not is_start
        if tag in (_TAG_ART, _TAG_DALVIKVM):
            is_start = (
                "Rejecting class" in message
                or "Verification error" in message
                or "VerifyError" in message
            )
            return is_start, False
        if tag == _TAG_ACTIVITY_MANAGER:
            is_start = "ANR in" in message or "has died" in message
            return is_start, False
        return False, False

    def _close(self) -> Optional[RvDiagnosticEvent]:
        """Build and return the buffered event (if any), resetting state."""
        if not self._buffer:
            return None

        lines = self._buffer
        tag = self._key[0] if self._key else ""
        self._buffer = []
        self._key = None

        try:
            if tag == _TAG_ANDROID_RUNTIME:
                return self._build_crash(lines)
            if tag in (_TAG_ART, _TAG_DALVIKVM):
                return self._build_verify_error(lines)
            if tag == _TAG_ACTIVITY_MANAGER:
                return self._build_anr(lines)
        except Exception as exc:  # defensive: never let a malformed block abort parsing
            logger.warning("Failed to build diagnostic event: %s", exc)
        return None

    @staticmethod
    def _select_app_frame(frames: List[str], process: str) -> Optional[str]:
        """Return the first frame belonging to ``process`` (by class package
        prefix), or the first frame overall, or None when there are no frames."""
        if process:
            for frame in frames:
                fm = _FRAME_RE.match(frame)
                if fm and fm.group(1).startswith(process):
                    return frame
        return frames[0] if frames else None

    @staticmethod
    def _common_fields(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fields shared by every category: timing, ids, raw block."""
        first = lines[0]
        return {
            "pid": first["pid"],
            "tid": first["tid"],
            "original_msg": "\n".join(line["original"] for line in lines),
            "time_occurred": _convert_to_datetime(first["date"], first["time"]),
        }

    def _build_crash(self, lines: List[Dict[str, Any]]) -> RvDiagnosticEvent:
        messages = [line["message"] for line in lines]
        common = self._common_fields(lines)

        header = messages[0]
        fatal = any(m.startswith("FATAL EXCEPTION") for m in messages)

        # App attribution from the "Process: <pkg>, PID: <n>" line (D6).
        process, pid = "", common["pid"]
        for m in messages:
            mp = _PROCESS_RE.match(m)
            if mp:
                process, pid = mp.group(1).strip(), mp.group(2)
                break

        # Exception class from the first exception-shaped line (skip the FATAL
        # header and the Process line); the message field keeps the header.
        exception_class = ""
        for m in messages:
            if m.startswith("FATAL EXCEPTION") or m.startswith("Process:"):
                continue
            em = _EXCEPTION_RE.match(m)
            if em:
                exception_class = em.group(1)
                break

        # Stack head → the app crash site: the first frame whose class belongs to
        # the attributed package (so a NullPointerException thrown deep in a
        # framework call still points at the app's own frame), falling back to the
        # first frame overall when attribution is absent or no app frame is present.
        frames = [m for m in messages if m.startswith("at ")]
        chosen = self._select_app_frame(frames, process)
        stack_head, method, source = "", "", ""
        if chosen:
            stack_head = chosen[len("at ") :].strip()
            fm = _FRAME_RE.match(chosen)
            if fm:
                method = fm.group(2)
                source = fm.group(3)

        return RvDiagnosticEvent(
            category=_CATEGORY_CRASH,
            class_full_name=exception_class,
            method=method,
            message=header,
            source=source,
            process=process,
            pid=pid,
            tid=common["tid"],
            fatal=fatal,
            stack_head=stack_head,
            n_frames=len(frames),
            original_msg=common["original_msg"],
            time_occurred=common["time_occurred"],
        )

    def _build_verify_error(self, lines: List[Dict[str, Any]]) -> RvDiagnosticEvent:
        common = self._common_fields(lines)
        message = lines[0]["message"]
        rc = _REJECTING_CLASS_RE.search(message)
        rejected_class = rc.group(1) if rc else ""
        return RvDiagnosticEvent(
            category=_CATEGORY_VERIFY_ERROR,
            class_full_name=rejected_class,
            method="",
            message=message,
            pid=common["pid"],
            tid=common["tid"],
            fatal=False,
            original_msg=common["original_msg"],
            time_occurred=common["time_occurred"],
        )

    def _build_anr(self, lines: List[Dict[str, Any]]) -> RvDiagnosticEvent:
        common = self._common_fields(lines)
        message = lines[0]["message"]
        am = _ANR_IN_RE.search(message)
        if am:
            package = am.group(1)
        else:
            dm = _PROCESS_DIED_RE.search(message)
            package = dm.group(1) if dm else ""
        return RvDiagnosticEvent(
            category=_CATEGORY_ANR,
            class_full_name=package,
            method="",
            message=message,
            process=package,
            pid=common["pid"],
            tid=common["tid"],
            fatal=False,
            original_msg=common["original_msg"],
            time_occurred=common["time_occurred"],
        )
