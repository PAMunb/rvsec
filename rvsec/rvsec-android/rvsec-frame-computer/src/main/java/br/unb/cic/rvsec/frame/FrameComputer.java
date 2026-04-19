package br.unb.cic.rvsec.frame;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.List;

/**
 * Recomputes stack map frames on all .class files in a directory using ASM.
 *
 * After AspectJ weaving, stack map frames may be corrupted (ajc uses BCEL which
 * doesn't always recompute frames correctly for modern bytecode patterns like
 * try-with-resources, lambdas, and switch expressions). This utility uses ASM's
 * COMPUTE_FRAMES to recompute all frames from scratch, producing bytecode that
 * the Android d8 compiler accepts.
 *
 * Usage: java -jar rv-frame-computer.jar &lt;classDir&gt; [--classpath &lt;cp&gt;]
 */
public class FrameComputer {

    private final ClassLoader resolverClassLoader;
    private int processed = 0;
    private int failed = 0;

    public FrameComputer(String classpath, String classDir) {
        this.resolverClassLoader = buildClassLoader(classpath, classDir);
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: FrameComputer <classDir> [--classpath <cp>]");
            System.exit(1);
        }

        String classDir = args[0];
        String classpath = "";

        for (int i = 1; i < args.length; i++) {
            if ("--classpath".equals(args[i]) && i + 1 < args.length) {
                classpath = args[++i];
            }
        }

        FrameComputer computer = new FrameComputer(classpath, classDir);
        computer.processDirectory(new File(classDir));

        System.out.printf("FrameComputer: %d processed, %d failed%n",
                computer.processed, computer.failed);
    }

    /**
     * Build a URLClassLoader from the classpath string so that
     * ClassWriter.COMPUTE_FRAMES can resolve the type hierarchy.
     */
    private static ClassLoader buildClassLoader(String classpath, String classDir) {
        List<URL> urls = new ArrayList<>();
        try {
            urls.add(new File(classDir).toURI().toURL());

            if (classpath != null && !classpath.isEmpty()) {
                for (String entry : classpath.split(File.pathSeparator)) {
                    File f = new File(entry.trim());
                    if (f.exists()) {
                        urls.add(f.toURI().toURL());
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("Warning: classpath construction error: " + e.getMessage());
        }
        return new URLClassLoader(urls.toArray(new URL[0]), ClassLoader.getSystemClassLoader());
    }

    private void processDirectory(File dir) {
        try {
            Files.walkFileTree(dir.toPath(), new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    if (file.toString().endsWith(".class")) {
                        processClassFile(file.toFile());
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            System.err.println("Error walking directory: " + e.getMessage());
        }
    }

    private void processClassFile(File classFile) {
        try {
            byte[] original = Files.readAllBytes(classFile.toPath());

            ClassReader reader = new ClassReader(original);
            // ClassWriter WITHOUT reader arg forces full frame recomputation.
            // With reader arg, ASM optimizes by copying original frames — if the
            // original had no StackMapTable, the copy is empty (no-op).
            ClassWriter writer = new FrameComputingClassWriter(
                    ClassWriter.COMPUTE_FRAMES, resolverClassLoader);
            reader.accept(writer, ClassReader.SKIP_FRAMES);

            byte[] recomputed = writer.toByteArray();

            try (FileOutputStream fos = new FileOutputStream(classFile)) {
                fos.write(recomputed);
            }
            processed++;

        } catch (Throwable e) {
            // Catch Throwable (not just Exception) because dex2jar can produce
            // classes with illegal modifiers that trigger ClassFormatError (an Error,
            // not Exception) when Class.forName() tries to load them during
            // getCommonSuperClass(). The file is preserved with original bytecode.
            failed++;
            System.err.println("Warning: frame computation failed for "
                    + classFile.getName() + ": " + e.getMessage());
        }
    }

    /**
     * ClassWriter subclass that resolves the type hierarchy via a ClassLoader
     * instead of loading .class files from the filesystem. Required for
     * COMPUTE_FRAMES when the class hierarchy spans multiple jars
     * (android.jar, aspectjrt.jar, etc.).
     */
    static class FrameComputingClassWriter extends ClassWriter {
        private final ClassLoader classLoader;

        FrameComputingClassWriter(int flags, ClassLoader classLoader) {
            super(flags);
            this.classLoader = classLoader;
        }

        @Override
        protected String getCommonSuperClass(String type1, String type2) {
            try {
                Class<?> c1 = Class.forName(type1.replace('/', '.'), false, classLoader);
                Class<?> c2 = Class.forName(type2.replace('/', '.'), false, classLoader);

                if (c1.isAssignableFrom(c2)) return type1;
                if (c2.isAssignableFrom(c1)) return type2;
                if (c1.isInterface() || c2.isInterface()) return "java/lang/Object";

                do {
                    c1 = c1.getSuperclass();
                } while (!c1.isAssignableFrom(c2));

                return c1.getName().replace('.', '/');

            } catch (Throwable e) {
                // ClassNotFoundException: type not on classpath (normal for Android classes)
                // ClassFormatError: dex2jar produces classes with illegal modifiers
                // NoClassDefFoundError: dependency of a class not loadable
                return "java/lang/Object";
            }
        }
    }
}
