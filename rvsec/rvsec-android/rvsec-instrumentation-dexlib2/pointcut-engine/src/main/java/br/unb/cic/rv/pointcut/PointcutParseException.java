package br.unb.cic.rv.pointcut;

/**
 * Raised by {@link PointcutExpressionParser} when the expression cannot be
 * tokenized or parsed.
 *
 * <p>The message always includes the source snippet and the offset where parsing
 * stopped, so callers can cite the exact position in their diagnostics.
 */
public final class PointcutParseException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public PointcutParseException(String message) {
        super(message);
    }

    public PointcutParseException(String message, Throwable cause) {
        super(message, cause);
    }
}
