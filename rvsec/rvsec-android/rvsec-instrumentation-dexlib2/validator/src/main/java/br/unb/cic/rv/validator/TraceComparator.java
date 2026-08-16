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
 * An oracle event matches an observed event when spec and error_type are
 * byte-equal, any declared {@code expected_message_substring} is contained in
 * the observed message (case-sensitive), and any declared {@code location}
 * agrees. The class is accepted in either the qualified or the short form the
 * violation line carries; the method must be equal. An oracle event that
 * declares no location falls back to {@code (spec, error_type)} alone.
 *
 * <p>
 * Location is matched, not merely reported, because the unit of analysis is
 * {@code (apk, class, method, spec)} — the article's unique misuse — and a
 * comparator that ignored the site would score two different misuses of the
 * same specification as one agreement (INV-INS-116, D-O3, D-O4).
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
     * Isolates the payload of an on-device violation line from whatever logcat
     * prefix precedes it.
     *
     * <p>
     * The producer is {@code ErrorCollector.addError} (rvsec-logger-logcat),
     * which calls {@code Log.v("RVSEC", message)}. Logcat's default
     * {@code threadtime} format renders that as a fixed-width tag, so the real
     * recordings carry {@code V RVSEC   :} — the tag padded with spaces to the
     * column width. The padding is why a naive {@code RVSEC:} literal matches
     * nothing on a real file.
     *
     * <p>
     * The tag boundary matters in the other direction too. The same apps emit
     * thousands of {@code RVSEC-COV:} coverage lines (2,266 against 5 violation
     * lines in the 2026-08-06 recording used by the tests), and those are not
     * violations. Requiring optional spaces and then the colon <em>immediately</em>
     * after {@code RVSEC} excludes them: {@code RVSEC-COV:} has {@code -COV}
     * where this pattern demands whitespace-or-colon.
     */
    private static final Pattern RVSEC_LINE = Pattern.compile(
            "(?:^|\\s)RVSEC\\s*:\\s*(?<payload>\\S.*)$");

    /**
     * Number of comma-separated fields a violation payload carries.
     *
     * <p>
     * {@code ErrorSummary.toString()} emits six —
     * {@code spec,classQualifiedName,className,methodName,location,error} — and
     * {@code ErrorCollector:37} appends {@code "," + expecting} for a seventh.
     * The {@code expecting} text is generated from the specification and
     * routinely contains commas of its own ({@code "expecting one of
     * PKIX,SunX509 but found ."}), so everything from this index on is rejoined
     * rather than split. This is the same rule
     * {@code rv-android/modules/rv-coverage/.../logcat_parser.py} applies, which
     * is the reference implementation for the format (INV-INS-117).
     */
    private static final int VIOLATION_FIELDS = 7;

    /** Index of the first field belonging to the rejoined {@code expecting} text. */
    private static final int EXPECTING_INDEX = 6;

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

        // Admission is consulted here rather than left to an operator who
        // remembers to run the `oracles` subcommand (D-O6). Listing the
        // directory directly, as this method used to, scores every file it
        // finds — including one rejected for circularity, which is the single
        // thing INV-INS-107 exists to keep out of a verdict. The rejections
        // travel into the report so a shrunken oracle set is visible rather
        // than merely smaller.
        OracleLoader.LoadResult loaded = OracleLoader.load(oracleDir);
        List<Path> oracleFiles = loaded.admitted();

        metrics.put("totalOracles", oracleFiles.size());
        metrics.put("discoveredOracles", loaded.files().size());
        metrics.put("rejectedOracles", loaded.rejected());
        if (oracleFiles.isEmpty()) {
            metrics.put("emptyOracles", List.of());
            metrics.put("skippedMissingTrace", List.of());
            metrics.put("perOracle", new LinkedHashMap<String, Object>());
            metrics.put("minDexF1", round4(1.0));
            metrics.put("minKappa", round4(1.0));
            String why = loaded.files().isEmpty()
                    ? "no oracles to compare"
                    : "no admissible oracles to compare: all " + loaded.files().size()
                            + " were rejected — see metrics.rejectedOracles";
            return new Report(LAYER_NAME, false, why, metrics);
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

        // Batch mode is where the per-APK oracles (D-O5) are consumed, so it is
        // where admission has to hold (D-O6). An oracle rejected here resolves
        // for no APK, and that APK is reported as having no oracle rather than
        // scored against an inadmissible one.
        OracleLoader.LoadResult loaded = OracleLoader.load(oracleDir);
        java.util.Set<Path> admitted = new java.util.LinkedHashSet<>(loaded.admitted());
        metrics.put("discoveredOracles", loaded.files().size());
        metrics.put("admittedOracles", loaded.admitted().size());
        metrics.put("rejectedOracles", loaded.rejected());

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
            Path oracleYaml = resolveOracleForApk(oracleDir, apk, admitted);
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
            if (resolveOracleForApk(oracleDir, apk, admitted) == null) {
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
     *
     * <p>
     * The result is additionally restricted to {@code admitted}: an oracle
     * whose provenance was rejected resolves for no APK, so batch mode enforces
     * the same admission rule as {@link #compare} (D-O6) rather than scoring
     * whatever file happens to bear the right name.
     */
    private static Path resolveOracleForApk(Path oracleDir, String apkFilename,
                                            java.util.Set<Path> admitted) {
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
        if (!Files.isRegularFile(candidate)) return null;
        if (!admitted.contains(candidate)) return null;
        return candidate;
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

        // Score the UNION of the specs the oracle declares and the specs either
        // trace reports. A spec observed but absent from the oracle gets an
        // empty expected-event list, so every event under it counts as a false
        // positive — which is exactly what it is.
        //
        // Iterating the oracle alone made the gate blind to the defect this
        // layer exists to detect. A wrapper-registry collision binds a call site
        // to the WRONG specification, so it surfaces under a spec the
        // independent weaver never reported for that APK — precisely the case
        // the oracle has no entry for. Measured over the derived set before this
        // change: 10 of 26 dexlib2 events in L3-b and 45 of 87 in L3-c were
        // never scored at all, and L3-b reported dexFp=0 while carrying five
        // dexlib2-only unique misuses.
        TreeSet<String> specs = new TreeSet<>(bySpec.keySet());
        for (ObservedEvent o : ajcObs) specs.add(o.spec);
        for (ObservedEvent o : dexObs) specs.add(o.spec);

        Map<String, Map<String, Object>> perSpec = new LinkedHashMap<>();
        boolean oraclePassed = true;
        for (String spec : specs) {
            List<OracleEvent> specOracle = bySpec.getOrDefault(spec, List.of());
            List<ObservedEvent> ajcSpec = filterBySpec(ajcObs, spec);
            List<ObservedEvent> dexSpec = filterBySpec(dexObs, spec);

            // Confusion matrix for this spec, oracle-anchored:
            //   TP = oracle events this pipeline actually fired (matched()).
            //   FN = oracle events it FAILED to fire (oracleSize - TP), i.e. a
            //        violation the ground truth expected but the trace missed.
            //   FP = observed events for this spec matching NO oracle entry,
            //        i.e. a violation the pipeline reported that shouldn't exist.
            // TP/FN are counted by iterating the oracle (each oracle event is
            // one gold item); FP is counted by iterating the observations. The
            // per-event ratings[a,d] pair feeds Cohen's kappa (agreement between
            // the two pipelines on each oracle event).
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
            if (satisfies(oe, o)) return true;
        }
        return false;
    }

    private static int countFalsePositives(List<ObservedEvent> obs, List<OracleEvent> oracle) {
        int fp = 0;
        for (ObservedEvent o : obs) {
            boolean any = false;
            for (OracleEvent oe : oracle) {
                if (satisfies(oe, o)) { any = true; break; }
            }
            if (!any) fp++;
        }
        return fp;
    }

    /**
     * Does this observation satisfy this oracle event?
     *
     * <p>
     * Single definition on purpose: true positives are counted by walking the
     * oracle and false positives by walking the observations, and if the two
     * walks disagreed about what a match is, an event could count as neither or
     * as both.
     */
    private static boolean satisfies(OracleEvent oe, ObservedEvent o) {
        if (!oe.spec.equals(o.spec)) return false;
        if (!oe.errorType.equals(o.etype)) return false;
        if (oe.expectedMessageSubstring != null
                && !o.msg.contains(oe.expectedMessageSubstring)) return false;
        return locationMatches(oe, o);
    }

    /**
     * Compare an oracle event's declared location against an observation's
     * (INV-INS-116).
     *
     * <p>
     * The class is accepted against either form the line carries — fully
     * qualified or short — because the two admissible provenances write
     * different ones and neither is wrong. The method, when declared, must
     * match exactly; it is a single identifier in both forms, so there is
     * nothing to normalise and a loose comparison would only hide a real
     * mismatch.
     *
     * <p>
     * An oracle event that declares no location keeps matching on
     * {@code (spec, errorType)} alone. That is deliberate: under-specification
     * stays available to an oracle author who has no site to name, and the
     * absence of a field is the only way to ask for it, so it can never happen
     * by accident.
     */
    private static boolean locationMatches(OracleEvent oe, ObservedEvent o) {
        if (oe.locationClass != null
                && !oe.locationClass.equals(o.classQualified)
                && !oe.locationClass.equals(o.className)) {
            return false;
        }
        return oe.locationMethod == null || oe.locationMethod.equals(o.method);
    }

    private static List<ObservedEvent> filterBySpec(List<ObservedEvent> all, String spec) {
        List<ObservedEvent> out = new ArrayList<>();
        for (ObservedEvent o : all) if (o.spec.equals(spec)) out.add(o);
        return out;
    }

    /**
     * Harmonic-mean F1 with vacuous-truth edge conventions:
     * <ul>
     *   <li>{@code (tp + fp) == 0} → precision = 1.0. The pipeline made NO
     *       predictions for this spec, so it produced no false positives;
     *       precision is vacuously perfect ("everything I predicted was
     *       correct" is trivially true over an empty prediction set).</li>
     *   <li>{@code (tp + fn) == 0} → recall = 1.0. The oracle expected NO
     *       events for this spec, so there was nothing to miss; recall is
     *       vacuously perfect.</li>
     * </ul>
     * The two edges compose sensibly: an empty oracle scored against an empty
     * trace yields P=R=1.0 ⇒ F1=1.0. If both precision and recall collapse to
     * zero, F1 is forced to 0.0 to avoid a 0/0.
     */
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
     * Parse RVSEC violation lines from a logcat file, in the format the
     * on-device collector actually emits.
     *
     * <p>
     * A line contributes an event only if it carries an {@code RVSEC} tag
     * <em>and</em> its payload splits into at least {@link #VIOLATION_FIELDS}
     * comma-separated fields. Both conditions are needed: the tag alone also
     * selects lines the collector never wrote, and a violation payload is the
     * only {@code RVSEC} payload with that shape. Anything else — blank lines,
     * other tags, a short payload — is skipped rather than guessed at, because
     * a mis-split line would enter the comparison as a fabricated event and
     * silently move a verdict.
     *
     * @see #RVSEC_LINE for why the tag match is anchored the way it is
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
                if (!m.find()) continue;
                ObservedEvent e = parseViolationPayload(m.group("payload"));
                if (e != null) out.add(e);
            }
        }
        return out;
    }

    /**
     * Split one {@code RVSEC} payload into an {@link ObservedEvent}, or return
     * {@code null} if it is not a violation record.
     *
     * <p>
     * The field order is {@code ErrorSummary.toString()}'s, with the collector's
     * appended {@code expecting}:
     * {@code spec,classQualifiedName,className,methodName,location,errorType,expecting}.
     * Both class forms are kept. The line carries the class fully qualified
     * <em>and</em> short because {@code ErrorSummary} writes both, and the two
     * admissible oracle provenances happen to use different forms — a
     * hand-validated {@code cryptoapp} oracle names {@code MessageDigestUtil}
     * while a derived one names {@code okhttp3.internal.platform.Platform}. An
     * oracle that declares either must be able to match, which is why
     * {@link #locationMatches} accepts both.
     */
    private static ObservedEvent parseViolationPayload(String payload) {
        String[] f = payload.split(",", -1);
        if (f.length < VIOLATION_FIELDS) return null;
        String expecting = String.join(",",
                java.util.Arrays.copyOfRange(f, EXPECTING_INDEX, f.length)).trim();
        return new ObservedEvent(
                f[0].trim(),   // spec
                f[5].trim(),   // errorType
                expecting,     // the human-readable `expecting` text
                f[1].trim(),   // classQualifiedName
                f[2].trim(),   // className (short)
                f[3].trim(),   // methodName
                f[4].trim());  // location (file:line)
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

        // State-machine state carried across lines:
        //   inEvents    — are we currently inside the expected_events block?
        //   baseIndent  — indent of the "expected_events:" key; the block ends
        //                 when a line dedents back to (or past) this column.
        //   itemIndent  — indent of the "- " dash that opened the current list
        //                 item; continuation keys must be indented DEEPER than
        //                 this to belong to that item.
        //   haveCurrent — an item is open and its accumulated fields are pending
        //                 a flush() into the events list.
        // Indentation is the ONLY structural signal here (no tokenizer), so the
        // three indent columns fully determine the transitions below.
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

            // Step 1: before the block, wait for the "expected_events:" key.
            if (!inEvents) {
                // Detect inline empty list: `expected_events: []`
                if (content.startsWith("expected_events:")) {
                    String rhs = content.substring("expected_events:".length()).strip();
                    if (rhs.equals("[]")) return Collections.emptyList();
                    inEvents = true;
                    // Remember this column so Step 2 can detect the block's end.
                    baseIndent = indent;
                }
                continue;
            }

            // Step 2: inside the block, a line that dedents to <= baseIndent is a
            // sibling top-level key, so the expected_events block is over. Flush
            // any item still open, then RE-EVALUATE this same line at top level:
            // if it happens to be another "expected_events:" key we re-enter the
            // block rather than dropping the line (defensive against a schema
            // that repeats the key), which a plain "continue" would lose.
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

            // Step 3: a "- " at this deeper indent opens a NEW list item. Flush
            // the previous item first, reset the field accumulators, and record
            // this dash's column as itemIndent so Step 4 can tell continuation
            // keys (deeper) from the next dash (same column).
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

            // Step 4: a key indented DEEPER than the dash is a continuation key
            // of the current item (e.g. "error_type:", "location:"); accumulate
            // it into the same field holder. A key at itemIndent would instead
            // be the next dash handled by Step 3.
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
        // Step 5: end-of-file flush — the last item has no following line to
        // trigger its flush inside the loop, so emit it here if one is open.
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

    /**
     * One violation line as the on-device collector wrote it.
     *
     * <p>
     * {@code classQualified} and {@code className} are the same class in two
     * forms, both taken from the line rather than derived from one another:
     * {@code ErrorSummary} computes the short form itself, and reproducing that
     * here would be a second implementation of a rule the producer already
     * owns.
     */
    record ObservedEvent(String spec, String etype, String msg,
                         String classQualified, String className,
                         String method, String location) {}

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
