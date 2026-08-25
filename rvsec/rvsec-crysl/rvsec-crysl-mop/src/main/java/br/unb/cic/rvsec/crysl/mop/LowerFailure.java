package br.unb.cic.rvsec.crysl.mop;

import java.util.Objects;

/**
 * A model that could not be written back as {@code .mop} text, recorded as a finding about that
 * model rather than as a crash of the run.
 *
 * <p>It is checked for the same reason {@link br.unb.cic.rvsec.crysl.core.LiftFailure} is: a caller
 * lowering one model has to be told it got no text, and a caller lowering a corpus has to catch it
 * and keep going. A run that aborted on the first refusal would measure nothing.
 *
 * <p>Every refusal raised here comes from the JavaMOP AST itself — {@code EventDefinition} re-parses
 * the pointcut string it is handed, and {@code JavaMOPSpec} re-runs its own parameter analysis — so
 * a failure means the model carries something the {@code .mop} AST cannot hold. That is the finding
 * the round-trip gate exists to surface, and it is worth a typed result rather than an
 * {@code IllegalStateException} nobody can count.
 */
public class LowerFailure extends Exception {

    private static final long serialVersionUID = 1L;

    private final transient String specification;

    /**
     * @param specification the specification that did not lower, named by its file
     * @param message       what could not be written, and why
     * @param cause         the exception the JavaMOP AST raised, or {@code null}
     */
    public LowerFailure(String specification, String message, Throwable cause) {
        super(specification + ": " + message, cause);
        this.specification = Objects.requireNonNull(specification,
                "LowerFailure.specification is mandatory");
    }

    /** The specification that did not lower. */
    public String specification() {
        return specification;
    }
}
