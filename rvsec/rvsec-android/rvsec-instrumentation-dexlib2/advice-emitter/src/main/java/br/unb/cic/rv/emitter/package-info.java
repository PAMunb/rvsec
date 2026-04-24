/**
 * Per-advice-kind instruction planners that produce {@link br.unb.cic.rv.emitter.EmitPlan}
 * values consumed by the {@code dex-mutator} module.
 *
 * <p>This module is the value-class owner per design decision D1: {@code EmitPlan}
 * and {@code RegisterRequest} live here so that {@code pointcut-engine} can remain
 * free of dexlib2 mutation concerns and {@code dex-mutator} can remain a pure
 * executor of plans. Spec-set agnostic — emits identical plan shapes whether the
 * advice originated from the JCA spec set or the Generic spec set.
 */
package br.unb.cic.rv.emitter;
