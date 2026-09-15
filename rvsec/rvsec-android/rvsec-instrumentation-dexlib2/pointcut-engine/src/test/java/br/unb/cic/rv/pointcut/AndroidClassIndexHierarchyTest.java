package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link AndroidClassIndex#exists} and {@link AndroidClassIndex#methodsInHierarchy} against a real
 * {@code android.jar} resolved from {@code ANDROID_HOME}; skipped when none is available.
 */
class AndroidClassIndexHierarchyTest {

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
    void declaredMethodIsReturnedFromTheClassItself() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        List<AndroidClassIndex.MethodInfo> found =
                index.methodsInHierarchy("javax.crypto.Cipher", "doFinal", false);
        assertFalse(found.isEmpty());
        assertEquals(index.methods("javax.crypto.Cipher", "doFinal", false).size(), found.size());
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void inheritedMethodIsFoundThroughAnInterface() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        assertTrue(index.methods("javax.crypto.SecretKey", "getEncoded", false).isEmpty(),
                "SecretKey does not redeclare getEncoded");
        List<AndroidClassIndex.MethodInfo> found =
                index.methodsInHierarchy("javax.crypto.SecretKey", "getEncoded", false);
        assertEquals(1, found.size());
        assertEquals("()[B", found.get(0).descriptor);
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void unknownClassYieldsEmptyAndFalse() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        assertTrue(index.methodsInHierarchy("does.not.Exist", "anything", false).isEmpty());
        assertTrue(index.methodsInHierarchy("javax.crypto.SecretKey", "noSuchMethod", false).isEmpty());
        assertFalse(index.exists("does/not/Exist"));
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void existsTakesInternalNamesWithDollar() {
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        assertTrue(index.exists("java/security/KeyStore"));
        assertTrue(index.exists("java/security/KeyStore$ProtectionParameter"));
        assertFalse(index.exists("java/security/KeyStore/ProtectionParameter"));
        assertFalse(index.exists(""));
        assertFalse(index.exists(null));
    }

    @Test
    void missingJarDegradesToEmptyAndFalse() {
        AndroidClassIndex index = new AndroidClassIndex(Path.of("/tmp/definitely-not-here.jar"));
        assertTrue(index.methodsInHierarchy("javax.crypto.SecretKey", "getEncoded", false).isEmpty());
        assertFalse(index.exists("java/security/KeyStore"));
    }
}
