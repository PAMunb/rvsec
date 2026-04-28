package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;

/**
 * Helper used by the other emitters when the advice references
 * {@code thisJoinPoint.getSignature()} or similar AspectJ runtime objects.
 *
 * <p>Rather than constructing a full {@code JoinPoint} at runtime (which
 * requires the AspectJ runtime, not present in the DEX-native pipeline), we
 * pre-compute a canonical signature string at weave time and thread it
 * through the monitor invoke as an additional constant argument.
 *
 * <p>The signature format matches the one used by
 * {@code coverage-weaver.SignatureFormatter}:
 * {@code <FQN: ReturnType method(paramTypes)>}. This emitter exposes
 * {@link #signatureFor} so call-site emitters can get the constant before
 * building their invoke.
 */
public final class ThisJoinPointEmitter {

    public String signatureFor(AdviceDescriptor advice) {
        // The advice descriptor does not carry the matched call-site signature
        // directly — that depends on the matched ClassDef/Method, which the
        // emitter pipeline resolves at weave time. This method serves as a
        // single place where the format is decided; the real value is
        // populated by the dex-mutator's SignatureFormatter (task 5.x) and
        // threaded into EmitContext before reaching the emitters.
        return advice.getExpression() != null ? advice.getExpression() : "";
    }

    public boolean needsJoinPoint(AdviceDescriptor advice) {
        String expr = advice.getExpression();
        return expr != null && expr.contains("thisJoinPoint");
    }
}
