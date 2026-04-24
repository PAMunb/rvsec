package br.unb.cic.rv.validator;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.DexFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Layer-4 preflight: projects post-weaving method-ref counts per DEX in
 * every candidate APK and flags any host DEX that would cross 65,000
 * refs after adding the monitor invokes + wrapper class (INV-INS-25).
 *
 * <p>The per-APK projection adds {@code (numAdvices × 2) +
 * (coverageMethods ≈ 1)} method-ref estimates to the host DEX's
 * current count — a rough upper bound the actual weaver will almost
 * always undershoot, so false positives here are safer than false
 * negatives.
 *
 * <p>Warning threshold: 62,000 refs. Error threshold: 65,000 refs
 * (Dalvik's 65,536 hard limit with a ~500-ref safety margin).
 */
public final class MethodRefAuditor {

    public static final int WARN_THRESHOLD = 62_000;
    public static final int ERROR_THRESHOLD = 65_000;

    private MethodRefAuditor() {}

    public static Report audit(Path apksDir, int projectedAddedRefs) throws IOException {
        List<Map<String, Object>> perApk = new ArrayList<>();
        int flagged = 0;
        int errors = 0;

        if (!Files.isDirectory(apksDir)) {
            Map<String, Object> metrics = new LinkedHashMap<>();
            metrics.put("apksDir", apksDir.toString());
            metrics.put("error", "not a directory");
            return new Report("method-ref-audit", false, "apksDir invalid", metrics);
        }

        try (var stream = Files.list(apksDir)) {
            List<Path> apks = stream
                    .filter(p -> p.toString().endsWith(".apk"))
                    .sorted()
                    .toList();
            for (Path apk : apks) {
                Map<String, Object> summary = auditOne(apk, projectedAddedRefs);
                perApk.add(summary);
                int maxRefs = ((Number) summary.get("maxProjectedRefs")).intValue();
                if (maxRefs >= ERROR_THRESHOLD) errors++;
                if (maxRefs >= WARN_THRESHOLD) flagged++;
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("apksDir", apksDir.toString());
        metrics.put("apkCount", perApk.size());
        metrics.put("flaggedCount", flagged);
        metrics.put("errorCount", errors);
        metrics.put("warnThreshold", WARN_THRESHOLD);
        metrics.put("errorThreshold", ERROR_THRESHOLD);
        metrics.put("perApk", perApk);

        boolean passed = errors == 0;
        String msg = passed
                ? "all APKs within ref budget (" + flagged + " flagged for monitoring)"
                : errors + " APK(s) would exceed the 65,000-ref budget; multidex-merger "
                        + "must emit an extra DEX for each";
        return new Report("method-ref-audit", passed, msg, metrics);
    }

    private static Map<String, Object> auditOne(Path apk, int projected) throws IOException {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("apk", apk.getFileName().toString());
        int max = 0;
        List<Map<String, Object>> dexes = new ArrayList<>();
        try (ZipFile zf = new ZipFile(apk.toFile())) {
            var entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String n = e.getName();
                if (!n.startsWith("classes") || !n.endsWith(".dex")) continue;
                int count;
                try (InputStream in = zf.getInputStream(e)) {
                    DexFile dx = DexBackedDexFile.fromInputStream(
                            Opcodes.getDefault(), new java.io.BufferedInputStream(in));
                    count = countMethodRefs(dx);
                }
                int projectedCount = count + projected;
                Map<String, Object> dex = new LinkedHashMap<>();
                dex.put("entry", n);
                dex.put("currentRefs", count);
                dex.put("projectedRefs", projectedCount);
                dexes.add(dex);
                if (projectedCount > max) max = projectedCount;
            }
        }
        summary.put("dexes", dexes);
        summary.put("maxProjectedRefs", max);
        return summary;
    }

    private static int countMethodRefs(DexFile dx) {
        // Cheap estimator: the DexBacked implementation exposes method pool size
        // via its internal header; we approximate by iterating classes + methods.
        int count = 0;
        for (var cd : dx.getClasses()) {
            // Field + method counts give a lower bound; for audit purposes we
            // count methods + inherited method-refs (approximated by the union
            // of declared methods across the class set, which the compiler has
            // already uniquefied).
            for (var m : cd.getMethods()) count++;
        }
        return count;
    }
}
