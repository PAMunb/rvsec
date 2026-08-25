package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.emit.StampedTable;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

/**
 * M1: how much of the rule's declared event set the specification actually monitors, and what each
 * side has that the other does not.
 *
 * <h2>Coverage never travels alone</h2>
 *
 * <p>A coverage percentage is the single most misleading number this component could publish. "The
 * specification covers 89% of the rule" says nothing about which 11% is missing, and it says
 * nothing at all about the calls the specification monitors that the rule never named — a set that
 * does not appear in the fraction at any value. The two differences mean opposite things: a
 * rule-only signature is an obligation nobody monitors, a MOP-only signature is a monitor watching
 * something the oracle does not ask for. So this class has <strong>no method that renders a
 * coverage figure as text</strong>. The percentage exists only as one cell of a row that also
 * carries both lists, written by {@link #table}, and {@link M1Result} cannot even be constructed
 * without both lists. That is the refusal of task 7.2, expressed as structure rather than as a
 * review comment.
 *
 * <h2>R-M1, the counting rule</h2>
 *
 * <p>A {@code .mop} signature <em>m</em> matches a rule signature <em>r</em> when the declaring
 * types agree, the method names are equal, and the parameter lists agree position by position.
 * Return types are <strong>not</strong> compared, and that is a measurement rather than a
 * convenience: the CrySL side carries a return type only where the rule binds the result, so
 * {@code MessageDigest.crysl} declares {@code getInstance(java.lang.String)} as returning
 * {@code void} while the pointcut that monitors it declares {@code MessageDigest}, and it declares
 * {@code digest(byte[], int, int)} as {@code void} where the platform method returns {@code int}.
 * Comparing return types would report every such pair as two different calls. Return type is not
 * part of Java's overload identity either, so nothing is lost.
 *
 * <p>Type names agree when they are equal, or when one of them is unqualified and the simple names
 * are equal. The specification side keeps types as the pointcut writes them, resolved through the
 * file's imports where an import exists, so a pointcut writes {@code String} where the rule writes
 * {@code java.lang.String}. Folding is one-sided on purpose: two <em>qualified</em> names that
 * differ stay different, so {@code javax.crypto.Cipher} never matches a hypothetical
 * {@code java.security.Cipher}.
 *
 * <h2>The two wildcards are not the same object</h2>
 *
 * <p>Both notations have a hole and R-M1 treats them differently, because they say different
 * things.
 *
 * <p>A pointcut's {@code ..} and {@code *} are a <strong>matcher</strong>. {@code call(void
 * MessageDigest.update(..))} is a claim about a set of calls, and the honest reading against the
 * oracle is the set of declared signatures it matches — all four {@code update} overloads. So a
 * MOP wildcard expands.
 *
 * <p>A rule's {@code _}, which the façade renders as {@code AnyType}, is a <strong>hole in a
 * declared obligation</strong>: {@code g2: getInstance(algorithm, _)} names one signature and
 * leaves one argument unbound. Expanding that hole against whatever overloads the specification
 * happens to name would make the oracle a function of the artifact under test — coverage would rise
 * because the specification wrote more overloads, which is not a measurement. So the rule's hole is
 * covered only by a specification that leaves the same position open, and the extra overloads are
 * reported as MOP-only where a reader can see them and decide.
 *
 * <p>The corpus shows both outcomes, which is what makes the asymmetry a rule and not a fudge.
 * {@code SecureRandomSpec.mop} writes {@code getInstance(String, ..)} and covers the rule's
 * {@code g2} hole. {@code MessageDigestSpec.mop} writes the two overloads out —
 * {@code getInstance(String, String)} and {@code getInstance(String, Provider)} — so the rule's
 * {@code getInstance(algorithm, _)} stays uncovered and the two overloads are reported MOP-only.
 * Neither file is wrong; the report says what each of them did.
 *
 * <h2>Refusals</h2>
 *
 * <p>M1 emits no {@link Unknown} of its own. Its one candidate refusal — a pointcut whose signature
 * does not exist on the platform — is decided by M0.3 against the {@code android.jar} index before
 * M1 is allowed to run at all (INV-CONF-09, design D-09), and a specification M0 refuses never
 * reaches this class. Repeating the check here would count one instrument limitation twice in the
 * per-metric refusal totals that sit beside every coverage figure. The field is still emitted, at
 * zero, because a column that disappears when it is empty is a column a reader cannot audit.
 */
public final class M1Events {

    /** The counting rule behind every number this class produces, stated in full (INV-CONF-02). */
    public static final String COUNTING_RULE =
            "R-M1: a .mop signature matches a rule signature when the declaring types agree, the "
                    + "method names are equal and the parameter lists agree position by position. "
                    + "Return types are not compared (the rule carries one only where it binds the "
                    + "result, and return type is not part of overload identity). Type names agree "
                    + "when equal, or when one side is unqualified and the simple names are equal. "
                    + "A .mop wildcard ('..' for a tail, '*' for one parameter) expands and matches "
                    + "every declared signature of the same declaring type and method name; a "
                    + "rule's unbound argument ('_', rendered AnyType) is matched only by a .mop "
                    + "wildcard at that position, never by a concrete type, so the oracle does not "
                    + "widen with whatever the artifact under test happens to declare. "
                    + "covered/declared count distinct rule signatures; mop_only and rule_only are "
                    + "the two set differences under the same match relation.";

    /** The counting rule behind the label alignment (INV-CONF-02). */
    public static final String ALIGNMENT_COUNTING_RULE =
            "R-M1-align: a .mop label aligns with a rule symbol when some signature of the label's "
                    + "pointcut matches some signature of the rule event, under R-M1. Derived from "
                    + "the signature-set intersection only; no name comparison of any kind takes "
                    + "part, because none is correct on this corpus (SecureRandomSpec.g3 is the "
                    + "rule's gI, and SecureRandomSpec.setSeed1 is the rule's s2, not s1).";

    /** The CrySL façade's rendering of an unbound argument, written {@code _} in the rule. */
    public static final String RULE_HOLE = "AnyType";

    /** A pointcut's tail wildcard, as {@code PointcutExpander} leaves it in the parameter list. */
    public static final String MOP_TAIL_WILDCARD = "..";

    /** A pointcut's single-parameter wildcard. */
    public static final String MOP_ANY_WILDCARD = "*";

    /** Column carrying the coverage fraction; never emitted without the two below beside it. */
    public static final String COVERAGE_COLUMN = "coverage";

    /** Column carrying the signatures the specification monitors and the rule does not name. */
    public static final String MOP_ONLY_COLUMN = "mop_only";

    /** Column carrying the signatures the rule names and the specification does not monitor. */
    public static final String RULE_ONLY_COLUMN = "rule_only";

    /** The body columns of every M1 table, before the stamp columns {@link StampedTable} adds. */
    public static final List<String> BODY_COLUMNS = List.of(
            "specification", "rule", "declared", "covered", COVERAGE_COLUMN,
            "rule_only_count", RULE_ONLY_COLUMN, "mop_only_count", MOP_ONLY_COLUMN, "refusals");

    /** The body columns of the alignment table M2 consumes. */
    public static final List<String> ALIGNMENT_COLUMNS = List.of(
            "specification", "rule", "decl_index", "mop_label", "rule_symbols",
            "shared_signatures");

    private M1Events() {
    }

    /**
     * Compares one specification against the rule it was paired with.
     *
     * @param specification the specification's identifier, as the corpus names it
     * @param specModel     the lifted specification
     * @param rule          the rule's identifier
     * @param ruleModel     the lifted rule
     * @return coverage and both differences, never one without the other
     */
    public static M1Result compare(String specification, SpecModel specModel,
                                   String rule, SpecModel ruleModel) {
        Objects.requireNonNull(specification, "specification is mandatory");
        Objects.requireNonNull(specModel, "specModel is mandatory");
        Objects.requireNonNull(rule, "rule is mandatory");
        Objects.requireNonNull(ruleModel, "ruleModel is mandatory");

        List<Signature> declared = distinctSignatures(ruleModel);
        List<Signature> monitored = distinctSignatures(specModel);

        List<Signature> ruleOnly = new ArrayList<>();
        int covered = 0;
        for (Signature r : declared) {
            if (monitored.stream().anyMatch(m -> matches(m, r))) {
                covered++;
            } else {
                ruleOnly.add(r);
            }
        }
        List<Signature> mopOnly = new ArrayList<>();
        for (Signature m : monitored) {
            if (declared.stream().noneMatch(r -> matches(m, r))) {
                mopOnly.add(m);
            }
        }
        return new M1Result(specification, rule, covered, declared.size(), mopOnly, ruleOnly,
                List.<Unknown>of(), COUNTING_RULE);
    }

    /**
     * The label alignment M2 consumes, from the signature-set intersection.
     *
     * @param specification the specification's identifier
     * @param specModel     the lifted specification
     * @param rule          the rule's identifier
     * @param ruleModel     the lifted rule
     * @return one entry per declared event, in declaration order, plus the unreached rule symbols
     */
    public static LabelAlignment align(String specification, SpecModel specModel,
                                       String rule, SpecModel ruleModel) {
        Objects.requireNonNull(specModel, "specModel is mandatory");
        Objects.requireNonNull(ruleModel, "ruleModel is mandatory");

        List<LabelAlignment.Entry> entries = new ArrayList<>();
        Set<Label> reached = new LinkedHashSet<>();
        for (Event event : specModel.events()) {
            List<Label> symbols = new ArrayList<>();
            List<Signature> shared = new ArrayList<>();
            for (Event ruleEvent : ruleModel.events()) {
                List<Signature> meeting = ruleEvent.signatures().stream()
                        .filter(r -> event.signatures().stream().anyMatch(m -> matches(m, r)))
                        .toList();
                if (!meeting.isEmpty()) {
                    symbols.add(ruleEvent.label());
                    shared.addAll(meeting);
                    reached.add(ruleEvent.label());
                }
            }
            entries.add(new LabelAlignment.Entry(event.label(), event.declIndex(), symbols, shared));
        }
        List<Label> unaligned = ruleModel.events().stream()
                .map(Event::label)
                .filter(label -> !reached.contains(label))
                .distinct()
                .toList();
        return new LabelAlignment(specification, rule, entries, unaligned,
                ALIGNMENT_COUNTING_RULE);
    }

    /**
     * R-M1, the match relation between one specification signature and one rule signature.
     *
     * <p>Public because the pairing needs it: {@link SpecRulePairing} breaks a contested rule by
     * asking which specification covers more of it, and "covers" has to mean the same thing there
     * as it means here or the pair chosen would not be the pair measured.
     *
     * @param mop  a signature the specification's pointcut resolves to
     * @param rule a signature the rule's {@code EVENTS} declares
     * @return whether the specification's signature monitors the rule's
     */
    public static boolean matches(Signature mop, Signature rule) {
        return typesAgree(mop.declaringType(), rule.declaringType())
                && mop.name().equals(rule.name())
                && parametersAgree(mop.paramTypes(), rule.paramTypes());
    }

    /**
     * Position-by-position agreement of the parameter lists.
     *
     * <p>The {@code ..} of a pointcut consumes the whole remaining tail, including an empty one:
     * {@code update(..)} matches {@code update(byte)} and {@code update(byte[], int, int)} alike.
     * Every event of the five corpora writes {@code ..} last, which is the only position AspectJ
     * makes useful here; a {@code ..} written elsewhere is still read as "the rest agrees", because
     * the alternative — a backtracking matcher — would buy a generality the corpus never exercises.
     */
    private static boolean parametersAgree(List<String> mop, List<String> rule) {
        int i = 0;
        while (i < mop.size()) {
            if (MOP_TAIL_WILDCARD.equals(mop.get(i))) {
                return true;
            }
            if (i >= rule.size()) {
                return false;
            }
            if (!parameterAgrees(mop.get(i), rule.get(i))) {
                return false;
            }
            i++;
        }
        return i == rule.size();
    }

    private static boolean parameterAgrees(String mop, String rule) {
        if (MOP_ANY_WILDCARD.equals(mop)) {
            // The pointcut leaves the position open, so it matches whatever the rule declares
            // there - including the rule's own hole, which is the case SecureRandomSpec exercises.
            return true;
        }
        if (RULE_HOLE.equals(rule)) {
            // The rule leaves the position unbound and the specification names a concrete type.
            // Not a match: see the class comment on why the oracle does not widen to fit the
            // artifact under test. The concrete overload surfaces in mop_only instead.
            return false;
        }
        return typesAgree(mop, rule);
    }

    /**
     * Two type names denote the same type.
     *
     * <p>Equal names agree. Otherwise the simple names are compared, but only when at least one
     * side is unqualified — that is the case the corpus produces (a pointcut writes {@code String}
     * where the rule writes {@code java.lang.String}). Two qualified names that differ stay
     * different, so folding can never merge two types that live in different packages.
     */
    private static boolean typesAgree(String mop, String rule) {
        if (mop.equals(rule)) {
            return true;
        }
        if (mop.indexOf('.') >= 0 && rule.indexOf('.') >= 0) {
            return false;
        }
        return simpleName(mop).equals(simpleName(rule));
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }

    /** The signatures of a model, deduplicated, in declaration order. */
    private static List<Signature> distinctSignatures(SpecModel model) {
        Set<Signature> signatures = new LinkedHashSet<>();
        for (Event event : model.events()) {
            signatures.addAll(event.signatures());
        }
        return List.copyOf(signatures);
    }

    /**
     * The M1 table: one row per specification, coverage and both differences in the same row.
     *
     * <p>This is the only method of this class that turns an M1 number into a character, and it
     * cannot write the coverage cell without writing the two difference cells beside it — they are
     * built together, from one {@link M1Result}, into one row of a fixed column set. The guard
     * below is what keeps that true after a later edit: drop a difference column from
     * {@link #BODY_COLUMNS} and the emitter fails before it writes anything, rather than quietly
     * publishing the bare percentage this whole capability exists to abolish.
     *
     * <p>The header naming the oracle's repository and commit and the pairing rule is not optional
     * either: {@link StampedTable} refuses a table whose counting rule is absent (INV-CONF-02), and
     * the pairing rule travels in the title because INV-CONF-11 requires every emitted report to
     * name it.
     *
     * @param results       one result per paired specification
     * @param mopVersion    corpus and commit of the specification side
     * @param oracleVersion corpus and commit of the oracle
     * @param pairingRule   how specifications were matched to rules (INV-CONF-11)
     */
    public static StampedTable table(List<M1Result> results, Version mopVersion,
                                     Version oracleVersion, String pairingRule) {
        requireBothDifferenceColumns();
        Objects.requireNonNull(pairingRule, "the pairing rule is mandatory (INV-CONF-11)");
        if (pairingRule.isBlank()) {
            throw new IllegalArgumentException("INV-CONF-11: an M1 table that does not name the "
                    + "pairing rule does not say which rule each row was measured against");
        }
        List<List<String>> rows = new ArrayList<>(results.size());
        for (M1Result result : results) {
            rows.add(List.of(
                    result.specification(),
                    result.rule(),
                    Integer.toString(result.declared()),
                    Integer.toString(result.covered()),
                    coverageCell(result),
                    Integer.toString(result.ruleOnly().size()),
                    render(result.ruleOnly()),
                    Integer.toString(result.mopOnly().size()),
                    render(result.mopOnly()),
                    Integer.toString(result.refusals().size())));
        }
        return new StampedTable("M1 — event coverage against the oracle", mopVersion, oracleVersion,
                COUNTING_RULE + " Pairing: " + pairingRule, BODY_COLUMNS, rows);
    }

    /**
     * The alignment table, one row per declared event of each specification.
     *
     * <p>Emitted separately from the coverage table because it is consumed rather than read: M2
     * needs one row per label, and folding it into the M1 row would put a variable-length list
     * inside a cell that also has to be diffable.
     */
    public static StampedTable alignmentTable(List<LabelAlignment> alignments, Version mopVersion,
                                              Version oracleVersion, String pairingRule) {
        Objects.requireNonNull(pairingRule, "the pairing rule is mandatory (INV-CONF-11)");
        List<List<String>> rows = new ArrayList<>();
        for (LabelAlignment alignment : alignments) {
            for (LabelAlignment.Entry entry : alignment.entries()) {
                rows.add(List.of(
                        alignment.specification(),
                        alignment.rule(),
                        Integer.toString(entry.declIndex()),
                        entry.mopLabel().name(),
                        String.join(" ", entry.ruleSymbols().stream().map(Label::name).toList()),
                        render(entry.sharedSignatures())));
            }
        }
        return new StampedTable("M1 — label alignment (input to M2)", mopVersion, oracleVersion,
                ALIGNMENT_COUNTING_RULE + " Pairing: " + pairingRule, ALIGNMENT_COLUMNS, rows);
    }

    /**
     * The coverage cell.
     *
     * <p>Private, and it takes the whole result rather than two integers. Nothing outside this
     * class can obtain a coverage figure as text, which is the mechanical form of task 7.2: a
     * caller that wants the percentage has to go through {@link #table}, and {@link #table} writes
     * both difference lists into the same row.
     */
    private static String coverageCell(M1Result result) {
        if (result.declared() == 0) {
            return "0/0 (n/a)";
        }
        double fraction = 100.0 * result.covered() / result.declared();
        return String.format(Locale.ROOT, "%d/%d (%.1f%%)",
                result.covered(), result.declared(), fraction);
    }

    private static void requireBothDifferenceColumns() {
        if (!BODY_COLUMNS.contains(COVERAGE_COLUMN)) {
            throw new IllegalStateException("M1 emits no coverage column at all");
        }
        if (!BODY_COLUMNS.contains(MOP_ONLY_COLUMN) || !BODY_COLUMNS.contains(RULE_ONLY_COLUMN)) {
            throw new IllegalStateException("task 7.2: an M1 table carries the coverage fraction "
                    + "only with both difference lists beside it - '" + MOP_ONLY_COLUMN + "' and '"
                    + RULE_ONLY_COLUMN + "' - and this column set has lost one of them: "
                    + BODY_COLUMNS);
        }
    }

    /** Signatures as one cell, space-separated, each in the {@code Type.name(params)} form. */
    private static String render(List<Signature> signatures) {
        StringBuilder out = new StringBuilder();
        for (Signature signature : signatures) {
            if (out.length() > 0) {
                out.append(' ');
            }
            out.append(signature.declaringType()).append('.').append(signature.name())
                    .append('(').append(String.join(",", signature.paramTypes())).append(')');
        }
        return out.toString();
    }
}
