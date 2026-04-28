package br.unb.cic.rv.emitter;

/**
 * Request from an {@link AdviceEmitter} to the {@code dex-mutator}'s
 * {@code RegisterAllocator} describing how many scratch registers the
 * {@link EmitPlan} needs.
 *
 * <p>The allocator decides whether the current method already has enough
 * unused registers or whether {@code RegisterShifter} must bump the method's
 * {@code registerCount} and shift existing references.
 */
public record RegisterRequest(
        int scratchCount,
        boolean needsWidePair,
        boolean mustBeLowRange
) {

    public static final RegisterRequest NONE = new RegisterRequest(0, false, false);

    public static RegisterRequest scratch(int count) {
        return new RegisterRequest(count, false, false);
    }

    public static RegisterRequest wide(int count) {
        return new RegisterRequest(count, true, false);
    }

    public static RegisterRequest lowRange(int count) {
        return new RegisterRequest(count, false, true);
    }
}
