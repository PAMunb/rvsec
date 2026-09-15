package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.AndroidClassIndex;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import javax.crypto.KeyAgreement;
import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.InvalidKeyException;
import java.security.Key;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * A plain {@code after} advice runs when the wrapped call returns and when it
 * throws, and the throwable is rethrown unchanged (INV-INS-163).
 *
 * <p>The generated wrapper source is checked for its shape, then compiled with the
 * running JDK's {@code javac} against a stub monitor and executed on JDK classes,
 * which proves the handler compiles under the wrapper's {@code throws Exception}
 * and that a throwing call reaches the monitor. The DEX the monitor builder makes
 * from the same source is checked on an instrumented APK.
 */
class WrapperAfterFinallyShapeTest {

    private static final String STUB_MONITOR = """
            package mop;

            public final class MultiSpec_1RuntimeMonitor {
                public static final java.util.List<String> CALLS = new java.util.ArrayList<>();

                public static void KeyAgreementSpec_gsEvent(javax.crypto.KeyAgreement ka,
                                                            java.security.Key k) {
                    CALLS.add("gs");
                }

                public static void KeyAgreementSpec_dophaseEvent(java.security.Key pubKey,
                                                                 boolean lastPhase,
                                                                 javax.crypto.KeyAgreement ka) {
                    CALLS.add("dophase:" + pubKey + "," + lastPhase + "," + (ka != null));
                }

                public static void MessageDigestSpec_updateEvent(java.security.MessageDigest md,
                                                                 byte[] input) {
                    CALLS.add("update:" + (input == null ? "null" : input.length));
                }
            }
            """;

    @Test
    void aPlainAfterAdviceRunsOnBothPathsAndRethrows(@TempDir Path out) throws Exception {
        AndroidClassIndex index = new AndroidClassIndex(EmitterTestFixtures.writeClassJar(
                out.resolve("android-fixture.jar"), Map.of(
                        "javax/crypto/KeyAgreement",
                        List.of("doPhase (Ljava/security/Key;Z)Ljava/security/Key;"),
                        "java/security/MessageDigest",
                        List.of("update ([B)V"))));
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(dophaseReturning(), dophase(), update()));

        WrapperEmitter.EmitResult result = WrapperEmitter.generate(descriptor, out, index);
        assertEquals(2, result.wrappers().size());
        String source = Files.readString(out.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));

        assertTrue(source.contains("""
                    public static java.security.Key javax_crypto_KeyAgreement_doPhase(\
                javax.crypto.KeyAgreement recv, java.security.Key p0, boolean p1) throws Exception {
                        java.security.Key result;
                        try {
                            result = recv.doPhase(p0, p1);
                        } catch (Throwable t) {
                            MultiSpec_1RuntimeMonitor.KeyAgreementSpec_dophaseEvent(p0, p1, recv);
                            throw t;
                        }
                        MultiSpec_1RuntimeMonitor.KeyAgreementSpec_gsEvent(recv, result);
                        MultiSpec_1RuntimeMonitor.KeyAgreementSpec_dophaseEvent(p0, p1, recv);
                        return result;
                    }
                """),
                "the call is guarded by a catch-all handler that fires only the plain after "
                        + "advice with the normal path's bound arguments and rethrows; the "
                        + "normal path fires every advice in descriptor order:\n" + source);
        assertTrue(source.contains("""
                    public static void java_security_MessageDigest_update(\
                java.security.MessageDigest recv, byte[] p0) throws Exception {
                        try {
                            recv.update(p0);
                        } catch (Throwable t) {
                            MultiSpec_1RuntimeMonitor.MessageDigestSpec_updateEvent(recv, p0);
                            throw t;
                        }
                        MultiSpec_1RuntimeMonitor.MessageDigestSpec_updateEvent(recv, p0);
                    }
                """),
                "a void call has no result local and no return:\n" + source);

        Path classes = compile(out, source);
        try (URLClassLoader loader = new URLClassLoader(new URL[]{classes.toUri().toURL()},
                getClass().getClassLoader())) {
            Class<?> wrappers = loader.loadClass("mop.MonitorWrappers");
            @SuppressWarnings("unchecked")
            List<String> calls = (List<String>) loader.loadClass("mop.MultiSpec_1RuntimeMonitor")
                    .getField("CALLS").get(null);

            Method doPhase = wrappers.getMethod("javax_crypto_KeyAgreement_doPhase",
                    KeyAgreement.class, Key.class, boolean.class);
            KeyAgreement uninitialised = KeyAgreement.getInstance("DH");
            Throwable fromCall = assertThrows(InvocationTargetException.class,
                    () -> doPhase.invoke(null, uninitialised, null, true)).getCause();
            assertInstanceOf(InvalidKeyException.class, fromCall,
                    "the checked exception of the call propagates unchanged");
            assertEquals(List.of("dophase:null,true,true"), calls,
                    "a throwing call fires the plain after advice once, and not the "
                            + "returning one");

            calls.clear();
            Method update = wrappers.getMethod("java_security_MessageDigest_update",
                    MessageDigest.class, byte[].class);
            update.invoke(null, MessageDigest.getInstance("SHA-256"), new byte[]{1, 2, 3});
            assertEquals(List.of("update:3"), calls, "a returning call fires the advice once");

            calls.clear();
            Throwable fromNull = assertThrows(InvocationTargetException.class,
                    () -> update.invoke(null, MessageDigest.getInstance("SHA-256"), null))
                    .getCause();
            assertInstanceOf(NullPointerException.class, fromNull);
            assertEquals(List.of("update:null"), calls,
                    "a throwing void call fires the advice once, from the handler");
        }
    }

    private static Path compile(Path out, String wrapperSource) throws IOException {
        Path src = out.resolve("src/mop");
        Files.createDirectories(src);
        Files.writeString(src.resolve("MonitorWrappers.java"), wrapperSource);
        Files.writeString(src.resolve("MultiSpec_1RuntimeMonitor.java"), STUB_MONITOR);
        Path classes = Files.createDirectories(out.resolve("classes"));
        JavaCompiler javac = ToolProvider.getSystemJavaCompiler();
        assertNotNull(javac, "tests run on a JDK");
        ByteArrayOutputStream diagnostics = new ByteArrayOutputStream();
        int rc = javac.run(null, diagnostics, diagnostics, "-d", classes.toString(),
                src.resolve("MonitorWrappers.java").toString(),
                src.resolve("MultiSpec_1RuntimeMonitor.java").toString());
        assertEquals(0, rc, "the generated wrapper source compiles:\n" + diagnostics);
        return classes;
    }

    /** {@code after(KeyAgreement ka) returning(Key k)} over {@code doPhase}. */
    private static AdviceDescriptor dophaseReturning() {
        AdviceDescriptor a = advice("KeyAgreementSpec_gs",
                List.of(new ParameterDescriptor("KeyAgreement", "ka")),
                "call(public java.security.Key javax.crypto.KeyAgreement.doPhase("
                        + "java.security.Key, boolean)) && target(ka)",
                "KeyAgreementSpec_gsEvent", List.of("ka", "k"));
        a.setReturning(List.of(new ParameterDescriptor("Key", "k")));
        return a;
    }

    /** Plain {@code after(Key pubKey, boolean lastPhase, KeyAgreement ka)} over {@code doPhase}. */
    private static AdviceDescriptor dophase() {
        return advice("KeyAgreementSpec_dophase",
                List.of(new ParameterDescriptor("Key", "pubKey"),
                        new ParameterDescriptor("boolean", "lastPhase"),
                        new ParameterDescriptor("KeyAgreement", "ka")),
                "call(public java.security.Key javax.crypto.KeyAgreement.doPhase("
                        + "java.security.Key, boolean)) && args(pubKey, lastPhase) && target(ka)",
                "KeyAgreementSpec_dophaseEvent", List.of("pubKey", "lastPhase", "ka"));
    }

    /** Plain {@code after(MessageDigest md, byte[] input)} over the void {@code update}. */
    private static AdviceDescriptor update() {
        return advice("MessageDigestSpec_update",
                List.of(new ParameterDescriptor("MessageDigest", "md"),
                        new ParameterDescriptor("byte[]", "input")),
                "call(public void java.security.MessageDigest.update(byte[])) "
                        + "&& target(md) && args(input)",
                "MessageDigestSpec_updateEvent", List.of("md", "input"));
    }

    private static AdviceDescriptor advice(String name, List<ParameterDescriptor> params,
                                           String expression, String event, List<String> args) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName(name.substring(0, name.indexOf('_')));
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(params);
        a.setExpression(expression);
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + event);
        mc.setSpecName(a.getSpecName());
        mc.setEventId(event);
        mc.setUniqueId(event);
        mc.setArgs(args);
        a.setMonitorCalls(List.of(mc));
        return a;
    }
}
