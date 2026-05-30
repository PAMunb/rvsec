package br.unb.cic.rv.grammar;

import br.unb.cic.rv.coverage.CoverageWeaver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.Reference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Shared fixture for the {@code coverage-weaver} NOT-NEEDED β assertion tests (§4.RT' / §4.CV'):
 * runs the real {@link CoverageWeaver} over a synthetic application class and serializes+reparses the
 * result, so the absorption claims are asserted against genuine woven DEX rather than narrative text.
 */
final class CoverageWeaveFixture {

    private CoverageWeaveFixture() { }

    static final String APP_CLASS = "Lcom/example/App;";

    /** Weave the coverage catch-all over a one-method application class and reparse the DEX. */
    static DexFile weaveAppClass() throws Exception {
        // A non-excluded static no-arg application method with one local register (regCount=1,
        // paramRegs=0 → localCount=1), so the coverage entry hook lands at v0 without a spill.
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                1,
                List.of(new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(APP_CLASS, "doWork", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef cls = new ImmutableClassDef(APP_CLASS, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(), null, null,
                Collections.emptyList(), List.of(m));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(cls));

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        CoverageWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) {
                return null;
            }
            return muts.computeIfAbsent(method.getName(),
                    k -> new MutableMethodImplementation(method.getImplementation()));
        };
        CoverageWeaver weaver = new CoverageWeaver();
        weaver.weave(dex, supplier);

        // Rebuild the class from the mutated impls and serialize via DexPool. A
        // MutableMethodImplementation IS a MethodImplementation, so ImmutableMethod.of() snapshots it.
        List<Method> woven = new ArrayList<>();
        for (Method method : cls.getMethods()) {
            MutableMethodImplementation mmi = muts.get(method.getName());
            woven.add(new ImmutableMethod(method.getDefiningClass(), method.getName(),
                    method.getParameters(), method.getReturnType(), method.getAccessFlags(),
                    method.getAnnotations(), method.getHiddenApiRestrictions(),
                    mmi == null ? method.getImplementation()
                            : ImmutableMethodImplementation.of(mmi)));
        }
        ClassDef wovenCls = new ImmutableClassDef(cls.getType(), cls.getAccessFlags(),
                cls.getSuperclass(), cls.getInterfaces(), cls.getSourceFile(), cls.getAnnotations(),
                cls.getStaticFields(), woven);
        DexFile wovenDex = new ImmutableDexFile(Opcodes.getDefault(), List.of(wovenCls));

        Path tmp = Files.createTempFile("gh62-coverage-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), wovenDex);
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                return DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    /** Every method-reference invoked anywhere in the woven DEX, in "Lowner;->name" form. */
    static List<String> invokedMethodRefs(DexFile dex) {
        List<String> refs = new ArrayList<>();
        for (ClassDef c : dex.getClasses()) {
            for (Method m : c.getMethods()) {
                if (m.getImplementation() == null) {
                    continue;
                }
                for (Instruction i : m.getImplementation().getInstructions()) {
                    if (i instanceof ReferenceInstruction) {
                        Reference r = ((ReferenceInstruction) i).getReference();
                        if (r instanceof MethodReference) {
                            MethodReference mr = (MethodReference) r;
                            refs.add(mr.getDefiningClass() + "->" + mr.getName());
                        }
                    }
                }
            }
        }
        return refs;
    }

    /** All type/method references in the woven DEX, flattened to their string form, so a substring
     *  scan over the reference pool can assert the absence of a package. */
    static List<String> allReferenceStrings(DexFile dex) {
        List<String> out = new ArrayList<>();
        for (ClassDef c : dex.getClasses()) {
            out.add(c.getType());
            out.add(c.getSuperclass());
            for (Method m : c.getMethods()) {
                out.add(m.getDefiningClass());
                out.add(m.getReturnType());
                if (m.getImplementation() == null) {
                    continue;
                }
                for (Instruction i : m.getImplementation().getInstructions()) {
                    if (i instanceof ReferenceInstruction) {
                        out.add(String.valueOf(((ReferenceInstruction) i).getReference()));
                    }
                }
            }
        }
        return out;
    }
}
