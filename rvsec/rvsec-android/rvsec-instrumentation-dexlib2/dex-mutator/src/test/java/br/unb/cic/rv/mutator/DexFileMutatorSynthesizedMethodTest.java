package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.TypeReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;

import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * §4.Y enabling mechanism: {@link DexFileMutator}'s class-level method-addition
 * path. A method registered via {@link DexFileMutator#addSynthesizedMethod}
 * MUST be appended to its class and survive {@code DexPool} serialization — the
 * pre-§4.Y {@link DexFileMutator} only substituted existing method bodies and
 * would have dropped a brand-new method.
 *
 * <p>This is the load-bearing proof against silent-inertness for the synthesis
 * path, isolated from the staticinit weave so a regression here is unambiguous.
 */
class DexFileMutatorSynthesizedMethodTest {

    private static final String OWNER = "LFoo;";

    @Test
    void synthesizedMethodSurvivesSerialization() throws Exception {
        // Original class Foo with a single existing method bar()V.
        ImmutableMethodImplementation barImpl = new ImmutableMethodImplementation(
                1, List.of(new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                Collections.emptyList(), Collections.emptyList());
        Method bar = new ImmutableMethod(OWNER, "bar", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, barImpl);
        ClassDef foo = new ImmutableClassDef(OWNER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, Collections.emptyList(),
                List.of(bar));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));

        // Synthesize a <clinit> with one const-class instruction (over Foo).
        List<BuilderInstruction> body = new ArrayList<>();
        body.add(new BuilderInstruction21c(Opcode.CONST_CLASS, 0,
                new ImmutableTypeReference(OWNER)));
        Method clinit = StaticInitSynthesizer.synthesize(OWNER, body, /*registerCount=*/ 1);

        DexFileMutator mutator = new DexFileMutator(dex);
        mutator.addSynthesizedMethod(OWNER, clinit);

        Path tmp = Files.createTempFile("gh62-synth-", ".dex");
        DexBackedDexFile parsed;
        try {
            DexPool.writeTo(tmp.toString(), mutator.toDexFile());
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
            }
        } finally {
            Files.deleteIfExists(tmp);
        }

        DexBackedClassDef parsedFoo = null;
        for (ClassDef cd : parsed.getClasses()) {
            if (OWNER.equals(cd.getType())) parsedFoo = (DexBackedClassDef) cd;
        }
        assertNotNull(parsedFoo, "Foo must be present in the reparsed dex");

        DexBackedMethod parsedClinit = null;
        DexBackedMethod parsedBar = null;
        for (DexBackedMethod m : parsedFoo.getMethods()) {
            if ("<clinit>".equals(m.getName())) parsedClinit = m;
            if ("bar".equals(m.getName())) parsedBar = m;
        }
        assertNotNull(parsedBar, "the original bar() must be preserved alongside the addition");
        assertNotNull(parsedClinit,
                "the synthesized <clinit> must survive serialization (not be dropped)");

        List<Instruction> insns = new ArrayList<>();
        for (Instruction i : parsedClinit.getImplementation().getInstructions()) insns.add(i);
        assertEquals(2, insns.size(), "const-class + return-void");
        assertEquals(Opcode.CONST_CLASS, insns.get(0).getOpcode());
        assertEquals(OWNER,
                ((TypeReference) ((ReferenceInstruction) insns.get(0)).getReference()).getType());
        assertEquals(Opcode.RETURN_VOID, insns.get(1).getOpcode());
    }
}
