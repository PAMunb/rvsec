package br.unb.cic.rvsec.crysl.core;

import java.util.Objects;

/**
 * One diagnostic a parser reported for a source file, as {@code line} plus the message the grammar
 * wrote, verbatim. It is the detail a {@link LiftFailure} carries beside its cause.
 *
 * <p>It exists because the CrySL façade throws the detail away. {@code CrySLModelReader.readRule}
 * answers a rule that does not load with a single {@code CrySLParserException} whose message is
 * {@code "Skipping rule since it contains errors: <uri>"} — enough to know that something is wrong,
 * never enough to say what. The two upstream residuals are only diagnosable through
 * {@code resource.getErrors()}: {@code OAEPParameterSpec.crysl:8: mismatched input 'alg' expecting
 * RULE_ID} and {@code SSLEngine.crysl:12: Couldn't resolve reference to Event 'cp1'.} A finding
 * recorded against a corpus has to name the line and the reason, or the next reader cannot check
 * it.
 *
 * <p>The type lives in the model module because {@link LiftFailure} does: it is a line and a
 * message, and nothing about it is specific to either grammar. The JavaMOP route reports no
 * positioned diagnostics at all, so its failures carry an empty list rather than a fabricated one.
 *
 * @param line    1-based line the diagnostic points at, or 0 when the diagnostic has no position
 * @param message the message as the grammar wrote it, verbatim
 */
public record ParseError(int line, String message) {

    public ParseError {
        Objects.requireNonNull(message, "ParseError.message is mandatory");
        if (line < 0) {
            throw new IllegalArgumentException("ParseError.line cannot be negative, got " + line);
        }
    }

    @Override
    public String toString() {
        return ":" + line + ": " + message;
    }
}
