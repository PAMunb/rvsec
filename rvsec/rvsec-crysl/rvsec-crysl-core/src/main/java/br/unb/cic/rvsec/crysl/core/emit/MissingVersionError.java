package br.unb.cic.rvsec.crysl.core.emit;

/**
 * A model or a report reached serialization without a usable version stamp (INV-CONF-01).
 *
 * <p>The record constructors of the model reject a {@code null} stamp, so this error is not about
 * the null case: it is about the placeholder. A {@code SourceStamp} whose commit is the empty
 * string, or {@code "unknown"}, or {@code "TODO"}, satisfies every type in the model and still
 * fails to say which corpus state the numbers beside it describe, which is the whole point of
 * carrying a stamp. Emission is the last place that can catch it, so it is caught here and it is
 * fatal.
 *
 * <p>It lives in {@code emit} rather than beside the model because nothing outside emission needs
 * to raise it: the invariant it defends is stated about serialization, not about construction.
 */
public class MissingVersionError extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public MissingVersionError(String message) {
        super(message);
    }
}
