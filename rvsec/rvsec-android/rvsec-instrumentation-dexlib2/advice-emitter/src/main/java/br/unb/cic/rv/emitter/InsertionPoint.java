package br.unb.cic.rv.emitter;

/**
 * Where a {@link EmitPlan}'s instructions land relative to the matched
 * instruction in the host method.
 */
public enum InsertionPoint {
    /** Insert the plan's instructions immediately before the matched instruction. */
    BEFORE,
    /** Insert the plan's instructions immediately after the matched instruction. */
    AFTER,
    /** Replace the matched instruction (used by {@code around} advice; out of scope for gh52). */
    REPLACE,
    /** Wrap the matched instruction in a try/catch whose handler runs the plan. */
    TRY_CATCH_WRAP,
    /** Insert at the head of the method (used by execution/staticinitialization). */
    METHOD_ENTRY
}
