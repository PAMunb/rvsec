package br.unb.cic.rvsec.crysl.core;

import java.nio.file.Path;
import java.util.List;
import java.util.Objects;

/**
 * A source file that did not lift, recorded as a finding about that file.
 *
 * <p>One type for both languages: a {@code .mop} that the JavaMOP parser refuses and a
 * {@code .crysl} that the CrySL façade refuses are the same event for every stage above the
 * lifters — the corpus has one fewer model and the report has one more entry. The CLI treats it as
 * a <em>result</em> and not as a run failure: a run that produces many of them still exits {@code
 * 0}, with the count in the report. That is the whole distinction against {@link CorpusReadError},
 * which says the run could not be set up at all.
 *
 * <p>It is checked on purpose. A caller lifting one file has to be told it did not get a model; a
 * caller lifting a corpus has to catch it and keep reading, which is what
 * {@code CryslLifter.liftCorpus} does. Two of the 49 upstream rules have never parsed, and a run
 * that aborted on them would measure nothing.
 *
 * <p>The failure carries both halves of the evidence, because neither is sufficient alone: the
 * cause proves which parser refused the file, and the {@link ParseError} list says at which line
 * and why. The list is empty where the parser reports no positioned diagnostic — every JavaMOP
 * failure, and a CrySL failure that was not a parse error at all, an unreadable file say.
 */
public class LiftFailure extends Exception {

    private static final long serialVersionUID = 1L;

    private final transient Path file;
    private final transient List<ParseError> errors;

    /**
     * @param file    the file that did not lift
     * @param message what went wrong, in the words of whoever refused it
     * @param errors  the positioned diagnostics, in the order the parser reported them; empty when
     *                there are none
     * @param cause   the exception the parser raised, or {@code null} when the lifter itself
     *                refused the file without one
     */
    public LiftFailure(Path file, String message, List<ParseError> errors, Throwable cause) {
        super(file + ": " + message + (errors.isEmpty() ? "" : " " + errors), cause);
        this.file = Objects.requireNonNull(file, "LiftFailure.file is mandatory");
        this.errors = List.copyOf(errors);
    }

    /** A failure with a cause and no positioned diagnostics. */
    public LiftFailure(Path file, String message, Throwable cause) {
        this(file, message, List.of(), cause);
    }

    /** A failure the lifter itself raised, with neither cause nor positioned diagnostics. */
    public LiftFailure(Path file, String message) {
        this(file, message, List.of(), null);
    }

    /** The file that did not lift. */
    public Path file() {
        return file;
    }

    /** The diagnostics, in the order the parser reported them. */
    public List<ParseError> errors() {
        return errors;
    }
}
