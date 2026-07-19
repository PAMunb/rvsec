/**
 * DEX mutation engine: consumes {@link br.unb.cic.rv.emitter.EmitPlan} values
 * from {@code advice-emitter} and realizes them against dexlib2's
 * {@code MutableMethodImplementation}.
 *
 * <p>Responsibilities split across classes per design D1:
 * <ul>
 *   <li>{@link br.unb.cic.rv.mutator.InstructionInjector} — primitive operations
 *       (insertBefore / insertAfter / replaceInvoke) on a method implementation.</li>
 *   <li>{@link br.unb.cic.rv.mutator.RegisterShifter} — grows a method's
 *       {@code registerCount} by cloning the {@code MutableMethodImplementation}
 *       onto a wider frame. dexlib2 exposes no setter for {@code registerCount},
 *       and a reflectively-mutated value is invisible to the {@code DexPool}
 *       writer, so the clone is the only serialisation-correct path. It also
 *       expands 4-bit register-index overflows to the wider {@code /from16}
 *       formats (INV-INS-80, INV-INS-87).</li>
 *   <li>{@link br.unb.cic.rv.mutator.RegisterAllocator} — decides which scratch
 *       registers an {@link br.unb.cic.rv.emitter.EmitPlan} gets; invokes
 *       {@code RegisterShifter} only when the method doesn't already have
 *       enough free registers.</li>
 *   <li>{@link br.unb.cic.rv.mutator.DexWeaver} — top-level orchestrator that
 *       iterates ClassDef × Method × Instruction, runs the matcher, drives
 *       emitters, and applies plans via the injector.</li>
 * </ul>
 *
 * <p>Spec-set agnostic — the same code path weaves JCA specs or Generic specs
 * without any branching on the specification family.
 */
package br.unb.cic.rv.mutator;
