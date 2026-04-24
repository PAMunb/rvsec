package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests depend on a real {@code android.jar} to parse real-world type hierarchies.
 * The jar is resolved via {@code ANDROID_HOME} environment variable (picking the
 * highest API level that ships an {@code android.jar}). When the env var is
 * unset or no jar is found, the tests are skipped rather than failing — this
 * mirrors the behavior of the legacy prototype's tests which needed the same
 * setup.
 */
class AndroidClassIndexTest {

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
    void cipherGetInstanceReturnsOverloads() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        List<AndroidClassIndex.MethodInfo> overloads =
                index.staticMethods("javax.crypto.Cipher", "getInstance");
        assertFalse(overloads.isEmpty(),
                "Cipher.getInstance overloads must be found in android.jar at " + androidJar);
        // Standard Android API ships at least the 3 overloads:
        //   getInstance(String), getInstance(String, String), getInstance(String, Provider)
        assertTrue(overloads.size() >= 3,
                "expected ≥3 getInstance overloads, got " + overloads.size()
                        + " in " + androidJar);
        assertTrue(overloads.stream().allMatch(m -> m.isStatic()),
                "all staticMethods() results must be ACC_STATIC");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void objectIsSupertypeOfEverything() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        assertTrue(index.isAssignableFrom("java.lang.Object", "javax.crypto.Cipher"));
        assertTrue(index.isAssignableFrom("java.lang.Object", "java.util.ArrayList"));
        assertFalse(index.isAssignableFrom("java.lang.Object", "int"),
                "primitives are not assignable to Object");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void listIsAssignableFromArrayList() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        assertTrue(index.isAssignableFrom("java.util.List", "java.util.ArrayList"));
        assertFalse(index.isAssignableFrom("java.util.ArrayList", "java.util.List"),
                "List is not assignable from its interface");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void missingClassReturnsEmptyResults() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        List<AndroidClassIndex.MethodInfo> result =
                index.staticMethods("does.not.Exist", "anything");
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void missingJarDegradesToEmptyResults() {
        // Constructing with a non-existent path must not throw; queries return empty.
        Path bogus = Path.of("/tmp/definitely-not-here.jar");
        assertFalse(Files.exists(bogus));
        AndroidClassIndex index = new AndroidClassIndex(bogus);
        assertTrue(index.staticMethods("javax.crypto.Cipher", "getInstance").isEmpty());
        assertFalse(index.isAssignableFrom("java.util.List", "java.util.ArrayList"));
    }
}
