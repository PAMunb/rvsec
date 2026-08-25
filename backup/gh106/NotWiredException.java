package br.unb.cic.rvsec.crysl.crysl.cli;

/**
 * A subcommand parsed, its inputs are readable, and the code that would do the work has not been
 * written yet.
 *
 * <p>Deliberately a distinct type rather than an {@code UnsupportedOperationException}: the CLI maps
 * it to {@link ExitCode#NOT_WIRED}, and a blanket catch of {@code UnsupportedOperationException}
 * would map a genuine defect deep in a lifter to the same code and call it "not written yet".
 *
 * <p>Every construction site names the task group that owns the missing piece. This class is
 * expected to have no construction sites left when the change closes; if it still does, that is a
 * fact the reader should be able to find from the exit code alone.
 */
class NotWiredException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    NotWiredException(String message) {
        super(message);
    }
}
