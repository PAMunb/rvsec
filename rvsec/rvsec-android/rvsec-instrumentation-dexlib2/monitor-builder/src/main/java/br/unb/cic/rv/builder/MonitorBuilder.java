package br.unb.cic.rv.builder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Drives {@code javac} then {@code d8} over the generated monitor / wrapper /
 * Coverage Java sources to produce one or more {@code .dex} files ready for
 * {@code multidex-merger} to inject into the target APK.
 *
 * <p>Inputs:
 * <ul>
 *   <li>{@code sourceDir} — directory containing the Java sources
 *       ({@code mop/Coverage.java}, {@code mop/MonitorWrappers.java}, and
 *       the rv-monitor-generated {@code MultiSpec_*RuntimeMonitor.java}).</li>
 *   <li>{@link BuilderConfig} — paths to {@code javac}, {@code d8},
 *       {@code rt.jar}, {@code android.jar}, and any additional runtime
 *       jars (rv-monitor-rt, rvsec-core, rvsec-logger-logcat, ...).</li>
 * </ul>
 *
 * <p>Output is one or more {@code classes<N>.dex} files under
 * {@code outputDir}. When the monitor class count exceeds the 65,536
 * method-id limit, d8 auto-splits into multiple dex files.
 *
 * <p>Failure modes surface as {@link CommandException}: javac non-zero exit
 * → {@code tool="javac"}, d8 non-zero exit → {@code tool="d8"}, subprocess
 * startup failure → wrapped IOException.
 *
 * <p>Spec-set agnostic: builds monitor sources identically for JCA or
 * Generic specifications.
 */
public final class MonitorBuilder {

    private final BuilderConfig config;

    public MonitorBuilder(BuilderConfig config) {
        this.config = Objects.requireNonNull(config);
    }

    /**
     * Compile {@code sourceDir/**\/*.java} to {@code .class} under
     * {@code outputDir/classes/} then run d8 to produce {@code outputDir/dex/}.
     *
     * @return the list of produced .dex files (ordered by classes<N>.dex name).
     */
    public List<Path> build(Path sourceDir, Path outputDir) throws IOException {
        Objects.requireNonNull(sourceDir);
        Objects.requireNonNull(outputDir);

        Path classesDir = outputDir.resolve("classes");
        Path dexDir = outputDir.resolve("dex");
        Files.createDirectories(classesDir);
        Files.createDirectories(dexDir);

        compileJavaSources(sourceDir, classesDir);
        return runD8(classesDir, dexDir);
    }

    private void compileJavaSources(Path sourceDir, Path classesDir) throws IOException {
        List<String> sources;
        try (Stream<Path> walk = Files.walk(sourceDir)) {
            sources = walk
                    .filter(p -> p.toString().endsWith(".java"))
                    .map(Path::toString)
                    .collect(Collectors.toList());
        }
        if (sources.isEmpty()) {
            throw new CommandException("javac", 0, "",
                    "no .java sources found under " + sourceDir);
        }

        String classpath = Stream.concat(
                Stream.of(config.androidJar.toString()),
                config.classpath.stream().map(Path::toString)
        ).collect(Collectors.joining(java.io.File.pathSeparator));

        List<String> cmd = new ArrayList<>();
        cmd.add(config.javacBin.toString());
        cmd.add("-d"); cmd.add(classesDir.toString());
        // Target Java 8 bytecode for d8 compatibility. Modern javac (≥9)
        // rejects -bootclasspath at target ≥9, and Android's d8 only
        // accepts ≤Java 11 class files anyway. --source/-target 1.8 is the
        // canonical Android-toolchain invocation. android.jar is on the
        // -classpath so android.* types resolve; java.* types come from
        // the JDK's default boot classpath.
        cmd.add("-source"); cmd.add("1.8");
        cmd.add("-target"); cmd.add("1.8");
        cmd.add("-classpath"); cmd.add(classpath);
        cmd.addAll(sources);

        runSubprocess("javac", cmd);
    }

    private List<Path> runD8(Path classesDir, Path dexDir) throws IOException {
        // Collect every .class under classesDir.
        List<String> classFiles;
        try (Stream<Path> walk = Files.walk(classesDir)) {
            classFiles = walk
                    .filter(p -> p.toString().endsWith(".class"))
                    .map(Path::toString)
                    .collect(Collectors.toList());
        }
        if (classFiles.isEmpty()) {
            throw new CommandException("d8", 0, "",
                    "no .class files found under " + classesDir);
        }

        List<String> cmd = new ArrayList<>();
        cmd.add(config.d8Bin.toString());
        cmd.add("--output"); cmd.add(dexDir.toString());
        cmd.addAll(classFiles);

        runSubprocess("d8", cmd);

        // d8 writes classes.dex (+ optional classes2.dex, classes3.dex) in dexDir.
        List<Path> out = new ArrayList<>();
        try (Stream<Path> ls = Files.list(dexDir)) {
            ls.filter(p -> p.toString().endsWith(".dex"))
              .sorted()
              .forEach(out::add);
        }
        return out;
    }

    private void runSubprocess(String tool, List<String> cmd) {
        try {
            ProcessBuilder pb = new ProcessBuilder(cmd).redirectErrorStream(false);
            Process p = pb.start();
            String stderr = new String(p.getErrorStream().readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
            int exit = p.waitFor();
            if (exit != 0) {
                throw new CommandException(tool, exit, stderr,
                        tool + " exited with code " + exit + "\n" + stderr);
            }
        } catch (IOException ex) {
            throw new CommandException(tool, "failed to start " + tool, ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new CommandException(tool, "interrupted waiting for " + tool, ex);
        }
    }
}
