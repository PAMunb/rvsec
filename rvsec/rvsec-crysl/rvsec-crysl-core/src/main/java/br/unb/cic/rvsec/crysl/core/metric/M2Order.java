package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.Determinizer;
import br.unb.cic.rvsec.crysl.core.automata.InverseMorphism;
import br.unb.cic.rvsec.crysl.core.automata.ProductSearch;
import br.unb.cic.rvsec.crysl.core.compare.AlphabetMap;
import br.unb.cic.rvsec.crysl.core.compare.CanonicalAlphabet;
import br.unb.cic.rvsec.crysl.core.compare.Normalizations;
import br.unb.cic.rvsec.crysl.core.compare.Observability;
import br.unb.cic.rvsec.crysl.core.compare.OrderSurgery;
import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * M2: what the specification's declared order accepts, against what the rule's {@code ORDER}
 * accepts.
 *
 * <p>Both languages arrive as automata over real signatures. Design D-20 moved the inverse morphism
 * {@code h⁻¹(L)} to lift time, so {@code SpecModel.order} is a signature language on both sides and
 * this class compares them directly - it does not build {@code h} and does not apply it a second
 * time. What it does is make the two alphabets one ({@link CanonicalAlphabet}), apply the
 * normalizations the inputs declare, determinize the rule side and search the product in both
 * directions.
 *
 * <p><strong>Every verdict is {@code M2-decl}.</strong> It is a statement about declared automata
 * and says nothing about what the generated monitor accuses at runtime. That is not a hedge added
 * for modesty: Phase 0 measured a case where the two halves disagree and only the behavioural one
 * is right - {@code KeyGeneratorSpec}'s {@code ORDER} is equivalent to its {@code ere} <em>and</em>
 * the generated monitor accuses order against a program the rule accepts. The emitter prints the
 * qualifier beside every row (INV-CONF-13), and no unqualified "equivalent" leaves this component.
 *
 * <p><strong>Refusals narrow the language, and the narrowing belongs to the refusal.</strong> Where
 * two labels claim one call and a guard separates them, the lift refuses the signature
 * ({@code Unknown{OverlappingDispatch}}) and it is not a letter of {@code SpecModel.order}. A
 * consumer that reads {@code order} without reading {@code morphism.refusals()} is therefore reading
 * a language narrower than the file, and would publish the specification as more restrictive than it
 * is. So this class takes the morphism, not just the automaton, and carries its refusals into
 * {@link M2Result#refusals()} where they are counted beside the verdict.
 *
 * <p><strong>Erasure is read, never inferred.</strong> Every &epsilon;-erasure comes from the
 * {@code disposition} column of {@code order_alphabet_map.csv} (INV-CONF-10, design D-05), and the
 * declared reason is quoted verbatim into the verdict's normalization block so that the erasure
 * travels with its justification. An event the map says nothing about produces a typed refusal and
 * never a choice.
 */
public final class M2Order {

    /** The counting rule behind every M2 verdict (INV-CONF-02). */
    public static final String COUNTING_RULE =
            "R-M2: the two declared orders are compared as languages over one alphabet, by "
                    + "breadth-first product search in both directions. The alphabet is the letter "
                    + "identification of " + CanonicalAlphabet.COUNTING_RULE + " "
                    + "Epsilon-erasure of a .mop event is taken from the disposition column of "
                    + "order_alphabet_map.csv and never from automaton shape (INV-CONF-10); an "
                    + "event with no row there is a refusal, not an erasure. The rule automaton is "
                    + "determinized before the search, always. Every verdict is labelled "
                    + M2Result.LABEL + " and every witness carries its status and the "
                    + "normalizations it was obtained under.";

    /**
     * The {@code mode} an {@link UnresolvedSignature} carries when the alphabet map declares
     * nothing about an event.
     *
     * <p>The taxonomy is closed to six tags (INV-CONF-06) and none of them was written for this
     * case: {@code UnresolvedSignature} was written for a signature the platform lacks. It is used
     * here because it is the only tag whose field schema fits - a signature, the class it belongs
     * to, why it did not resolve and where - and because opening a seventh tag is a contract change
     * that belongs to a researcher decision and not to a metric. The mismatch is stated rather than
     * hidden: what did not resolve here is the event's <em>symbol in the rule</em>, not its
     * signature on the platform, and a reader counting refusals by tag must know that.
     */
    public static final String UNDECLARED_EVENT_MODE = "ORDER-SEM-DISPOSICAO";

    /**
     * The caveat every verdict whose witness rests on a refused signature is published under.
     *
     * <p>This is the consumer caveat design D-20 leaves for M2, and it is not a footnote: it
     * changes what the verdict is about. Where two labels claim one call and complementary
     * {@code condition}s separate them - the negated-twin idiom, which most of this set uses for
     * the rejected-algorithm accuser - the lift refuses the signature and it is not a letter of
     * {@code SpecModel.order}. The specification's language is then narrower than the file, the
     * rule accepts a word the specification cannot, and the verdict reads "MOP more restrictive"
     * about a call the specification does in fact monitor. The narrowing belongs to the refusal and
     * not to the specification, and saying so is the difference between a measurement and an
     * accusation.
     */
    public static final String NARROWING_CAVEAT =
            "A witness marked refusal-borne contains a letter the lift refused as "
                    + "Unknown{OverlappingDispatch}: two or more labels claim that call and a "
                    + "condition separates them, so the morphism declines to say how many letters "
                    + "it emits and the call is absent from SpecModel.order. The specification "
                    + "does monitor that call. The verdict is about the language the component "
                    + "could read, and that language is narrower than the file by exactly the "
                    + "refused letters (design D-20).";

    private M2Order() {
    }

    /**
     * What the comparison found, in both directions.
     *
     * <p>{@link M2Result} carries one witness, the shortest of the two, because that is what a
     * report row shows. The two directions are exposed beside it because they are different claims:
     * {@code CipherSpec} was published as incomparable on the strength of two witnesses and one of
     * them died when gh105 made {@code f1} and {@code f2} disjoint, so which direction sustains a
     * verdict is itself a measurement.
     *
     * @param result   the published verdict
     * @param mopOnly  the shortest word the specification accepts and the rule rejects
     * @param ruleOnly the shortest word the rule accepts and the specification rejects
     * @param narrowing empty when no witness rests on a refused letter; otherwise the statement
     *                 {@link #NARROWING_CAVEAT} demands, naming the labels and the call
     */
    public record Comparison(M2Result result, Optional<Witness> mopOnly,
                             Optional<Witness> ruleOnly, Optional<String> narrowing) {

        public Comparison {
            Objects.requireNonNull(result, "Comparison.result is mandatory");
            Objects.requireNonNull(mopOnly, "Comparison.mopOnly is mandatory (Optional.empty())");
            Objects.requireNonNull(ruleOnly, "Comparison.ruleOnly is mandatory (Optional.empty())");
            Objects.requireNonNull(narrowing,
                    "Comparison.narrowing is mandatory (Optional.empty())");
        }

        /** Whether a distinguishing witness rests on a call the lift refused. */
        public boolean refusalBorne() {
            return narrowing.isPresent();
        }
    }

    /**
     * The three facts M2 is not allowed to derive for itself.
     *
     * @param site          where a refusal about this specification is attributed
     * @param indexes       M0.1's answer: does the generated monitor build a {@code MapOfMonitor}?
     *                      N1 is applied only when it does (task 10.9). Re-deriving it here is not
     *                      possible - the oracle is the generated monitor - and guessing it is
     *                      unsound in both directions
     * @param predicateOnlyAcceptingStates states the {@code .mop} marks with an {@code alias
     *                      match*} purely to give a predicate an acceptance point, which N3 removes
     *                      from the accepting set. The alias names do not survive the lift, so they
     *                      are declared by the caller rather than recovered here
     * @param platform      the access flags N2 is decided from; {@link Observability#EVERYTHING}
     *                      when none was supplied, in which case N2 is not applied
     */
    public record Options(Provenance site, boolean indexes,
                          Set<String> predicateOnlyAcceptingStates, Observability platform) {

        public Options {
            Objects.requireNonNull(site, "Options.site is mandatory");
            Objects.requireNonNull(platform,
                    "Options.platform is mandatory (use Observability.EVERYTHING)");
            predicateOnlyAcceptingStates = Set.copyOf(predicateOnlyAcceptingStates);
        }

        /** The options of a specification with no platform, no N3 states and M0.1 as given. */
        public static Options of(Provenance site, boolean indexes) {
            return new Options(site, indexes, Set.of(), Observability.EVERYTHING);
        }
    }

    /**
     * Compares one specification's declared order with its rule's.
     *
     * @param specification the specification's identifier, as the corpus names it
     * @param specModel     the lifted specification; {@code order} is already {@code h⁻¹(L)}
     * @param morphism      the morphism the lift built, for its images and its refusals
     * @param rule          the rule's identifier, paired by declared type (INV-CONF-11)
     * @param ruleModel     the lifted rule
     * @param map           the alphabet map, the sole source of &epsilon;-erasure
     * @param options       the facts M2 does not derive
     */
    public static Comparison compare(String specification, SpecModel specModel,
                                     InverseMorphism morphism, String rule, SpecModel ruleModel,
                                     AlphabetMap map, Options options) {
        List<Normalization> normalizations = new ArrayList<>();
        List<Unknown> refusals = new ArrayList<>(morphism.refusals());

        // N4 is a construction step since D-02: the preimage already accounts for a call that
        // emits several letters. Reported, because a comparison over a non-disjoint alphabet is a
        // different claim from one over a disjoint alphabet.
        if (morphism.images().values().stream().anyMatch(labels -> labels.size() > 1)) {
            normalizations.add(Normalizations.N4_OVERLAPPING_POINTCUTS);
        }

        Automaton mop = specModel.order();
        Automaton narrowed = OrderSurgery.withoutAccepting(mop,
                options.predicateOnlyAcceptingStates());
        if (narrowed != mop) {
            normalizations.add(Normalizations.N3_ACCEPTANCE);
        }
        mop = narrowed;

        Set<Label> erasedLabels = new LinkedHashSet<>();
        for (Event event : specModel.events()) {
            String label = event.label().name();
            if (!map.declares(specification, label)) {
                refusals.add(undeclared(specification, specModel, event, options.site()));
                continue;
            }
            if (map.erases(specification, label)) {
                erasedLabels.add(event.label());
            }
        }

        Map<Signature, List<Label>> images = morphism.images();
        Set<Signature> erased = new LinkedHashSet<>();
        Set<Label> effective = new LinkedHashSet<>();
        for (Signature letter : mop.alphabet()) {
            List<Label> emitted = images.getOrDefault(letter, List.of());
            if (emitted.isEmpty() || !erasedLabels.containsAll(emitted)) {
                // A letter some surviving label also emits keeps its symbol on that label's
                // authority. Erasing it would delete a call the map says the rule orders.
                continue;
            }
            erased.add(letter);
            effective.addAll(emitted);
        }
        for (Label label : effective) {
            normalizations.add(Normalizations.erasure(specification, label,
                    reasonOf(map, specification, label)));
        }
        mop = OrderSurgery.erase(mop, erased);

        Automaton ruleOrder = ruleModel.order();
        Set<Signature> unobservable = options.platform().unobservable(ruleOrder.alphabet());
        if (!unobservable.isEmpty()) {
            normalizations.add(Normalizations.N2_NON_OBSERVABLE);
            // Restriction and not erasure: a protected method is not a call the program makes and
            // hides, it is a call the program cannot make, so the words containing it leave the
            // language rather than losing a letter. See OrderSurgery.restrict.
            ruleOrder = OrderSurgery.restrict(ruleOrder, unobservable);
        }

        CanonicalAlphabet alphabet = CanonicalAlphabet.of(mop.alphabet(), ruleOrder.alphabet());
        if (alphabet.aggregated()) {
            normalizations.add(Normalizations.AGGREGATE);
        }
        if (specModel.events().stream()
                .anyMatch(event -> map.renames(specification, event.label().name()))) {
            normalizations.add(Normalizations.CROSS_RENUMBERING);
        }

        Set<Signature> creators = new LinkedHashSet<>();
        for (Signature creator : OrderSurgery.creators(specModel, mop)) {
            creators.add(alphabet.mopToCanonical().getOrDefault(creator, creator));
        }
        Automaton mopCanonical = OrderSurgery.relabel(mop, alphabet.mopToCanonical());
        Automaton ruleCanonical = OrderSurgery.relabel(ruleOrder, alphabet.ruleToCanonical());
        if (options.indexes() && !creators.isEmpty()) {
            mopCanonical = OrderSurgery.atMostOneCreator(mopCanonical, creators);
            normalizations.add(Normalizations.N1_PARAMETRIC_SLICING);
        }

        // Task 10.2. The determinization is a no-op on most of this corpus and it still runs: a
        // rule of the shape `ORDER con, a?, a` is genuinely non-deterministic under the Glushkov
        // construction, and would otherwise be compared wrongly and silently. Whether it was a
        // no-op here is recorded as a measurement rather than assumed.
        boolean alreadyDeterministic = Determinizer.isDeterministic(ruleCanonical);
        Automaton ruleDeterministic = Determinizer.determinize(ruleCanonical);

        ProductSearch.OrderComparison comparison =
                ProductSearch.compare(mopCanonical, ruleDeterministic);
        List<Normalization> applied = List.copyOf(normalizations);
        M2Result result = new M2Result(specification, rule, comparison.verdict(),
                comparison.shortestWitness(applied), applied, alreadyDeterministic, refusals,
                COUNTING_RULE);
        Optional<Witness> mopOnly = comparison.mopOnlyWitness(applied);
        Optional<Witness> ruleOnly = comparison.cryslOnlyWitness(applied);
        return new Comparison(result, mopOnly, ruleOnly,
                narrowing(specification, morphism, alphabet, mopOnly, ruleOnly));
    }

    /**
     * The statement a refusal-borne verdict is published with, or empty.
     *
     * <p>A refused signature is not a letter of the specification's language, but it may well be a
     * letter of the rule's - the rule orders the call whether or not the {@code .mop} splits it
     * into an accepted and a rejected twin. So the check is: does a distinguishing word contain a
     * canonical letter that some refused signature denotes?
     */
    private static Optional<String> narrowing(String specification, InverseMorphism morphism,
                                              CanonicalAlphabet alphabet, Optional<Witness> mopOnly,
                                              Optional<Witness> ruleOnly) {
        Map<Signature, OverlappingDispatch> refused = new java.util.LinkedHashMap<>();
        for (Unknown item : morphism.refusals()) {
            if (item instanceof OverlappingDispatch overlap) {
                refused.put(overlap.signature(), overlap);
            }
        }
        if (refused.isEmpty()) {
            return Optional.empty();
        }
        Map<Signature, OverlappingDispatch> byCanonical = new java.util.LinkedHashMap<>();
        alphabet.ruleToCanonical().forEach((letter, canonical) ->
                refused.forEach((signature, overlap) -> {
                    if (CanonicalAlphabet.identifies(signature, letter)) {
                        byCanonical.putIfAbsent(canonical, overlap);
                    }
                }));
        Set<Signature> inWitnesses = new LinkedHashSet<>();
        mopOnly.ifPresent(witness -> inWitnesses.addAll(witness.word()));
        ruleOnly.ifPresent(witness -> inWitnesses.addAll(witness.word()));

        List<String> hits = new ArrayList<>();
        for (Signature letter : inWitnesses) {
            OverlappingDispatch overlap = byCanonical.get(letter);
            if (overlap != null) {
                hits.add(letter.declaringType() + "." + letter.name() + "("
                        + String.join(",", letter.paramTypes()) + ") claimed by labels "
                        + overlap.labels() + " at " + overlap.site());
            }
        }
        if (hits.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of("the verdict for " + specification + " is refusal-borne: "
                + String.join("; ", hits) + ". " + NARROWING_CAVEAT);
    }

    /**
     * How many of the given rule automata were already deterministic, with the rule that counted
     * them (task 10.2-bis, closing G03 3.10).
     *
     * <p>G03 built {@link Determinizer#census} and left the measurement open, because
     * {@code rvsec-crysl-core} may not depend on either parser and the automata have to come from
     * the CrySL lifter. The number is taken over whatever corpus is handed in and is <em>new</em>:
     * the historical "all 30 of them were" was measured over the abandoned {@code api30}
     * generation, which is method history and not a target.
     */
    public static Determinizer.Census census(Collection<SpecModel> rules) {
        return Determinizer.census(rules.stream().map(SpecModel::order).toList());
    }

    /**
     * The rule's model with every letter a refusal covers deleted from its order.
     *
     * <p>The second number a refusal-borne verdict needs. The first says what the two languages do,
     * given that the component could not read some of the specification's alphabet; this one says
     * what they do over the alphabet it <em>could</em> read, by removing those letters from the
     * rule as well. The two together separate "the specification is more restrictive than its rule"
     * from "the reader lost a letter" - and the separation is not academic: measured over
     * {@code jca_android}, three of the seven refusal-borne verdicts become EQUIVALENT under it.
     *
     * <p>Deletion and not &epsilon;-erasure, for the reason {@link OrderSurgery#restrict} states:
     * erasing would let the rule accept the rest of a word without the call, which is a larger
     * language and a different question.
     */
    public static SpecModel withoutRefusedLetters(SpecModel rule, InverseMorphism morphism) {
        Set<Signature> removed = new LinkedHashSet<>();
        for (Unknown item : morphism.refusals()) {
            if (item instanceof OverlappingDispatch overlap) {
                for (Signature letter : rule.order().alphabet()) {
                    if (CanonicalAlphabet.identifies(overlap.signature(), letter)) {
                        removed.add(letter);
                    }
                }
            }
        }
        if (removed.isEmpty()) {
            return rule;
        }
        return new SpecModel(rule.version(), rule.type(), rule.objects(), rule.events(),
                OrderSurgery.restrict(rule.order(), removed), rule.constraints(), rule.ensures(),
                rule.requires(), rule.negates(), rule.forbidden(), rule.provenance());
    }

    /**
     * The counting rule an M2 report carries, with the determinization census printed beside it.
     *
     * <p>INV-CONF-02 reads this at emission: an aggregate without its rule is not a measurement,
     * and the census is an aggregate.
     */
    public static String reportCountingRule(Determinizer.Census census) {
        return COUNTING_RULE + " | rule automata already deterministic: "
                + census.alreadyDeterministic() + " of " + census.total() + " | "
                + census.countingRule() + " | " + CanonicalAlphabet.HOLE_CAVEAT + " | "
                + NARROWING_CAVEAT;
    }

    /**
     * Turns verdicts into emitter entries, all with {@link MarkdownEmitter.Claim#NONE}.
     *
     * <p>Task 10.12-bis, and it is a one-line method on purpose. Every witness M2 produces is
     * {@code ABSTRACT} - the product search finds words, it does not run programs - and the emitter
     * refuses to render a false-positive or false-negative claim beside an abstract witness. That
     * refusal is the invariant (INV-CONF-08), not an obstacle, so the claim is {@code NONE} at the
     * one place where entries are built and there is no parameter with which a caller could ask for
     * anything else.
     */
    public static List<MarkdownEmitter.VerdictEntry> publish(List<M2Result> results) {
        return results.stream()
                .map(result -> new MarkdownEmitter.VerdictEntry(result,
                        MarkdownEmitter.Claim.NONE))
                .toList();
    }

    private static String reasonOf(AlphabetMap map, String specification, Label label) {
        List<String> reasons = map.rowsOf(specification, label.name()).stream()
                .map(AlphabetMap.Row::reason)
                .filter(reason -> !reason.isBlank())
                .toList();
        return String.join(" / ", reasons);
    }

    private static Unknown undeclared(String specification, SpecModel model, Event event,
                                      Provenance fallback) {
        Signature signature = event.signatures().stream()
                .min(CanonicalAlphabet.ORDER)
                .orElse(new Signature(model.type(), event.label().name(), List.of(), "void"));
        Provenance site = model.provenance().getOrDefault(event, fallback);
        return new UnresolvedSignature(signature, model.type(),
                UNDECLARED_EVENT_MODE + ": " + specification + "." + event.label().name()
                        + " has no row in order_alphabet_map.csv, so M2 neither maps it nor erases "
                        + "it (INV-CONF-10, task 10.4)",
                site);
    }
}
