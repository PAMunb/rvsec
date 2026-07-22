package br.unb.cic.rv.emitter;

/**
 * Raised when an emitter encounters an AspectJ construct it cannot lower to
 * valid DEX. The weaver treats this as fail-loud: the offending advice is not
 * woven and the error surfaces (no silent always-match, no degraded emission).
 *
 * <p>Current producer: {@link IfGuardEmitter}, when an {@code if(<expr>)}
 * pointcut clause uses an expression outside the two shapes the in-weaver
 * lowering recognises ({@code <bound> == null} and
 * {@code !Thread.holdsLock(<bound>)}). A new expression shape must extend the
 * dispatch in {@code IfGuardEmitter} rather than being silently ignored — an
 * unrecognised guard that defaulted to always-match would weave a monitor
 * invoke the source intended to gate.
 */
public final class UnsupportedAspectConstructError extends RuntimeException {

    public UnsupportedAspectConstructError(String message) {
        super(message);
    }
}
