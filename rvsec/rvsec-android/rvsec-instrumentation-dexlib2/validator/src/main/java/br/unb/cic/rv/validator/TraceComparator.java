package br.unb.cic.rv.validator;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Layer-3 oracle-based trace comparator. For every {@code *-oracle.yaml}
 * under {@code oracleDir} (excluding {@code layer4-thresholds.yaml}), the
 * comparator pairs the canonical expected events list with the captured
 * RVSEC violations from the two pipelines (ajc + dexlib2) running the
 * SAME APK with the SAME UI driver. Per-spec F1 and Cohen's kappa across
 * the two pipelines are computed; both must clear pre-registered gates.
 *
 * <h2>Matching</h2>
 * An oracle event matches an observed event when the {@code (spec,
 * error_type, expected_message_substring?)} triple agrees: spec and
 * error_type are byte-equal, and if the oracle declares an
 * {@code expected_message_substring} then the observed message must
 * contain it (case-sensitive). The oracle's {@code location.{class,
 * method}} is informational — it appears in the report for diagnostics
 * but is NOT used for matching, because the location is implicit in the
 * spec (each spec is bound to a class/method by its construction
 * inventory).
 *
 * <h2>Gate</h2>
 * Per-spec {@code F1(dexlib2) >= 0.98} AND per-spec {@code kappa >= 0.9}
 * across the two pipelines. Both conditions must hold for every spec
 * observed in any oracle. Empty oracles (e.g. the hateitorrateit slot
 * awaiting ground truth) are skipped and recorded under
 * {@code metrics.emptyOracles}.
 *
 * <h2>Logcat layout</h2>
 * The comparator expects {@code apkSubsetDir/<oracleName>/ajc.logcat} and
 * {@code apkSubsetDir/<oracleName>/dexlib2.logcat}. Missing pairs are
 * recorded under {@code metrics.skippedMissingTrace}.
 */
public final class TraceComparator {

    public static final String LAYER_NAME = "layer3-trace-comparator";

    /** Layer name used by {@link #batchAnalyze} reports. */
    public static final String BATCH_LAYER_NAME = "layer3-trace-comparator-batch";

    /** Per-spec dexlib2 F1 floor. */
    private static final double GATE_F1_THRESHOLD = 0.98;
    /** Per-spec inter-pipeline kappa floor. */
    private static final double GATE_KAPPA_THRESHOLD = 0.9;

    /** Cap on the {@code skippedUnpaired} list emitted into the batch report. */
    private static final int MAX_UNPAIRED_DIAGNOSTIC = 50;

    /**
     * Same regex used by {@code rv-android/scripts/drive_cryptoapp.py}: an
     * optional {@code RVSEC:} prefix, a bracketed spec name, an error
     * type, and a colon-or-dash separated detail message.
     */
    private static final Pattern RVSEC_LINE = Pattern.compile(
            "(?:RVSEC:\\s*)?\\[(?<spec>\\w+)\\]\\s+(?<etype>\\w+)\\s*[:\\-]\\s*(?<msg>.*)$");

    /**
     * Filename grammar emitted by rv-experiment:
     * {@code <apk>.apk__<rep>__<timeout>__<tool>.logcat}. The {@code tool}
     * group accepts colons (e.g. {@code aperv:sata_mop}) but not dots
     * because the {@code .logcat} extension is the terminator.
     */
    private static final Pattern RESULT_LOGCAT = Pattern.compile(
            "^(?<apk>.+\\.apk)__(?<rep>\\d+)__(?<timeout>\\d+)__(?<tool>[^.]+)\\.logcat$");

    private TraceComparator() {}

    public static Report compare(Path oracleDir, Path apkSubsetDir) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("oracleDir", oracleDir.toString());
        metrics.put("apkSubsetDir", apkSubsetDir.toString());
        metrics.put("gateF1Threshold", GATE_F1_THRESHOLD);
        metrics.put("gateKappaThreshold", GATE_KAPPA_THRESHOLD);

        List<Path> oracleFiles = new ArrayList<>();
        if (Files.isDirectory(oracleDir)) {
            try (Stream<Path> ls = Files.list(oracleDir)) {
                ls.filter(Files::isRegularFile)
                  .filter(p -> p.getFileName().toString().endsWith("-oracle.yaml"))
                  .sorted()
                  .forEach(oracleFiles::add);
            }
        }

        metrics.put("totalOracles", oracleFiles.size());
        if (oracleFiles.isEmpty()) {
            metrics.put("emptyOracles", List.of());
            metrics.put("skippedMissingTrace", List.of());
            metrics.put("perOracle", new LinkedHashMap<String, Object>());
            metrics.put("minDexF1", round4(1.0));
            metrics.put("minKappa", round4(1.0));
            return new Report(LAYER_NAME, false, "no oracles to compare", metrics);
        }

        List<String> emptyOracles = new ArrayList<>();
        List<String> skippedMissingTrace = new ArrayList<>();
        Map<String, Object> perOracle = new LinkedHashMap<>();
        boolean overallPassed = true;
        double minDexF1 = Double.POSITIVE_INFINITY;
        double minKappa = Double.POSITIVE_INFINITY;
        int evaluatedSpecCount = 0;

        for (Path yaml : oracleFiles) {
            String oracleName = stripSuffix(yaml.getFileName().toString(), "-oracle.yaml");
            List<OracleEvent> oracle = parseOracle(yaml);
            if (oracle.isEmpty()) {
                emptyOracles.add(oracleName);
                continue;
            }
            Path traceDir = apkSubsetDir.resolve(oracleName);
            Path ajcLog = traceDir.resolve("ajc.logcat");
            Path dexLog = traceDir.resolve("dexlib2.logcat");
            if (!Files.isRegularFile(ajcLog) || !Files.isRegularFile(dexLog)) {
                skippedMissingTrace.add(oracleName);
                continue;
            }

            List<ObservedEvent> ajcObs = parseObserved(ajcLog);
            List<ObservedEvent> dexObs = parseObserved(dexLog);

            Map<String, Object> oracleEntry = scoreOracle(oracle, ajcObs, dexObs);
            boolean oraclePassed = (boolean) oracleEntry.get("passed");
            overallPassed &= oraclePassed;

            @SuppressWarnings("unchecked")
            Map<String, Map<String, Object>> perSpec =
                    (Map<String, Map<String, Object>>) oracleEntry.get("perSpec");
            for (Map<String, Object> sp : perSpec.values()) {
                double dexF1 = ((Number) sp.get("dexF1")).doubleValue();
                double kappa = ((Number) sp.get("kappa")).doubleValue();
                if (dexF1 < minDexF1) minDexF1 = dexF1;
                if (kappa < minKappa) minKappa = kappa;
                evaluatedSpecCount++;
            }
            perOracle.put(oracleName, oracleEntry);
        }

        if (evaluatedSpecCount == 0) {
            // Every oracle was either empty or missing traces; gate cannot pass.
            minDexF1 = 0.0;
            minKappa = 0.0;
            overallPassed = false;
        }

        metrics.put("emptyOracles", emptyOracles);
        metrics.put("skippedMissingTrace", skippedMissingTrace);
        metrics.put("perOracle", perOracle);
        metrics.put("minDexF1", round4(minDexF1));
        metrics.put("minKappa", round4(minKappa));

        String message = String.format(Locale.ROOT,
                "trace comparison %s: F1_min=%.2f, kappa_min=%.2f across %d specs",
                overallPassed ? "passed" : "failed",
                minDexF1, minKappa, evaluatedSpecCount);
        return new Report(LAYER_NAME, overallPassed, message, metrics);
    }

    // --- batch analyze (per (apk, rep, tool) CSV) ----------------------------

    /**
     * Batch entry point that fans out the analyze pipeline over a directory
     * tree of paired logcats and emits one CSV row per
     * {@code (apk, rep, tool, spec)} combination. The CSV is the input
     * format the Layer-4 BatchValidator's per-spec F1 / Cohen's-κ TOST will
     * consume in a follow-up commit; the existing {@link #compare} entry
     * point remains the spec-gate path and is unchanged.
     *
     * <h3>Input layout</h3>
     * Both {@code ajcResultsDir} and {@code dexlibResultsDir} mirror the
     * canonical rv-experiment results tree:
     * <pre>{@code
     *   <resultsDir>/<apk>.apk/<apk>.apk__<rep>__<timeout>__<tool>.logcat
     * }</pre>
     * Filenames are parsed with the regex
     * {@code ^(?<apk>.+\.apk)__(?<rep>\d+)__(?<timeout>\d+)__(?<tool>[^.]+)\.logcat$}.
     * Logcats are paired by the {@code (apk, rep, tool)} triple; the
     * timeout is informational. If two logcats on the same side share a
     * triple but differ in timeout, the one with the longest timeout wins
     * (operators sometimes re-run with longer windows and we want the
     * most-data variant).
     *
     * <h3>Oracle resolution</h3>
     * Each APK maps to {@code oracleDir/<apkBaseName>-oracle.yaml}, where
     * {@code apkBaseName} strips {@code .apk} and any trailing
     * {@code _<digits>} version suffix (e.g. {@code app.pwhs.blockads_45.apk}
     * resolves {@code app.pwhs.blockads-oracle.yaml}). APKs without an
     * oracle land in {@code metrics.skippedNoOracle}.
     *
     * <h3>CSV schema</h3>
     * Header (this exact order; downstream Layer-4 reads positionally):
     * <pre>{@code
     *   apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn
     * }</pre>
     * F1 and κ are rounded to four decimals via
     * {@code Math.round(x*10000)/10000.0} with {@link Locale#ROOT} number
     * formatting. Rows are sorted lexicographically by {@code (apk, tool,
     * spec)} with {@code rep} sorted numerically (so rep=10 follows
     * rep=2, not rep=1).
     */
    public static Report batchAnalyze(Path oracleDir,
                                      Path ajcResultsDir,
                                      Path dexlibResultsDir,
                                      Path outputCsv) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("oracleDir", oracleDir.toString());
        metrics.put("ajcResultsDir", ajcResultsDir.toString());
        metrics.put("dexlibResultsDir", dexlibResultsDir.toString());
        metrics.put("outputCsv", outputCsv.toString());

        Map<String, ResultLogcat> ajcByTriple = collectByTriple(ajcResultsDir);
        Map<String, ResultLogcat> dexByTriple = collectByTriple(dexlibResultsDir);
        int totalLogcats = ajcByTriple.size() + dexByTriple.size();

        TreeSet<String> allTriples = new TreeSet<>();
        allTriples.addAll(ajcByTriple.keySet());
        allTriples.addAll(dexByTriple.keySet());

        TreeSet<String> pairedTriples = new TreeSet<>(ajcByTriple.keySet());
        pairedTriples.retainAll(dexByTriple.keySet());

        List<String> skippedUnpaired = new ArrayList<>();
        TreeSet<String> unpairedSet = new TreeSet<>(allTriples);
        unpairedSet.removeAll(pairedTriples);
        for (String t : unpairedSet) {
            if (skippedUnpaired.size() >= MAX_UNPAIRED_DIAGNOSTIC) break;
            String side = ajcByTriple.containsKey(t) ? " (missing in dexlib2)" : " (missing in ajc)";
            skippedUnpaired.add(t + side);
        }

        // Group paired triples by APK so we can resolve the oracle once per APK.
        Map<String, List<String>> triplesByApk = new TreeMap<>();
        for (String t : pairedTriples) {
            String apk = t.substring(0, t.indexOf('|'));
            triplesByApk.computeIfAbsent(apk, k -> new ArrayList<>()).add(t);
        }

        TreeSet<String> skippedNoOracleSet = new TreeSet<>();
        TreeSet<String> uniqueApksWithRows = new TreeSet<>();
        TreeSet<String> uniqueSpecs = new TreeSet<>();
        List<CsvRow> rows = new ArrayList<>();

        for (Map.Entry<String, List<String>> entry : triplesByApk.entrySet()) {
            String apk = entry.getKey();
            Path oracleYaml = resolveOracleForApk(oracleDir, apk);
            if (oracleYaml == null) {
                skippedNoOracleSet.add(apk);
                continue;
            }
            List<OracleEvent> oracle = parseOracle(oracleYaml);
            if (oracle.isEmpty()) {
                // Empty oracle yields no rows but is not "missing" — silently skip.
                continue;
            }
            for (String triple : entry.getValue()) {
                ResultLogcat ajc = ajcByTriple.get(triple);
                ResultLogcat dex = dexByTriple.get(triple);
                List<ObservedEvent> ajcObs = parseObserved(ajc.path);
                List<ObservedEvent> dexObs = parseObserved(dex.path);
                Map<String, Object> scored = scoreOracle(oracle, ajcObs, dexObs);
                @SuppressWarnings("unchecked")
                Map<String, Map<String, Object>> perSpec =
                        (Map<String, Map<String, Object>>) scored.get("perSpec");
                for (Map.Entry<String, Map<String, Object>> sp : perSpec.entrySet()) {
                    Map<String, Object> v = sp.getValue();
                    rows.add(new CsvRow(
                            ajc.apk, ajc.rep, ajc.tool, sp.getKey(),
                            ((Number) v.get("ajcF1")).doubleValue(),
                            ((Number) v.get("dexF1")).doubleValue(),
                            ((Number) v.get("kappa")).doubleValue(),
                            ((Number) v.get("ajcTp")).intValue(),
                            ((Number) v.get("ajcFp")).intValue(),
                            ((Number) v.get("ajcFn")).intValue(),
                            ((Number) v.get("dexTp")).intValue(),
                            ((Number) v.get("dexFp")).intValue(),
                            ((Number) v.get("dexFn")).intValue()));
                    uniqueSpecs.add(sp.getKey());
                }
                uniqueApksWithRows.add(ajc.apk);
            }
        }

        // Also flag APKs whose triples were unpaired but never reached the oracle check.
        for (String t : unpairedSet) {
            String apk = t.substring(0, t.indexOf('|'));
            if (resolveOracleForApk(oracleDir, apk) == null) {
                skippedNoOracleSet.add(apk);
            }
        }

        rows.sort(Comparator
                .comparing((CsvRow r) -> r.apk)
                .thenComparingInt(r -> r.repInt)
                .thenComparing(r -> r.tool)
                .thenComparing(r -> r.spec));

        if (outputCsv.getParent() != null) {
            Files.createDirectories(outputCsv.getParent());
        }
        writeCsv(outputCsv, rows);

        metrics.put("totalLogcats", totalLogcats);
        metrics.put("pairedTriples", pairedTriples.size());
        metrics.put("rowsWritten", rows.size());
        metrics.put("skippedNoOracle", new ArrayList<>(skippedNoOracleSet));
        metrics.put("skippedUnpaired", skippedUnpaired);
        metrics.put("uniqueApks", uniqueApksWithRows.size());
        metrics.put("uniqueSpecs", uniqueSpecs.size());

        boolean passed = !rows.isEmpty();
        String message = String.format(Locale.ROOT,
                "batch-mode wrote %d rows over %d (apk, rep, tool) triples",
                rows.size(), pairedTriples.size());
        return new Report(BATCH_LAYER_NAME, passed, message, metrics);
    }

    /**
     * Resolve {@code <apkBaseName>-oracle.yaml} for a given {@code <apk>.apk}
     * file name. Strips the {@code .apk} suffix and any trailing
     * {@code _<digits>} version suffix; returns {@code null} if no matching
     * file exists. Caveat: APK package names that legitimately end with
     * {@code _<digits>} would be misclassified, but our F-Droid corpus
     * uses {@code _<versionCode>.apk} as the universal naming convention.
     */
    private static Path resolveOracleForApk(Path oracleDir, String apkFilename) {
        String base = apkFilename.endsWith(".apk")
                ? apkFilename.substring(0, apkFilename.length() - 4)
                : apkFilename;
        // Strip a trailing _<digits> version suffix introduced by rv-experiment.
        int us = base.lastIndexOf('_');
        if (us > 0 && us < base.length() - 1) {
            String tail = base.substring(us + 1);
            boolean allDigits = !tail.isEmpty();
            for (int i = 0; i < tail.length(); i++) {
                if (!Character.isDigit(tail.charAt(i))) { allDigits = false; break; }
            }
            if (allDigits) base = base.substring(0, us);
        }
        Path candidate = oracleDir.resolve(base + "-oracle.yaml");
        return Files.isRegularFile(candidate) ? candidate : null;
    }

    /**
     * Walk {@code root} (one level: {@code <apk>.apk/<filename>.logcat})
     * and return a map keyed by {@code "<apk>|<rep>|<tool>"}. When two
     * files match the same key (different timeouts), the longer-timeout
     * file wins.
     */
    private static Map<String, ResultLogcat> collectByTriple(Path root) throws IOException {
        Map<String, ResultLogcat> out = new TreeMap<>();
        if (!Files.isDirectory(root)) return out;
        try (Stream<Path> walk = Files.walk(root)) {
            walk.filter(Files::isRegularFile)
                .filter(p -> p.getFileName().toString().endsWith(".logcat"))
                .forEach(p -> {
                    String fname = p.getFileName().toString();
                    Matcher m = RESULT_LOGCAT.matcher(fname);
                    if (!m.matches()) return;
                    String apk = m.group("apk");
                    String rep = m.group("rep");
                    int timeout = Integer.parseInt(m.group("timeout"));
                    String tool = m.group("tool");
                    String key = apk + "|" + rep + "|" + tool;
                    ResultLogcat existing = out.get(key);
                    if (existing == null || timeout > existing.timeout) {
                        out.put(key, new ResultLogcat(p, apk, rep, timeout, tool));
                    }
                });
        }
        return out;
    }

    private static void writeCsv(Path outputCsv, List<CsvRow> rows) throws IOException {
        try (BufferedWriter w = Files.newBufferedWriter(outputCsv, StandardCharsets.UTF_8)) {
            // Column order is part of the Layer-4 contract — see Javadoc.
            w.write("apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn");
            w.newLine();
            for (CsvRow r : rows) {
                w.write(String.format(Locale.ROOT,
                        "%s,%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d",
                        r.apk, r.rep, r.tool, r.spec,
                        formatScore(r.ajcF1),
                        formatScore(r.dexF1),
                        formatScore(r.kappa),
                        r.ajcTp, r.ajcFp, r.ajcFn,
                        r.dexTp, r.dexFp, r.dexFn));
                w.newLine();
            }
        }
    }

    private static String formatScore(double x) {
        if (Double.isNaN(x)) return "NaN";
        if (Double.isInfinite(x)) return x > 0 ? "Infinity" : "-Infinity";
        return String.format(Locale.ROOT, "%s", round4(x));
    }

    // --- scoring -------------------------------------------------------------

    private static Map<String, Object> scoreOracle(List<OracleEvent> oracle,
                                                   List<ObservedEvent> ajcObs,
                                                   List<ObservedEvent> dexObs) {
        // Group oracle events by spec, preserving declared order for stable kappa pairings.
        Map<String, List<OracleEvent>> bySpec = new TreeMap<>();
        for (OracleEvent e : oracle) {
            bySpec.computeIfAbsent(e.spec, k -> new ArrayList<>()).add(e);
        }

        Map<String, Map<String, Object>> perSpec = new LinkedHashMap<>();
        boolean oraclePassed = true;
        for (Map.Entry<String, List<OracleEvent>> en : bySpec.entrySet()) {
            String spec = en.getKey();
            List<OracleEvent> specOracle = en.getValue();
            List<ObservedEvent> ajcSpec = filterBySpec(ajcObs, spec);
            List<ObservedEvent> dexSpec = filterBySpec(dexObs, spec);

            // For each oracle event in this spec, did each pipeline fire it?
            List<int[]> ratings = new ArrayList<>(specOracle.size());
            int ajcTp = 0;
            int dexTp = 0;
            for (OracleEvent oe : specOracle) {
                int a = matched(oe, ajcSpec) ? 1 : 0;
                int d = matched(oe, dexSpec) ? 1 : 0;
                ratings.add(new int[]{a, d});
                ajcTp += a;
                dexTp += d;
            }
            int ajcFn = specOracle.size() - ajcTp;
            int dexFn = specOracle.size() - dexTp;
            // FP = observed events for this spec that don't match any oracle entry.
            int ajcFp = countFalsePositives(ajcSpec, specOracle);
            int dexFp = countFalsePositives(dexSpec, specOracle);

            double ajcF1 = f1(ajcTp, ajcFp, ajcFn);
            double dexF1 = f1(dexTp, dexFp, dexFn);
            double kappa = cohensKappa(ratings);

            boolean specPassed = dexF1 >= GATE_F1_THRESHOLD && kappa >= GATE_KAPPA_THRESHOLD;
            oraclePassed &= specPassed;

            Map<String, Object> sp = new LinkedHashMap<>();
            sp.put("ajcTp", ajcTp);
            sp.put("ajcFp", ajcFp);
            sp.put("ajcFn", ajcFn);
            sp.put("dexTp", dexTp);
            sp.put("dexFp", dexFp);
            sp.put("dexFn", dexFn);
            sp.put("ajcF1", round4(ajcF1));
            sp.put("dexF1", round4(dexF1));
            sp.put("kappa", round4(kappa));
            sp.put("passed", specPassed);
            perSpec.put(spec, sp);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("perSpec", perSpec);
        out.put("passed", oraclePassed);
        return out;
    }

    private static boolean matched(OracleEvent oe, List<ObservedEvent> obs) {
        for (ObservedEvent o : obs) {
            if (!o.spec.equals(oe.spec)) continue;
            if (!o.etype.equals(oe.errorType)) continue;
            if (oe.expectedMessageSubstring != null
                    && !o.msg.contains(oe.expectedMessageSubstring)) continue;
            return true;
        }
        return false;
    }

    private static int countFalsePositives(List<ObservedEvent> obs, List<OracleEvent> oracle) {
        int fp = 0;
        for (ObservedEvent o : obs) {
            boolean any = false;
            for (OracleEvent oe : oracle) {
                if (!oe.spec.equals(o.spec)) continue;
                if (!oe.errorType.equals(o.etype)) continue;
                if (oe.expectedMessageSubstring != null
                        && !o.msg.contains(oe.expectedMessageSubstring)) continue;
                any = true;
                break;
            }
            if (!any) fp++;
        }
        return fp;
    }

    private static List<ObservedEvent> filterBySpec(List<ObservedEvent> all, String spec) {
        List<ObservedEvent> out = new ArrayList<>();
        for (ObservedEvent o : all) if (o.spec.equals(spec)) out.add(o);
        return out;
    }

    private static double f1(int tp, int fp, int fn) {
        double p = (tp + fp) == 0 ? 1.0 : (double) tp / (tp + fp);
        double r = (tp + fn) == 0 ? 1.0 : (double) tp / (tp + fn);
        if (p + r == 0.0) return 0.0;
        return 2.0 * p * r / (p + r);
    }

    /**
     * Cohen's kappa over rated items. Each {@code int[]} is {@code [a, b]}
     * with values in {0,1} (1 = pipeline fired the oracle event). Marginals
     * use the empirical rate of "1" per rater; perfect-agreement edge case
     * ({@code Pe == 1}) returns 1.0 to match the standard convention.
     */
    static double cohensKappa(List<int[]> ratings) {
        int n = ratings.size();
        if (n == 0) return 1.0;
        int agree = 0;
        int aOnes = 0;
        int bOnes = 0;
        for (int[] r : ratings) {
            if (r[0] == r[1]) agree++;
            aOnes += r[0];
            bOnes += r[1];
        }
        double po = (double) agree / n;
        double pa1 = (double) aOnes / n;
        double pb1 = (double) bOnes / n;
        double pe = pa1 * pb1 + (1.0 - pa1) * (1.0 - pb1);
        if (pe >= 1.0) return 1.0; // both raters constant AND identical -> perfect agreement.
        return (po - pe) / (1.0 - pe);
    }

    // --- I/O + parsing -------------------------------------------------------

    /**
     * Parse RVSEC violation lines from a logcat file. Empty/blank lines and
     * lines whose tag does not match the {@link #RVSEC_LINE} pattern are
     * silently skipped — same lenient behaviour as
     * {@code drive_cryptoapp.py}.
     */
    static List<ObservedEvent> parseObserved(Path logcat) throws IOException {
        List<ObservedEvent> out = new ArrayList<>();
        var decoder = java.nio.charset.Charset.defaultCharset().newDecoder()
                .onMalformedInput(CodingErrorAction.IGNORE)
                .onUnmappableCharacter(CodingErrorAction.IGNORE);
        try (var reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(Files.newInputStream(logcat), decoder))) {
            String line;
            while ((line = reader.readLine()) != null) {
                Matcher m = RVSEC_LINE.matcher(line);
                if (m.find()) {
                    out.add(new ObservedEvent(
                            m.group("spec"),
                            m.group("etype"),
                            m.group("msg") == null ? "" : m.group("msg").trim()));
                }
            }
        }
        return out;
    }

    /**
     * Minimal hand-rolled parser for the {@code *-oracle.yaml} schema.
     * SnakeYAML is intentionally not on the validator classpath (the prompt
     * forbids new pom deps); the schema is small and stable, so we walk
     * the {@code expected_events} block extracting the four fields used
     * for matching. Anything else (provenance, acceptance, notes) is
     * ignored.
     */
    static List<OracleEvent> parseOracle(Path yaml) throws IOException {
        List<String> lines = Files.readAllLines(yaml);
        List<OracleEvent> events = new ArrayList<>();

        boolean inEvents = false;
        Integer baseIndent = null;
        Integer itemIndent = null;
        String spec = null, etype = null, locClass = null, locMethod = null, msgSub = null;
        boolean haveCurrent = false;

        for (String raw : lines) {
            // Strip trailing '#' comments (only outside quoted strings; our schema has none with '#' inside).
            String stripped = stripComment(raw);
            // Skip blank lines but keep them in flow.
            String trimmed = stripped.stripTrailing();
            if (trimmed.isBlank()) continue;

            int indent = leadingSpaces(stripped);
            String content = stripped.substring(indent);

            if (!inEvents) {
                // Detect inline empty list: `expected_events: []`
                if (content.startsWith("expected_events:")) {
                    String rhs = content.substring("expected_events:".length()).strip();
                    if (rhs.equals("[]")) return Collections.emptyList();
                    inEvents = true;
                    baseIndent = indent;
                }
                continue;
            }

            // We're inside expected_events. A top-level key at indent <= baseIndent ends the block.
            if (indent <= baseIndent) {
                if (haveCurrent) {
                    flush(events, spec, etype, locClass, locMethod, msgSub);
                    haveCurrent = false;
                }
                inEvents = false;
                // Re-evaluate this same line at top level.
                if (content.startsWith("expected_events:")) {
                    inEvents = true;
                }
                continue;
            }

            // List item start: "- id: N" at item indent.
            if (content.startsWith("- ")) {
                if (haveCurrent) {
                    flush(events, spec, etype, locClass, locMethod, msgSub);
                }
                spec = etype = locClass = locMethod = msgSub = null;
                haveCurrent = true;
                itemIndent = indent;
                String afterDash = content.substring(2).trim();
                applyKey(afterDash,
                        v -> { /* id ignored unless explicitly requested */ });
                // afterDash is "id: N" typically; absorb generic key for safety.
                String[] kv = splitKv(afterDash);
                if (kv != null) {
                    // First key on the dashed line; commonly "id".
                    Object[] o = new Object[]{spec, etype, locClass, locMethod, msgSub};
                    assignField(kv[0], kv[1], o);
                    spec = (String) o[0];
                    etype = (String) o[1];
                    locClass = (String) o[2];
                    locMethod = (String) o[3];
                    msgSub = (String) o[4];
                }
                continue;
            }

            // Continuation key for the current item (indent > itemIndent).
            if (haveCurrent && itemIndent != null && indent > itemIndent) {
                String[] kv = splitKv(content);
                if (kv == null) continue;
                Object[] o = new Object[]{spec, etype, locClass, locMethod, msgSub};
                assignField(kv[0], kv[1], o);
                spec = (String) o[0];
                etype = (String) o[1];
                locClass = (String) o[2];
                locMethod = (String) o[3];
                msgSub = (String) o[4];
            }
        }
        if (inEvents && haveCurrent) {
            flush(events, spec, etype, locClass, locMethod, msgSub);
        }
        return events;
    }

    private static void applyKey(String s, java.util.function.Consumer<String> sink) {
        // hook kept for future schema extensions; intentionally a no-op for "id".
    }

    private static void flush(List<OracleEvent> events,
                              String spec, String etype,
                              String locClass, String locMethod, String msgSub) {
        if (spec == null || etype == null) return;
        events.add(new OracleEvent(spec, etype, locClass, locMethod, msgSub));
    }

    private static void assignField(String key, String value, Object[] holder) {
        switch (key) {
            case "spec" -> holder[0] = unquote(value);
            case "error_type" -> holder[1] = unquote(value);
            case "location" -> {
                // Inline-flow map: { class: X, method: Y }
                String v = value.strip();
                if (v.startsWith("{") && v.endsWith("}")) {
                    String inner = v.substring(1, v.length() - 1);
                    for (String part : inner.split(",")) {
                        String[] kv = splitKv(part.trim());
                        if (kv == null) continue;
                        if ("class".equals(kv[0])) holder[2] = unquote(kv[1]);
                        else if ("method".equals(kv[0])) holder[3] = unquote(kv[1]);
                    }
                }
            }
            case "expected_message_substring" -> {
                String v = value.strip();
                if (v.equals("null") || v.isEmpty()) holder[4] = null;
                else holder[4] = unquote(v);
            }
            default -> { /* id / unknown -> ignore */ }
        }
    }

    private static String[] splitKv(String s) {
        int idx = s.indexOf(':');
        if (idx < 0) return null;
        String k = s.substring(0, idx).trim();
        String v = s.substring(idx + 1).trim();
        if (k.isEmpty()) return null;
        return new String[]{k, v};
    }

    private static String unquote(String s) {
        if (s == null) return null;
        String t = s.strip();
        if (t.length() >= 2
                && ((t.charAt(0) == '"' && t.charAt(t.length() - 1) == '"')
                 || (t.charAt(0) == '\'' && t.charAt(t.length() - 1) == '\''))) {
            return t.substring(1, t.length() - 1);
        }
        return t;
    }

    private static int leadingSpaces(String s) {
        int i = 0;
        while (i < s.length() && s.charAt(i) == ' ') i++;
        return i;
    }

    private static String stripComment(String line) {
        // Remove inline comments after a '#' that is not inside a quoted string.
        boolean inSingle = false;
        boolean inDouble = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '\'' && !inDouble) inSingle = !inSingle;
            else if (c == '"' && !inSingle) inDouble = !inDouble;
            else if (c == '#' && !inSingle && !inDouble) return line.substring(0, i);
        }
        return line;
    }

    private static String stripSuffix(String s, String suffix) {
        return s.endsWith(suffix) ? s.substring(0, s.length() - suffix.length()) : s;
    }

    private static double round4(double x) {
        if (Double.isNaN(x) || Double.isInfinite(x)) return x;
        return Math.round(x * 10000.0) / 10000.0;
    }

    // --- value types ---------------------------------------------------------

    record ObservedEvent(String spec, String etype, String msg) {}

    record OracleEvent(String spec, String errorType,
                       String locationClass, String locationMethod,
                       String expectedMessageSubstring) {}

    /** A {@code .logcat} file plus its parsed {@code (apk, rep, timeout, tool)} key. */
    private static final class ResultLogcat {
        final Path path;
        final String apk;
        final String rep;
        final int timeout;
        final String tool;
        ResultLogcat(Path path, String apk, String rep, int timeout, String tool) {
            this.path = path;
            this.apk = apk;
            this.rep = rep;
            this.timeout = timeout;
            this.tool = tool;
        }
    }

    /** One row of the per-(apk, rep, tool, spec) CSV emitted by {@link #batchAnalyze}. */
    private static final class CsvRow {
        final String apk;
        final String rep;
        final int repInt;
        final String tool;
        final String spec;
        final double ajcF1;
        final double dexF1;
        final double kappa;
        final int ajcTp;
        final int ajcFp;
        final int ajcFn;
        final int dexTp;
        final int dexFp;
        final int dexFn;

        CsvRow(String apk, String rep, String tool, String spec,
               double ajcF1, double dexF1, double kappa,
               int ajcTp, int ajcFp, int ajcFn,
               int dexTp, int dexFp, int dexFn) {
            this.apk = apk;
            this.rep = rep;
            this.repInt = Integer.parseInt(rep);
            this.tool = tool;
            this.spec = spec;
            this.ajcF1 = ajcF1;
            this.dexF1 = dexF1;
            this.kappa = kappa;
            this.ajcTp = ajcTp;
            this.ajcFp = ajcFp;
            this.ajcFn = ajcFn;
            this.dexTp = dexTp;
            this.dexFp = dexFp;
            this.dexFn = dexFn;
        }
    }

    // Visible for tests that want to introspect spec listings.
    static List<String> distinctSpecs(List<OracleEvent> events) {
        return new ArrayList<>(new TreeSet<>(events.stream().map(e -> e.spec).toList()));
    }
}
