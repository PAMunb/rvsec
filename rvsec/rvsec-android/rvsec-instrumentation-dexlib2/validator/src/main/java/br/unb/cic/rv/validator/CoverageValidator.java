package br.unb.cic.rv.validator;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.CodingErrorAction;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Layer-5 coverage-recall validator: pairs ajc and dexlib2 logcat captures
 * by APK name, extracts the set of distinct Soot signatures emitted under
 * the {@code RVSEC-COV} tag in each, and computes per-pair recall as
 * {@code |coveredAjc &cap; coveredDex| / |coveredAjc|}.
 *
 * <p>Each runtime-instrumented app method emits one log line of the form
 * {@code RVSEC-COV: <full.qualified.ClassName: returnType methodName(paramType,...)>}.
 * Two events are equal iff the full bracketed signature is byte-equal.
 *
 * <h2>Pairing</h2>
 * Logcats are discovered by recursive glob {@code **\/*.logcat} under each
 * input directory. The immediate parent directory of each {@code .logcat}
 * is treated as the APK name (matches the standard rv-android layout
 * {@code results/<exp>/<apk>.apk/<apk>.apk__<rep>__<timeout>__<tool>.logcat}).
 * Logcats whose APK name has no peer in the other tree are recorded in
 * {@code metrics.skippedNotPaired} and excluded from aggregates.
 *
 * <h2>Gate</h2>
 * Both {@code aggregateRecall &ge; 0.99} (micro-averaged across pairs) and
 * {@code |aggregateDelta| &le; 0.01 * sum(coveredAjc)} must hold.
 */
public final class CoverageValidator {

    public static final String LAYER_NAME = "layer5-coverage-validator";

    private static final double GATE_RECALL_THRESHOLD = 0.99;
    private static final double GATE_DELTA_PP_THRESHOLD = 0.01;

    /** Match {@code RVSEC-COV:} as a complete tag (no trailing letter/digit/dash) followed by a {@code <...>} signature. */
    private static final Pattern COV_LINE = Pattern.compile("\\bRVSEC-COV(?![A-Za-z0-9_-]):\\s*(<[^>]+>)");

    private CoverageValidator() {}

    /**
     * Compute the Layer-5 coverage-recall report by pairing ajc and dexlib2
     * logcat trees by APK name, unioning each side's distinct
     * {@code RVSEC-COV} signatures per APK, and applying the two-part gate
     * (micro-averaged recall ≥ 0.99 AND {@code |aggregateDelta|} within
     * {@code 0.01 × totalAjc}).
     *
     * @param ajcLogcatDir    logcat tree from the ajc pipeline (baseline)
     * @param dexlibLogcatDir logcat tree from the dexlib2 pipeline (candidate)
     * @return a {@link Report} whose {@code passed} reflects the gate and whose
     *         metrics carry per-APK and aggregate recall/delta diagnostics
     */
    public static Report compare(Path ajcLogcatDir, Path dexlibLogcatDir) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("ajcLogcatDir", ajcLogcatDir.toString());
        metrics.put("dexlibLogcatDir", dexlibLogcatDir.toString());
        metrics.put("gateRecallThreshold", GATE_RECALL_THRESHOLD);
        metrics.put("gateDeltaPpThreshold", GATE_DELTA_PP_THRESHOLD);

        boolean ajcOk = Files.isDirectory(ajcLogcatDir);
        boolean dexOk = Files.isDirectory(dexlibLogcatDir);
        if (!ajcOk || !dexOk) {
            metrics.put("ajcDirExists", ajcOk);
            metrics.put("dexlibDirExists", dexOk);
            return new Report(LAYER_NAME, false,
                    "input directory missing or not a directory", metrics);
        }

        Map<String, Set<String>> ajcByApk = collectByApk(ajcLogcatDir);
        Map<String, Set<String>> dexByApk = collectByApk(dexlibLogcatDir);

        List<String> skipped = new ArrayList<>();
        Set<String> allApks = new TreeSet<>();
        allApks.addAll(ajcByApk.keySet());
        allApks.addAll(dexByApk.keySet());

        List<String> paired = new ArrayList<>();
        for (String apk : allApks) {
            boolean inAjc = ajcByApk.containsKey(apk);
            boolean inDex = dexByApk.containsKey(apk);
            if (inAjc && inDex) paired.add(apk);
            else if (inAjc) skipped.add(apk + " (missing in dexlib2)");
            else skipped.add(apk + " (missing in ajc)");
        }
        metrics.put("skippedNotPaired", skipped);

        // Empty-pairs branch: recall is vacuously 1.0 (nothing to miss), yet
        // this FAILS the gate deliberately. Zero paired APKs means the two
        // trees never overlapped — a configuration/plumbing error, not a clean
        // comparison. Passing here would let a mis-pointed input silently
        // "prove" parity, so we treat no-evidence as gate failure.
        if (paired.isEmpty()) {
            metrics.put("totalPairs", 0);
            metrics.put("perApk", new LinkedHashMap<String, Object>());
            metrics.put("aggregateRecall", 1.0);
            metrics.put("aggregateDelta", 0);
            metrics.put("medianRecall", 1.0);
            metrics.put("medianDelta", 0);
            metrics.put("totalAjcSignatures", 0);
            metrics.put("totalDexSignatures", 0);
            return new Report(LAYER_NAME, false, "no logcat pairs to compare", metrics);
        }

        Map<String, Map<String, Object>> perApk = new LinkedHashMap<>();
        long totalAjc = 0;
        long totalDex = 0;
        long totalIntersect = 0;
        List<Double> recalls = new ArrayList<>(paired.size());
        List<Long> deltas = new ArrayList<>(paired.size());

        for (String apk : paired) {
            Set<String> a = ajcByApk.getOrDefault(apk, Collections.emptySet());
            Set<String> d = dexByApk.getOrDefault(apk, Collections.emptySet());
            int intersect = 0;
            for (String s : a) if (d.contains(s)) intersect++;
            double recall = a.isEmpty() ? 1.0 : (double) intersect / a.size();
            int delta = d.size() - a.size();

            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("ajcCovered", a.size());
            entry.put("dexCovered", d.size());
            entry.put("intersect", intersect);
            entry.put("recall", recall);
            entry.put("delta", delta);
            perApk.put(apk, entry);

            totalAjc += a.size();
            totalDex += d.size();
            totalIntersect += intersect;
            recalls.add(recall);
            deltas.add((long) delta);
        }

        double aggregateRecall = totalAjc == 0 ? 1.0 : (double) totalIntersect / totalAjc;
        long aggregateDelta = totalDex - totalAjc;
        double medianRecall = median(recalls);
        long medianDelta = medianLong(deltas);

        boolean recallOk = aggregateRecall >= GATE_RECALL_THRESHOLD;
        // Delta gate: the net signature count difference (dexlib2 − ajc) must
        // stay within 1% of the ajc total. Recall alone only bounds MISSED
        // signatures; this two-sided budget also catches a dexlib2 side that
        // OVER-emits (extra signatures ajc never produced), which would inflate
        // coverage without recall noticing.
        boolean deltaOk = Math.abs(aggregateDelta) <= GATE_DELTA_PP_THRESHOLD * totalAjc;
        boolean passed = recallOk && deltaOk;

        metrics.put("totalPairs", paired.size());
        metrics.put("perApk", perApk);
        metrics.put("aggregateRecall", aggregateRecall);
        metrics.put("aggregateDelta", aggregateDelta);
        metrics.put("medianRecall", medianRecall);
        metrics.put("medianDelta", medianDelta);
        metrics.put("totalAjcSignatures", totalAjc);
        metrics.put("totalDexSignatures", totalDex);

        String message = String.format(java.util.Locale.ROOT,
                "coverage gate %s: aggregate recall=%.2f, delta=%s%d",
                passed ? "passed" : "failed",
                aggregateRecall,
                aggregateDelta >= 0 ? "+" : "",
                aggregateDelta);
        return new Report(LAYER_NAME, passed, message, metrics);
    }

    /** RVSEC-COV: {@code <com.foo.Bar: void baz(int)>} -> "&lt;com.foo.Bar: void baz(int)&gt;" full match. */
    static Set<String> extractCoveredSignatures(Path logcatFile) throws IOException {
        Set<String> out = new LinkedHashSet<>();
        var decoder = java.nio.charset.Charset.defaultCharset().newDecoder()
                .onMalformedInput(CodingErrorAction.IGNORE)
                .onUnmappableCharacter(CodingErrorAction.IGNORE);
        try (var reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(Files.newInputStream(logcatFile), decoder));
             Stream<String> lines = reader.lines()) {
            lines.forEach(line -> {
                Matcher m = COV_LINE.matcher(line);
                if (m.find()) out.add(m.group(1));
            });
        }
        return out;
    }

    /**
     * Recursively gather every {@code .logcat} file under {@code root}, group
     * them by their immediate parent directory name (= APK name in the
     * standard layout), and union the signatures across all logcats sharing
     * an APK name (multi-rep tolerance).
     */
    private static Map<String, Set<String>> collectByApk(Path root) throws IOException {
        Map<String, Set<String>> out = new TreeMap<>();
        try (Stream<Path> stream = Files.walk(root)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().endsWith(".logcat"))
                    .forEach(p -> {
                        Path parent = p.getParent();
                        String apk = parent == null ? "" : parent.getFileName().toString();
                        Set<String> sigs = out.computeIfAbsent(apk, k -> new LinkedHashSet<>());
                        try {
                            sigs.addAll(extractCoveredSignatures(p));
                        } catch (IOException e) {
                            throw new UncheckedIOException(e);
                        }
                    });
        } catch (UncheckedIOException e) {
            throw e.getCause();
        }
        return out;
    }

    private static double median(List<Double> xs) {
        if (xs.isEmpty()) return 0.0;
        List<Double> sorted = new ArrayList<>(xs);
        Collections.sort(sorted);
        int n = sorted.size();
        if ((n & 1) == 1) return sorted.get(n / 2);
        return (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2.0;
    }

    private static long medianLong(List<Long> xs) {
        if (xs.isEmpty()) return 0L;
        List<Long> sorted = new ArrayList<>(xs);
        Collections.sort(sorted);
        int n = sorted.size();
        if ((n & 1) == 1) return sorted.get(n / 2);
        // For even n, return the floor of the average to keep an integer-valued metric.
        return (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2L;
    }
}
