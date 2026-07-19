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
    void indexExpansionAppliesTrailingVarargsPrefixFilter(@TempDir Path out) throws IOException {
        // "doFinal(byte[], ..)" fixes the first param and lets the tail vary: the
        // fixture's doFinal([B) and doFinal([BII) share the byte[] prefix and both
        // become wrappers, but the zero-arg doFinal() has fewer params than the
        // fixed prefix and must be dropped. Guards the fixed-prefix arity/pattern
        // check under trailing varargs (regression for the specs.size()-1 off-by-one).
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "doFinal",
                "Cipher",
                "call(public byte[] Cipher.doFinal(byte[], ..)) && target(c)",
                List.of(new ParameterDescriptor("Cipher", "c")),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out, idx);
        assertEquals(2, entries.size(),
                "byte[]-prefix must match the ([B) and ([BII) overloads, not the zero-arg ()");
        assertTrue(entries.stream().noneMatch(e -> e.isStatic),
                "doFinal is an instance method on every matched overload");
        assertTrue(entries.stream().allMatch(e -> e.originalParamFqn.get(0).equals("byte[]")),
                "every matched overload keeps byte[] as its fixed first param");
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

    @Test
    void literalFallbackEmitsStaticWrapperWithoutIndex(@TempDir Path out) throws IOException {
        // With NO AndroidClassIndex the emitter falls back to the descriptor's
        // literal types: expandCallTarget short-circuits (index == null), so the
        // whole wrapper must be materialized from the pointcut text alone. A plain
        // static target has to survive that path and resolve its simple names
        // ("Cipher", "String") through the descriptor imports — no android.jar is
        // consulted. This is the back-compat path unit tests without a fixture jar
        // rely on; if the fallback ever regressed to dropping static targets the
        // monitor would silently lose every getInstance event.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String))",
                List.of(),
                "result"));

        // Two-arg overload = the index-less back-compat entry point.
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);

        assertEquals(1, entries.size(), "static target must yield one literal-fallback wrapper");
        WrapperEmitter.WrapperEntry e = entries.get(0);
        assertTrue(e.isStatic, "the literal fallback always marks the target static");
        assertEquals("javax_crypto_Cipher_getInstance", e.wrapperName);
        assertEquals("javax.crypto.Cipher", e.originalClassFqn);
        assertEquals(List.of("java.lang.String"), e.originalParamFqn,
                "String must resolve to java.lang.String via the descriptor imports");
        assertEquals("javax.crypto.Cipher", e.originalReturnFqn);

        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(src.contains(
                        "public static javax.crypto.Cipher "
                                + "javax_crypto_Cipher_getInstance(java.lang.String p0)"),
                "static wrapper signature; got:\n" + src);
        assertTrue(src.contains(
                        "javax.crypto.Cipher result = javax.crypto.Cipher.getInstance(p0);"),
                "static wrapper delegates to Cls.method(args); got:\n" + src);
        assertTrue(src.contains("MultiSpec_1RuntimeMonitor.event(result);"),
                "monitor call receives the returning value; got:\n" + src);
        assertTrue(src.contains("return result;"),
                "non-void wrapper returns the original result; got:\n" + src);
    }

    @Test
    void literalFallbackSkipsInstanceTargetWithoutStaticModifier(@TempDir Path out)
            throws IOException {
        // No android.jar → no way to read ACC_STATIC from bytecode, so the
        // fallback trusts the lexical `static` modifier in the call() text. An
        // instance target (no `static` prefix) cannot be safely wrapped without
        // the index (the wrapper would need a receiver whose type the fallback
        // can't confirm), so it is dropped. Guards targetLooksStatic == false.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "doFinal",
                "Cipher",
                "call(public byte[] Cipher.doFinal(byte[]))",
                List.of(),
                "result"));
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);
        assertTrue(entries.isEmpty(),
                "instance target must be skipped by the index-less fallback");
    }

    @Test
    void literalFallbackSkipsAmbiguousObjectParam(@TempDir Path out) throws IOException {
        // The descriptor encodes an un-enumerable overload as a solitary Object
        // parameter; without the index the fallback cannot tell which concrete
        // Cipher.getInstance(String, ?) overload it means, so emitting
        // getInstance(String, Object) would not match any real method. A non-
        // leading Object param therefore vetoes the wrapper. Guards
        // hasAmbiguousObjectParam == true.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String, Object))",
                List.of(),
                "result"));
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);
        assertTrue(entries.isEmpty(),
                "a non-leading Object param must veto the literal-fallback wrapper");
    }

    @Test
    void literalFallbackSkipsMidListWildcardParam(@TempDir Path out) throws IOException {
        // A MIDDLE ".." (as opposed to a trailing one, which the parser folds into
        // the varargs flag) survives as a literal ParamSpec descriptor. It has no
        // finite lowering to a Java signature, so the fallback skips the whole
        // pointcut. Guards hasWildcardParamSpec == true while CallPC.varargs() is
        // false (the trailing "int" keeps varargs off).
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String, .., int))",
                List.of(),
                "result"));
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);
        assertTrue(entries.isEmpty(),
                "a mid-list '..' wildcard must veto the literal-fallback wrapper");
    }

    @Test
    void literalFallbackResolvesArrayAndPrimitiveTypes(@TempDir Path out) throws IOException {
        // resolveFqn has to peel "[]" suffixes, resolve the element type, and
        // reattach the array rank — and route primitives (byte, int) through the
        // primitive branch instead of the import table. A static target mixing a
        // reference type, an array, and a primitive exercises all three: array
        // return (byte[]), array param (byte[]) and primitive param (int) must
        // survive the fallback with their ranks and primitiveness intact.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static byte[] Cipher.getInstance(String, byte[], int))",
                List.of(),
                "result"));
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);

        assertEquals(1, entries.size());
        WrapperEmitter.WrapperEntry e = entries.get(0);
        assertEquals(List.of("java.lang.String", "byte[]", "int"), e.originalParamFqn,
                "array rank and primitive types must survive resolveFqn");
        assertEquals("byte[]", e.originalReturnFqn, "array return rank must be preserved");

        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(src.contains(
                        "public static byte[] javax_crypto_Cipher_getInstance("
                                + "java.lang.String p0, byte[] p1, int p2)"),
                "wrapper signature must carry array + primitive params; got:\n" + src);
        assertTrue(src.contains(
                        "byte[] result = javax.crypto.Cipher.getInstance(p0, p1, p2);"),
                "array-returning static call must delegate with all three args; got:\n" + src);
    }

    @Test
    void indexExpansionMatchesReturnSubtypePattern(@TempDir Path out) throws IOException {
        // A "Cipher+" return pattern (any subtype of Cipher) forces expansion and
        // routes the return type through the subtype branch of patternMatchesFqn:
        // getInstance returns javax.crypto.Cipher, which is assignable to Cipher,
        // so the String-arg overload still matches. Guards returnIsSubtypePattern
        // and index.isAssignableFrom on the return type.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher+ Cipher.getInstance(String))",
                List.of(),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out, idx);
        assertEquals(1, entries.size(),
                "return-subtype pattern must still resolve the String-arg overload");
        assertEquals(List.of("java.lang.String"), entries.get(0).originalParamFqn);
    }

    @Test
    void indexExpansionRejectsMidListVarargs(@TempDir Path out) throws IOException {
        // A MIDDLE ".." has no finite lowering, so expandCallTarget bails to an
        // empty list even with the index present; the literal fallback then also
        // vetoes it (mid-list wildcard). Net: zero wrappers. This is the
        // index-present twin of literalFallbackSkipsMidListWildcardParam, covering
        // the middle-".." early return inside expandCallTarget.
        AspectDescriptor d = newDescriptor(adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String, .., int))",
                List.of(),
                "result"));
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out, idx);
        assertTrue(entries.isEmpty(),
                "a mid-list '..' must produce no wrappers even with the index present");
    }

    @Test
    void forwardsAppImportsButFiltersAspectJRuntime(@TempDir Path out) throws IOException {
        // MonitorWrappers.java is compiled by monitor-builder against a classpath
        // that has android.jar + rv-monitor-rt + rvsec-agent — NOT the AspectJ /
        // JavaMOP / RV-Monitor runtime jars. So the descriptor's application
        // imports must be forwarded verbatim while every runtime import
        // (org.aspectj.*, javamoprt.*, rvmonitorrt.*, com.runtimeverification.*)
        // is dropped; a blank entry is skipped and the "import x.y.Z;" statement
        // form is normalized. Exercises isAspectJRuntimeImport's four prefixes and
        // the import-line stripping in generate().
        AdviceDescriptor advice = adviceAfterReturning(
                "getInstance",
                "Cipher",
                "call(public static Cipher Cipher.getInstance(String))",
                List.of(),
                "result");
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("Test");
        d.setImports(List.of(
                "javax.crypto.Cipher",
                "java.lang.String",
                "import javax.crypto.KeyGenerator;",     // statement form → normalized
                "",                                        // blank → skipped
                "org.aspectj.lang.JoinPoint",             // runtime → dropped
                "javamoprt.MOPLogging",                    // runtime → dropped
                "rvmonitorrt.map.RVMMap",                  // runtime → dropped
                "com.runtimeverification.rvmonitor.X"));   // runtime → dropped
        d.setAdvices(List.of(advice));

        WrapperEmitter.generate(d, out);
        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));

        assertTrue(src.contains("import javax.crypto.Cipher;"),
                "application import must be forwarded; got:\n" + src);
        assertTrue(src.contains("import javax.crypto.KeyGenerator;"),
                "statement-form import must be normalized and forwarded; got:\n" + src);
        assertFalse(src.contains("org.aspectj"),
                "AspectJ runtime import must be filtered out; got:\n" + src);
        assertFalse(src.contains("javamoprt"),
                "JavaMOP runtime import must be filtered out; got:\n" + src);
        assertFalse(src.contains("rvmonitorrt"),
                "RV-Monitor runtime import must be filtered out; got:\n" + src);
        assertFalse(src.contains("com.runtimeverification"),
                "RV runtime import must be filtered out; got:\n" + src);
    }

    @Test
    void instanceWrapperMapsTargetToRecvAndArgPositionally(@TempDir Path out) throws IOException {
        // For an instance target the receiver is materialized as "recv" and is NOT
        // one of the positional wrapper params (p0..pN). buildMonitorArgs must map
        // the advice's target(c) binding to "recv" WITHOUT advancing the positional
        // cursor, so the next binding args(input) still lands on p0 (not p1) and
        // the returning value maps to "result". A monitor call referencing all
        // three (c, input, result) proves the alignment end-to-end — an off-by-one
        // here would silently feed the monitor the wrong DEX registers.
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("doFinal");
        advice.setSpecName("Cipher");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setParameters(List.of(
                new ParameterDescriptor("Cipher", "c"),
                new ParameterDescriptor("byte[]", "input")));
        advice.setReturning(List.of(new ParameterDescriptor("byte[]", "result")));
        advice.setExpression(
                "call(public byte[] Cipher.doFinal(byte[])) && target(c) && args(input)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.event");
        mc.setSpecName("Cipher");
        mc.setEventId("event");
        mc.setUniqueId("event");
        mc.setArgs(List.of("c", "input", "result"));
        advice.setMonitorCalls(List.of(mc));

        AspectDescriptor d = newDescriptor(advice);
        AndroidClassIndex idx = new AndroidClassIndex(androidJar);
        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out, idx);
        assertEquals(1, entries.size(), "byte[]-arg doFinal has exactly one overload");
        assertFalse(entries.get(0).isStatic, "doFinal is an instance method");

        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(src.contains("javax.crypto.Cipher recv, byte[] p0"),
                "receiver is recv and the single arg is p0; got:\n" + src);
        assertTrue(src.contains("MultiSpec_1RuntimeMonitor.event(recv, p0, result);"),
                "target→recv, args→p0 (not p1), returning→result; got:\n" + src);
    }

    @Test
    void voidTargetEmitsWrapperWithoutResultCapture(@TempDir Path out) throws IOException {
        // Void-returning targets are common monitored operations (Mac.update,
        // MessageDigest.update, ...). Their wrapper must NOT declare a `result`
        // local or a `return` — it just calls the original and fires the monitor.
        // A plain `after` (no returning clause) also drives the
        // getReturning() == null branch in buildMonitorArgs. Modeled on the
        // static void Security.setProperty via the index-less literal fallback.
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("setProperty");
        advice.setSpecName("Security");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setParameters(List.of(
                new ParameterDescriptor("String", "k"),
                new ParameterDescriptor("String", "v")));
        advice.setReturning(null);
        advice.setExpression(
                "call(public static void Security.setProperty(String, String)) && args(k, v)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.event");
        mc.setSpecName("Security");
        mc.setEventId("event");
        mc.setUniqueId("event");
        mc.setArgs(List.of("k", "v"));
        advice.setMonitorCalls(List.of(mc));

        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("Test");
        d.setImports(List.of("java.security.Security", "java.lang.String"));
        d.setAdvices(List.of(advice));

        List<WrapperEmitter.WrapperEntry> entries = WrapperEmitter.generate(d, out);
        assertEquals(1, entries.size());
        assertEquals("void", entries.get(0).originalReturnFqn);

        String src = Files.readString(out.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(src.contains("java.security.Security.setProperty(p0, p1);"),
                "void wrapper delegates without capturing a result; got:\n" + src);
        assertFalse(src.contains("result ="),
                "void wrapper must not declare a result local; got:\n" + src);
        assertFalse(src.contains("return result"),
                "void wrapper must not return a result; got:\n" + src);
        assertTrue(src.contains("MultiSpec_1RuntimeMonitor.event(p0, p1);"),
                "monitor call maps args positionally to p0, p1; got:\n" + src);
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
