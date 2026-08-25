package br.unb.cic.rvsec.crysl.crysl.cli;

import br.unb.cic.rvsec.crysl.core.CorpusReadError;
import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationGate;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationReport;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTarget;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTargets;
import br.unb.cic.rvsec.crysl.core.calibration.Measurement;
import br.unb.cic.rvsec.crysl.core.calibration.MonitorIndexCensus;
import br.unb.cic.rvsec.crysl.core.metric.CountingRule;
import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.M0Vitality;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.SpecRulePairing;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.crysl.CryslLifter;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.stream.Stream;

/**
 * The body of {@code calibrate}: the component measures the eight quantities itself and the gate
 * compares each against the route that produced the target.
 *
 * <h2>It measures rather than reading a report</h2>
 *
 * <p>Only three of the eight quantities appear in a {@code compare} report at all — the other five
 * are about corpora {@code compare} never reads ({@code generic}, {@code generic_new}) or about
 * facts no emitted table carries. So the gate re-reads the corpora, which is also what makes it
 * runnable on its own: a corpus move can be checked in seconds without a full comparison run
 * (task 12.8).
 *
 * <h2>Every measurement carries the rule the component counted under</h2>
 *
 * <p>The interesting disagreements in this corpus are not "one side is wrong" but "the two sides
 * counted different things", and only two rules printed side by side make that visible. Target 5 is
 * the clearest case: the route counts semicolons in raw text and the component counts
 * {@code ISLConstraint}s off the CrySL facade, which is a genuinely different implementation and is
 * therefore able to contradict it.
 */
final class CalibrateRun {

    /** The five corpora, in the order the census reports them. */
    static final List<String> CORPORA =
            List.of("jca", "jca_android", "jca_android_bug_predicate", "generic", "generic_new");

    /** The corpus the eight targets about {@code .mop} specifications are taken over. */
    static final String ANDROID_CORPUS = "jca_android";

    private CalibrateRun() {
    }

    /**
     * What the gate run produced.
     *
     * @param report      every target's outcome, both stamps and the publication decision
     * @param routeRetake the freshly re-taken target-8 route, when a regenerated monitor was
     *                    supplied; empty otherwise
     */
    record Summary(CalibrationReport report, Optional<String> routeRetake) {
    }

    /**
     * The five {@code .mop} corpora, lifted once.
     *
     * @param corpora     corpus name to the specifications that lifted, by name
     * @param failures    corpus name to how many files did not lift
     * @param androidText the {@code jca_android} sources, which M0's absorption scan is textual by
     *                    design and therefore needs
     */
    record MopSide(Map<String, Map<String, MopLift>> corpora, Map<String, Integer> failures,
                   Map<String, String> androidText) {

        Map<String, MopLift> android() {
            return corpora.get(ANDROID_CORPUS);
        }
    }

    /**
     * Lifts the five corpora.
     *
     * <p>Separate from {@link #run} because five of the eight quantities — targets 1, 2, 3, 7 and
     * 8 — are about the {@code .mop} side alone and can therefore be checked wherever this
     * repository is checked out, oracle or no oracle. Only targets 4, 5 and 6 need
     * {@code rvsec-cognicrypt}, and only target 8's <em>route</em> needs a generation pass. That
     * split is what keeps most of the gate reachable in CI instead of local-only.
     *
     * @param commit  the {@code rvsec} commit this run reads the corpora at
     * @param mopRoot the directory holding the five corpora, read-only
     * @return the lifts, the failure counts and the {@code jca_android} sources
     */
    static MopSide liftMopCorpora(String commit, Path mopRoot) {
        Map<String, Map<String, MopLift>> corpora = new LinkedHashMap<>();
        Map<String, Integer> failures = new LinkedHashMap<>();
        Map<String, String> androidText = new LinkedHashMap<>();
        MopLifter lifter = new MopLifter();
        for (String corpus : CORPORA) {
            Version version = new Version(corpus,
                    new SourceStamp(CompareRun.MOP_REPOSITORY, commit, Instant.now()));
            Map<String, MopLift> lifts = new LinkedHashMap<>();
            int failed = 0;
            for (Path file : mopFiles(mopRoot.resolve(corpus))) {
                String name = specificationName(file);
                try {
                    lifts.put(name, lifter.read(file, version));
                    if (ANDROID_CORPUS.equals(corpus)) {
                        androidText.put(name, read(file));
                    }
                } catch (LiftFailure e) {
                    // A file that does not lift is a finding about that file, counted here and
                    // published as part of target 1 rather than aborting the gate.
                    failed++;
                }
            }
            corpora.put(corpus, lifts);
            failures.put(corpus, failed);
        }
        return new MopSide(corpora, failures, androidText);
    }

    /**
     * The five measurements that need no oracle: targets 1, 2, 3, 7 and 8.
     *
     * @param mop the lifted corpora
     * @return the measurements, keyed by target id
     */
    static Map<String, Measurement> mopMeasurements(MopSide mop) {
        Map<String, Measurement> measurements = new LinkedHashMap<>();
        put(measurements, mopLift(mop.corpora(), mop.failures()));
        put(measurements, multiParameter("T2-generic-multiparameter",
                mop.corpora().get("generic"), true));
        put(measurements, multiParameter("T3-android-multiparameter", mop.android(), false));
        put(measurements, partialBinding(mop.android()));
        put(measurements, withoutMapOfMonitor(mop.android(), mop.androidText()));
        return measurements;
    }

    /**
     * Measures the eight quantities and checks them against the pinned targets.
     *
     * @param args     the parsed {@code calibrate} arguments
     * @param mopRoot  the directory holding the five {@code .mop} corpora, read-only
     * @param rulesDir the upstream oracle, read-only
     * @param monitor  a regenerated {@code MultiSpec_1RuntimeMonitor.java}, or {@code null}
     * @return the report and, when a monitor was supplied, the re-taken route
     */
    static Summary run(CalibrateArgs args, Path mopRoot, Path rulesDir, Path monitor) {
        MopSide mop = liftMopCorpora(args.commit, mopRoot);

        Version oracleVersion = new Version(CompareRun.ORACLE_CORPUS,
                new SourceStamp(CompareRun.ORACLE_REPOSITORY, args.oracleCommit, Instant.now()));
        CryslLifter.CorpusLift oracle;
        try {
            oracle = new CryslLifter().liftCorpus(rulesDir, oracleVersion);
        } catch (IOException e) {
            throw new CorpusReadError("the upstream oracle (" + e.getMessage() + ")", rulesDir);
        }

        Map<String, MopLift> android = mop.android();
        SpecRulePairing.Result pairing = SpecRulePairing.pair(candidates(android), rules(oracle));

        Map<String, Measurement> measurements = new LinkedHashMap<>(mopMeasurements(mop));
        put(measurements, rulesThatLoad(oracle));
        put(measurements, m3Denominator(oracle, rulesDir, pairing));
        put(measurements, pairing(android, pairing));

        Map<String, SourceStamp> runStamps = new LinkedHashMap<>();
        runStamps.put(CompareRun.MOP_REPOSITORY,
                new SourceStamp(CompareRun.MOP_REPOSITORY, args.commit, Instant.now()));
        runStamps.put(CompareRun.ORACLE_REPOSITORY,
                new SourceStamp(CompareRun.ORACLE_REPOSITORY, args.oracleCommit, Instant.now()));

        CalibrationReport report = CalibrationGate.check(CalibrationTargets.eight(), measurements,
                runStamps, CalibrationTargets.unreproducibleFigures());
        return new Summary(report, retake(monitor, android.keySet()));
    }

    /**
     * Re-takes target 8's route from a regenerated monitor, so the run can say whether the pinned
     * route still holds at today's corpus rather than assuming it carried (task 12.5).
     */
    private static Optional<String> retake(Path monitor, java.util.Set<String> fileNames) {
        if (monitor == null) {
            return Optional.empty();
        }
        MonitorIndexCensus census = MonitorIndexCensus.read(read(monitor));
        List<String> without = MonitorIndexCensus.asFileNames(census.notIndexing(), fileNames);
        CalibrationTarget pinned = CalibrationTargets.withoutMapOfMonitor();
        String value = without.size() + " of " + census.declared().size();
        String verdict = value.equals(pinned.value()) && without.equals(pinned.items())
                ? "agrees with the pinned route"
                : "DIFFERS from the pinned route (" + pinned.value() + ": "
                        + String.join(", ", pinned.items()) + ") - a finding about the target, to "
                        + "be adjudicated and never used to adjust the component";
        return Optional.of("target 8 route re-taken from " + monitor + ": " + value + " ("
                + String.join(", ", without) + ") - " + verdict + ". Rule: "
                + MonitorIndexCensus.RULE);
    }

    private static void put(Map<String, Measurement> measurements, Measurement measurement) {
        measurements.put(measurement.targetId(), measurement);
    }

    // ── the eight component-side measurements ─────────────────────────────────────────────────

    private static Measurement mopLift(Map<String, Map<String, MopLift>> corpora,
                                       Map<String, Integer> failures) {
        List<String> items = new ArrayList<>(CORPORA.size());
        int files = 0;
        int ok = 0;
        int failed = 0;
        for (String corpus : CORPORA) {
            int lifted = corpora.get(corpus).size();
            int broken = failures.get(corpus);
            items.add(corpus + " " + lifted + "/" + (lifted + broken));
            files += lifted + broken;
            ok += lifted;
            failed += broken;
        }
        return new Measurement("T1-mop-lift",
                files + " files, " + ok + " ok, " + failed + " fail", items,
                "files whose name ends in .mop under each of the five corpus directories; a file "
                        + "is ok when MopLifter.read returns a MopLift and fail when it raises "
                        + "LiftFailure. MOPNameSpace.init() runs before each file (INV-CONF-05) and "
                        + "the parse is never parallelised, because JavaMOPParser keeps state in a "
                        + "static field");
    }

    private static Measurement multiParameter(String id, Map<String, MopLift> corpus,
                                              boolean withHistogram) {
        Map<Integer, Integer> histogram = new TreeMap<>();
        int multi = 0;
        for (MopLift lift : corpus.values()) {
            int parameters = lift.declaredParameterCount();
            histogram.merge(parameters, 1, Integer::sum);
            if (parameters > 1) {
                multi++;
            }
        }
        List<String> items = withHistogram
                ? histogram.entrySet().stream()
                        .filter(entry -> entry.getKey() > 0)
                        .map(entry -> entry.getKey() + ":" + entry.getValue())
                        .toList()
                : List.of();
        return new Measurement(id, multi + " of " + corpus.size(), items,
                "MopLift.declaredParameterCount(), which is " + MopLift.PARAMETER_COUNTING_RULE
                        + " carried off the parse; multi-parameter means that count is greater "
                        + "than 1. The items are the histogram of the count over the corpus, "
                        + "rendered size:count, with the parameterless specifications left out "
                        + "because the target's histogram does the same");
    }

    private static Measurement rulesThatLoad(CryslLifter.CorpusLift oracle) {
        List<String> items = oracle.failures().stream()
                .map(failure -> failure.file().getFileName().toString())
                .sorted()
                .toList();
        return new Measurement("T4-rules-that-load",
                oracle.ok() + " of " + (oracle.ok() + oracle.failed()), items,
                "CryslLifter.liftCorpus, which constructs one CrySLModelReader per rule "
                        + "(INV-CONF-04) and reads each .crysl exactly as it stands; a rule loads "
                        + "when it yields a SpecModel and is a counted LiftFailure otherwise. The "
                        + "items are the files that did not load");
    }

    /**
     * The M3 denominator, taken off the CrySL facade rather than by counting semicolons.
     *
     * <p>The facade has nothing for the two rules that do not parse, so R1 is applied to their raw
     * text for the "all 49" half and the rule says so. The paired half needs no such addition: all
     * 22 paired rules load.
     */
    private static Measurement m3Denominator(CryslLifter.CorpusLift oracle, Path rulesDir,
                                             SpecRulePairing.Result pairing) {
        Map<String, Integer> perRule = new TreeMap<>();
        int all = 0;
        for (SpecModel rule : oracle.models()) {
            int clauses = rule.constraints().size();
            perRule.put(simpleName(rule.type()), clauses);
            all += clauses;
        }
        for (LiftFailure failure : oracle.failures()) {
            all += CountingRule.countClauses(read(rulesDir.resolve(failure.file().getFileName())));
        }
        List<String> items = new ArrayList<>();
        int paired = 0;
        for (SpecRulePairing.Pair pair : pairing.pairs()) {
            int clauses = perRule.getOrDefault(pair.rule().name(), 0);
            items.add(pair.rule().name() + "=" + clauses);
            paired += clauses;
        }
        items.sort(String::compareTo);
        return new Measurement("T5-m3-denominator", paired + " of " + all, items,
                "one clause per ISLConstraint of the CrySL facade, which is what M3's own "
                        + "denominator counts, summed over the rules the component paired; the two "
                        + "rules that do not parse have no facade, so R1 (" + CountingRule.R1.id()
                        + ") is applied to their raw text for the 'all' half only. Reported as "
                        + "'paired of all'");
    }

    private static Measurement pairing(Map<String, MopLift> android,
                                       SpecRulePairing.Result pairing) {
        return new Measurement("T6-pairing",
                pairing.pairs().size() + " of " + android.size(), pairing.unpairedNames(),
                SpecRulePairing.PAIRING_RULE);
    }

    private static Measurement partialBinding(Map<String, MopLift> android) {
        List<String> items = new ArrayList<>();
        int withParameter = 0;
        for (Map.Entry<String, MopLift> entry : android.entrySet()) {
            MopLift lift = entry.getValue();
            if (lift.declaredParameterCount() == 0) {
                continue;
            }
            withParameter++;
            if (lift.eventsBindingParameters() < lift.declaredEventCount()) {
                items.add(entry.getKey());
            }
        }
        items.sort(String::compareTo);
        return new Measurement("T7-partial-binding", items.size() + " of " + withParameter, items,
                "over the specifications declaring at least one parameter, those whose "
                        + "MopLift.eventsBindingParameters() is below their declaredEventCount() — "
                        + "that is, at least one event binds no declared parameter ("
                        + MopLift.EVENT_BINDING_COUNTING_RULE + "). Items are .mop file names "
                        + "without the extension");
    }

    private static Measurement withoutMapOfMonitor(Map<String, MopLift> android,
                                                   Map<String, String> text) {
        List<String> items = new ArrayList<>();
        for (Map.Entry<String, MopLift> entry : android.entrySet()) {
            MopLift lift = entry.getValue();
            M0Result m0 = M0Vitality.examine(lift.model(), lift.labelOrder(),
                    lift.monitorFacts(MisuseAbsorption.scan(text.get(entry.getKey()))),
                    Optional.empty());
            if (!m0.indexes()) {
                items.add(entry.getKey());
            }
        }
        items.sort(String::compareTo);
        return new Measurement("T8-without-map-of-monitor",
                items.size() + " of " + android.size(), items,
                "M0.1's AST proxy: " + M0Vitality.INDEXING_RULE + ". "
                        + M0Vitality.INDEXING_PROXY_CAVEAT);
    }

    // ── corpus access ─────────────────────────────────────────────────────────────────────────

    private static List<SpecRulePairing.Candidate> candidates(Map<String, MopLift> lifts) {
        List<SpecRulePairing.Candidate> candidates = new ArrayList<>(lifts.size());
        lifts.forEach((name, lift) ->
                candidates.add(new SpecRulePairing.Candidate(name, lift.model())));
        return candidates;
    }

    private static List<SpecRulePairing.Candidate> rules(CryslLifter.CorpusLift oracle) {
        List<SpecRulePairing.Candidate> candidates = new ArrayList<>(oracle.models().size());
        for (SpecModel model : oracle.models()) {
            candidates.add(new SpecRulePairing.Candidate(simpleName(model.type()), model));
        }
        return candidates;
    }

    private static List<Path> mopFiles(Path corpus) {
        try (Stream<Path> entries = Files.list(corpus)) {
            return entries.filter(path -> path.getFileName().toString().endsWith(".mop"))
                    .sorted().toList();
        } catch (IOException e) {
            throw new CorpusReadError("a .mop corpus (" + e.getMessage() + ")", corpus);
        }
    }

    private static String read(Path file) {
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new CorpusReadError("an input of the calibration gate (" + e.getMessage() + ")",
                    file);
        }
    }

    private static String specificationName(Path file) {
        String name = file.getFileName().toString();
        return name.endsWith(".mop") ? name.substring(0, name.length() - ".mop".length()) : name;
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }
}
