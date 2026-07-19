package br.unb.cic.rv.coverage;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.StringReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertSame;

/**
 * Behavioural coverage for {@link CoverageWeaver#weave} — the weave loop,
 * package-exclusion skip, abstract-method skip, the injected
 * {@code const-string + invoke-static Lmop/Coverage;.log(...)} pair, and the
 * {@code localCount == 0} register-spill path. The class was 0% covered; a
 * regression in the skip logic (dropping app coverage) or in the injected
 * hook shape would previously ship undetected.
 */
class CoverageWeaverTest {

    /** Supplier over synthetic methods: hands back a mutable copy per method
     *  and records the post-spill MMI so tests can inspect the woven body. */
    private static final class CapturingSupplier implements CoverageWeaver.MutableImplSupplier {
        final Map<String, MutableMethodImplementation> impls = new HashMap<>();

        @Override
        public MutableMethodImplementation forMethod(Method method) {
            MethodImplementation src = method.getImplementation();
            if (src == null) return null;
            return impls.computeIfAbsent(method.getName(),
                    k -> new MutableMethodImplementation(src));
        }

        @Override
        public void replaceImpl(Method method, MutableMethodImplementation newImpl) {
            // Mirror DexFileMutator: the spill path swaps the cached MMI.
            impls.put(method.getName(), newImpl);
        }
    }

    private static Method concreteMethod(String owner, String name,
                                         int accessFlags,
                                         MethodImplementation impl,
                                         String... paramTypes) {
        List<ImmutableMethodParameter> params = new ArrayList<>();
        for (String t : paramTypes) params.add(new ImmutableMethodParameter(t, null, null));
        return new ImmutableMethod(owner, name, params, "V", accessFlags, null, null, impl);
    }

    private static MethodImplementation returnVoidBody(int registerCount) {
        return new ImmutableMethodImplementation(registerCount,
                List.of(new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                List.of(), List.of());
    }

    private static ClassDef classOf(String type, List<Method> methods) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, List.of(), methods);
    }

    @Test
    void weaveInstrumentsAppMethodsAndSkipsExcludedAndAbstract() {
        String app = "Lcom/example/App;";
        // foo: 1 register, 0 params → one free local, no spill needed.
        Method foo = concreteMethod(app, "foo",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                returnVoidBody(1));
        // bar: abstract → null implementation → skipped.
        Method bar = concreteMethod(app, "bar",
                AccessFlags.PUBLIC.getValue() | AccessFlags.ABSTRACT.getValue(),
                null);
        ClassDef appClass = classOf(app, List.of(foo, bar));
        // The whole mop.Coverage class is excluded by PackageFilter → not visited.
        ClassDef excluded = classOf("Lmop/Coverage;",
                List.of(concreteMethod("Lmop/Coverage;", "log",
                        AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                        returnVoidBody(1))));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(appClass, excluded));

        CapturingSupplier supplier = new CapturingSupplier();
        CoverageWeaver.CoverageReport report = new CoverageWeaver().weave(dex, supplier);

        assertEquals(2, report.classesSeen());
        assertEquals(1, report.classesSkipped(), "the excluded mop.* class is skipped whole");
        assertEquals(1, report.methodsInstrumented());
        assertEquals(1, report.methodsSkipped(), "the abstract (null-impl) method is skipped");
        assertEquals(0, report.methodsSpillFailed());

        // The excluded class's method must never be touched.
        org.junit.jupiter.api.Assertions.assertFalse(supplier.impls.containsKey("log"),
                "a method under an excluded package must not be instrumented");

        // foo must carry the injected const-string + invoke-static at entry.
        List<BuilderInstruction> insns = supplier.impls.get("foo").getInstructions();
        BuilderInstruction21c constStr = assertInstanceOf(BuilderInstruction21c.class, insns.get(0));
        assertEquals(Opcode.CONST_STRING, constStr.getOpcode());
        assertEquals("<com.example.App: void foo()>",
                ((StringReference) constStr.getReference()).getString(),
                "the pre-computed Soot-style signature is the const-string operand");
        BuilderInstruction35c invoke = assertInstanceOf(BuilderInstruction35c.class, insns.get(1));
        assertEquals(Opcode.INVOKE_STATIC, invoke.getOpcode());
        MethodReference ref = (MethodReference) invoke.getReference();
        assertEquals("Lmop/Coverage;", ref.getDefiningClass());
        assertEquals("log", ref.getName());
        assertEquals(0, invoke.getRegisterC(), "the hook uses the freed scratch v0");
    }

    @Test
    void weaveSpillsWhenNoFreeLocalAndStillInjects() {
        String app = "Lcom/example/NoLocals;";
        // Static method with one int param and registerCount == 1: the param
        // occupies the entire frame (localCount == 0), forcing the spill path.
        Method baz = concreteMethod(app, "baz",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                returnVoidBody(1), "I");
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(),
                List.of(classOf(app, List.of(baz))));

        CapturingSupplier supplier = new CapturingSupplier();
        CoverageWeaver.CoverageReport report = new CoverageWeaver().weave(dex, supplier);

        assertEquals(1, report.methodsInstrumented(),
                "register pressure must NOT skip the method — the frame is grown instead");
        assertEquals(0, report.methodsSpillFailed());

        MutableMethodImplementation woven = supplier.impls.get("baz");
        assertEquals(2, woven.getRegisterCount(),
                "spillLowRegisters grows the frame by 1 to free scratch v0");
        assertInstanceOf(BuilderInstruction21c.class, woven.getInstructions().get(0));
        assertInstanceOf(BuilderInstruction35c.class, woven.getInstructions().get(1));

        // The spill path must have notified the supplier with the fresh MMI
        // (INV-INS-87) — the cached MMI is the one that carries the injection.
        assertSame(woven, supplier.forMethod(baz),
                "replaceImpl must publish the post-spill MMI to the supplier cache");
    }
}
