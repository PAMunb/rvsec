package br.unb.cic.rvsec.crysl.core.calibration;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.time.Instant;
import java.util.List;

/**
 * The eight targets, as data: each with its value, its counting rule, and the repository and commit
 * <strong>its own route</strong> was taken at.
 *
 * <h2>Why the stamps are not all the same</h2>
 *
 * <p>{@link #RVSEC_PINNED} is {@code 5fbe8173}, the commit the change's targets were pinned at, and
 * it is an ancestor of the {@code rvsec} HEAD rather than HEAD: the checkout moved four times while
 * the change was implemented. {@link #ORACLE_PINNED} is {@code f2f4d3b}, and it is the current HEAD
 * of {@code rvsec-cognicrypt}, which has not moved since May; the {@code CrySL-Rules} directory
 * itself has not changed since {@code 801e330} (2025-12-04). The Android side carries an API level
 * rather than a commit, because an SDK directory has none.
 *
 * <p>That asymmetry is the whole reason D-17 makes the stamp per corpus. A run stamped
 * {@code 5fbe8173} beside the {@code 47 of 49} of the upstream rules would attribute an
 * oracle-derived number to a repository that did not produce it.
 *
 * <h2>Every route here is one the component does not produce</h2>
 *
 * <p>Target 6 pairs through the two G-ORDER skips {@code order_alphabet_map.csv} declares, rather
 * than through the component's declared-type rule, and target 8 counts {@code MapOfMonitor} in the
 * <em>regenerated monitors</em> rather than through the AST proxy the component implements. Both
 * were written the other way once, and a gate built on them could not fail (RISK-006, D-18).
 */
public final class CalibrationTargets {

    /** The {@code rvsec} commit every {@code .mop}-side route was taken at. */
    public static final String RVSEC_PINNED = "5fbe8173";

    /** The {@code rvsec-cognicrypt} commit every oracle-side route was taken at. */
    public static final String ORACLE_PINNED = "f2f4d3b";

    /** The Android platform the signature index is anchored to; an SDK has no commit. */
    public static final String ANDROID_PINNED = "android-30";

    /** The day the routes of this set were run, for the stamps that carry an instant. */
    public static final Instant TAKEN_AT = Instant.parse("2026-08-24T00:00:00Z");

    /** The probe directory every {@code .mop}-side and oracle-side probe route lives in. */
    public static final String HARNESS = "rv-android/docs/handoff/20260824_arnes_adjudicacao";

    private CalibrationTargets() {
    }

    /** The eight, in the order the change's artifacts number them. */
    public static List<CalibrationTarget> eight() {
        return List.of(mopLift(), genericMultiParameter(), androidMultiParameter(), rulesThatLoad(),
                m3Denominator(), pairing(), partialBinding(), withoutMapOfMonitor());
    }

    private static SourceStamp rvsec() {
        return new SourceStamp("rvsec", RVSEC_PINNED, TAKEN_AT);
    }

    private static SourceStamp oracle() {
        return new SourceStamp("rvsec-cognicrypt", ORACLE_PINNED, TAKEN_AT);
    }

    /** Target 1: every {@code .mop} of the five corpora is read by {@code SpecExtractor}. */
    public static CalibrationTarget mopLift() {
        return new CalibrationTarget("T1-mop-lift",
                "SpecExtractor over the five .mop corpora",
                "215 files, 215 ok, 0 fail",
                List.of("jca 23/23", "jca_android 24/24", "jca_android_bug_predicate 23/23",
                        "generic 118/118", "generic_new 27/27"),
                "files whose name ends in .mop under each of the five corpus directories; a file "
                        + "is ok when javamop.parser.SpecExtractor.parse returns without throwing, "
                        + "and fail otherwise. One .mop file holds one specification in every "
                        + "corpus of this set, so files and specifications coincide here",
                RouteClass.INDEPENDENT_PROBE, HARNESS + "/probes/Census.java",
                "the five .mop corpora", rvsec(), PublishedMetric.MOP_LIFT,
                "the file counts are unchanged between the pinned commit and HEAD, so this target "
                        + "is not at risk from the corpus move that happened during the change");
    }

    /** Target 2: how many {@code generic} specifications declare more than one parameter. */
    public static CalibrationTarget genericMultiParameter() {
        return new CalibrationTarget("T2-generic-multiparameter",
                "multi-parameter specifications in generic, with the histogram",
                "93 of 118",
                List.of("1:25", "2:39", "3:28", "4:18", "5:7", "6:1"),
                "spec.getParameters().size() on the parsed AST; multi-parameter means that size is "
                        + "greater than 1. The items are the histogram of that size over the 118 "
                        + "files, rendered size:count, and they sum to 118 because every file of "
                        + "this corpus declares exactly one specification",
                RouteClass.INDEPENDENT_PROBE, HARNESS + "/probes/Census.java",
                "generic", rvsec(), PublishedMetric.MOP_LIFT,
                "an earlier independent count reached the same 93 and the same buckets, which is "
                        + "why this target is stated with the histogram and not only with the "
                        + "total: a total can coincide over a different distribution");
    }

    /** Target 3: {@code jca_android} declares no multi-parameter specification at all. */
    public static CalibrationTarget androidMultiParameter() {
        return new CalibrationTarget("T3-android-multiparameter",
                "multi-parameter specifications in jca_android",
                "0 of 24", List.of(),
                "spec.getParameters().size() > 1 on the parsed AST, over the 24 files of "
                        + "jca_android. The histogram is {0:2, 1:22}: two specifications declare no "
                        + "parameter at all and the other 22 declare exactly one",
                RouteClass.INDEPENDENT_PROBE, HARNESS + "/probes/Census.java",
                "jca_android", rvsec(), PublishedMetric.MOP_LIFT,
                "this is what makes the single-parameter slicing boundary irrelevant for this "
                        + "corpus: no specification of the set declares a tuple");
    }

    /** Target 4: the upstream rules that load with one fresh reader per rule. */
    public static CalibrationTarget rulesThatLoad() {
        return new CalibrationTarget("T4-rules-that-load",
                "upstream rules that load, one fresh reader per rule, no normalization",
                "47 of 49",
                List.of("OAEPParameterSpec.crysl", "SSLEngine.crysl"),
                "one CrySLModelReader constructed per rule (INV-CONF-04), reading the .crysl file "
                        + "exactly as it stands on disk with no lexical normalization of any kind; "
                        + "a rule loads when readRule returns a CrySLRule. The items are the two "
                        + "that do not load: OAEPParameterSpec uses the grammar's reserved word "
                        + "'alg' as an object name, and SSLEngine's ORDER references the "
                        + "undeclared event 'cp1' where line 11 declares 'ep1'",
                RouteClass.INDEPENDENT_PROBE, HARNESS + "/probes/V3Fresh.java",
                "CrySL-Rules", oracle(), PublishedMetric.ORACLE_LIFT,
                "both failures are upstream defects and are reported as findings, never repaired "
                        + "in place (INV-CONF-12)");
    }

    /** Target 5: the M3 denominator over the upstream oracle, under R1. */
    public static CalibrationTarget m3Denominator() {
        return new CalibrationTarget("T5-m3-denominator",
                "M3 denominator under R1: clauses in the 22 paired upstream rules",
                "80 of 119",
                List.of("Cipher=25", "CipherInputStream=3", "CipherOutputStream=3",
                        "DHGenParameterSpec=1", "GCMParameterSpec=4", "HMACParameterSpec=0",
                        "IvParameterSpec=3", "KeyGenerator=2", "KeyManagerFactory=3", "KeyPair=0",
                        "KeyPairGenerator=5", "KeyStore=5", "Mac=5", "MessageDigest=7",
                        "PBEKeySpec=3", "PBEParameterSpec=1", "SSLContext=1", "SecretKey=0",
                        "SecretKeySpec=3", "SecureRandom=1", "Signature=4", "TrustManagerFactory=1"),
                "R1: one clause per ';' inside CONSTRAINTS, comments removed, '&&' conjunctions "
                        + "NOT split. Counted over the raw text of the 49 .crysl files with no "
                        + "parser involved at all, and reported as 'paired of all': 80 clauses in "
                        + "the 22 rules a jca_android specification pairs with, 119 across all 49. "
                        + "The pair list comes from the hand-authored table of "
                        + "docs/20260824_mapeamento_mop_crysl.md section 2.2, not from the "
                        + "component's pairing",
                RouteClass.INDEPENDENT_PROBE,
                HARNESS + " R1 census (raw text, no parser) + docs/20260824_mapeamento_mop_crysl.md",
                "CrySL-Rules", oracle(), PublishedMetric.M3,
                "the component answers from the CrySL facade — one ISLConstraint per clause — "
                        + "which is a different implementation from counting semicolons, so the "
                        + "two can disagree and the target can fail. The committed "
                        + "constraint_table.csv (25/55, api30-anchored human judgement over "
                        + "jca_android) is a labelled historical reconciliation and is NOT a "
                        + "calibration route");
    }

    /** Target 6: which specifications have a rule at all. */
    public static CalibrationTarget pairing() {
        return new CalibrationTarget("T6-pairing",
                ".mop specifications that have an upstream rule as their oracle",
                "22 of 24",
                List.of("IvChainJunction", "RandomStringPassword"),
                "the 24 jca_android specifications minus the two that "
                        + "data/jca_android/order_alphabet_map.csv declares G-ORDER skips. A "
                        + "declared skip is prose in that file's header and deliberately never a "
                        + "data row - any row at all, even an empty one, would take the file out "
                        + "of the skip and make the gate look for a rule that does not exist - so "
                        + "the route is the two declarations and not the per-row disposition "
                        + "column, which the change's own artifacts name loosely. Each carries a "
                        + "written reason: RandomStringPassword is a dataflow bridge "
                        + "over two JDK conversions no rule orders, and IvChainJunction is a "
                        + "junction whose ere accepts every sequence of its own events and which "
                        + "therefore states no ordering to compare. The items are the two skips, "
                        + "named by .mop file name without the extension",
                RouteClass.COMMITTED_ARTIFACT, "data/jca_android/order_alphabet_map.csv "
                        + "(the two declared G-ORDER skips)",
                "jca_android", rvsec(), PublishedMetric.PAIRING,
                "the committed map is anchored to the abandoned api30 corpus and cites .cryptsl "
                        + "files, but both written reasons survive the re-anchoring to upstream, "
                        + "which is why it is a usable route. The component reaches the same 22 "
                        + "only because its pairing is INJECTIVE: CipherSpec.mop and "
                        + "IvChainJunction.mop declare byte-identically the same type, so a plain "
                        + "declared-type function would pair both with Cipher.crysl and answer 23. "
                        + "INV-CONF-11 states 'by declared type' and does not state injectivity — "
                        + "artifact debt for /opsx:update, recorded rather than assumed");
    }

    /** Target 7: specifications whose parameter binding is partial or empty. */
    public static CalibrationTarget partialBinding() {
        return new CalibrationTarget("T7-partial-binding",
                "specifications with at least one event that binds no declared parameter",
                "5 of 22",
                List.of("HMACParameterSpecSpec", "KeyPairSpec", "KeyStoreSpec", "PBEKeySpecSpec",
                        "RandomStringPassword"),
                "over the 22 jca_android specifications that declare at least one parameter, those "
                        + "with at least one event whose getMOPParametersOnSpec() is empty — that "
                        + "is, an event binding none of the parameters the specification declares. "
                        + "The denominator is 22 and not 24 because two specifications declare no "
                        + "parameter at all and the question does not arise for them. Items are "
                        + ".mop file names without the extension",
                RouteClass.INDEPENDENT_PROBE, HARNESS + "/probes/Binding.java",
                "jca_android", rvsec(), PublishedMetric.M0,
                "route and component consult the same parser API and are still different routes: "
                        + "the probe re-parses each file itself and the component reads the count "
                        + "the lift carried. What this target cannot detect is a defect in "
                        + "getMOPParametersOnSpec() itself, and saying so is cheaper than "
                        + "pretending otherwise");
    }

    /** Target 8: specifications for which no {@code MapOfMonitor} is generated. */
    public static CalibrationTarget withoutMapOfMonitor() {
        return new CalibrationTarget("T8-without-map-of-monitor",
                "specifications for which the generated monitor builds no MapOfMonitor",
                "5 of 24",
                List.of("CipherInputStreamSpec", "CipherOutputStreamSpec", "HMACParameterSpecSpec",
                        "KeyStoreSpec", "RandomStringPassword"),
                "the 24 jca_android specifications are regenerated with rv-monitor-generator into "
                        + "a scratch directory, and MultiSpec_1RuntimeMonitor.java is read for a "
                        + "field declaration of the shape 'MapOfMonitor<XMonitor> X_..._Map'. A "
                        + "specification without such a field indexes nothing and compiles to one "
                        + "monitor for the whole program. The monitor names a specification by its "
                        + "DECLARED name, so RandomStringPasswordSpec is mapped back to its file "
                        + "RandomStringPassword.mop and IvChainJunctionSpec to IvChainJunction.mop "
                        + "before the items are compared",
                RouteClass.REGENERATED_ARTIFACT,
                "rv-monitor-generator over the 24 jca_android specs, into scratch; the generated "
                        + "MultiSpec_1RuntimeMonitor.java",
                "jca_android", rvsec(), PublishedMetric.M0,
                "the component answers with an AST proxy — at least one declared parameter and at "
                        + "least one event binding one — and the proxy is not this measurement. "
                        + "This is the only route for this quantity that can come out wrong, which "
                        + "is what it costs a generation pass for (D-18)");
    }

    /**
     * The figures the change's own artifacts publish that no written rule reproduces (task 12.10).
     *
     * <p>{@code 101/71} is not merely unreproduced but impossible in principle: it is offered as
     * the total after splitting {@code &&}, and splitting a clause can only <em>raise</em> a count,
     * so a split total below the unsplit 119 cannot be right. Three independent routes agree on
     * 119 / 125 / 145. The hypothesis — recorded as a hypothesis — is that the pair was measured
     * over the abandoned {@code api30} corpus, which deletes clauses relative to upstream; that is
     * the only way a split total lands below 119, and D-06 abandoned that oracle, so it is not
     * worth chasing.
     */
    public static List<UnreproducibleFigure> unreproducibleFigures() {
        return List.of(
                new UnreproducibleFigure("101/71 clauses when '&&' is split",
                        "specs/conformance/spec.md section M3, and task 8.6",
                        "three independent routes over the 49 upstream rules — a text census, the "
                                + "CrySL facade, and a raw-text count with neither parser involved "
                                + "— agree on 119 unsplit, 125 with the 6 '&&' split and 145 with "
                                + "the 26 '=>' split. No reading reaches 101, and none can: "
                                + "splitting a clause can only raise a count",
                        "125 across all 49 rules, 86 across the 22 paired",
                        "R1 with the 6 top-level '&&' inside CONSTRAINTS split into separate "
                                + "clauses"),
                new UnreproducibleFigure("117/87 clauses when the sides of '=>' are split",
                        "specs/conformance/spec.md section M3, and task 8.6",
                        "the same three routes answer 145/99 for this rule; 117 is below the "
                                + "unsplit 119 and is therefore impossible for the same reason",
                        "145 across all 49 rules, 99 across the 22 paired",
                        "R1 with the two sides of each of the 26 '=>' counted as separate "
                                + "clauses"));
    }
}
