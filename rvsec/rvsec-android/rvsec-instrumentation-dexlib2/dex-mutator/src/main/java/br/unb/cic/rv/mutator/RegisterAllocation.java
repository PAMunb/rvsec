package br.unb.cic.rv.mutator;

import java.util.Collections;
import java.util.List;

/**
 * Result of a scratch-register allocation request: the concrete register
 * indices granted plus the delta applied to the method's
 * {@code registerCount}.
 */
public record RegisterAllocation(List<Integer> scratch, int registerCountDelta) {
    public RegisterAllocation {
        scratch = scratch == null ? Collections.emptyList() : List.copyOf(scratch);
    }

    public static final RegisterAllocation NONE = new RegisterAllocation(Collections.emptyList(), 0);
}
