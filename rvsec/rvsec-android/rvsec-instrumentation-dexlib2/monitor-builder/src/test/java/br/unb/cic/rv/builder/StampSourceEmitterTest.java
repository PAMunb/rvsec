package br.unb.cic.rv.builder;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** The handler-stamp source: emitted, removed, and compilable against android.jar alone. */
class StampSourceEmitterTest {

    private static Path androidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return null;
        Path jar = Path.of(home, "platforms", "android-30", "android.jar");
        return Files.isRegularFile(jar) ? jar : null;
    }

    static boolean canCompile() {
        return androidJar() != null
                && Files.isExecutable(Path.of(System.getProperty("java.home"), "bin", "javac"));
    }

    @Test
    void emitWritesTheStampClassUnderMop(@TempDir Path dir) throws Exception {
        Path file = StampSourceEmitter.emit(dir);
        assertEquals(dir.resolve("mop").resolve("RvsecStamp.java"), file);
        String src = Files.readString(file);
        assertTrue(src.contains("package mop;"));
        assertTrue(src.contains("public static void setOnClickListener(View v, View.OnClickListener l)"));
        assertTrue(src.contains("public static void composeNode(Object infoCompat, Object semanticsNode)"));
    }

    @Test
    void removeDeletesTheSourceAndOnlyTheStampClasses(@TempDir Path dir) throws Exception {
        Path src = dir.resolve("src");
        Path classes = dir.resolve("classes");
        StampSourceEmitter.emit(src);
        Files.createDirectories(classes.resolve("mop"));
        for (String n : List.of("RvsecStamp.class", "RvsecStamp$Delegate.class", "Coverage.class",
                "RvsecStampOther.class")) {
            Files.createFile(classes.resolve("mop").resolve(n));
        }

        StampSourceEmitter.remove(src, classes);

        assertFalse(Files.exists(src.resolve("mop").resolve("RvsecStamp.java")));
        assertFalse(Files.exists(classes.resolve("mop").resolve("RvsecStamp.class")));
        assertFalse(Files.exists(classes.resolve("mop").resolve("RvsecStamp$Delegate.class")));
        assertTrue(Files.exists(classes.resolve("mop").resolve("Coverage.class")));
        assertTrue(Files.exists(classes.resolve("mop").resolve("RvsecStampOther.class")));
        StampSourceEmitter.remove(dir.resolve("absent"), dir.resolve("absent"));
    }

    @Test
    @EnabledIf("canCompile")
    void theSourceCompilesAgainstAndroidJarAtJava8(@TempDir Path dir) throws Exception {
        Path file = StampSourceEmitter.emit(dir.resolve("src"));
        Path out = Files.createDirectories(dir.resolve("out"));
        Process p = new ProcessBuilder(
                Path.of(System.getProperty("java.home"), "bin", "javac").toString(),
                "-source", "1.8", "-target", "1.8", "-Xlint:-options",
                "-d", out.toString(), "-classpath", androidJar().toString(), file.toString())
                .redirectErrorStream(true).start();
        String output = new String(p.getInputStream().readAllBytes());
        assertEquals(0, p.waitFor(), output);
        assertTrue(Files.exists(out.resolve("mop").resolve("RvsecStamp.class")));
        assertTrue(Files.exists(out.resolve("mop").resolve("RvsecStamp$Delegate.class")));
    }
}
