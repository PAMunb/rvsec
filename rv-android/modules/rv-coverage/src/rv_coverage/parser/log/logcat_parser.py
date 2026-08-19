"""
Parse Android logcat output for runtime verification and coverage data.

Extract RVSEC (property violation) and RVSEC-COV (method coverage) entries
from standard Android logcat format, producing typed domain objects
(RvErrorLog, RvCoverageLog) stored in a LogcatRepository.

### Role in the System:
Entry point for all logcat data in rv-coverage. Both CoverageTracker
(real-time) and CoverageAnalyzer (batch) delegate line-level parsing here.

### Key Features:
- Three error formats: JCA comma-separated, FSM ``:::``, generic spec error
- Two coverage formats: Soot angle-bracket signatures, triple-colon ``:::``
- Year-aware timestamp conversion handling December/January transitions
- Memory-efficient line-by-line file processing

### Integration Points:
- RvErrorLog / RvCoverageLog (rv-android-core): domain model output
- LogcatRepository (rv-android-core): repository populated by parse_logcat_file
- CoverageTracker: calls parse_logcat_line per line in real-time
- CoverageAnalyzer: calls parse_logcat_file for batch processing
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from rv_android_core.domain.coverage import LogcatRepository, ParserDiagnostics
from rv_android_core.domain.log import (
    TAG_RVSEC,
    TAG_RVSEC_COV,
    RvCoverageLog,
    RvErrorLog,
)
from rv_android_core.util.android.repository_initializer import (
    initialize_repository_from_static_data,
)

# A stack frame reliably ends with "(<file>:<line>)"; nothing else about it is
# reliable. The guard therefore tests only that trailing group: no nested
# parenthesis inside it, and it must end in ":<digits>". Both properties matter.
# Real method names in the corpus (Kotlin backtick test names) contain their own
# parenthesis pairs, so the prefix must be left completely unconstrained
# (INV-ANA-52); and requiring a line number is what distinguishes a source
# position from a parenthesis that belongs to the name, so a well-formed value
# can never be truncated by accident (INV-ANA-51).
_FRAME_SUFFIX = re.compile(r"\(([^()]+:\d+)\)$")


def _normalize_frame(value: str) -> Optional[Tuple[str, str, str]]:
    """Recover ``(class, method, source)`` from a whole stack-frame string.

    The Java monitor is supposed to hand the parser a class and a method already
    split apart. When its own split fails — which it does for every method name
    containing ``$``, ``-`` or a space — it falls back to copying the entire
    ``StackTraceElement`` into *both* fields, source position included. That
    position then rides inside the ``(apk, class, method, spec)`` key every
    downstream analysis uses, and one misuse gets counted once per line it
    occurs at (issue #89).

    Normalizing here rather than only upstream is not redundant: an APK is
    instrumented once and replayed across many runs, so every APK already
    instrumented with an uncorrected monitor jar keeps emitting the broken form
    no matter what the Java does afterwards.

    The algorithm deliberately does not try to describe what a method name looks
    like — that is the assumption that failed. It strips the trailing
    ``(<file>:<line>)`` group and splits the remainder at its **last** dot,
    because the class part is a dotted path and a method name never contains a
    dot. Nothing about the method name needs to be predicted.

    Args:
        value: Any string, including one already well-formed or empty.

    Returns:
        ``(class, method, source)`` when ``value`` is in frame form, else
        ``None`` — the signal to leave the caller's fields untouched.
    """
    match = _FRAME_SUFFIX.search(value)
    if not match:
        return None

    remainder = value[: match.start()]
    last_dot = remainder.rfind(".")
    if last_dot == -1:
        # A frame this shape cannot come from a real StackTraceElement (there is
        # always at least a package-or-class dot before the method). Mangling it
        # on a guess would be worse than leaving it, so keep the value and say so.
        logging.getLogger(__name__).warning(
            "Frame-form value has no class/method separator, "
            f"left unnormalized: {value}"
        )
        return None

    return remainder[:last_dot], remainder[last_dot + 1 :], match.group(1)


def _stamp_time(time_occurred: datetime, tool_execution_start: datetime) -> int:
    """Seconds elapsed from tool execution start to ``time_occurred`` (INV-ANA-49).

    Same arithmetic as the live ``CoverageTracker._process_line``: truncate to
    whole seconds and clamp to zero — logcat lines buffered from before tool
    start (e.g., a previous run) would otherwise yield negative offsets.
    """
    return max(0, int((time_occurred - tool_execution_start).total_seconds()))


def parse_logcat_file(
    log_file: str,
    static_data=None,
    tool_execution_start: Optional[datetime] = None,
) -> LogcatRepository:
    """
    Parse a logcat file and return a populated LogcatRepository.

    Read the file line-by-line for memory efficiency, extracting all RVSEC
    error entries and RVSEC-COV coverage entries. Optionally initialize the
    repository with static analysis data to enable reachability-based metrics.

    When ``tool_execution_start`` is given, every parsed error, coverage entry,
    and diagnostic event is stamped with ``time_since_task_start`` (seconds
    since that epoch, INV-ANA-49) before registration — reconstructed
    repositories are then temporally equivalent to ones populated live by
    ``CoverageTracker``. Without it, all stamps keep the default ``0`` and one
    warning flags the degraded timing (callers that only need MOP violations
    omit it deliberately).

    Args:
        log_file: Absolute path to the logcat file.
        static_data: Optional StaticAnalysisData to pre-populate the repository
            with reachable classes and methods.
        tool_execution_start: Optional tool execution start epoch (e.g.,
            ``TaskResult.tool_execution_start`` restored from tasks.json).

    Returns:
        LogcatRepository containing all parsed errors and method calls.
    """
    # Initialize the repository
    repository = LogcatRepository()
    logger = logging.getLogger(__name__)

    # The repository owns the counters and the parser increments them, so a caller
    # that holds the repository holds the account of the whole file (INV-ANA-62).
    diagnostics = repository.parser_diagnostics

    # Initialize repository with static data if provided
    if static_data and hasattr(static_data, "classes"):
        logger.debug("Initializing repository with static analysis data")
        initialize_repository_from_static_data(repository, static_data, "LogcatParser")

    # Local import breaks the module-load cycle: diagnostic_parser imports the
    # threadtime helpers from this module.
    from rv_coverage.parser.log.diagnostic_parser import DiagnosticEventParser

    diagnostic_parser = DiagnosticEventParser()

    # Process log file line by line for memory efficiency. Each line drives the
    # RVSEC/COV parse (unchanged hot path) and, independently, the stateful
    # diagnostic parser; diagnostic events land in the isolated collection so
    # reconstruction-on-resume repopulates them too (gh58 path).
    #
    # Timing MUST be stamped before registration: register_method_call collapses
    # repeated calls into MethodCoverageData keyed by first call, so the
    # first-call time is unrecoverable afterwards (design gh83, Decision 1).
    entries_parsed = False
    line_number = 0
    try:
        with open(log_file, "r") as f:
            for line_number, line in enumerate(f, start=1):
                error_log, coverage_log = parse_logcat_line(line, diagnostics)

                if error_log:
                    if tool_execution_start and error_log.time_occurred:
                        error_log.time_since_task_start = _stamp_time(
                            error_log.time_occurred, tool_execution_start
                        )
                    entries_parsed = True
                    repository.register_rv_error(error_log)
                elif coverage_log:
                    if tool_execution_start and coverage_log.time_occurred:
                        coverage_log.time_since_task_start = _stamp_time(
                            coverage_log.time_occurred, tool_execution_start
                        )
                    entries_parsed = True
                    repository.register_method_call(coverage_log)

                event = diagnostic_parser.feed_line(line)
                if event:
                    if tool_execution_start and event.time_occurred:
                        event.time_since_task_start = _stamp_time(
                            event.time_occurred, tool_execution_start
                        )
                    entries_parsed = True
                    repository.register_diagnostic_event(event)

        # Emit any event still buffered at end of file.
        tail = diagnostic_parser.flush()
        if tail:
            if tool_execution_start and tail.time_occurred:
                tail.time_since_task_start = _stamp_time(
                    tail.time_occurred, tool_execution_start
                )
            entries_parsed = True
            repository.register_diagnostic_event(tail)
    except Exception as e:
        # Re-raised, never swallowed. Returning the repository built so far would hand
        # the caller a partial file it has no way to recognise as partial: every count
        # it reads — total_errors, unique_errors, coverage — would be computed over the
        # prefix that happened to parse, and would look exactly like a complete result.
        # The line number is logged because it is the only thing that locates the input
        # that broke, and it is lost the moment the exception leaves this frame.
        logger.error(
            f"Error parsing logcat file {log_file} at line {line_number}: {e}",
            exc_info=True,
        )
        raise

    if tool_execution_start is None and entries_parsed:
        logger.warning(
            f"No tool execution start epoch supplied for {log_file} — "
            "reconstructed timing is unavailable, time_since_task_start values remain 0"
        )

    return repository


def parse_logcat_line(
    line: str,
    diagnostics: Optional[ParserDiagnostics] = None,
) -> Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]:
    """
    Parse a single logcat line for RVSEC or RVSEC-COV entries.

    Every line that does not become a record increments exactly one counter of
    ``diagnostics`` (INV-ANA-62), so that the account of a file is arithmetic:
    records registered plus counted lines equals lines read. The only lines that do
    neither are the diagnostic-tag lines, which ``DiagnosticEventParser`` assembles
    into multi-line events on its own pass over the same input.

    Args:
        line: Raw logcat line in standard Android format.
        diagnostics: The counter object to increment. Callers that hold a repository
            pass ``repository.parser_diagnostics`` — the live ``CoverageTracker`` and
            the offline ``parse_logcat_file`` both do, which is what makes the two
            paths count onto the same totals. ``None`` means "count nowhere": the
            parse is unchanged, the counts simply go to a throwaway object.

    Returns:
        Tuple of ``(error_log, coverage_log)``. At most one element is
        non-None. Both are None for non-RVSEC lines or unparseable input.
    """
    if diagnostics is None:
        diagnostics = ParserDiagnostics()

    entry = _parse_logcat_line(line)
    if not entry:
        diagnostics.lines_not_threadtime += 1
        return None, None

    tag = entry["tag"]
    message = entry["message"]

    # Parse based on the tag
    if tag == TAG_RVSEC:
        error = _parse_error_message(message, diagnostics, (entry["pid"], entry["tid"]))
        if error:
            error.original_msg = entry["original"]
            error.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
            return error, None
        return None, None
    if tag == TAG_RVSEC_COV:
        coverage = _parse_coverage_message(message)
        if coverage:
            coverage.original_msg = entry["original"]
            coverage.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
            return None, coverage
        diagnostics.unrecognised += 1
        return None, None

    if tag not in _diagnostic_base_tags():
        diagnostics.lines_other_tag += 1

    return None, None


_DIAGNOSTIC_TAGS: Optional[frozenset] = None


def _diagnostic_base_tags() -> frozenset:
    """The tags whose lines belong to ``DiagnosticEventParser``, cached.

    Those lines are neither records here nor discards: they are the raw material of
    the multi-line diagnostic events the other parser assembles from the same file,
    so counting them as dropped would misstate the account. The import is deferred
    and cached because ``diagnostic_parser`` imports this module at load time; the
    same reason ``parse_logcat_file`` defers its own import of that module.
    """
    global _DIAGNOSTIC_TAGS
    if _DIAGNOSTIC_TAGS is None:
        from rv_coverage.parser.log.diagnostic_parser import _DIAGNOSTIC_BASE_TAGS

        _DIAGNOSTIC_TAGS = _DIAGNOSTIC_BASE_TAGS
    return _DIAGNOSTIC_TAGS


def _parse_logcat_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a raw logcat line into its component fields.

    Shared with ``DiagnosticEventParser``, which reuses this split so both
    parsers agree on what counts as a well-formed logcat line.

    Args:
        line: Raw logcat line, trailing newline included.

    Returns:
        Dict with date, time, pid, tid, level, tag, message, original;
        or None if the line does not match standard logcat format.
    """
    # Standard Android logcat "threadtime" format:
    #   MM-DD HH:MM:SS.mmm  PID  TID  LEVEL  TAG: message
    # Note: logcat omits the year -- _convert_to_datetime infers it.
    pattern = r"(\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s*(.*)"
    match = re.match(pattern, line)
    if not match:
        return None

    date, time, pid, tid, level, tag, message = match.groups()
    return {
        "date": date,
        "time": time,
        "pid": pid,
        "tid": tid,
        "level": level,
        "tag": tag,
        "message": message,
        "original": line.strip(),
    }


# Sentinels. A value the producer did not supply is named, never invented: an
# invented value ("Unknown Source:1", "No additional message") reads as a
# measurement in every file it reaches, and there is no way back from it.
_SENTINEL_UNSPECIFIED = "UNSPECIFIED"
_SENTINEL_SOURCE = "UNSPECIFIED:0"

# One `key=` of the v1 envelope. Quoted values are scanned by hand rather than by
# a regex because the escape (`\'`) has to be undone as the value is read, and a
# value whose closing quote never arrives is the evidence of truncation, not a
# non-match.
_ENVELOPE_KEY = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=")
_ENVELOPE_PREFIX = "v=1"

# The separator of `unique_msg`. The envelope grammar forbids it inside a value;
# the parser detects and counts a producer that emits it anyway, and keeps the
# value verbatim — repairing it here would hide the defect from the only place
# that can see it.
_FORBIDDEN_IN_VALUE = ":::"

# Format 1 and Format 3 end in the same words and differ in their punctuation: the
# generic emitter writes " ::: " with spaces, the FSM emitter writes ":::" without.
_ERROR_STATE_SUFFIX = "went into an error state."
_FORMAT1_SEPARATOR = " ::: "


def _parse_envelope(message: str) -> Optional[Tuple[Dict[str, str], bool]]:
    """Decompose a v1 message envelope into its keys.

    The grammar is
    ``v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>'
    exp='<expected>' msg='<text>'``: bare values carry no space, quoted values are
    delimited by ``'`` with ``\'`` as the escape and ``\n`` for a newline the
    collector escaped so that logcat would not split the line in two.

    Args:
        message: The seventh comma field of a Format-2 line.

    Returns:
        ``(fields, truncated)``, or ``None`` when the text is not an envelope at
        all (a legacy ``unknown``, a free-text ``expecting …``, a cmp162 message).
        ``truncated`` is True when a quoted value's closing quote never arrived —
        logcat cuts a payload at 4068 bytes without a marker, so an unclosed quote
        is the only evidence the parser has that it is holding half a record. The
        fields parsed before the cut are kept; nothing from the cut value onwards
        is, because a value read up to an arbitrary byte is not the value.
    """
    if not message.startswith(_ENVELOPE_PREFIX):
        return None

    fields: Dict[str, str] = {}
    truncated = False
    pos, size = 0, len(message)

    while pos < size:
        match = _ENVELOPE_KEY.match(message, pos)
        if not match:
            # Whitespace between fields, or text the producer wrote outside the
            # grammar. Skipping it keeps a malformed envelope readable up to the
            # keys it did get right, which is more use than discarding the record.
            pos += 1
            continue

        key = match.group(1)
        pos = match.end()

        if pos < size and message[pos] == "'":
            pos += 1
            value, pos, closed = _read_quoted(message, pos)
            if not closed:
                truncated = True
                break
            fields[key] = value
        else:
            end = message.find(" ", pos)
            end = size if end == -1 else end
            fields[key] = message[pos:end]
            pos = end

    return fields, truncated


def _read_quoted(message: str, pos: int) -> Tuple[str, int, bool]:
    """Read one single-quoted envelope value, undoing its escapes.

    Returns ``(value, position_after_the_closing_quote, closed)``.
    """
    chars = []
    size = len(message)
    while pos < size:
        char = message[pos]
        if char == "\\" and pos + 1 < size:
            following = message[pos + 1]
            if following == "'":
                chars.append("'")
            elif following == "n":
                chars.append("\n")
            elif following == "\\":
                chars.append("\\")
            else:
                chars.append(char)
                pos += 1
                continue
            pos += 2
            continue
        if char == "'":
            return "".join(chars), pos + 1, True
        chars.append(char)
        pos += 1
    return "".join(chars), pos, False


def _apply_envelope(
    error: RvErrorLog, message: str, diagnostics: ParserDiagnostics
) -> None:
    """Fill the envelope fields of a record, or its sentinels, and count both.

    A message that is not an envelope leaves ``code`` and ``event`` at the sentinel
    ``UNSPECIFIED`` — never at ``""`` — so that a reader can tell a record whose
    producer named no event from one whose event was named and empty. The same
    counters catch an envelope whose ``code=`` or ``ev=`` is *itself* the literal
    sentinel (the collector's ``null`` guard writes exactly that): the value is a
    sentinel whoever wrote it.
    """
    parsed = _parse_envelope(message)
    if parsed is not None:
        fields, truncated = parsed
        error.code = fields.get("code") or _SENTINEL_UNSPECIFIED
        error.event = fields.get("ev") or _SENTINEL_UNSPECIFIED
        error.obj = fields.get("obj", "")
        error.val = fields.get("val", "")
        error.exp = fields.get("exp", "")
        error.msg = fields.get("msg", "")
        error.truncated = truncated
        if truncated:
            diagnostics.truncated_envelopes += 1
        if any(_FORBIDDEN_IN_VALUE in value for value in fields.values()):
            # One per record, not one per offending value: the record is the unit
            # everything else here counts in, and a record is either readable as
            # seven `:::` parts downstream or it is not.
            diagnostics.envelope_forbidden_chars += 1

    if error.code == _SENTINEL_UNSPECIFIED:
        diagnostics.sentinel_code += 1
    if error.event == _SENTINEL_UNSPECIFIED:
        diagnostics.sentinel_event += 1


def _parse_error_message(
    message: str,
    diagnostics: Optional[ParserDiagnostics] = None,
    thread_key: Optional[Tuple[str, str]] = None,
) -> Optional[RvErrorLog]:
    """
    Parse an RVSEC error message into an RvErrorLog.

    Try three formats, each recognised by structure: Format 1, the generic spec
    error, by the suffix ``went into an error state.``; Format 2, the JCA line the
    logcat ``ErrorCollector`` writes, by its comma count; Format 3, the FSM line,
    by ``:::``. A message that matches none is counted and returns None.

    Args:
        message: The message portion of an RVSEC-tagged logcat line.
        diagnostics: Counters to increment (INV-ANA-62).
        thread_key: ``(pid, tid)`` of the line, used only to recognise the second
            half of a payload logcat split on a newline.

    Returns:
        Parsed RvErrorLog, or None if the message format is unrecognized.
    """
    if diagnostics is None:
        diagnostics = ParserDiagnostics()

    # The line after a truncated record from the same thread is that record's
    # second half, not a record of its own. The state is one-shot — it is cleared
    # here whether or not this line is the continuation — so a truncation can
    # swallow at most one following line, and that line is counted rather than
    # dropped. Reading it as a fresh record is the failure this guards: a second
    # half that happens to carry six commas parses into a JCA record whose every
    # field is a fragment of a value.
    if thread_key is not None and diagnostics.last_truncated_key == thread_key:
        diagnostics.last_truncated_key = None
        diagnostics.continuation_lines += 1
        logging.getLogger(__name__).warning(
            f"Continuation of a truncated RVSEC record, counted not parsed: {message}"
        )
        return None

    # Format 1: Generic spec error -- "class.method(file:line) ::: Spec went into an error state."
    #
    # The suffix alone does not select it: an FSM line (Format 3) ends in the same
    # words. What separates them is the punctuation — the generic emitter writes the
    # separator with spaces around it, the FSM emitter writes it without — so both
    # are required here, and an unspaced `:::` line falls through to Format 3 below
    # where it belongs.
    if message.endswith(_ERROR_STATE_SUFFIX) and _FORMAT1_SEPARATOR in message:
        generic = _parse_generic_spec_error(message)
        if generic:
            error = RvErrorLog(
                generic["spec"],
                generic["spec"],
                generic["class"],
                generic["method"],
                generic["file_name"],
                generic["message"],
            )
            _apply_envelope(error, generic["message"], diagnostics)
            return error

        # The regex disagreed with the punctuation, so the line is dropped here
        # rather than retried below. Falling through was the old behaviour and it
        # scrambled: a generic class or method name bearing five commas —
        # `com.example.Svc.call(a,b,c,d,e,f) ::: HasNext went into an error state.` —
        # satisfies the comma count and comes out as a JCA record whose `spec` is
        # `com.example.Svc.call(a`.
        #
        # A left part with no dot at all cannot be a `class.method` under any format
        # and is counted as the unresolvable `:::` line it is — that is the shape of
        # the `[helper] ::: ` lines of `generic_new`, a written non-goal of gh104.
        if "." in message.split(_FORMAT1_SEPARATOR, 1)[0]:
            diagnostics.format1_regex_failed += 1
        else:
            diagnostics.format3_unresolved += 1
        logging.getLogger(__name__).warning(
            f"Format-1 message did not match its regex, dropped: {message}"
        )
        return None

    # Format 2: JCA comma-separated -- "spec,class,className,method,source,error_type[,expecting]"
    # The logcat ErrorCollector writes ErrorSummary.toString() then "," then the
    # expecting text, so fields beyond index 6 are the expecting text's own commas
    # rejoined: 27 % of the recorded messages carry one and every one of them is legal.
    parts = message.split(",")

    if len(parts) >= 6:
        clazz, method, source = parts[1], parts[3], parts[4]

        # Format 2 is the only format whose class and method arrive pre-split by
        # the Java ErrorSummary, so it is the only one that can inherit that
        # split's failure mode (a whole stack frame in both fields). Formats 1
        # and 3 below split structurally and are left alone. When the fallback
        # fired upstream both fields hold the same frame, so recovering from
        # either yields the same triple; the method field is tried first because
        # that is the one the upstream regex is documented to reject.
        recovered = _normalize_frame(method) or _normalize_frame(clazz)
        if recovered:
            clazz, method, source = recovered
            logging.getLogger(__name__).debug(
                f"Normalized frame-form violation record {parts[3]!r} to "
                f"class={clazz!r} method={method!r} source={source!r}"
            )

        error_type = parts[5]
        if not error_type.strip():
            error_type = _SENTINEL_UNSPECIFIED
            diagnostics.sentinel_error_type += 1
        if not source.strip():
            source = _SENTINEL_SOURCE
            diagnostics.sentinel_source += 1

        # An absent seventh field is an empty message, not the words "No additional
        # message": that string was written into 6-field records for years and reads
        # downstream as something the monitor said.
        message_text = ",".join(parts[6:]) if len(parts) > 6 else ""

        error = RvErrorLog(parts[0], error_type, clazz, method, source, message_text)
        _apply_envelope(error, message_text, diagnostics)
        if error.truncated and thread_key is not None:
            diagnostics.last_truncated_key = thread_key
        return error

    # Format 3: FSM triple-colon -- "class.method(params):::Spec message"
    # Older RV-Monitor FSM output. Extract class and method by finding the last
    # dot before the opening parenthesis (handles inner classes with dots).
    if _FORBIDDEN_IN_VALUE in message:
        split = message.split(_FORBIDDEN_IN_VALUE)
        if len(split) >= 2:
            tmp = split[0]
            tmp = tmp[: tmp.find("(") if "(" in tmp else len(tmp)]
            dot_idx = tmp.rfind(".")
            if dot_idx != -1:
                clazz = tmp[:dot_idx]
                method = tmp[dot_idx + 1 :]
                message_text = split[1].strip()
                spec = message_text.split(" ")[0]
                # The FSM line carries no source position at all. `Unknown Source:1`
                # used to be written here and is a fabricated line number: it reads
                # as a measurement, and one that agrees with itself across every
                # unrelated record.
                diagnostics.sentinel_source += 1
                error = RvErrorLog(
                    spec, spec, clazz, method, _SENTINEL_SOURCE, message_text
                )
                _apply_envelope(error, message_text, diagnostics)
                return error

        # A `:::` line whose left part has no dot resolves to no class and no
        # method — the `[helper] ::: ` lines of `generic_new`, a written non-goal of
        # this change. Counted, so that the set's traffic is visible rather than
        # simply absent.
        diagnostics.format3_unresolved += 1
        logging.getLogger(__name__).warning(
            f"Unresolvable ':::' message, counted not parsed: {message}"
        )
        return None

    # Between one and four commas, no `:::`, no Format-1 suffix: the shape logcat
    # leaves when it cuts a payload before its sixth comma.
    logging.getLogger(__name__).warning(f"Failed to parse error message: {message}")
    if 1 <= len(parts) - 1 <= 4:
        diagnostics.format2_short += 1
    else:
        diagnostics.unrecognised += 1
    return None


def _parse_generic_spec_error(log_line: str) -> Optional[Dict[str, Any]]:
    """Parse ``class.method(file:line) ::: Spec went into an error state.`` format.

    Args:
        log_line: Message portion of an RVSEC line already known to end with
            ``went into an error state.``.

    Returns:
        Dict with class, method, file_name, line_number, spec, message;
        or None if the pattern does not match.
    """
    pattern = r"(.*)\.(.*)\((.*):(.*)\) ::: (.*) went into an error state."
    match = re.match(pattern, log_line)

    if match:
        class_name, method_name, file_name, line_number, spec = match.groups()
        return {
            "class": class_name,
            "method": method_name,
            "file_name": file_name,
            "line_number": int(line_number) if line_number.isdigit() else 0,
            "spec": spec,
            "message": f"{spec} went into an error state.",
        }
    return None


def _parse_coverage_message(message: str) -> Optional[RvCoverageLog]:
    """
    Parse an RVSEC-COV message into an RvCoverageLog.

    Try the Soot angle-bracket format first (``<class: retType method(params)>``),
    then the triple-colon format. Log a warning and return None if neither matches.

    Args:
        message: The message portion of an RVSEC-COV-tagged logcat line.

    Returns:
        Parsed RvCoverageLog, or None if the message format is unrecognized.
    """
    # Soot-signature format: "<class: returnType method(params)>"
    # This is what the current RVSEC instrumentation emits via RVSEC-COV tag.
    match = re.match(r"<([^:]+):\s+([^ ]+)\s+([^:(]+)\(([^)]*)\)>", message)
    if match:
        class_name, return_type, method_name, parameters = match.groups()
        return RvCoverageLog(class_name, method_name, parameters, message)

    # Triple-colon format: "class:::method:::params"
    # An APK is instrumented once and replayed across many runs, so APKs carrying
    # an older Coverage aspect keep emitting this layout and must still parse.
    parts = message.split(":::")
    if len(parts) >= 2:
        class_name = parts[0].strip()
        method_name = parts[1].strip()
        params = parts[2].strip() if len(parts) > 2 else ""
        return RvCoverageLog(class_name, method_name, params, message)

    # Fallback for malformed messages - log warning instead of creating malformed data
    logging.getLogger(__name__).warning(f"Failed to parse coverage message: {message}")
    return None


def _convert_to_datetime(date: str, time: str) -> datetime:
    """
    Convert logcat date and time strings to a datetime object.

    Logcat timestamps lack a year. Infer the year from the current date,
    attributing December entries to the previous year when the current
    month is January (year-transition handling).

    Args:
        date: Date string in ``MM-DD`` format.
        time: Time string in ``HH:MM:SS.mmm`` format.

    Returns:
        Datetime with the inferred year.
    """
    current_year = datetime.now().year

    # Android logcat timestamps lack a year. We infer it from the current date.
    # Edge case: if we're in January and the log entry is from December, it must
    # be from the previous year (experiment started before midnight on Dec 31).
    # This only handles a one-month overlap, which is sufficient because
    # experiments never span more than a few hours.
    current_month = datetime.now().month
    log_month = int(date.split("-")[0])

    year = current_year - 1 if current_month == 1 and log_month == 12 else current_year

    date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_str = f"{year}-{date} {time}"
    return datetime.strptime(date_str, date_format)
