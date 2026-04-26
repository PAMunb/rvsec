package br.unb.cic.rv.validator;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link BaksmaliDiffer}.
 *
 * <p>Each test builds two synthetic single-class DEX files (one "ajc-side",
 * one "dexlib2-side"), packs each into a ZIP-shaped APK with a single
 * {@code classes.dex} entry, writes a minimal descriptor JSON, and asserts on
 * the {@link Report} fields. No $ANDROID_HOME / android.jar / external APK
 * dependency.
 */
class BaksmaliDifferTest {

    private static final String CALLER_CLASS = "LFoo;";
    private static final String CALLER_METHOD = "bar";

    private static final MethodReference MD_EVENT = new ImmutableMethodReference(
            "Lmop/MultiSpec_1RuntimeMonitor;",
            "MessageDigestSpec_g4Event",
            List.of("Ljava/lang/String;"),
            "V");
    private static final MethodReference CIPHER_EVENT = new ImmutableMethodReference(
            "Lmop/MultiSpec_1RuntimeMonitor;",
            "CipherSpec_g1Event",
            List.of("Ljava/lang/String;"),
            "V");
    private static final MethodReference CIPHER_WRAPPER = new ImmutableMethodReference(
            "Lmop/MonitorWrappers;",
            "javax_crypto_Cipher_doFinal",
            List.of("Ljavax/crypto/Cipher;", "[B"),
            "[B");

    @Test
    void bothPipelinesEmitSameHooks(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectory(tmp.resolve("ajc"));
        Path dexlibDir = Files.createDirectory(tmp.resolve("dexlib2"));
        // Both pipelines emit the SAME inline runtime-monitor invoke.
        DexFile sameDex = oneClass(invokeStatic(MD_EVENT));
        writeApk(ajcDir.resolve("a.apk"), sameDex);
        writeApk(dexlibDir.resolve("a.apk"), sameDex);

        Path desc = writeMinimalDescriptor(tmp.resolve("desc.json"), List.of());

        Report r = BaksmaliDiffer.diff(ajcDir, dexlibDir, desc);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(1, r.metrics.get("totalApkPairs"));
        assertEquals(1, r.metrics.get("apksWithFullRecall"));
        Map<?, ?> agg = (Map<?, ?>) r.metrics.get("aggregateRecallBySpec");
        assertEquals(1.0, ((Number) agg.get("MessageDigestSpec")).doubleValue(), 1e-9);
        // Optional: dump the JSON report for manual inspection (no assertion).
        // Enabled when -DdumpLayer1Sample=<path> is set on the JVM.
        String dumpPath = System.getProperty("dumpLayer1Sample");
        if (dumpPath != null) r.write(Path.of(dumpPath));
    }

    @Test
    void dexlib2MissesOneSpec(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectory(tmp.resolve("ajc"));
        Path dexlibDir = Files.createDirectory(tmp.resolve("dexlib2"));
        // ajc fires both MessageDigestSpec AND CipherSpec; dexlib2 only fires
        // MessageDigestSpec, so recall(CipherSpec)=0.0 and the gate fails.
        DexFile ajcDex = oneClass(invokeStatic(MD_EVENT), invokeStatic(CIPHER_EVENT));
        DexFile dexlibDex = oneClass(invokeStatic(MD_EVENT));
        writeApk(ajcDir.resolve("a.apk"), ajcDex);
        writeApk(dexlibDir.resolve("a.apk"), dexlibDex);

        Path desc = writeMinimalDescriptor(tmp.resolve("desc.json"), List.of());

        Report r = BaksmaliDiffer.diff(ajcDir, dexlibDir, desc);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        assertEquals(1, r.metrics.get("totalApkPairs"));
        assertEquals(0, r.metrics.get("apksWithFullRecall"));
        Map<?, ?> agg = (Map<?, ?>) r.metrics.get("aggregateRecallBySpec");
        assertEquals(1.0, ((Number) agg.get("MessageDigestSpec")).doubleValue(), 1e-9);
        assertEquals(0.0, ((Number) agg.get("CipherSpec")).doubleValue(), 1e-9);
    }

    @Test
    void wrapperHookCountsTowardSpec(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectory(tmp.resolve("ajc"));
        Path dexlibDir = Files.createDirectory(tmp.resolve("dexlib2"));
        // ajc emits the inline CipherSpec event; dexlib2 routes through the
        // MonitorWrappers static — both must count as the same hook.
        DexFile ajcDex    = oneClass(invokeStatic(CIPHER_EVENT));
        DexFile dexlibDex = oneClass(invokeStatic(CIPHER_WRAPPER));
        writeApk(ajcDir.resolve("a.apk"), ajcDex);
        writeApk(dexlibDir.resolve("a.apk"), dexlibDex);

        // Descriptor with one after-advice on Cipher.doFinal whose monitorCalls
        // fires CipherSpec_g1Event — this teaches BaksmaliDiffer that the
        // wrapper "javax_crypto_Cipher_doFinal" attributes to CipherSpec.
        Path desc = writeMinimalDescriptor(tmp.resolve("desc.json"),
                List.of(advice(
                        "after",
                        "call(* javax.crypto.Cipher.doFinal(..)) && args(input)",
                        "CipherSpec_g1Event")));

        Report r = BaksmaliDiffer.diff(ajcDir, dexlibDir, desc);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        Map<?, ?> agg = (Map<?, ?>) r.metrics.get("aggregateRecallBySpec");
        assertEquals(1.0, ((Number) agg.get("CipherSpec")).doubleValue(), 1e-9);
    }

    // --- fixture builders ----------------------------------------------------

    /**
     * Build a synthetic 1-class DEX whose only method ({@code Foo.bar()V})
     * contains the supplied invoke instructions followed by a return-void.
     * Two virtual registers are reserved (v0, v1) — enough for invoke-static
     * with up to 2 args; the synthetic invokes use unused register slots so
     * the DEX verifies cleanly.
     */
    private static DexFile oneClass(ImmutableInstruction35c... invokes) {
        var instructions = new java.util.ArrayList<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction>();
        Collections.addAll(instructions, invokes);
        instructions.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4,
                instructions,
                Collections.emptyList(),
                Collections.emptyList());
        ImmutableMethod method = new ImmutableMethod(
                CALLER_CLASS, CALLER_METHOD,
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef cls = new ImmutableClassDef(
                CALLER_CLASS, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(method));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(cls));
    }

    /**
     * Construct an {@code invoke-static} (Format35c) targeting {@code mr} with
     * one register argument at v0. Sufficient for tests — the validator only
     * inspects the opcode and the reference, not the register list.
     */
    private static ImmutableInstruction35c invokeStatic(MethodReference mr) {
        int regCount = mr.getParameterTypes().size();
        // Cap at 5 (Format35c's max) — none of our test refs cross that.
        if (regCount > 5) regCount = 5;
        return new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC,
                regCount,
                /*c=*/ 0, /*d=*/ 1, /*e=*/ 2, /*f=*/ 3, /*g=*/ 4,
                mr);
    }

    /** Pack a DEX into a ZIP-shaped APK with a single {@code classes.dex} entry. */
    private static void writeApk(Path apk, DexFile dex) throws IOException {
        Path tmpDex = Files.createTempFile("classes", ".dex");
        try {
            DexPool.writeTo(tmpDex.toString(), dex);
            try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(apk));
                 InputStream in = Files.newInputStream(tmpDex)) {
                zos.putNextEntry(new ZipEntry("classes.dex"));
                in.transferTo(zos);
                zos.closeEntry();
            }
        } finally {
            Files.deleteIfExists(tmpDex);
        }
    }

    /**
     * Write a minimal AspectDescriptor JSON (only the fields BaksmaliDiffer
     * reads). The descriptor's {@code imports} are left empty because the
     * tests use FQNs in their pointcut expressions ({@code javax.crypto.Cipher}
     * not {@code Cipher}).
     */
    private static Path writeMinimalDescriptor(Path path, List<Map<String, Object>> advices)
            throws IOException {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("aspectName", "MultiSpec_1MonitorAspect");
        root.put("fileName", "MultiSpec_1MonitorAspect.aj");
        root.put("shortName", "MultiSpec_1");
        root.put("package", "package mop;");
        root.put("imports", List.of());
        root.put("commonPointcut", "");
        root.put("baseAspectExclusions", List.of());
        root.put("advices", advices);
        new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(path.toFile(), root);
        return path;
    }

    private static Map<String, Object> advice(String position, String expression,
                                              String monitorMethod) {
        Map<String, Object> a = new LinkedHashMap<>();
        a.put("name", "a1");
        a.put("specName", "TestSpec");
        a.put("parameters", List.of());
        a.put("position", position);
        a.put("isAround", false);
        a.put("returnType", "void");
        a.put("returning", null);
        a.put("throwing", null);
        a.put("expression", expression);
        Map<String, Object> mc = new LinkedHashMap<>();
        mc.put("method", monitorMethod);
        mc.put("specName", "TestSpec");
        mc.put("eventId", "g1");
        mc.put("uniqueId", "u1");
        mc.put("args", List.of());
        mc.put("countCond", null);
        a.put("monitorCalls", List.of(mc));
        return a;
    }
}
