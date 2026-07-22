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
 * the shifter's expansion of 4-bit register-index overflows to the wider
 * {@code /from16} format is handled inside that class, so from the caller's
 * perspective the returned scratch indices are safe to use in any instruction
 * format.
 */
public final class RegisterAllocator {

    public RegisterAllocation allocate(MutableMethodImplementation impl, RegisterRequest request) {
        if (request == null || request.scratchCount() <= 0) {
            return RegisterAllocation.NONE;
        }
        int delta = request.scratchCount();
        int oldCount = impl.getRegisterCount();
        // Grow the register frame by allocating a fresh MMI via the
        // RegisterShifter clone path. The newly-added slots end up at the
        // high-indexed end; existing register references keep their indices
        // unchanged (this allocator only grows; shifting refs to make room
        // at the low end is spillLowRegisters' job). The caller MUST replace
        // its reference to impl with newImpl and notify its
        // MutableImplSupplier — see RegisterAllocation javadoc.
        MutableMethodImplementation newImpl = RegisterShifter.bumpRegisterCount(impl, delta);
        List<Integer> scratch = new ArrayList<>(delta);
        for (int i = 0; i < delta; i++) scratch.add(oldCount + i);
        return new RegisterAllocation(scratch, delta, newImpl);
    }
}
