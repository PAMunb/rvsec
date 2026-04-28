package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import java.util.Objects;

/**
 * Everything an {@link AdviceEmitter} needs to produce an {@link EmitPlan} for
 * one matched advice occurrence.
 *
 * <p>Bundled rather than passed as 5+ positional arguments because the
 * emitter pipeline in {@code dex-mutator.DexWeaver} passes the same set around
 * per match.
 */
public final class EmitContext {

    public final AdviceDescriptor advice;
    public final Match match;
    public final TypeResolver typeResolver;
    public final String monitorOwnerDescriptor;

    public EmitContext(AdviceDescriptor advice, Match match, TypeResolver typeResolver,
                       String monitorOwnerDescriptor) {
        this.advice = Objects.requireNonNull(advice, "advice");
        this.match = Objects.requireNonNull(match, "match");
        this.typeResolver = Objects.requireNonNull(typeResolver, "typeResolver");
        this.monitorOwnerDescriptor = Objects.requireNonNull(monitorOwnerDescriptor,
                "monitorOwnerDescriptor");
    }

    /** Convenience accessor for the single monitor call typical of a MOP advice. */
    public MonitorCallDescriptor primaryMonitorCall() {
        if (advice.getMonitorCalls().isEmpty()) return null;
        return advice.getMonitorCalls().get(0);
    }
}
