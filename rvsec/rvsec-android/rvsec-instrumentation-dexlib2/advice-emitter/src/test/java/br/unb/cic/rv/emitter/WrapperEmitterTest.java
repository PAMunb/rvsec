package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.AndroidClassIndex;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests the AndroidClassIndex-driven wrapper expansion (port of
 * {@code WrapperGenerator.expandSupertypes} from prototipo-dexlib2).
 *
 * <p>To stay self-contained the tests build a tiny in-memory "android.jar"
 * via ASM containing only the {@code javax/crypto/Cipher} skeleton needed to
 * exercise overload enumeration. We mirror the actual Android API surface
 * for {@code getInstance} (3 static overloads) and {@code doFinal}
 * (8 instance overloads — abridged to the byte[]-returning four since
 * those are what the JCA spec set's pointcuts actually call).
 */
class WrapperEmitterTest {

    private static Path androidJar;

    @BeforeAll
    static void buildFixture(@TempDir Path tmp) throws IOException {
        androidJar = tmp.resolve("android-fixture.jar");
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(androidJar))) {
            writeClass(zos, "java/lang/Object", null, classWriter -> {});
            writeClass(zos, "javax/crypto/Cipher", "java/lang/Object", cw -> {
                // Three static getInstance overloads, mirroring android.jar.
                cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC,
                        "getInstance",
                        "(Ljava/lang/String;)Ljavax/crypto/Cipher;",
                        null, null).visitEnd();
                cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC,
                        "getInstance",
                        "(Ljava/lang/String;Ljava/lang/String;)Ljavax/crypto/Cipher;",
                        null, null).visitEnd();
                cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC,
                        "getInstance",
                        "(Ljava/lang/String;Ljava/security/Provider;)Ljavax/crypto/Cipher;",
                        null, null).visitEnd();
                // Instance doFinal overloads.
                cw.visitMethod(Opcodes.ACC_PUBLIC,
                        "doFinal",
                        "()[B",
                        null, null).visitEnd();
                cw.visitMethod(Opcodes.ACC_PUBLIC,
                        "doFinal",
                        "([B)[B",
                        null, null).visitEnd();
                cw.visitMethod(Opcodes.ACC_PUBLIC,
                        "doFinal",
                        "([BII)[B",
                        null, null).visitEnd();
            });
            // Stand-in for java.security.Provider so AndroidClassIndex can
            // resolve the parameter type without actually loading anything.
            writeClass(zos, "java/security/Provider", "java/lang/Object", cw -> {});
        }
    }

    @Test
    void expandsStaticCipherGetInstance(@TempDir Path out) throws IOException {
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String))",
                List.of(),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(d, out, idx);
        assertEquals(1, entries.size(), "expected one entry for the String-arg overload");
        WrapperEmitter.WrapperEntry e = entries.get(0);
        assertTrue(e.isStatic, "Cipher.getInstance is static");
        assertEquals(List.of("java.lang.String"), e.originalParamFqn);
        assertEquals("javax.crypto.Cipher", e.originalReturnFqn);
    }

    @Test
    void expandsInstanceCipherDoFinal(@TempDir Path out) throws IOException {
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "doFinal",
                "Cipher",
                "call(public byte[] Cipher.doFinal(byte[])) && target(c) && args(input)",
                List.of(new ParameterDescriptor("Cipher", "c"),
                        new ParameterDescriptor("byte[]", "input")),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(d, out, idx);
        assertEquals(1, entries.size(), "expected single byte[]-arg doFinal overload");
        WrapperEmitter.WrapperEntry e = entries.get(0);
        assertFalse(e.isStatic, "doFinal is an instance method");
        // Receiver is NOT in originalParamFqn — the dex-mutator prepends it
        // when synthesizing the wrapper MethodReference.
        assertEquals(List.of("byte[]"), e.originalParamFqn);
        assertEquals("byte[]", e.originalReturnFqn);

        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(src.contains("recv.doFinal(p0)"),
                "instance wrapper must call recv.doFinal(p0); got:\n" + src);
        assertTrue(src.contains("javax.crypto.Cipher recv"),
                "instance wrapper must take Cipher recv as first param; got:\n" + src);
    }

    @Test
    void expandsVarargsViaIndex(@TempDir Path out) throws IOException {
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static * Cipher.getInstance(..))",
                List.of(),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(d, out, idx);
        assertEquals(3, entries.size(),
                "expected 3 getInstance overloads from the fixture; got " + entries.size());
        assertTrue(entries.stream().allMatch(e -> e.isStatic));
    }

    @Test
    void nullIndexFallsBackToSkip(@TempDir Path out) throws IOException {
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static * Cipher.getInstance(..))",
                List.of(),
                "result"));
        // No index → varargs cannot be expanded → wrapper skipped (zero entries).
        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(d, out, null);
        assertTrue(entries.isEmpty(),
                "varargs must not produce wrappers when AndroidClassIndex is null");
    }

    // --- fixture helpers -----------------------------------------------------

    private static AspectDescriptor newDescriptor(AdviceDescriptor advice) {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("Test");
        d.setImports(List.of(
                "javax.crypto.Cipher",
                "java.lang.String",
                "java.security.Provider"));
        d.setAdvices(List.of(advice));
        return d;
    }

    private static AdviceDescriptor adviceAfterReturning(String name, String specName,
                                                         String expression,
                                                         List<ParameterDescriptor> params,
                                                         String returningName) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName(specName);
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(params);
        a.setReturning(List.of(new ParameterDescriptor("Object", returningName)));
        a.setExpression(expression);
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.event");
        mc.setSpecName(specName);
        mc.setEventId("event");
        mc.setUniqueId("event");
        mc.setArgs(List.of(returningName));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private interface ClassBuilder {
        void accept(ClassWriter cw);
    }

    private static void writeClass(ZipOutputStream zos, String internal, String superInternal,
                                    ClassBuilder body) throws IOException {
        ClassWriter cw = new ClassWriter(0);
        cw.visit(Opcodes.V1_8,
                Opcodes.ACC_PUBLIC,
                internal,
                /*signature*/ null,
                superInternal,
                /*interfaces*/ null);
        body.accept(cw);
        cw.visitEnd();
        zos.putNextEntry(new ZipEntry(internal + ".class"));
        zos.write(cw.toByteArray());
        zos.closeEntry();
    }
}
