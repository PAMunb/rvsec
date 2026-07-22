package br.unb.cic.rv.merger;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * Produces the final signed APK from (a) the original APK (resources,
 * manifest, assets preserved) plus (b) the woven DEX files — both the
 * app DEXes the dex-mutator wrote out and the monitor DEX(es)
 * monitor-builder produced.
 *
 * <p>Pipeline:
 * <ol>
 *   <li>Rewrite the ZIP: copy every non-DEX entry from the input APK
 *       verbatim; replace {@code classes<N>.dex} entries with the woven
 *       versions; append monitor DEX entries using the next free
 *       {@code classes<N>.dex} name.</li>
 *   <li>Run {@code zipalign -p 4} for 4-byte alignment and page-align
 *       shared objects (apksigner v3 accepts pre-aligned inputs).</li>
 *   <li>Run {@code apksigner sign} with the keystore from
 *       {@link MergerConfig}.</li>
 * </ol>
 *
 * <p>Preserves multidex split decisions (INV-INS-52): the original APK's
 * {@code classes.dex} + {@code classes2.dex} + ... partitioning is kept
 * exactly; monitor DEX(es) go into new slots beyond the highest existing
 * N. No silent merging ever happens.
 */
public final class MultidexMerger {

    private final MergerConfig config;

    public MultidexMerger(MergerConfig config) {
        this.config = Objects.requireNonNull(config);
    }

    /**
     * @param inputApk       original APK to instrument.
     * @param appDexEntries  replacement DEX bytes for the app classes; keys
     *                       are the original entry names (e.g.
     *                       {@code classes.dex}, {@code classes2.dex}) and
     *                       values are the woven file paths.
     * @param monitorDexes   additional DEX files carrying monitor + wrapper
     *                       + Coverage classes; automatically slotted into
     *                       {@code classes<N>.dex} names after the highest
     *                       existing app DEX.
     * @param outputApk      where to write the signed result.
     */
    public void merge(Path inputApk, Map<String, Path> appDexEntries,
                      List<Path> monitorDexes, Path outputApk) throws IOException {
        Path tmpUnsigned = Files.createTempFile("rvsec-dexlib2-unsigned-", ".apk");
        Path tmpAligned = Files.createTempFile("rvsec-dexlib2-aligned-", ".apk");
        try {
            repackZip(inputApk, appDexEntries, monitorDexes, tmpUnsigned);
            runZipalign(tmpUnsigned, tmpAligned);
            runApksigner(tmpAligned, outputApk);
        } finally {
            Files.deleteIfExists(tmpUnsigned);
            Files.deleteIfExists(tmpAligned);
        }
    }

    private void repackZip(Path inputApk, Map<String, Path> appDexEntries,
                            List<Path> monitorDexes, Path outputUnsigned) throws IOException {
        List<String> replaced = new ArrayList<>(appDexEntries.keySet());
        // Find the highest classes<N>.dex index in the input so monitor DEXes
        // slot in beyond it.
        int highestAppDexIndex = 0;
        try (ZipFile zf = new ZipFile(inputApk.toFile())) {
            var entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String n = e.getName();
                if (n.startsWith("classes") && n.endsWith(".dex")) {
                    int idx = parseClassesIndex(n);
                    if (idx > highestAppDexIndex) highestAppDexIndex = idx;
                }
            }
        }

        try (ZipFile in = new ZipFile(inputApk.toFile());
             ZipOutputStream out = new ZipOutputStream(Files.newOutputStream(outputUnsigned))) {
            var entries = in.entries();
            while (entries.hasMoreElements()) {
                ZipEntry src = entries.nextElement();
                String n = src.getName();
                if (replaced.contains(n)) {
                    // Write the woven replacement in place of the original.
                    writeEntry(out, n, appDexEntries.get(n));
                } else {
                    // Preserve the original entry's storage method and metadata.
                    // Critical for API 30+ install: resources.arsc must remain
                    // STORED (uncompressed). Recompressing with the default
                    // DEFLATED triggers PackageManager parse failure -124
                    // ("Targeting R+ requires resources.arsc stored uncompressed").
                    // For STORED entries the size/crc must be set on the
                    // destination entry; ZipOutputStream computes them itself
                    // for DEFLATED so they can be left unset.
                    ZipEntry dst = new ZipEntry(n);
                    dst.setMethod(src.getMethod());
                    dst.setTime(src.getTime());
                    if (src.getMethod() == ZipEntry.STORED) {
                        dst.setSize(src.getSize());
                        dst.setCompressedSize(src.getCompressedSize());
                        dst.setCrc(src.getCrc());
                    }
                    out.putNextEntry(dst);
                    try (InputStream is = in.getInputStream(src)) {
                        is.transferTo(out);
                    }
                    out.closeEntry();
                }
            }
            // Append monitor DEX slots.
            int next = highestAppDexIndex + 1;
            for (Path md : monitorDexes) {
                String name = next == 1 ? "classes.dex" : "classes" + next + ".dex";
                writeEntry(out, name, md);
                next++;
            }
        }
    }

    private static int parseClassesIndex(String entryName) {
        // "classes.dex" → 1; "classes<N>.dex" → N.
        String body = entryName.substring("classes".length(),
                entryName.length() - ".dex".length());
        if (body.isEmpty()) return 1;
        try {
            return Integer.parseInt(body);
        } catch (NumberFormatException ex) {
            return 1;
        }
    }

    private static void writeEntry(ZipOutputStream out, String name, Path file) throws IOException {
        ZipEntry e = new ZipEntry(name);
        out.putNextEntry(e);
        Files.copy(file, out);
        out.closeEntry();
    }

    private void runZipalign(Path input, Path output) {
        List<String> cmd = List.of(
                config.zipalignBin.toString(),
                "-p", "-f", "4",
                input.toString(),
                output.toString()
        );
        runSubprocess("zipalign", cmd);
    }

    private void runApksigner(Path aligned, Path output) {
        try {
            Files.copy(aligned, output, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException ex) {
            throw new MergerException("apksigner", "failed to stage APK for signing", ex);
        }
        List<String> cmd = new ArrayList<>();
        cmd.add(config.apksignerBin.toString());
        cmd.add("sign");
        cmd.add("--ks"); cmd.add(config.keystore.toString());
        cmd.add("--ks-pass"); cmd.add("pass:" + config.keystorePassword);
        cmd.add("--ks-key-alias"); cmd.add(config.keyAlias);
        cmd.add("--key-pass"); cmd.add("pass:" + config.keyPassword);
        cmd.add(output.toString());
        runSubprocess("apksigner", cmd);
    }

    private static void runSubprocess(String tool, List<String> cmd) {
        try {
            ProcessBuilder pb = new ProcessBuilder(cmd).redirectErrorStream(false);
            Process p = pb.start();
            String stderr = new String(p.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
            int exit = p.waitFor();
            if (exit != 0) {
                throw new MergerException(tool, exit, stderr,
                        tool + " exited with code " + exit + "\n" + stderr);
            }
        } catch (IOException ex) {
            throw new MergerException(tool, "failed to start " + tool, ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new MergerException(tool, "interrupted waiting for " + tool, ex);
        }
    }
}
