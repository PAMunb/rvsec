package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.UnreachableAccusationSite;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

/**
 * The metric that runs first and is allowed to refuse.
 *
 * <p>M0 exists because Phase 0 measured that the other four would otherwise emit confident verdicts
 * about artifacts that cannot accuse anything: 26 of the 73 predicate sites of the corpus, 36 %,
 * live in specifications whose slicing is broken or whose accusation site is unreachable, and M4
 * would have scored every one of them as faithful. An order verdict over a monitor that does not
 * run is empty, so the order verdict is not produced (design D-03, INV-CONF-09).
 *
 * <h2>The three questions</h2>
 *
 * <p><strong>M0.1 — does it index?</strong> The generated monitor builds a {@code MapOfMonitor}
 * when the specification's parameter binding is effective. A specification with {@code 0/N} binding,
 * or one declared with no parameter at all, compiles to {@code Tuple2<Set, Monitor>} — one monitor
 * for the whole program — and parametric slicing is a no-op in it. The answer here is
 * <strong>a proxy</strong>; see {@link #INDEXING_PROXY_CAVEAT}, which is emitted with every result.
 *
 * <p><strong>M0.2 — is the accusation site reachable?</strong> A specification accuses either from
 * a {@code @fail} with a body, when the observed word leaves the language, or from an
 * {@code addError} inside an event body the formula admits, when a {@code condition} decides the
 * call was wrong. A specification with neither cannot accuse under any trace.
 *
 * <p><strong>M0.3 — does the pointcut resolve?</strong> Every signature the pointcut resolved to is
 * looked up in the {@code android.jar} index. A signature whose declaring class the platform does
 * not have can never match on device, and that is {@code Unknown{UnresolvedSignature}}.
 *
 * <h2>The three causes of silence</h2>
 *
 * <p>They are kept apart because only one of them is a repairable defect of a file, and because
 * collapsing them reports a limit of the formalism as a defect of a specification. See
 * {@link SilenceCause}, whose three constants carry the written reason each one is emitted under.
 *
 * <h2>What M0.2 asks, and the second specification it refuses</h2>
 *
 * <p>The delta spec states the sufficient condition it had a witness for: "a specification with an
 * empty {@code @match} and no {@code @fail} cannot accuse under any trace". The question underneath
 * it is whether an {@code addError} is reachable at all, and asking that question of the whole
 * corpus finds a <strong>second</strong> specification with no accusation site, in both
 * {@code jca} and {@code jca_android}: {@code SecretKeySpec.mop}, whose {@code @match} is not empty
 * — it writes a predicate — and which declares no {@code @fail} and no {@code addError} anywhere.
 * The file says so itself, at its own event: "nothing here translates a constraint and nothing here
 * accuses". It is a propagation bridge, and M0 refuses it for the same reason it refuses
 * {@code RandomStringPassword}: publishing four verdicts about how faithfully it accuses would be
 * publishing four verdicts about something it does not do.
 *
 * <p>That is a consequence worth naming rather than burying: {@code SecretKeySpec.mop} is one of the
 * 22 pairs D-06 names, so refusing it removes a pair from what M1-M4 report on. The behavioural run
 * never examined it, because it examined the five specifications that do not index and this one
 * does.
 *
 * <h2>How the refusal is typed</h2>
 *
 * <p>INV-CONF-09 says a refusal "MUST be emitted as a typed {@code Unknown}", and until 2026-08-24
 * none of the taxonomy's tags named an unreachable accusation site: the nearest,
 * {@link br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature}, is about a signature the platform
 * does not have, which is a different claim about a different subject. The tag
 * {@link br.unb.cic.rvsec.crysl.core.model.UnreachableAccusationSite} was added for it, by
 * researcher decision, and adding it is the visible contract change design D-11 asks a new tag to
 * be.
 *
 * <p>A refused specification therefore carries the finding in two registers, and they are not
 * redundant. The {@link Silence} is the <strong>classification</strong>: it says which of the three
 * causes this is, and its {@link SilenceCause.Disposition} is what {@link M0Result} consults to
 * decide whether M1-M4 run at all. The {@code Unknown} is the <strong>emission</strong>: one
 * countable refusal vocabulary, so this refusal is counted beside every other refusal of the report
 * instead of in a column of its own.
 */
public final class M0Vitality {

    /** The rule behind {@link M0Result#indexes()}, stated in full (INV-CONF-02). */
    public static final String INDEXING_RULE =
            "a specification indexes when it declares at least one parameter and at least one of "
                    + "its events binds one — that is, the event's getMOPParametersOnSpec() is "
                    + "non-empty. A specification with 0/N binding, or declared with no parameter, "
                    + "does not index";

    /**
     * The standing caveat on M0.1, emitted with every result.
     *
     * <p>It is a caveat and not a footnote. The proxy and the oracle agree on the five
     * specifications of {@code jca_android} today; that agreement is a measured coincidence of one
     * corpus at one commit, not a proof that the two measurements are the same measurement.
     * Publishing the proxy's answer as if it were the generated monitor's would be the exact error
     * this capability exists to prevent.
     */
    public static final String INDEXING_PROXY_CAVEAT =
            "M0.1 is an AST proxy. The real oracle is the generated monitor: a specification "
                    + "indexes when MultiSpec_1RuntimeMonitor.java builds a MapOfMonitor for it. "
                    + "The proxy gives the same five specifications of jca_android today and it is "
                    + "still not the same measurement; reproducing it costs one rv-monitor "
                    + "generation pass, and until that pass is run the number here is a proxy's";

    /**
     * The standing caveat on the AST checker, emitted whenever it finds anything.
     *
     * <p>The point is not that the checker found something. The point is where it found it: in
     * files that the parser, the monitor generator and {@code javac} all accepted without a single
     * diagnostic.
     */
    public static final String AST_CHECKER_CAVEAT =
            "the files these violations were found in parse, generate a monitor and compile with "
                    + "zero errors, so neither 'it parsed' nor 'it compiled' is an oracle of "
                    + "sanity and no stage downstream of the parser can be relied on to catch this "
                    + "class of defect";

    /** Emitted when no {@code android.jar} was supplied, so M0.3 was not answered. */
    public static final String NO_INDEX_NOTE =
            "M0.3 did not run: no android.jar index was supplied. No signature of this "
                    + "specification was checked against the platform, and the absence of an "
                    + "UnresolvedSignature refusal here means 'not checked', not 'resolves'";

    /** The mode {@link UnresolvedSignature} carries when the platform has no such class. */
    public static final String MODE_ABSENT_CLASS = "CLASSE-AUSENTE";

    private M0Vitality() {
    }

    /**
     * Runs the three questions and the AST checker over one specification.
     *
     * @param model      the lifted specification
     * @param labelOrder the language its {@code ere}/{@code fsm} denotes, over labels; the label
     *                   automaton rather than {@code model.order()} because every question here is
     *                   about the declared formula and the events that appear in it
     * @param facts      the MOP-side facts the shared model has no field for
     * @param index      the {@code android.jar} index, or empty where the platform jar is not
     *                   available — in which case M0.3 is not answered and the result says so
     * @return the vitality of this specification, refused or not
     */
    public static M0Result examine(SpecModel model, LabelAutomaton labelOrder, MonitorFacts facts,
                                   Optional<ApiIndex> index) {
        Provenance site = facts.site();
        String specification = specificationOf(site);

        boolean indexes = facts.declaredParameters() > 0 && facts.eventsBindingParameters() > 0;

        Set<String> formulaAlphabet = new TreeSet<>();
        for (LabelTransition transition : labelOrder.transitions()) {
            formulaAlphabet.add(transition.symbol().name());
        }
        boolean accusationSiteReachable = failCanAccuse(facts)
                || absorbingEventInFormula(facts, formulaAlphabet);

        List<Unknown> refusals = new ArrayList<>();
        List<String> notes = new ArrayList<>();
        List<Silence> silences = new ArrayList<>();
        notes.add(INDEXING_PROXY_CAVEAT);

        if (index.isPresent()) {
            Set<String> absentClasses = new TreeSet<>();
            List<String> uncheckable = resolve(model, index.get(), site, refusals, absentClasses);
            if (!uncheckable.isEmpty()) {
                notes.add("the index records declared members and does not follow inheritance, so "
                        + "these lookups missed on a class the platform does have; they are limits "
                        + "of the checker and not absences in the platform, and the report must not "
                        + "merge them with an absent class: " + String.join(", ", uncheckable));
            }
            if (!absentClasses.isEmpty()) {
                silences.add(new Silence(specification, SilenceCause.LIVE_TARGET_ABSENT,
                        "the pointcut names " + String.join(", ", absentClasses)
                                + ", absent from the index built from " + index.get().source(),
                        site));
            }
        } else {
            notes.add(NO_INDEX_NOTE);
        }

        Optional<String> livePrefix = livePrefix(labelOrder);
        if (livePrefix.isPresent()) {
            silences.add(new Silence(specification, SilenceCause.LIVE_BLIND_TO_END_OF_TRACE,
                    livePrefix.get(), site));
        }

        if (!accusationSiteReachable) {
            String evidence = accusationSiteEvidence(facts);
            silences.add(new Silence(specification, SilenceCause.LIVE_WITHOUT_ACCUSATION_SITE,
                    evidence, site));
            // The Silence classifies; this is the typed emission INV-CONF-09 asks for, in the one
            // vocabulary every refusal of the report is counted in.
            refusals.add(new UnreachableAccusationSite(specification, evidence, site));
        }

        List<String> astViolations = AstChecker.check(specification, model, labelOrder, facts);
        if (!astViolations.isEmpty()) {
            notes.add(AST_CHECKER_CAVEAT);
        }

        return new M0Result(specification, indexes, accusationSiteReachable, facts.absorption(),
                silences, astViolations, refusals, notes, countingRule());
    }

    /** The rules behind every count of an {@link M0Result}, concatenated in question order. */
    public static String countingRule() {
        return "M0.1: " + INDEXING_RULE
                + " | M0.2: a specification can accuse when it declares a @fail with a body, or "
                + "when an event the formula admits carries an addError in its body"
                + " | M0.3: every signature the pointcut resolved to is looked up in the "
                + "android.jar index; a signature whose declaring class is absent is "
                + "Unknown{UnresolvedSignature, mode: " + MODE_ABSENT_CLASS + "}, and a miss on a "
                + "class the index does have is a limit of the checker rather than a finding"
                + " | AST checker: " + AstChecker.RULE
                + " | absorption: " + MisuseAbsorption.RULE;
    }

    /**
     * The name a result is reported under: the {@code .mop} file's, without its extension.
     *
     * <p>Not {@code SpecModel.type()}. Two files can declare the same type - {@code SecretKeySpec.mop}
     * declares {@code SecretKeySpec(SecretKey ...)} and so reports as {@code SecretKey} - and a
     * refusal attributed to a type the reader cannot find the file for is not actionable. The
     * declared type is what <em>pairing</em> runs on (INV-CONF-11); identity in a report is the file.
     */
    private static String specificationOf(Provenance site) {
        String file = site.file();
        return file.endsWith(".mop") ? file.substring(0, file.length() - ".mop".length()) : file;
    }

    /**
     * Whether a {@code @fail} can fire at all.
     *
     * <p>{@link HandlerState#UNPARSED} counts as "can accuse". The body did not parse, so its
     * content is unknown; reading unknown as empty would make M0 refuse a healthy specification the
     * day {@code JavaParserAdapter} swallows an exception on a handler that does report.
     */
    private static boolean failCanAccuse(MonitorFacts facts) {
        HandlerState state = facts.handler(MonitorFacts.FAIL);
        return state == HandlerState.NON_EMPTY || state == HandlerState.UNPARSED;
    }

    /** Whether some event carrying an {@code addError} is a symbol the formula admits. */
    private static boolean absorbingEventInFormula(MonitorFacts facts, Set<String> formulaAlphabet) {
        for (Label label : facts.absorption().events()) {
            if (formulaAlphabet.contains(label.name())) {
                return true;
            }
        }
        return false;
    }

    /** The evidence line for a specification that cannot accuse, naming what it does declare. */
    private static String accusationSiteEvidence(MonitorFacts facts) {
        String matches = facts.matchKeys().isEmpty()
                ? "no @match" : "@" + String.join(", @", facts.matchKeys()) + " "
                        + facts.matchKeys().stream().map(facts::handler).map(Enum::name).toList();
        return "@fail is " + facts.handler(MonitorFacts.FAIL) + " and " + matches
                + "; no event body carries an addError the formula admits";
    }

    /**
     * M0.3, in the classification order {@code ApiIndex} declares.
     *
     * <p>Exact hit; else the declaring class is absent, which is a finding about the pointcut; else
     * an arity-only hit, which is a weaker answer and not a finding; else the class is present and
     * the member is not, which is the checker's inheritance limitation and must not be reported as
     * an absence in the platform. The order matters: an absent class cannot produce an arity hit,
     * and counting it as one would hide a platform absence behind a checker limitation.
     *
     * @return the lookups that missed on a class the platform does have
     */
    private static List<String> resolve(SpecModel model, ApiIndex index, Provenance site,
                                        List<Unknown> refusals, Set<String> absentClasses) {
        List<String> uncheckable = new ArrayList<>();
        Set<Signature> seen = new LinkedHashSet<>();
        for (Event event : model.events()) {
            for (Signature signature : event.signatures()) {
                if (!seen.add(signature)) {
                    continue;
                }
                if (index.hasSignature(signature)) {
                    continue;
                }
                if (!index.hasClass(signature.declaringType())) {
                    absentClasses.add(signature.declaringType());
                    refusals.add(new UnresolvedSignature(signature, signature.declaringType(),
                            MODE_ABSENT_CLASS, model.provenance().getOrDefault(event, site)));
                } else if (!index.hasSignatureWithArity(signature)) {
                    uncheckable.add(signature.declaringType() + "." + signature.name()
                            + signature.paramTypes());
                }
            }
        }
        return uncheckable;
    }

    /**
     * The blind spot of the formalism, decided from the shape of the declared language.
     *
     * <p>JavaMOP fires {@code @fail} when the observed word leaves the language and there is no
     * end-of-trace event, so a trace that stops on a prefix which is neither accepted nor rejected
     * is never reported. That prefix exists exactly when some state other than the initial one is
     * reachable, is not accepting, and can still reach an accepting state.
     *
     * <p>The initial state is excluded deliberately. Stopping there means the program never made
     * the first call, which is not a violation of anything the specification says; including it
     * would report the blind spot for every specification whose language excludes the empty word,
     * which is nearly all of them, and a finding that fires everywhere carries no information.
     *
     * @return the evidence line, or empty when the language is prefix-closed from the first move on
     */
    private static Optional<String> livePrefix(LabelAutomaton automaton) {
        Set<String> reachable = reachableFrom(automaton, Set.of(automaton.initial()));
        for (String state : reachable) {
            if (state.equals(automaton.initial()) || automaton.accepting().contains(state)) {
                continue;
            }
            Set<String> onwards = reachableFrom(automaton, Set.of(state));
            if (onwards.stream().anyMatch(automaton.accepting()::contains)) {
                return Optional.of("state '" + state + "' is reachable, is not accepting and can "
                        + "still reach one, so a trace that stops there has left the automaton on a "
                        + "live prefix and @fail never fires");
            }
        }
        return Optional.empty();
    }

    private static Set<String> reachableFrom(LabelAutomaton automaton, Set<String> seeds) {
        Set<String> seen = new LinkedHashSet<>(seeds);
        Deque<String> pending = new ArrayDeque<>(seeds);
        while (!pending.isEmpty()) {
            String current = pending.removeFirst();
            for (LabelTransition transition : automaton.transitions()) {
                if (transition.from().equals(current) && seen.add(transition.to())) {
                    pending.addLast(transition.to());
                }
            }
        }
        return seen;
    }
}
