package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.StaticInitializationEmitter;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.TypeReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.Y executor side: {@link DexWeaver}'s staticinit pre-pass
 * ({@code weaveStaticInit}), previously fully dark in this module — the
 * emitter's delivery sequence was covered in advice-emitter, but the weave
 * orchestration (probe-matching each class, synthesize-vs-prepend decision,
 * supplier notification, counters) was not.
 *
 * <p>One {@code staticinitialization(com.example.app..*)} Signature advice is
 * woven over a 3-class DEX and must take BOTH delivery routes in one pass:
 * <ul>
 *   <li>{@code NoClinit} (no {@code <clinit>}): a fresh {@code <clinit>} is
 *       synthesized (delivery body + {@code return-void}, static|constructor
 *       flags) and registered via {@code addSynthesizedMethod} — the
 *       per-method loop can never reach this class, so a missing synthesize
 *       call silently drops the event;</li>
 *   <li>{@code HasClinit} (existing {@code <clinit>}): v0/v1 are spilled and
 *       the 4-instruction delivery is PREPENDED at method entry on the grown
 *       MMI handed back through {@code replaceImpl} — asserting against the
 *       supplier's final view catches the gh61-class bug where the growth
 *       lands on an MMI the supplier no longer serves;</li>
 *   <li>{@code Outside} (package excluded by the pattern): untouched — no
 *       synthesized {@code <clinit>}, proving the probe-match gates the
 *       pre-pass per class.</li>
 * </ul>
 *
 * <p>A second test locks the §4.Y scope guard: a staticinit advice whose
 * monitor call does NOT pass the
 * {@code thisJoinPoint.getStaticPart().getSignature()} token is skipped
 * entirely (no synthesize, no prepend, no counters) rather than emitting a
 * malformed event.
 */
class DexWeaverStaticInitWeaveTest {

    private static final String NO_CLINIT_DESC  = "Lcom/example/app/NoClinit;";
    private static final String HAS_CLINIT_DESC = "Lcom/example/app/HasClinit;";
    private static final String OUTSIDE_DESC    = "Lcom/other/Outside;";
    private static final String MONITOR_DESC    = "Lmop/MultiSpec_1RuntimeMonitor;";
    private static final String EVENT           = "SampleSpec_clinitEvent";
    private static final String CLASS_SIGNATURE_DESC =
            StaticInitializationEmitter.CLASS_SIGNATURE_DESC;

    /** Supplier that records synthesized methods and tracks replaceImpl swaps. */
    private static final class RecordingSupplier implements DexWeaver.MutableImplSupplier {
        final Map<String, MutableMethodImplementation> muts = new HashMap<>();
        final Map<String, Method> synthesized = new HashMap<>();

        @Override
        public MutableMethodImplementation forMethod(Method method) {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            return muts.computeIfAbsent(k, kk ->
                    new MutableMethodImplementation(method.getImplementation()));
        }

        @Override
        public void replaceImpl(Method method, MutableMethodImplementation newImpl) {
            // The pre-pass grows the frame via spillLowRegisters and MUST hand
            // the fresh MMI back here — the test asserts against this view,
            // exactly what serialization would read (gh61 INV-INS-87).
            muts.put(methodKey(method), newImpl);
        }

        @Override
        public void addSynthesizedMethod(String definingClassDescriptor, Method method) {
            synthesized.put(definingClassDescriptor, method);
        }
    }

    @Test
    void signatureAdviceSynthesizesAndPrependsAcrossClasses() {
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                classWithoutClinit(NO_CLINIT_DESC),
                classWithClinit(HAS_CLINIT_DESC),
                classWithoutClinit(OUTSIDE_DESC)));
        RecordingSupplier supplier = new RecordingSupplier();

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, signatureDescriptor(), new TypeResolver(List.of()),
                inheritance(dex), supplier);

        // Counters: one class per route, both feeding matchesApplied.
        assertEquals(1, report.staticInitSynthesized(),
                "NoClinit (no <clinit>) must take the synthesize route");
        assertEquals(1, report.staticInitPrepended(),
                "HasClinit (existing <clinit>) must take the prepend route");
        assertEquals(2, report.matchesApplied(),
                "both staticinit deliveries count as applied matches");

        // --- synthesize route: shape of the registered <clinit> ---
        Method clinit = supplier.synthesized.get(NO_CLINIT_DESC);
        assertNotNull(clinit, "a <clinit> must be synthesized for NoClinit");
        assertEquals("<clinit>", clinit.getName());
        assertEquals("V", clinit.getReturnType());
        assertTrue(clinit.getParameterTypes().isEmpty());
        int clinitFlags = AccessFlags.STATIC.getValue()
                | AccessFlags.CONSTRUCTOR.getValue();
        assertEquals(clinitFlags, clinit.getAccessFlags() & clinitFlags,
                "synthesized <clinit> must carry static|constructor flags");
        List<Instruction> synth = new ArrayList<>();
        for (Instruction ins : clinit.getImplementation().getInstructions()) synth.add(ins);
        assertDeliveryAt(synth, 0, NO_CLINIT_DESC);
        assertEquals(Opcode.RETURN_VOID, synth.get(4).getOpcode(),
                "synthesized body is delivery + return-void");
        assertEquals(5, synth.size());

        // --- prepend route: delivery lands at entry of the GROWN MMI ---
        MutableMethodImplementation grown =
                supplier.muts.get(HAS_CLINIT_DESC + "-><clinit>()V");
        assertNotNull(grown, "the existing <clinit> must be materialised + swapped");
        assertTrue(grown.getRegisterCount() >= 2,
                "spillLowRegisters must free v0/v1 for the delivery frame");
        List<Instruction> prep = new ArrayList<>(grown.getInstructions());
        assertEquals(5, prep.size(), "4 delivery instructions + original return-void");
        assertDeliveryAt(prep, 0, HAS_CLINIT_DESC);
        assertEquals(Opcode.RETURN_VOID, prep.get(4).getOpcode(),
                "the original <clinit> body still runs after the delivery");

        // --- excluded class: untouched ---
        assertEquals(1, supplier.synthesized.size(),
                "Outside (pattern-excluded) must NOT get a synthesized <clinit>");
    }

    @Test
    void nonSignatureStaticInitAdviceIsSkippedEntirely() {
        // Same DEX, but the advice's monitor call passes no Signature token
        // (empty args). §4.Y scopes the pre-pass to Signature delivery; an
        // out-of-scope staticinit advice must be a no-op, not a malformed emit.
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                classWithoutClinit(NO_CLINIT_DESC),
                classWithClinit(HAS_CLINIT_DESC)));
        RecordingSupplier supplier = new RecordingSupplier();

        AspectDescriptor descriptor = signatureDescriptor();
        descriptor.getAdvices().get(0).getMonitorCalls().get(0)
                .setArgs(List.of());  // drop the Signature token

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, new TypeResolver(List.of()),
                inheritance(dex), supplier);

        assertEquals(0, report.staticInitSynthesized());
        assertEquals(0, report.staticInitPrepended());
        assertEquals(0, report.matchesApplied());
        assertTrue(supplier.synthesized.isEmpty(),
                "no <clinit> may be synthesized for out-of-scope advice");
        // The existing <clinit> must not even be materialised — the skip
        // happens before any forMethod call for this advice.
        assertTrue(supplier.muts.isEmpty(),
                "no method may be touched for out-of-scope staticinit advice");
    }

    @Test
    void classInvariantCommonPointcutGatesStaticInitPerClass() {
        // §4.PERF.P2.1 × §4.Y: a class-invariant commonPointcut (here
        // !within(com.other..*) — the same shape as the canonical
        // !within(...RVMObject+) exclusion) is HOISTED to a once-per-class
        // gate in BOTH the staticinit pre-pass and the main loop, instead of
        // being AND-composed into every probe. The advice pattern (com..*)
        // matches both classes, so the exclusion below can only come from the
        // commonPointcut gate — proving the gate actually reaches the
        // staticinit pre-pass.
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                classWithoutClinit(NO_CLINIT_DESC),
                classWithoutClinit(OUTSIDE_DESC)));
        RecordingSupplier supplier = new RecordingSupplier();

        AspectDescriptor descriptor = signatureDescriptor();
        descriptor.getAdvices().get(0).setExpression(
                "staticinitialization(com..*)");
        descriptor.setCommonPointcut("!within(com.other..*)");

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, new TypeResolver(List.of()),
                inheritance(dex), supplier);

        assertEquals(1, report.staticInitSynthesized(),
                "NoClinit passes the common gate and is synthesized");
        assertTrue(supplier.synthesized.containsKey(NO_CLINIT_DESC));
        assertEquals(1, supplier.synthesized.size(),
                "Outside is rejected by the hoisted commonPointcut gate — "
                        + "the advice pattern alone would have matched it");
        // The §4.PERF.P2.1 instrumentation counter: with the hoist, the
        // common verdict is evaluated once per class per pass (staticinit
        // pre-pass: 2 classes; main per-method loop: 2 classes) — NOT once
        // per (instruction × advice), which is the regression the counter
        // exists to catch.
        assertEquals(4, weaver.getCommonAstEvals(),
                "hoisted gate: one eval per class per pass (2 classes × 2 passes)");
    }

    // ------------------------------------------------------------------
    // assertion helper: the §4.Y 4-instruction Signature delivery
    // ------------------------------------------------------------------

    /**
     * Assert instructions {@code [at, at+4)} are the delivery sequence for
     * {@code classDesc}: const-class → new-instance ClassSignature →
     * invoke-direct ClassSignature.&lt;init&gt; → invoke-static monitor.EVENT.
     */
    private static void assertDeliveryAt(List<Instruction> ins, int at, String classDesc) {
        assertEquals(Opcode.CONST_CLASS, ins.get(at).getOpcode());
        TypeReference constClass = (TypeReference)
                ((ReferenceInstruction) ins.get(at)).getReference();
        assertEquals(classDesc, constClass.getType(),
                "const-class must load the MATCHED class, not the aspect's");
        assertEquals(Opcode.NEW_INSTANCE, ins.get(at + 1).getOpcode());
        TypeReference newInstance = (TypeReference)
                ((ReferenceInstruction) ins.get(at + 1)).getReference();
        assertEquals(CLASS_SIGNATURE_DESC, newInstance.getType());
        assertEquals(Opcode.INVOKE_DIRECT, ins.get(at + 2).getOpcode());
        MethodReference ctor = (MethodReference)
                ((ReferenceInstruction) ins.get(at + 2)).getReference();
        assertEquals(CLASS_SIGNATURE_DESC, ctor.getDefiningClass());
        assertEquals("<init>", ctor.getName());
        assertEquals(Opcode.INVOKE_STATIC, ins.get(at + 3).getOpcode());
        MethodReference event = (MethodReference)
                ((ReferenceInstruction) ins.get(at + 3)).getReference();
        assertEquals(MONITOR_DESC, event.getDefiningClass());
        assertEquals(EVENT, event.getName());
    }

    // ------------------------------------------------------------------
    // fixtures
    // ------------------------------------------------------------------

    /** A class whose only method is an ordinary static helper — NO <clinit>. */
    private static ClassDef classWithoutClinit(String classDesc) {
        return new ImmutableClassDef(
                classDesc, AccessFlags.PUBLIC.getValue(), "Ljava/lang/Object;",
                Collections.emptyList(), null, null, Collections.emptyList(),
                List.of(voidMethod(classDesc, "helper",
                        AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue())));
    }

    /** A class WITH an existing <clinit> (single return-void body). */
    private static ClassDef classWithClinit(String classDesc) {
        return new ImmutableClassDef(
                classDesc, AccessFlags.PUBLIC.getValue(), "Ljava/lang/Object;",
                Collections.emptyList(), null, null, Collections.emptyList(),
                List.of(voidMethod(classDesc, "<clinit>",
                        AccessFlags.STATIC.getValue()
                                | AccessFlags.CONSTRUCTOR.getValue())));
    }

    private static ImmutableMethod voidMethod(String classDesc, String name, int flags) {
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 1, body,
                Collections.emptyList(), Collections.emptyList());
        return new ImmutableMethod(classDesc, name,
                Collections.emptyList(), "V", flags, null, null, impl);
    }

    /** One staticinit Signature advice over the com.example.app package. */
    private static AspectDescriptor signatureDescriptor() {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("MultiSpec_1");
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("si1");
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setReturnType("void");
        a.setParameters(Collections.emptyList());
        a.setExpression("staticinitialization(com.example.app..*)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + EVENT);
        mc.setSpecName("SampleSpec");
        mc.setEventId("si1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of(StaticInitializationEmitter.SIGNATURE_ARG_TOKEN));
        a.setMonitorCalls(List.of(mc));
        d.setAdvices(List.of(a));
        return d;
    }

    private static InheritanceResolver inheritance(DexFile dex) {
        return new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
    }

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }
}
