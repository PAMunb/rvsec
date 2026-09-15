package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.ExceptionHandler;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.TryBlock;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * INV-INS-163 on the inline constructor path: a plain {@code after} advice on
 * {@code IvParameterSpec.<init>([B)V} runs its monitor call when the constructor
 * returns and when it throws. The woven method is serialised through DexPool,
 * reloaded, and read instruction by instruction: a catch-all try range covers the
 * constructor invoke alone; its handler is {@code move-exception vX}, the monitor
 * call with the same operands as the normal path, and {@code throw vX}; the normal
 * path keeps the monitor call right after the constructor.
 */
class DexWeaverCtorAfterFinallyTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String IV_DESC = "Ljavax/crypto/spec/IvParameterSpec;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    @Test
    void plainAfterOnAConstructorRunsOnBothPaths() throws Exception {
        DexWeaverNestedTryCatchTest.TrackingSupplier supplier =
                new DexWeaverNestedTryCatchTest.TrackingSupplier();
        DexFile dex = fixture();
        DexWeaver.WeaveReport report = weave(dex, advice(false), supplier);

        assertEquals(1, report.matchesApplied());
        assertEquals(1, report.constructorInlineApplied());

        MethodImplementation impl = reload(supplier.toDexFile(dex));
        List<Instruction> ins = new ArrayList<>();
        impl.getInstructions().forEach(ins::add);

        int ctorIdx = indexOf(ins, Opcode.INVOKE_DIRECT);
        List<? extends TryBlock<? extends ExceptionHandler>> tries = List.copyOf(impl.getTryBlocks());
        assertEquals(1, tries.size(), "one try range for the constructor site");
        TryBlock<? extends ExceptionHandler> range = tries.get(0);
        assertEquals(addressOf(ins, ctorIdx), range.getStartCodeAddress(),
                "the range starts at the constructor invoke");
        assertEquals(ins.get(ctorIdx).getCodeUnits(), range.getCodeUnitCount(),
                "the range covers the constructor invoke alone, not the normal-path call");
        assertEquals(1, range.getExceptionHandlers().size());
        ExceptionHandler handler = range.getExceptionHandlers().get(0);
        assertNull(handler.getExceptionType(), "catch-all handler");

        // Normal path: the monitor call immediately follows the constructor.
        Instruction normal = ins.get(ctorIdx + 1);
        assertMonitorCall(normal);
        assertEquals(Opcode.RETURN_VOID, ins.get(ctorIdx + 2).getOpcode());

        // Handler: move-exception vX; the same monitor call; throw vX.
        int handlerIdx = indexAt(ins, handler.getHandlerCodeAddress());
        Instruction moveException = ins.get(handlerIdx);
        assertEquals(Opcode.MOVE_EXCEPTION, moveException.getOpcode(),
                "the handler begins with move-exception");
        int exceptionRegister = ((OneRegisterInstruction) moveException).getRegisterA();
        Instruction handlerCall = ins.get(handlerIdx + 1);
        assertMonitorCall(handlerCall);
        assertEquals(operands((Instruction35c) normal), operands((Instruction35c) handlerCall),
                "the handler passes the same bound registers as the normal path");
        Instruction rethrow = ins.get(handlerIdx + 2);
        assertEquals(Opcode.THROW, rethrow.getOpcode(), "the handler ends in throw");
        assertEquals(exceptionRegister, ((OneRegisterInstruction) rethrow).getRegisterA(),
                "the caught exception is rethrown unchanged");
        assertTrue(!operands((Instruction35c) handlerCall).contains(exceptionRegister)
                        && !operands((Instruction35c) handlerCall).contains(2),
                "neither the exception nor the uninitialised object reaches the monitor call");
    }

    @Test
    void afterReturningOnAConstructorKeepsTheNormalPathOnly() throws Exception {
        DexWeaverNestedTryCatchTest.TrackingSupplier supplier =
                new DexWeaverNestedTryCatchTest.TrackingSupplier();
        DexFile dex = fixture();
        weave(dex, advice(true), supplier);

        MethodImplementation impl = reload(supplier.toDexFile(dex));
        assertTrue(List.copyOf(impl.getTryBlocks()).isEmpty(),
                "the constructed object exists only on normal completion; no handler is installed");
        List<Instruction> ins = new ArrayList<>();
        impl.getInstructions().forEach(ins::add);
        assertMonitorCall(ins.get(indexOf(ins, Opcode.INVOKE_DIRECT) + 1));
    }

    // --- fixtures -----------------------------------------------------------

    /**
     * <pre>
     *   static void iv() {
     *     new-instance v2, IvParameterSpec
     *     const-class v1, [B                     ; stands in for the byte[] argument
     *     invoke-direct {v2, v1}, IvParameterSpec.&lt;init&gt;([B)V
     *     return-void
     *   }
     * </pre>
     */
    private static DexFile fixture() {
        MethodReference init = new ImmutableMethodReference(IV_DESC, "<init>", List.of("[B"), "V");
        List<ImmutableInstruction> body = List.of(
                new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 2, new ImmutableTypeReference(IV_DESC)),
                new ImmutableInstruction21c(Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")),
                new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 2, 2, 1, 0, 0, 0, init),
                new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethod iv = new ImmutableMethod(FOO_DESC, "iv", List.of(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null,
                new ImmutableMethodImplementation(4, body, null, null));
        ClassDef foo = new ImmutableClassDef(FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", List.of(), null, null, List.of(), List.of(iv));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    /**
     * {@code after(byte[] iv): call(public IvParameterSpec.new(byte[])) && args(iv)}, or,
     * with {@code returning}, the same advice binding the constructed object as well.
     */
    private static AspectDescriptor advice(boolean returning) {
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("g1");
        advice.setSpecName("IvParameterSpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression("call(public IvParameterSpec.new(byte[])) && args(iv)");
        advice.setParameters(List.of(new ParameterDescriptor("byte[]", "iv")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_g1Event");
        mc.setSpecName("IvParameterSpecSpec");
        mc.setEventId("g1");
        mc.setUniqueId("u1");
        if (returning) {
            advice.setReturning(List.of(new ParameterDescriptor("IvParameterSpec", "ivSpec")));
            mc.setArgs(List.of("iv", "ivSpec"));
        } else {
            mc.setArgs(List.of("iv"));
        }
        advice.setMonitorCalls(List.of(mc));
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        descriptor.setAdvices(List.of(advice));
        return descriptor;
    }

    private static DexWeaver.WeaveReport weave(DexFile dex, AspectDescriptor descriptor,
                                               DexWeaver.MutableImplSupplier supplier) {
        InheritanceResolver inheritance =
                new InheritanceResolver(new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        return new DexWeaver(new EmitterDispatch(), new RegisterAllocator())
                .weave(dex, descriptor, new TypeResolver(descriptor.getImports()), inheritance, supplier);
    }

    private static MethodImplementation reload(DexFile woven) throws Exception {
        Path tmp = Files.createTempFile("ctor-after-finally-", ".dex");
        try {
            com.android.tools.smali.dexlib2.writer.pool.DexPool.writeTo(tmp.toString(), woven);
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                for (DexBackedClassDef cd : parsed.getClasses()) {
                    for (DexBackedMethod m : cd.getMethods()) {
                        if ("iv".equals(m.getName())) return m.getImplementation();
                    }
                }
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
        throw new AssertionError("iv()V not found in the reloaded DEX");
    }

    private static void assertMonitorCall(Instruction insn) {
        assertEquals(Opcode.INVOKE_STATIC, insn.getOpcode());
        MethodReference ref = (MethodReference) ((ReferenceInstruction) insn).getReference();
        assertEquals(MONITOR_DESC, ref.getDefiningClass());
        assertEquals("IvParameterSpecSpec_g1Event", ref.getName());
    }

    private static List<Integer> operands(Instruction35c i) {
        List<Integer> regs = List.of(i.getRegisterC(), i.getRegisterD(), i.getRegisterE(),
                i.getRegisterF(), i.getRegisterG());
        return regs.subList(0, i.getRegisterCount());
    }

    private static int indexOf(List<Instruction> ins, Opcode op) {
        for (int i = 0; i < ins.size(); i++) {
            if (ins.get(i).getOpcode() == op) return i;
        }
        throw new AssertionError("no " + op);
    }

    private static int addressOf(List<Instruction> ins, int index) {
        int address = 0;
        for (int i = 0; i < index; i++) address += ins.get(i).getCodeUnits();
        return address;
    }

    private static int indexAt(List<Instruction> ins, int address) {
        int a = 0;
        for (int i = 0; i < ins.size(); i++) {
            if (a == address) return i;
            a += ins.get(i).getCodeUnits();
        }
        throw new AssertionError("no instruction at address " + address);
    }
}
