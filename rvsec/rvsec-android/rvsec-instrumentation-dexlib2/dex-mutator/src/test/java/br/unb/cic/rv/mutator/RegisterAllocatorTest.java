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
        MutableMethodImplementation impl = new MutableMethodImplementation(4);
        RegisterAllocation allocation = new RegisterAllocator()
                .allocate(impl, RegisterRequest.scratch(2));
        assertEquals(6, impl.getRegisterCount(),
                "registerCount must grow by scratchCount");
        assertEquals(2, allocation.scratch().size());
        assertEquals(4, allocation.scratch().get(0), "first scratch at old-count");
        assertEquals(5, allocation.scratch().get(1));
        assertEquals(2, allocation.registerCountDelta());
    }
}
