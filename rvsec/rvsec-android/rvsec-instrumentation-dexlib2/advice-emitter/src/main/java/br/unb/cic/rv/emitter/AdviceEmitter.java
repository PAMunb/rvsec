package br.unb.cic.rv.emitter;

/**
 * Contract for concrete emitters: one per AspectJ advice kind the weaver
 * supports.
 *
 * <p>Each emitter is stateless; inputs arrive via {@link EmitContext}. The
 * returned {@link EmitPlan} captures everything the {@code dex-mutator}
 * executor needs to realize the advice at the matched site.
 */
public interface AdviceEmitter {

    /**
     * @return an {@link EmitPlan} describing what to inject and where, never
     *         {@code null}. When the advice is unsupported on this match (e.g.
     *         {@code around} advice hitting this weaver), the emitter throws
     *         {@code UnsupportedAspectConstructError} (defined in
     *         {@code rv-instrumentation-dexlib2} Python wrapper; Java side
     *         throws {@link UnsupportedOperationException} until a Java-side
     *         sibling error type is introduced in Group 5).
     */
    EmitPlan emit(EmitContext ctx);

    /** Identifier used by the weaver for logging / dispatch-table lookup. */
    String kind();
}
