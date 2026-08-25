package br.unb.cic.rvsec.crysl.crysl.cli;

/**
 * What the process exits with, and the rule for deciding which is which.
 *
 * <p>The rule is the point of this enum, not the numbers. A run exits non-zero when the component
 * <em>could not measure</em>: the corpus was unreadable, a model reached emission unstamped, or a
 * calibration target was not reproduced. A run exits {@code 0} when the component measured and
 * published, <strong>however unfavourable the measurement</strong> — a report full of
 * {@code Unknown} items and a corpus in which several files failed to lift is a successful run with
 * findings, and the counts belong in the report where a reader can see them.
 *
 * <p>Collapsing those two is the failure this component exists to remove. If a {@code LiftFailure}
 * exited non-zero, the two known upstream residuals ({@code OAEPParameterSpec} and
 * {@code SSLEngine}) would turn every run red, and the pressure would be to stop reporting them.
 */
public enum ExitCode {

    /** The run measured and emitted. Findings, including {@code Unknown} and {@code LiftFailure}, do not change this. */
    OK(0),

    /** The arguments could not be parsed, or a required one was absent. */
    USAGE(1),

    /**
     * {@code CorpusReadError} — an input directory or file is missing or unreadable. Fatal before
     * any metric runs; nothing partial is emitted.
     */
    CORPUS_READ_ERROR(2),

    /**
     * {@code MissingVersionError} — a model reached emission unstamped (INV-CONF-01). Fatal by
     * construction: an unstamped number cannot be attributed to a corpus state.
     */
    MISSING_VERSION(3),

    /**
     * {@code CalibrationMismatch} — a calibration target the component does not reproduce
     * (INV-CONF-14). The mismatch is a finding to adjudicate with both measurements, never a reason
     * to adjust the component until it agrees.
     *
     * <p>Raised by {@code calibrate} after the whole report has been printed, so the reader sees
     * both halves at once: which target was not reproduced, and which metrics still publish. The
     * mismatch stops the affected metric and nothing else.
     */
    CALIBRATION_MISMATCH(4);

    private final int code;

    ExitCode(int code) {
        this.code = code;
    }

    /** The value handed to {@code System.exit}. */
    public int code() {
        return code;
    }
}
