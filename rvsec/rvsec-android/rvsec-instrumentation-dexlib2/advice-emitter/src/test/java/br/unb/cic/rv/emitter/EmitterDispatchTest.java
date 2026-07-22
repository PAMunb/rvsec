package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class EmitterDispatchTest {

    private final EmitterDispatch dispatch = new EmitterDispatch();

    @Test
    void selectsBeforeEmitterForBeforeAdvice() {
        AdviceDescriptor a = EmitterTestFixtures.adviceBefore("before1");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(BeforeEmitter.class, e);
    }

    @Test
    void selectsAfterEmitterForPlainAfter() {
        AdviceDescriptor a = EmitterTestFixtures.adviceAfter("after1");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(AfterEmitter.class, e);
    }

    @Test
    void selectsAfterReturningEmitterWhenReturningPresent() {
        AdviceDescriptor a = EmitterTestFixtures.adviceAfterReturning("aret1");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(AfterReturningEmitter.class, e);
    }

    @Test
    void selectsAfterThrowingEmitterWhenThrowingPresent() {
        AdviceDescriptor a = EmitterTestFixtures.adviceAfterThrowing("ath1", "Exception");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(AfterThrowingEmitter.class, e);
    }

    @Test
    void selectsStaticInitEmitterForStaticinitialization() {
        AdviceDescriptor a = EmitterTestFixtures.adviceStaticInit("si1", "java.util.Iterator+");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(StaticInitializationEmitter.class, e);
    }

    @Test
    void wrapsInIfGuardWhenExpressionContainsIfClause() {
        AdviceDescriptor a = EmitterTestFixtures.adviceWithIfGuard("guarded1");
        AdviceEmitter e = dispatch.select(a);
        assertInstanceOf(IfGuardEmitter.class, e);
    }

    @Test
    void aroundAdviceRejected() {
        AdviceDescriptor a = EmitterTestFixtures.adviceBefore("around1");
        a.setAround(true);
        assertThrows(UnsupportedOperationException.class, () -> dispatch.select(a));
    }

    @Test
    void bothReturningAndThrowingIsIllegal() {
        AdviceDescriptor a = EmitterTestFixtures.adviceAfterReturning("both1");
        a.setThrowing(java.util.List.of(
                new br.unb.cic.rv.descriptor.ParameterDescriptor("Throwable", "t")));
        assertThrows(IllegalStateException.class, () -> dispatch.select(a));
    }
}
