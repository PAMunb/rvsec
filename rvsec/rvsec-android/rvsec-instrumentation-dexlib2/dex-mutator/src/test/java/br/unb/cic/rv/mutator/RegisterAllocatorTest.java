package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.RegisterRequest;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class RegisterAllocatorTest {

    @Test
    void zeroScratchReturnsNone() {
        MutableMethodImplementation impl = new MutableMethodImplementation(4);
        RegisterAllocation allocation = new RegisterAllocator().allocate(impl, RegisterRequest.NONE);
        assertSame(RegisterAllocation.NONE, allocation);
        assertEquals(4, impl.getRegisterCount(), "registerCount must not change for NONE");
    }

    @Test
    void nullRequestReturnsNone() {
        MutableMethodImplementation impl = new MutableMethodImplementation(2);
        RegisterAllocation allocation = new RegisterAllocator().allocate(impl, null);
        assertSame(RegisterAllocation.NONE, allocation);
    }

    @Test
    void scratchAllocationBumpsRegisterCountAndReturnsHighIndices() {
        // gh61: allocate() now returns a FRESH MMI (clone path) — the source
        // MMI's registerCount is unchanged; the new one carries the grown
        // frame. Caller MUST consume allocation.newImpl() and notify its
        // supplier (see RegisterAllocation javadoc / design.md D5).
        MutableMethodImplementation impl = new MutableMethodImplementation(4);
        RegisterAllocation allocation = new RegisterAllocator()
                .allocate(impl, RegisterRequest.scratch(2));
        assertNotNull(allocation.newImpl(),
                "non-zero allocation MUST carry the cloned MMI");
        assertEquals(6, allocation.newImpl().getRegisterCount(),
                "newImpl.registerCount must equal oldCount + scratchCount");
        assertEquals(4, impl.getRegisterCount(),
                "source MMI is unchanged (clone path) — caller swaps the ref");
        assertEquals(2, allocation.scratch().size());
        assertEquals(4, allocation.scratch().get(0), "first scratch at old-count");
        assertEquals(5, allocation.scratch().get(1));
        assertEquals(2, allocation.registerCountDelta());
    }
}
