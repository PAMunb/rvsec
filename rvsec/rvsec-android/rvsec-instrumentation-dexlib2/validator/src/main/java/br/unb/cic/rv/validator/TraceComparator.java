package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.charset.CodingErrorAction;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
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

    /** Per-spec dexlib2 F1 floor. */
    private static final double GATE_F1_THRESHOLD = 0.98;
    /** Per-spec inter-pipeline kappa floor. */
    private static final double GATE_KAPPA_THRESHOLD = 0.9;

    /**
     * Same regex used by {@code rv-android/scripts/drive_cryptoapp.py}: an
     * optional {@code RVSEC:} prefix, a bracketed spec name, an error
     * type, and a colon-or-dash separated detail message.
     */
    private static final Pattern RVSEC_LINE = Pattern.compile(
            "(?:RVSEC:\\s*)?\\[(?<spec>\\w+)\\]\\s+(?<etype>\\w+)\\s*[:\\-]\\s*(?<msg>.*)$");

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

    // Visible for tests that want to introspect spec listings.
    static List<String> distinctSpecs(List<OracleEvent> events) {
        return new ArrayList<>(new TreeSet<>(events.stream().map(e -> e.spec).toList()));
    }
}
