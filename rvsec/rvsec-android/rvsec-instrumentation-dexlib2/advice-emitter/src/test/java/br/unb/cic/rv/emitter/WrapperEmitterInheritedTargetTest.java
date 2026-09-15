package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.AndroidClassIndex;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * A wrapper target whose owner inherits the method from a framework ancestor
 * without redeclaring it is wrapped under the owner written in the pointcut, and
 * a target that resolves to no method is counted (INV-INS-160).
 *
 * <p>{@code javax.crypto.SecretKey} declares no {@code getEncoded()}; the method is
 * declared by {@code java.security.Key}. The tests read the real {@code android.jar}
 * (highest API level under {@code ANDROID_HOME/platforms}) because the hierarchy
 * is the subject, and are skipped when none is present.
 */
class WrapperEmitterInheritedTargetTest {

    private static Path androidJar;

    @BeforeAll
    static void resolveAndroidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return;
        Path platforms = Path.of(home, "platforms");
        if (!Files.isDirectory(platforms)) return;
        try (Stream<Path> levels = Files.list(platforms)) {
            androidJar = levels
                    .filter(Files::isDirectory)
                    .map(p -> p.resolve("android.jar"))
                    .filter(Files::isRegularFile)
                    .max((a, b) -> a.getParent().getFileName().toString()
                            .compareTo(b.getParent().getFileName().toString()))
                    .orElse(null);
        } catch (IOException ex) {
            androidJar = null;
        }
    }

    static boolean hasAndroidJar() {
        return androidJar != null;
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void anInheritedMethodIsWrappedUnderThePatternOwner(@TempDir Path out) throws IOException {
        WrapperEmitter.EmitResult result = WrapperEmitter.generate(
                descriptor(getEncoded("SecretKeySpec", "e1", "SecretKey+")), out,
                new AndroidClassIndex(androidJar));

        assertEquals(1, result.wrappers().size());
        WrapperEmitter.WrapperEntry e = result.wrappers().get(0);
        assertEquals("javax.crypto.SecretKey", e.originalClassFqn,
                "the wrapper's owner is the type written at the call site, not the "
                        + "ancestor that declares the method");
        assertFalse(e.isStatic);
        assertEquals("()[B", descriptorOf(e), "the inherited signature Key.getEncoded()");
        assertEquals(0, result.wrapperTargetsUnresolved());
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void anInheritedMethodOnAFrameworkInterfaceIsWrapped(@TempDir Path out) throws IOException {
        WrapperEmitter.EmitResult result = WrapperEmitter.generate(
                descriptor(getEncoded("SecretKeySpec", "e1", "SecretKey+"),
                        getEncoded("KeySpec", "ge1", "Key+")),
                out, new AndroidClassIndex(androidJar));
        String source = Files.readString(out.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));

        String secretKeyWrapper = wrapperMethod(source, "(javax.crypto.SecretKey recv)");
        assertTrue(secretKeyWrapper.contains("MultiSpec_1RuntimeMonitor.SecretKeySpec_e1Event(recv, result);"),
                "the SecretKey wrapper fires the SecretKey+ advice:\n" + source);
        assertTrue(secretKeyWrapper.contains("MultiSpec_1RuntimeMonitor.KeySpec_ge1Event(recv, result);"),
                "the SecretKey wrapper also fires the Key+ advice, whose pattern admits "
                        + "SecretKey:\n" + source);
        assertTrue(secretKeyWrapper.indexOf("SecretKeySpec_e1Event")
                        < secretKeyWrapper.indexOf("KeySpec_ge1Event"),
                "merged advices keep descriptor order:\n" + source);

        String keyWrapper = wrapperMethod(source, "(java.security.Key recv)");
        assertTrue(keyWrapper.contains("KeySpec_ge1Event("), "the Key wrapper fires Key+:\n" + source);
        assertFalse(keyWrapper.contains("SecretKeySpec_e1Event("),
                "SecretKey+ does not admit Key:\n" + source);
        assertEquals(0, result.wrapperTargetsUnresolved());
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void aTargetNoAncestorDeclaresIsCounted(@TempDir Path out) throws IOException {
        AdviceDescriptor missing = getEncoded("SecretKeySpec", "e9", "SecretKey+");
        missing.setExpression("call(public byte[] SecretKey+.noSuchMethod()) && target(k)");

        WrapperEmitter.EmitResult result = WrapperEmitter.generate(
                descriptor(missing), out, new AndroidClassIndex(androidJar));

        assertTrue(result.wrappers().isEmpty(), "no method to wrap, no wrapper");
        assertEquals(1, result.wrapperTargetsUnresolved(),
                "the dropped wrapper target is counted");
    }

    private static AdviceDescriptor getEncoded(String spec, String event, String ownerPattern) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(spec + "_" + event);
        a.setSpecName(spec);
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(List.of(new ParameterDescriptor("Key", "k")));
        a.setReturning(List.of(new ParameterDescriptor("byte[]", "material")));
        a.setExpression("call(public byte[] " + ownerPattern + ".getEncoded()) && target(k)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + spec + "_" + event + "Event");
        mc.setSpecName(spec);
        mc.setEventId(event);
        mc.setUniqueId(event);
        mc.setArgs(List.of("k", "material"));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static AspectDescriptor descriptor(AdviceDescriptor... advices) {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("Test");
        d.setImports(List.of("javax.crypto.SecretKey", "java.security.Key"));
        d.setAdvices(List.of(advices));
        return d;
    }

    private static String wrapperMethod(String source, String paramList) {
        int start = source.indexOf(paramList + " throws Exception {");
        assertTrue(start >= 0, "no wrapper with parameters " + paramList + ":\n" + source);
        return source.substring(start, source.indexOf("\n    }\n", start));
    }

    /** Method descriptor of the wrapped call, primitives and arrays only as the test needs. */
    private static String descriptorOf(WrapperEmitter.WrapperEntry e) {
        StringBuilder sb = new StringBuilder("(");
        for (String p : e.originalParamFqn) sb.append(typeDescriptor(p));
        return sb.append(')').append(typeDescriptor(e.originalReturnFqn)).toString();
    }

    private static String typeDescriptor(String fqn) {
        if (fqn.endsWith("[]")) return "[" + typeDescriptor(fqn.substring(0, fqn.length() - 2));
        return switch (fqn) {
            case "byte" -> "B";
            case "int" -> "I";
            case "void" -> "V";
            default -> "L" + fqn.replace('.', '/') + ";";
        };
    }
}
