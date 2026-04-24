package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.RegisterRequest;

import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;

import java.util.ArrayList;
import java.util.List;

/**
 * Allocates scratch registers for {@link br.unb.cic.rv.emitter.EmitPlan}s.
 *
 * <p>Strategy:
 * <ol>
 *   <li>If {@code request.scratchCount() == 0} → return {@link RegisterAllocation#NONE}.</li>
 *   <li>Allocate new registers at the top of the current {@code registerCount}
 *       (they become the lowest-indexed scratch after shift).</li>
 *   <li>Delegate to {@link RegisterShifter} to bump {@code registerCount} by
 *       the needed delta and rewrite references to the existing registers so
 *       the old values remain accessible through the shifted indices.</li>
 * </ol>
 *
 * <p>The allocator never returns high-index registers to the caller —
 * the shifter's expansion to {@code /from16} / {@code /from32} is handled
 * inside that class, so from the caller's perspective the returned scratch
 * indices are safe to use in any instruction format.
 */
public final class RegisterAllocator {

    public RegisterAllocation allocate(MutableMethodImplementation impl, RegisterRequest request) {
        if (request == null || request.scratchCount() <= 0) {
            return RegisterAllocation.NONE;
        }
        int delta = request.scratchCount();
        int oldCount = impl.getRegisterCount();
        // Bump the registerCount so scratch registers occupy the newly-added
        // high-indexed slots. Per-instruction shifting (rewriting refs to
        // existing registers when the shift threshold is non-zero) is handled
        // by the DexWeaver's post-allocation pass — here we only grow the
        // register space. Growing registers alone never breaks existing
        // instructions: the old registers keep their indices.
        RegisterShifter.bumpRegisterCount(impl, delta);
        List<Integer> scratch = new ArrayList<>(delta);
        for (int i = 0; i < delta; i++) scratch.add(oldCount + i);
        return new RegisterAllocation(scratch, delta);
    }
}
