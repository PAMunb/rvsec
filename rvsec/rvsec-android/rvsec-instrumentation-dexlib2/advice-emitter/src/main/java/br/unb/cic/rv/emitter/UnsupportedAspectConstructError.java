package br.unb.cic.rv.emitter;

/**
 * Raised when an emitter encounters an AspectJ construct it cannot lower to
 * valid DEX. The weaver treats this as fail-loud: the offending advice is not
 * woven and the error surfaces (no silent always-match, no degraded emission).
 *
 * <p>Producers:
 * <ul>
 *   <li>{@link IfGuardEmitter}, when an {@code if(<expr>)} pointcut clause uses
 *       an expression outside the two shapes the in-weaver lowering recognises
 *       ({@code <bound> == null} and {@code !Thread.holdsLock(<bound>)}). A new
 *       expression shape must extend the dispatch in {@code IfGuardEmitter}
 *       rather than being silently ignored — an unrecognised guard that
 *       defaulted to always-match would weave a monitor invoke the source
 *       intended to gate.</li>
 *   <li>{@code DexWeaver.parseCommonPointcut}, when the descriptor's
 *       {@code commonPointcut} is present but unparseable. That expression
 *       carries the class-level exclusions and they appear in no advice's own
 *       expression, so swallowing the parse failure weaves every site they
 *       exist to exclude.</li>
 * </ul>
 */
public final class UnsupportedAspectConstructError extends RuntimeException {

    public UnsupportedAspectConstructError(String message) {
        super(message);
    }

    public UnsupportedAspectConstructError(String message, Throwable cause) {
        super(message, cause);
    }
}
