package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;

import java.util.Collections;
import java.util.List;

/**
 * Result of a scratch-register allocation request.
 *
 * <p>{@code newImpl} is the {@link MutableMethodImplementation} returned by
 * {@link RegisterShifter#bumpRegisterCount(MutableMethodImplementation, int)}
 * (a freshly-allocated MMI with the grown frame). The caller MUST replace
 * any reference to the source MMI with {@code newImpl}, and — when the
 * source MMI came from a {@code MutableImplSupplier} — notify the supplier
 * via {@code replaceImpl(method, newImpl)} so the per-method cache stops
 * handing out the stale MMI (INV-INS-87, design.md D5). For {@link #NONE}
 * (zero-delta allocations), {@code newImpl} is {@code null} and the caller
 * keeps its existing reference.
 */
public record RegisterAllocation(
        List<Integer> scratch,
        int registerCountDelta,
        MutableMethodImplementation newImpl) {
    public RegisterAllocation {
        scratch = scratch == null ? Collections.emptyList() : List.copyOf(scratch);
    }

    public static final RegisterAllocation NONE =
            new RegisterAllocation(Collections.emptyList(), 0, null);
}
