package br.unb.cic.rv.builder;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Emits the {@code mop/RvsecStamp.java} runtime class source consumed by
 * {@link MonitorBuilder}: the handler stamp the weaver routes
 * {@code View.setOnClickListener}, {@code View.setOnLongClickListener} and
 * {@code View.setAccessibilityDelegate} call sites to.
 *
 * <p>The source is a fixed resource of this module, compiled with the monitor
 * sources against {@code android.jar} and nothing else, so it is identical for
 * every specification set. It emits no monitor event.
 *
 * <p>The monitor source directory and the build directory are shared by every
 * APK of a batch, so a run without the stamp MUST call {@link #remove} to keep
 * a source or class file left there by an earlier run with the stamp out of
 * the monitor DEX.
 */
public final class StampSourceEmitter {

    public static final String STAMP_PACKAGE = "mop";
    public static final String STAMP_CLASS = "RvsecStamp";
    private static final String RESOURCE = "stamp/" + STAMP_CLASS + ".java";

    private StampSourceEmitter() {}

    /**
     * Write {@code mop/RvsecStamp.java} under {@code outputDir}.
     *
     * @return the written file
     */
    public static Path emit(Path outputDir) throws IOException {
        Path dir = outputDir.resolve(STAMP_PACKAGE);
        Files.createDirectories(dir);
        Path file = dir.resolve(STAMP_CLASS + ".java");
        Files.writeString(file, sourceText());
        return file;
    }

    /**
     * Delete the stamp source under {@code sourceDir} and the stamp class files
     * (the class and its nested classes) under {@code classesDir}, when present.
     */
    public static void remove(Path sourceDir, Path classesDir) throws IOException {
        Files.deleteIfExists(sourceDir.resolve(STAMP_PACKAGE).resolve(STAMP_CLASS + ".java"));
        Path pkg = classesDir.resolve(STAMP_PACKAGE);
        if (!Files.isDirectory(pkg)) return;
        try (DirectoryStream<Path> classes = Files.newDirectoryStream(pkg, STAMP_CLASS + "*.class")) {
            for (Path c : classes) {
                String name = c.getFileName().toString();
                if (name.equals(STAMP_CLASS + ".class") || name.startsWith(STAMP_CLASS + "$")) {
                    Files.delete(c);
                }
            }
        }
    }

    static String sourceText() {
        try (InputStream in = StampSourceEmitter.class.getResourceAsStream(RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("missing resource " + RESOURCE);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException ex) {
            throw new UncheckedIOException(ex);
        }
    }
}
