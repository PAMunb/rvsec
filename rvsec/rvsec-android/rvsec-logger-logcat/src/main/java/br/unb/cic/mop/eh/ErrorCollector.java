package br.unb.cic.mop.eh;

import java.util.Collections;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import android.util.Log;

/**
 * Receives every violation report of the instrumented app and turns it into logcat lines on two
 * streams.
 *
 * <p>
 * {@code RVSEC} carries <em>what</em> was violated: one line per identity per process, written on
 * the identity's first report, with the full message envelope. {@code RVSEC-OCC} carries
 * <em>when</em> and <em>how often</em>: every report is counted, and a line with the identity's key
 * and the count so far is written on the first report and afterwards at most once per identity per
 * {@link #OCC_INTERVAL_NANOS}. The occurrence line repeats the first six fields of the
 * {@code RVSEC} line byte for byte, so a reader recovers the message by joining on the key instead
 * of reading it again on every occurrence.
 *
 * <p>
 * The monitors call the collector from whatever thread runs the monitored code — the UI thread,
 * worker pools, coroutine dispatchers — so the instance is created when the class is initialised
 * and both per-identity structures are concurrent. A lazily created instance could be created twice,
 * each copy with its own counters and its own first-occurrence set, and a plain {@code HashSet} can
 * let two threads both pass {@code add} for one identity and write two {@code RVSEC} lines for one
 * violation.
 */
public class ErrorCollector {

    static final String RVSEC_TAG = "RVSEC";

    static final String OCC_TAG = "RVSEC-OCC";

    /**
     * The shortest gap, on {@link System#nanoTime()}, between two {@code RVSEC-OCC} lines of one
     * identity.
     *
     * <p>
     * A hot violated method can report thousands of times a second, and every line competes with
     * the coverage and heartbeat streams for the same {@code logd} buffer. The window bounds one
     * identity's share of that buffer at ten lines a second while the counter keeps counting what
     * the window drops, so the gap between two consecutive {@code n} values still says how many
     * occurrences fell between them.
     */
    static final long OCC_INTERVAL_NANOS = 100_000_000L;

    private static final ErrorCollector INSTANCE = new ErrorCollector();

    /**
     * What a report carries when the specification supplied no expecting value.
     *
     * <p>
     * A {@code null} expecting used to reach the line as the four characters {@code null} (or, once
     * {@code trim()} was called on it, as a {@code NullPointerException} that lost the report
     * altogether). Both are worse than saying nothing: the reader cannot tell a specification that
     * named no expectation from one whose expectation happened to be the word. The sentinel envelope
     * is the v1 grammar with every value empty and the two identity keys set to {@code UNSPECIFIED},
     * so the parser reads a well-formed record whose absence of attribution is explicit.
     */
    static final String SENTINEL_ENVELOPE =
            "v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''";

    /** The identities that already have their {@code RVSEC} line in this process. */
    private final Set<ErrorDescription> errors = ConcurrentHashMap.newKeySet();

    /**
     * The occurrence state of each identity, keyed by the summary rather than the report so the
     * map holds no reference to the {@code expecting} text. It grows with distinct identities only.
     */
    private final ConcurrentHashMap<ErrorSummary, Occurrence> occurrences = new ConcurrentHashMap<>();

    /**
     * One identity's count of reports and the time of its last {@code RVSEC-OCC} line.
     *
     * <p>
     * {@code lastLineNanos} starts at the creation time because the first report always writes its
     * line, so the window that follows it opens at that moment.
     */
    private static final class Occurrence {
        final AtomicLong count = new AtomicLong();
        final AtomicLong lastLineNanos;

        Occurrence(long createdNanos) {
            lastLineNanos = new AtomicLong(createdNanos);
        }
    }

    private ErrorCollector() {
    }

    public static ErrorCollector instance() {
        return INSTANCE;
    }

    /**
     * Forgets every identity, so the next report of any of them writes its {@code RVSEC} line again
     * and its {@code RVSEC-OCC} count restarts at 1. Both structures are cleared in place: they are
     * {@code final} and shared across threads, and swapping in new ones would publish them without
     * a happens-before edge to a concurrent reader.
     */
    public void reset() {
        errors.clear();
        occurrences.clear();
    }

    public void addError(ErrorType type, String spec, String location) {
        addError(new ErrorDescription(type, spec, location));
    }

    public void addError(ErrorType type, String spec, String location, String expecting) {
        addError(new ErrorDescription(type, spec, location, expecting));
    }

    /**
     * Writes the {@code RVSEC} line if this is the identity's first report, then counts the report
     * and writes the {@code RVSEC-OCC} line if the window allows it.
     *
     * <p>
     * The {@code RVSEC} decision comes first so that on a first report the full record precedes the
     * occurrence line with {@code n=1}, and a reader scanning forward meets the message before its
     * first count. The occurrence call is unconditional: its counter has to see every report,
     * including the ones that write nothing.
     */
    public void addError(ErrorDescription err) {
        if (errors.add(err)) {
            Log.v(RVSEC_TAG, buildLine(err));
        }
        String occ = occurrenceLine(err, System.nanoTime());
        if (occ != null) {
            Log.v(OCC_TAG, occ);
        }
    }

    /**
     * Counts one report of the identity and returns its {@code RVSEC-OCC} line, or {@code null}
     * when the line falls inside the identity's window.
     *
     * <p>
     * The line is {@code summary,code,event,n}: the six fields the {@code RVSEC} line starts with,
     * then the two envelope identity keys, so two causes at one call site stay two keys, then the
     * count so far. The envelope itself is not repeated, because it is already on the identity's
     * {@code RVSEC} line.
     *
     * <p>
     * Outside the first report, a line is written only by the call that wins the compare-and-set on
     * {@code lastLineNanos}, so two threads cannot both write a line for one identity in one window.
     * Reports after an identity's last line are counted here and never written: the last {@code n}
     * an identity shows in the log is a lower bound on its occurrences, not their total.
     *
     * <p>
     * {@code nowNanos} is a parameter, and the method does not touch {@code android.util.Log}, so
     * the throttle is testable against the stub jar with a clock the test controls.
     */
    String occurrenceLine(ErrorDescription err, long nowNanos) {
        ErrorSummary summary = err.getErrorSummary();
        Occurrence occ = occurrences.computeIfAbsent(summary, k -> new Occurrence(nowNanos));
        long n = occ.count.incrementAndGet();
        if (n != 1) {
            long last = occ.lastLineNanos.get();
            if (nowNanos - last < OCC_INTERVAL_NANOS || !occ.lastLineNanos.compareAndSet(last, nowNanos)) {
                return null;
            }
        }
        return summary.toString() + "," + summary.getCode() + "," + summary.getEvent() + "," + n;
    }

    /**
     * The single violation line: the six summary fields, a comma, and the escaped expecting text.
     *
     * <p>
     * Kept apart from {@link #addError(ErrorDescription)} because that method calls
     * {@code android.util.Log}, whose every method throws {@code RuntimeException} in the stub jar
     * this module compiles against — the line text is therefore only testable if it is built
     * somewhere the device is not needed.
     */
    String buildLine(ErrorDescription err) {
        String expecting = err.getExpecting();
        if (expecting == null) {
            return err.getErrorSummary() + "," + SENTINEL_ENVELOPE;
        }
        return err.getErrorSummary() + "," + escape(expecting.trim());
    }

    /**
     * Escapes only what logcat itself would destroy: a newline ends the line, so the record would
     * arrive as two, the second of which has no structure at all and is read as a fabricated one.
     *
     * <p>
     * Commas are deliberately left alone. The line is positional with a seventh field that swallows
     * every remaining comma, and 27 % of the recorded messages carry one — quoting them, as the
     * dead CSV-style escaper did, would only hide them from a reader that splits on the first six.
     */
    String escape(String data) {
        return data.replaceAll("\\R", "\\\\n");
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }
}
