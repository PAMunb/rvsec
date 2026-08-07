package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import java.util.List;
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
    /**
     * DEX type descriptor ({@code Lcom/foo/Bar;}) of the class the advice is
     * being woven into, when statically known at the emit site. Populated by
     * {@link br.unb.cic.rv.emitter.StaticInitializationEmitter}'s caller for
     * {@code staticinitialization(T+)} advice so the emitter can deliver a
     * {@code ClassSignature} over the matched class (§4.Y); {@code null} for
     * call-site advice where the join point is an invoke, not a class.
     */
    public final String matchedClassDescriptor;

    public EmitContext(AdviceDescriptor advice, Match match, TypeResolver typeResolver,
                       String monitorOwnerDescriptor) {
        this(advice, match, typeResolver, monitorOwnerDescriptor, null);
    }

    public EmitContext(AdviceDescriptor advice, Match match, TypeResolver typeResolver,
                       String monitorOwnerDescriptor, String matchedClassDescriptor) {
        this.advice = Objects.requireNonNull(advice, "advice");
        this.match = Objects.requireNonNull(match, "match");
        this.typeResolver = Objects.requireNonNull(typeResolver, "typeResolver");
        this.monitorOwnerDescriptor = Objects.requireNonNull(monitorOwnerDescriptor,
                "monitorOwnerDescriptor");
        this.matchedClassDescriptor = matchedClassDescriptor;
    }

    /**
     * Every monitor call this advice carries, in descriptor order, never null.
     *
     * <p>An advice may carry more than one: JavaMOP fuses advices whose
     * position and pointcut coincide, and the production descriptor holds 115
     * advices of which 17 are fused. Descriptor order is normative — it is the
     * order the generated monitor expects its events in — so callers iterate
     * this list and never reorder it (INV-INS-104).
     */
    public List<MonitorCallDescriptor> monitorCalls() {
        List<MonitorCallDescriptor> calls = advice.getMonitorCalls();
        return calls == null ? List.of() : calls;
    }
}
