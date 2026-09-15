package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;

/**
 * INV-INS-168: an advice's pointcut expression is parsed once per weave.
 *
 * <p>The matching path asks for the expression of every advice at every instruction of every
 * method of every class, so a parse there is the same work repeated once per instruction. The
 * memo hands out one instance, which is sound because the pointcut AST is built of immutable
 * records and the matcher keeps the state of a match in the context it creates per call.
 */
class DexWeaverParseMemoTest {

    @Test
    void theSameAdviceYieldsTheSameExpressionInstance() {
        DexWeaver weaver = newWeaver();
        AdviceDescriptor advice = advice("call(public IvParameterSpec.new(byte[])) && args(iv)");

        PointcutExpression first = weaver.parseCached(advice);
        PointcutExpression second = weaver.parseCached(advice);

        assertSame(first, second, "the second call must answer from the memo, not parse again");
    }

    @Test
    void anExpressionThatDoesNotParseIsMemoisedAsWell() {
        DexWeaver weaver = newWeaver();
        AdviceDescriptor advice = advice("call(");

        assertNull(weaver.parseCached(advice));
        assertNull(weaver.parseCached(advice), "a rejected expression must not be parsed again");
    }

    @Test
    void aNewWeaveStartsWithAnEmptyMemo() {
        DexWeaver weaver = newWeaver();
        AdviceDescriptor advice = advice("call(public IvParameterSpec.new(byte[])) && args(iv)");
        PointcutExpression beforeWeave = weaver.parseCached(advice);

        DexFile empty = new ImmutableDexFile(Opcodes.getDefault(), Collections.emptyList());
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        descriptor.setAdvices(List.of(advice));
        AndroidClassIndex android = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        weaver.weave(empty, descriptor, new TypeResolver(descriptor.getImports()),
                new InheritanceResolver(android, empty), method -> null);

        assertNotSame(beforeWeave, weaver.parseCached(advice),
                "the memo of a weave must not be read by the next one");
    }

    private static DexWeaver newWeaver() {
        return new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
    }

    private static AdviceDescriptor advice(String expression) {
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("a1");
        advice.setSpecName("IvParameterSpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression(expression);
        return advice;
    }
}
