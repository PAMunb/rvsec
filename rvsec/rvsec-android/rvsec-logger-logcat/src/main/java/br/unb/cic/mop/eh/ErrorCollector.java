package br.unb.cic.mop.eh;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import android.util.Log;

public class ErrorCollector {
    private static ErrorCollector instance;

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

    private Set<ErrorDescription> errors;

    private ErrorCollector() {
        errors = new HashSet<>();
    }

    public static ErrorCollector instance() {
        if (instance == null) {
            instance = new ErrorCollector();
        }
        return instance;
    }

    public void reset() {
        errors = new HashSet<>();
    }

    public void addError(ErrorType type, String spec, String location) {
        addError(new ErrorDescription(type, spec, location));
    }

    public void addError(ErrorType type, String spec, String location, String expecting) {
        addError(new ErrorDescription(type, spec, location, expecting));
    }

    public void addError(ErrorDescription err) {
        if (errors.add(err)) {
            Log.v("RVSEC", buildLine(err));
        }
    }

    /**
     * The single violation line: the six summary fields, a comma, and the escaped expecting text.
     *
     * <p>
     * Kept apart from {@link #addError(ErrorDescription)} because that method's only other statement
     * is a call into {@code android.util.Log}, whose every method throws {@code RuntimeException}
     * in the stub jar this module compiles against — the line text is therefore only testable if it
     * is built somewhere the device is not needed.
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
