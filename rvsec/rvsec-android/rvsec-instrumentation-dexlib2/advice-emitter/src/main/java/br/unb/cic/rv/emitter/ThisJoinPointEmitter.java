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
        // Intentional pass-through (decision Q5): return the advice's raw
        // pointcut expression unchanged (empty string when absent). The matched
        // call-site signature depends on the ClassDef/Method resolved at weave
        // time, which this stateless helper does not see; the emitter pipeline
        // supplies the concrete signature through EmitContext. Forwarding the raw
        // expression here is the deliberate current behaviour, not a placeholder.
        return advice.getExpression() != null ? advice.getExpression() : "";
    }

    public boolean needsJoinPoint(AdviceDescriptor advice) {
        String expr = advice.getExpression();
        return expr != null && expr.contains("thisJoinPoint");
    }
}
