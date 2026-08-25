package br.unb.cic.rvsec.crysl.crysl.cli;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.CorpusReadError;
import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.compare.AlphabetMap;
import br.unb.cic.rvsec.crysl.core.compare.Observability;
import br.unb.cic.rvsec.crysl.core.compare.Pipeline;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter;
import br.unb.cic.rvsec.crysl.core.emit.CsvSchema;
import br.unb.cic.rvsec.crysl.core.emit.JsonEmitter;
import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter;
import br.unb.cic.rvsec.crysl.core.metric.ClauseVerdict;
import br.unb.cic.rvsec.crysl.core.metric.ConformanceReport;
import br.unb.cic.rvsec.crysl.core.metric.CountingRule;
import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.M0Vitality;
import br.unb.cic.rvsec.crysl.core.metric.M1Events;
import br.unb.cic.rvsec.crysl.core.metric.M1Result;
import br.unb.cic.rvsec.crysl.core.metric.M2Order;
import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.metric.M3Constraints;
import br.unb.cic.rvsec.crysl.core.metric.M3Result;
import br.unb.cic.rvsec.crysl.core.metric.M4Predicates;
import br.unb.cic.rvsec.crysl.core.metric.MetricResult;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.PredicateGraph;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSiteFacts;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSubstrate;
import br.unb.cic.rvsec.crysl.core.metric.Silence;
import br.unb.cic.rvsec.crysl.core.metric.SpecRulePairing;
import br.unb.cic.rvsec.crysl.core.metric.SpecificationIdioms;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.crysl.CryslLifter;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import br.unb.cic.rvsec.crysl.mop.PredicateSite;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

/**
 * The body of {@code compare}: M0–M4 over one {@code .mop} corpus against the single upstream
 * oracle, emitted as JSON, CSV and Markdown.
 *
 * <h2>Two stamps, because the input is two repositories</h2>
 *
 * <p>{@code --commit} stamps the {@code .mop} side and {@code --oracle-commit} stamps the rules,
 * and the two {@link Version}s built here travel into {@link ConformanceReport}'s header and into
 * every emitted table (INV-CONF-01, D-17). The repository names are constants rather than
 * arguments: there is one oracle (D-06), it is {@code rvsec-cognicrypt/CrySL-Rules}, and the
 * {@code .mop} sets live in {@code rvsec}. What the caller asserts is the <em>state</em> of each,
 * which is the commit, and that is what has no default.
 *
 * <p>The pairing rule sits in the same header, because pairing is by declared type and never by
 * file name; a number published under the older by-name pairing has to be re-stamped before it can
 * be reused (INV-CONF-11). It is read off {@link SpecRulePairing.Result#pairingRule()} rather than
 * restated here, so the header cannot drift from the rule that produced the pairs.
 *
 * <h2>M0 gates, and it gates by not computing</h2>
 *
 * <p>Every specification of the corpus receives an M0 verdict, paired or not, because vitality is a
 * question about the file alone. M1–M4 arrive through {@link Pipeline#run}: the supplier is invoked
 * only when M0 did not refuse, so a refused specification's downstream verdicts are not filtered
 * out of the report — they are never produced (INV-CONF-09). The rows the emitters publish are
 * collected from inside that supplier for the same reason.
 *
 * <h2>One identity per specification</h2>
 *
 * <p>Every metric names a specification by its file name without the {@code .mop} extension, which
 * is what {@link M0Vitality} derives and what {@code constraint_table.csv} already holds. The
 * committed {@code predicate_graph.csv} writes {@code CipherSpec.mop} in its {@code file} column;
 * the emitted one writes {@code CipherSpec}, so that one specification has one identity across the
 * five metrics of a single report. The schema — the columns — is untouched.
 */
final class CompareRun {

    /** The repository the {@code .mop} corpora are read from. */
    static final String MOP_REPOSITORY = "rvsec";

    /** The repository the single oracle is read from (D-06). */
    static final String ORACLE_REPOSITORY = "rvsec-cognicrypt";

    /** The corpus name the oracle is stamped under. */
    static final String ORACLE_CORPUS = "CrySL-Rules";

    static final String REPORT_JSON = "conformance_report.json";
    static final String M1_MARKDOWN = "m1_events.md";
    static final String M2_MARKDOWN = "m2_order.md";
    static final String M4_MARKDOWN = "m4_predicates.md";

    /**
     * What the M2 counting rule has to say about the normalization this command cannot apply.
     *
     * <p>N3 removes states a specification marks accepting purely to give a predicate an acceptance
     * point. Which states those are is human judgement — the {@code alias match*} names do not
     * survive the lift — and {@code compare} has no argument to declare them, so N3 is not applied
     * and the verdicts below are taken over the wider accepting set. Said in the counting rule and
     * not in a comment, because it changes what the numbers mean (INV-CONF-02).
     */
    static final String N3_NOT_DECLARED =
            "N3 (acceptance narrowing) was NOT applied by this run: the states a specification "
                    + "marks accepting only to give a predicate an acceptance point are declared by "
                    + "the caller - the alias names do not survive the lift - and this command has "
                    + "no argument to declare them. Every verdict here is therefore taken over the "
                    + "specification's full accepting set; CipherSpec's s3 is the one such state "
                    + "measured in jca_android";

    private CompareRun() {
    }

    /**
     * What the run produced, for the line {@code compare} prints when it is done.
     *
     * @param specifications specifications the corpus holds and that lifted
     * @param liftFailures   {@code .mop} files that did not lift; findings, not failures
     * @param rules          rules of the oracle that lifted
     * @param ruleFailures   rules that did not lift; the two upstream residuals live here
     * @param pairs          specifications paired with a rule, by declared type
     * @param refused        specifications M0 refused, which receive no M1-M4 verdict
     * @param compared       paired specifications that reached M1-M4
     * @param written        the files that were written, in the order they were written
     */
    record Summary(int specifications, int liftFailures, int rules, int ruleFailures, int pairs,
                   int refused, int compared, List<Path> written) {
    }

    /**
     * Reads both corpora, runs the five metrics and emits the three formats.
     *
     * @param args       the parsed {@code compare} arguments
     * @param mopDir     the {@code .mop} corpus, already checked readable
     * @param rulesDir   the upstream oracle, already checked readable
     * @param alphabetCsv the alphabet map M2 takes its ε-erasure decisions from
     * @param androidJar the platform jar, used as an index and never on a parser classpath
     * @return what was measured and where it went
     */
    static Summary run(CompareArgs args, Path mopDir, Path rulesDir, Path alphabetCsv,
                       Path androidJar) {
        Instant mopReadAt = Instant.now();
        Version mopVersion = new Version(args.corpus,
                new SourceStamp(MOP_REPOSITORY, args.commit, mopReadAt));

        MopLifter lifter = new MopLifter();
        Map<String, MopLift> lifts = new LinkedHashMap<>();
        Map<String, String> texts = new LinkedHashMap<>();
        int mopFailures = 0;
        for (Path file : mopFiles(mopDir)) {
            String name = specificationName(file);
            String text = read(file);
            try {
                lifts.put(name, lifter.read(file, mopVersion));
                texts.put(name, text);
            } catch (LiftFailure e) {
                // A file that does not lift is a finding about that file, counted in the summary
                // and leaving the exit code at OK.
                mopFailures++;
            }
        }

        ApiIndex index = index(androidJar);
        Observability platform = observability(androidJar);
        AlphabetMap map = alphabet(alphabetCsv);

        Instant oracleReadAt = Instant.now();
        Version oracleVersion = new Version(ORACLE_CORPUS,
                new SourceStamp(ORACLE_REPOSITORY, args.oracleCommit, oracleReadAt));
        CryslLifter.CorpusLift oracle = oracle(rulesDir, oracleVersion);

        SpecRulePairing.Result pairing = SpecRulePairing.pair(candidates(lifts), rules(oracle));
        Map<String, SpecRulePairing.Pair> bySpecification = new LinkedHashMap<>();
        for (SpecRulePairing.Pair pair : pairing.pairs()) {
            bySpecification.put(pair.specification().name(), pair);
        }

        // The predicate graph spans the whole corpus under measurement: the reachability questions
        // M4 asks - an orphan read, a dead-end write - are about predicates that cross files, and a
        // graph built per specification would answer them wrong rather than not answer them.
        List<PredicateSiteFacts> corpusSites = new ArrayList<>();
        for (Map.Entry<String, MopLift> entry : lifts.entrySet()) {
            corpusSites.addAll(sitesOf(entry.getKey(), entry.getValue()));
        }
        PredicateGraph graph = PredicateGraph.of(corpusSites);

        List<MetricResult> results = new ArrayList<>();
        List<M1Result> m1 = new ArrayList<>();
        List<M2Result> m2 = new ArrayList<>();
        List<CsvEmitter.M4Row> m4Rows = new ArrayList<>();
        List<CsvEmitter.ConstraintRow> constraintRows = new ArrayList<>();
        List<CsvEmitter.DivergenceRow> divergences = new ArrayList<>();
        M4Predicates m4 = new M4Predicates();
        int refused = 0;
        int compared = 0;

        for (Map.Entry<String, MopLift> entry : lifts.entrySet()) {
            String name = entry.getKey();
            MopLift lift = entry.getValue();
            M0Result m0 = M0Vitality.examine(lift.model(), lift.labelOrder(),
                    lift.monitorFacts(MisuseAbsorption.scan(texts.get(name))), Optional.of(index));
            SpecRulePairing.Pair pair = bySpecification.get(name);

            Pipeline.Outcome outcome = pair == null
                    // No rule is the oracle of this specification, so there is nothing for M1-M4 to
                    // compare it against. It still carries its M0 verdict into the report.
                    ? Pipeline.run(m0, List::of)
                    : Pipeline.run(m0, () -> downstream(name, lift, texts.get(name), pair, map,
                            platform, graph, m4, m0, m1, m2, m4Rows, constraintRows));
            results.addAll(outcome.results());

            if (m0.refused()) {
                refused++;
            } else if (pair != null) {
                compared++;
            }
            for (Silence divergence : m0.divergences()) {
                divergences.add(divergenceRow(divergence));
            }
        }

        Path outputDir = Paths.get(args.outputDir);
        List<Path> written = emit(args, mopVersion, oracleVersion, pairing, oracle, outputDir,
                results, m1, m2, m4Rows, constraintRows, divergences);

        return new Summary(lifts.size(), mopFailures, oracle.ok(), oracle.failed(),
                pairing.pairs().size(), refused, compared, written);
    }

    /**
     * M1 through M4 for one paired specification, invoked only when M0 did not refuse.
     *
     * <p>The collector lists are filled here rather than after the loop, and that is the
     * INV-CONF-09 mechanism rather than an implementation detail: a row that is never built cannot
     * be published by a later reader who forgets which specifications were refused.
     */
    private static List<MetricResult> downstream(String name, MopLift lift, String text,
                                                 SpecRulePairing.Pair pair, AlphabetMap map,
                                                 Observability platform, PredicateGraph graph,
                                                 M4Predicates m4, M0Result m0,
                                                 List<M1Result> m1Out, List<M2Result> m2Out,
                                                 List<CsvEmitter.M4Row> m4Out,
                                                 List<CsvEmitter.ConstraintRow> constraintsOut) {
        String rule = pair.rule().name();
        SpecModel ruleModel = pair.rule().model();

        M1Result m1 = M1Events.compare(name, lift.model(), rule, ruleModel);
        m1Out.add(m1);

        M2Order.Options options = new M2Order.Options(lift.site(), m0.indexes(), Set.of(), platform);
        M2Result m2 = M2Order.compare(name, lift.model(), lift.morphism(), rule, ruleModel, map,
                options).result();
        m2Out.add(m2);

        M3Result m3 = M3Constraints.census(lift.model(), ruleModel,
                SpecificationIdioms.of(name, text));
        for (ClauseVerdict clause : m3.rows()) {
            constraintsOut.add(new CsvEmitter.ConstraintRow(name, clause.ruleSite().toString(),
                    clause.site().map(Provenance::toString).orElse(""), constraintVerdict(clause)));
        }

        M4Predicates.M4Analysis analysis = m4.compare(name, rule, sitesOf(name, lift), ruleModel,
                graph, M4Predicates.Judgements.empty());
        m4Out.addAll(analysis.rows());

        return List.of(m1, m2, m3, analysis.result());
    }

    /**
     * Writes the three formats, in the order a reader of the output directory meets them.
     *
     * <p>Nothing is written outside {@code --out} (INV-CONF-12), and every file goes through an
     * emitter of {@code core.emit}, so no table reaches disk without both stamps and its counting
     * rule.
     */
    private static List<Path> emit(CompareArgs args, Version mopVersion, Version oracleVersion,
                                   SpecRulePairing.Result pairing, CryslLifter.CorpusLift oracle,
                                   Path outputDir, List<MetricResult> results, List<M1Result> m1,
                                   List<M2Result> m2, List<CsvEmitter.M4Row> m4Rows,
                                   List<CsvEmitter.ConstraintRow> constraintRows,
                                   List<CsvEmitter.DivergenceRow> divergences) {
        List<Path> written = new ArrayList<>();

        JsonEmitter json = new JsonEmitter();
        ConformanceReport report = new ConformanceReport(mopVersion, oracleVersion,
                pairing.pairingRule(), results);
        written.add(json.write(outputDir, REPORT_JSON, json.toJson(report)));

        CsvEmitter csv = new CsvEmitter(mopVersion, oracleVersion);
        written.add(csv.write(outputDir, CsvSchema.PREDICATE_GRAPH,
                csv.predicateGraph(M4Predicates.COUNTING_RULE, m4Rows)));
        written.add(csv.write(outputDir, CsvSchema.CONSTRAINT_TABLE,
                csv.constraintTable(CountingRule.R1.toString(), constraintRows)));
        written.add(csv.write(outputDir, CsvSchema.DIVERGENCE_RECORD,
                csv.divergenceRecord(M0Vitality.countingRule(), divergences)));

        MarkdownEmitter markdown = new MarkdownEmitter();
        written.add(markdown.write(outputDir, M1_MARKDOWN,
                M1Events.table(m1, mopVersion, oracleVersion, pairing.pairingRule())
                        .markdown(List.of())));
        String m2Rule = M2Order.reportCountingRule(M2Order.census(oracle.models()))
                + " | " + N3_NOT_DECLARED;
        written.add(markdown.write(outputDir, M2_MARKDOWN,
                markdown.orderReport("M2 · " + args.corpus + " against the upstream rules",
                        mopVersion, oracleVersion, m2Rule, M2Order.publish(m2))));
        written.add(markdown.write(outputDir, M4_MARKDOWN,
                markdown.predicateReport("M4 · " + args.corpus + " against the upstream rules",
                        mopVersion, oracleVersion, M4Predicates.COUNTING_RULE, m4Rows)));

        return written;
    }

    /**
     * The clause verdict in the vocabulary {@code constraint_table.csv} already publishes.
     *
     * <p>The four values are exclusive and exhaustive because {@link ClauseVerdict} makes them so:
     * a clause is implemented through a recognised idiom, or the reader declined to decide, or it
     * is genuinely not implemented. The alias-table case is separated from plain agreement because
     * an allow-list transcribed character for character is <em>more permissive</em> than the rule
     * when it is consulted through the table.
     */
    private static String constraintVerdict(ClauseVerdict clause) {
        if (clause.implemented()) {
            return clause.widenedByAliasTable() ? "MOP-MAIS-PERMISSIVO" : "IGUAL";
        }
        return clause.refused() ? "NAO-DERIVADO" : "CRYSL-NAO-IMPLEMENTADO";
    }

    /** One M0 silence whose disposition is the divergence record rather than any verdict. */
    private static CsvEmitter.DivergenceRow divergenceRow(Silence silence) {
        return new CsvEmitter.DivergenceRow(silence.site().file(), "", silence.cause().name(),
                silence.detail(), silence.cause().reason(), "");
    }

    /**
     * The {@code -mop} module's predicate sites in the shape {@code -core} compares.
     *
     * <p>{@code argumentTypes} is left empty rather than guessed: a type inferred from an argument
     * name would be a fabrication carrying the authority of a measurement. The event a site sits in
     * and whether it is in an event body or a {@code @match} handler have no source in the current
     * lift, so every site crosses as a body site with no event name, which costs the derived
     * {@code verdict} column its {@code :acceptance} half and costs the comparison nothing — arity,
     * polarity and argument position are all on the reference itself.
     */
    private static List<PredicateSiteFacts> sitesOf(String specification, MopLift lift) {
        List<PredicateSiteFacts> facts = new ArrayList<>(lift.predicateSites().size());
        for (PredicateSite site : lift.predicateSites()) {
            facts.add(new PredicateSiteFacts(specification, section(site.kind()),
                    substrate(site.substrate()), "", PredicateSiteFacts.SiteKind.BODY,
                    site.verdict(), List.of(), site.ref()));
        }
        return facts;
    }

    private static PredicateSiteFacts.Section section(PredicateSite.Kind kind) {
        return switch (kind) {
            case ENSURES -> PredicateSiteFacts.Section.ENSURES;
            case REQUIRES -> PredicateSiteFacts.Section.REQUIRES;
            case NEGATES -> PredicateSiteFacts.Section.NEGATES;
        };
    }

    private static PredicateSubstrate substrate(PredicateSite.Substrate substrate) {
        return switch (substrate) {
            case EXECUTION_CONTEXT -> PredicateSubstrate.EXECUTION_CONTEXT;
            case PREDICATE_STORE -> PredicateSubstrate.PREDICATE_STORE;
        };
    }

    private static List<SpecRulePairing.Candidate> candidates(Map<String, MopLift> lifts) {
        List<SpecRulePairing.Candidate> candidates = new ArrayList<>(lifts.size());
        for (Map.Entry<String, MopLift> entry : lifts.entrySet()) {
            candidates.add(new SpecRulePairing.Candidate(entry.getKey(), entry.getValue().model()));
        }
        return candidates;
    }

    private static List<SpecRulePairing.Candidate> rules(CryslLifter.CorpusLift oracle) {
        List<SpecRulePairing.Candidate> candidates = new ArrayList<>(oracle.models().size());
        for (SpecModel model : oracle.models()) {
            candidates.add(new SpecRulePairing.Candidate(simpleName(model.type()), model));
        }
        return candidates;
    }

    /**
     * The {@code .mop} files of the corpus, in name order.
     *
     * <p>A directory that holds none is refused rather than measured: a run over an empty corpus
     * emits a report of zero rows and exits {@code 0}, which is a green with nothing behind it —
     * the one outcome this component exists to stop producing.
     */
    private static List<Path> mopFiles(Path mopDir) {
        try (Stream<Path> entries = Files.list(mopDir)) {
            List<Path> files = entries
                    .filter(path -> path.getFileName().toString().endsWith(".mop"))
                    .sorted()
                    .toList();
            if (files.isEmpty()) {
                throw new CorpusReadError(
                        "a .mop corpus with at least one specification in it (this directory holds "
                                + "no *.mop file, and a run over an empty corpus would publish a "
                                + "report of zero rows and exit 0)", mopDir);
            }
            return files;
        } catch (IOException e) {
            throw new CorpusReadError("the .mop corpus (" + e.getMessage() + ")", mopDir);
        }
    }

    private static CryslLifter.CorpusLift oracle(Path rulesDir, Version oracleVersion) {
        CryslLifter.CorpusLift lift;
        try {
            lift = new CryslLifter().liftCorpus(rulesDir, oracleVersion);
        } catch (IOException e) {
            throw new CorpusReadError("the upstream oracle (" + e.getMessage() + ")", rulesDir);
        }
        if (lift.models().isEmpty()) {
            throw new CorpusReadError(
                    "an oracle with at least one rule in it (this directory yielded no lifted "
                            + "rule, so every specification would be reported unpaired)", rulesDir);
        }
        return lift;
    }

    private static ApiIndex index(Path androidJar) {
        try {
            return ApiIndex.index(androidJar);
        } catch (IOException e) {
            throw new CorpusReadError("android.jar (" + e.getMessage() + ")", androidJar);
        }
    }

    private static Observability observability(Path androidJar) {
        try {
            return Observability.of(androidJar);
        } catch (IOException e) {
            throw new CorpusReadError("android.jar (" + e.getMessage() + ")", androidJar);
        }
    }

    private static AlphabetMap alphabet(Path alphabetCsv) {
        try {
            return AlphabetMap.read(alphabetCsv);
        } catch (IOException e) {
            throw new CorpusReadError("the order alphabet map (" + e.getMessage() + ")",
                    alphabetCsv);
        }
    }

    private static String read(Path file) {
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new CorpusReadError("a specification of the corpus (" + e.getMessage() + ")",
                    file);
        }
    }

    /** The corpus identifier of a {@code .mop} file: its name, without the extension. */
    private static String specificationName(Path file) {
        String name = file.getFileName().toString();
        return name.endsWith(".mop") ? name.substring(0, name.length() - ".mop".length()) : name;
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }
}
