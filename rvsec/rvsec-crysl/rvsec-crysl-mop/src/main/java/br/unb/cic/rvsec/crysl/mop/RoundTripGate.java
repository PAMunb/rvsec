package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.ProductSearch;
import br.unb.cic.rvsec.crysl.core.metric.AstChecker;
import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.model.Constraint;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

/**
 * Validates what {@link MopLowerer} emitted, in two layers that do not have the same standing.
 *
 * <h2>Layer 1 is the gate</h2>
 *
 * <p>The five non-normalized checks over the <em>generated</em> tree: no two events share an
 * identifier, every symbol of the formula is a declared event, every declared event appears in the
 * formula, every declared {@code @match} is paired with a {@code @fail}, and every signature the
 * pointcuts resolved to is found in the {@code android.jar} index. The first four are
 * {@link AstChecker}, called here rather than copied — it is M0's checker, one implementation
 * answering both the gate and the published metric (design D-03). The fifth is M0.3, whose own
 * routine is private to {@code M0Vitality}, so the classification order is applied here over
 * {@link ApiIndex} directly and the constant naming the mode is shared.
 *
 * <h2>Layer 2 is evidence, not the gate</h2>
 *
 * <p>Layer 2 is the product search of the generated order against the paired rule's, published with
 * the normalizations it was made under. It never decides. The reason is structural rather than a
 * matter of taste: a language-equivalence gate compares the generator's output against the rule
 * <em>through the same normalization layer the comparator uses</em>, so it cannot see a defect that
 * lives inside its own quotient — and the two failure modes {@link #LAYER_2_BLIND_SPOTS} names are
 * exactly of that kind (design D-12). {@link Report#passed()} therefore reads Layer 1 and nothing
 * else, and {@link Report#layer2()} is a field a reader reads, not a field the gate branches on.
 *
 * <h2>The round trip is reported per field</h2>
 *
 * <p>{@link Report#roundTrip()} lists the fields on which the re-lifted model disagrees with the one
 * that was lowered, each with both sides. Never one boolean: a boolean says a file changed and says
 * nothing about where to look, and the point of running the round trip at all is to say where.
 *
 * <p>Provenance is deliberately outside the comparison. The lowered file is a different file with
 * different line numbers, so comparing sites would compare the two files' formatting rather than
 * what they say; the model's {@code version} is outside it for the same reason. What is compared is
 * the six fields the capability states: type, objects, events in declaration order, order automaton,
 * constraints and predicates.
 */
public final class RoundTripGate {

    /** The rule behind every Layer 1 violation, stated in full (INV-CONF-02). */
    public static final String LAYER_1_RULE =
            "five checks over the generated specification as written, before any normalization. "
                    + "Four are AstChecker's, run over the generated tree: " + AstChecker.RULE
                    + ". The fifth is M0.3: every signature the generated pointcuts resolve to is "
                    + "looked up in the android.jar index, and a signature whose declaring class "
                    + "the index does not have is a violation, while a miss on a class the index "
                    + "does have is a limitation of the checker and is reported as a note";

    /** Why Layer 2 is evidence and not the gate. */
    public static final String LAYER_2_STANDING =
            "Layer 2 is evidence and never decides. An equivalence gate compares the generator's "
                    + "output against the rule through the same normalization layer the comparator "
                    + "uses, so it cannot see a defect living inside its own quotient (design "
                    + "D-12). Its verdict is published with the normalizations it was made under, "
                    + "because 'equivalent under two erasures' and 'equivalent' are different "
                    + "claims";

    /**
     * The two failure modes Layer 2 provably cannot catch, each with the corpus file that shows it.
     *
     * <p>They are the reason the split exists, so they are written down rather than left as an
     * assertion in a design document. {@code RoundTripGateTest} demonstrates the first: Layer 1
     * fails a generated specification with an event absent from the formula while Layer 2, asked
     * about the same pair, answers {@code EQUIVALENT}.
     */
    public static final String LAYER_2_BLIND_SPOTS =
            "a declared event absent from the ere gains an all-fail transition row and accuses "
                    + "every live monitor of the specification when it fires — jca/PBEKeySpecSpec"
                    + ".mop:26-32 records this having happened — and language equivalence cannot "
                    + "see it, because the event contributes no letter to either language, it is "
                    + "local, and ε-normalization can erase it outright; and a @match with no @fail "
                    + "produces a specification that compiles, runs and never accuses — "
                    + "jca/SecretKeySpec.mop and jca/RandomStringPassword.mop are both exactly that "
                    + "today, which is why M0 refuses SecretKeySpec.mop — and language equivalence "
                    + "cannot see that either, because it is about handlers, and two specifications "
                    + "differing only in the handler have identical languages";

    /** Emitted when no index was supplied, so the fifth Layer 1 check did not run. */
    public static final String NO_INDEX_NOTE =
            "the fifth Layer 1 check did not run: no android.jar index was supplied. No signature "
                    + "of the generated specification was looked up, and the absence of a "
                    + "resolution violation here means 'not checked', not 'resolves'";

    /** The mode a violation carries when the platform has no such class; M0.3's own wording. */
    public static final String ABSENT_CLASS = "CLASSE-AUSENTE";

    private RoundTripGate() {
    }

    /**
     * Lowers one lifted specification, lifts the result back and runs both layers over it.
     *
     * <p>The argument is a {@link MopLift} and not a {@link SpecModel}, and that shape is forced by
     * design D-20: {@code h⁻¹(L)} is applied at lift time, so the model's order automaton is over
     * signatures and the preimage cannot be run backwards into a formula. The label automaton and
     * the morphism are retained on the lift result for exactly this reason, and the lowerer writes
     * the formula from them.
     *
     * @param original        the lift of the file under test
     * @param outputDirectory where the generated {@code .mop} is written; never a corpus directory
     *                        (INV-CONF-12 — this component never writes where it reads)
     * @param index           the {@code android.jar} index, or empty where the platform jar is not
     *                        available, in which case the fifth check does not run and the report
     *                        says so
     * @param oracle          the paired rule's language, or empty when the specification pairs with
     *                        no rule; Layer 2 runs only when it is present
     * @return what both layers found, and where the round trip disagreed
     */
    public static Report run(MopLift original, Path outputDirectory, Optional<ApiIndex> index,
                             Optional<LanguageOracle> oracle)
            throws LowerFailure, IOException, LiftFailure {
        Objects.requireNonNull(original, "the lift under test is mandatory");
        Objects.requireNonNull(index, "index is mandatory (use Optional.empty())");
        Objects.requireNonNull(oracle, "oracle is mandatory (use Optional.empty())");

        String specification = MopLowerer.specificationNameOf(original);
        Path generated = new MopLowerer().lowerTo(original, outputDirectory);
        MopLift regenerated = new MopLifter().read(generated, original.model().version());

        List<String> notes = new ArrayList<>();
        notes.add(MopLowerer.COMMENTS_ARE_DISCARDED);
        notes.add(MopLowerer.FORMULA_SYNTAX_RULE);

        List<String> layer1 = new ArrayList<>(AstChecker.check(specification, regenerated.model(),
                regenerated.labelOrder(),
                regenerated.monitorFacts(MisuseAbsorption.scan(generated))));
        if (index.isPresent()) {
            layer1.addAll(unresolved(specification, regenerated.model(), index.get(), notes));
        } else {
            notes.add(NO_INDEX_NOTE);
        }

        Optional<Evidence> layer2 = oracle.map(paired -> {
            ProductSearch.OrderComparison comparison =
                    ProductSearch.compare(regenerated.model().order(), paired.order());
            return new Evidence(paired.rule(), comparison.verdict(),
                    comparison.shortestWitness(paired.normalizations()), paired.normalizations());
        });

        return new Report(specification, generated, List.copyOf(layer1),
                disagreements(original.model(), regenerated.model()), layer2, List.copyOf(notes));
    }

    /**
     * The fifth Layer 1 check, in M0.3's classification order.
     *
     * <p>Exact hit; else the declaring class is absent from the platform, which is a violation about
     * the pointcut; else an arity-only hit, which is a weaker answer and not a finding; else the
     * class is present and the member is not, which is the index's own limitation — it records
     * declared members and does not follow inheritance — and must be reported as a note rather than
     * merged with a real absence.
     */
    private static List<String> unresolved(String specification, SpecModel model, ApiIndex index,
                                           List<String> notes) {
        List<String> violations = new ArrayList<>();
        List<String> uncheckable = new ArrayList<>();
        Set<Signature> seen = new LinkedHashSet<>();
        for (Event event : model.events()) {
            for (Signature signature : event.signatures()) {
                if (!seen.add(signature) || index.hasSignature(signature)) {
                    continue;
                }
                if (!index.hasClass(signature.declaringType())) {
                    violations.add(specification + ": the pointcut of event '"
                            + event.label().name() + "' names " + signature.declaringType()
                            + ", absent from the index built from " + index.source() + " ("
                            + ABSENT_CLASS + "). The generated specification observes a call the "
                            + "platform cannot make");
                } else if (!index.hasSignatureWithArity(signature)) {
                    uncheckable.add(signature.declaringType() + "." + signature.name()
                            + signature.paramTypes());
                }
            }
        }
        if (!uncheckable.isEmpty()) {
            notes.add("the index records declared members and does not follow inheritance, so "
                    + "these lookups missed on a class the platform does have; they are limits of "
                    + "the checker and not absences in the platform: "
                    + String.join(", ", uncheckable));
        }
        return violations;
    }

    /** The six fields, each compared on its own so that the answer says where to look. */
    private static List<Disagreement> disagreements(SpecModel before, SpecModel after) {
        List<Disagreement> found = new ArrayList<>();
        if (!before.type().equals(after.type())) {
            found.add(new Disagreement("type", before.type(), after.type()));
        }
        if (!before.objects().equals(after.objects())) {
            found.add(new Disagreement("objects", objects(before), objects(after)));
        }
        List<Event> left = ordered(before);
        List<Event> right = ordered(after);
        if (left.size() != right.size()) {
            found.add(new Disagreement("events", left.size() + " declared", right.size()
                    + " declared"));
        }
        for (int i = 0; i < Math.min(left.size(), right.size()); i++) {
            if (!left.get(i).equals(right.get(i))) {
                found.add(new Disagreement("events[" + i + "]", event(left.get(i)),
                        event(right.get(i))));
            }
        }
        if (!before.order().equals(after.order())) {
            found.add(new Disagreement("order", order(before.order()), order(after.order())));
        }
        List<String> constraintsBefore = before.constraints().stream().map(Constraint::text).toList();
        List<String> constraintsAfter = after.constraints().stream().map(Constraint::text).toList();
        if (!constraintsBefore.equals(constraintsAfter)) {
            found.add(new Disagreement("constraints", constraintsBefore.toString(),
                    constraintsAfter.toString()));
        }
        predicates(found, "ensures", before.ensures(), after.ensures());
        predicates(found, "requires", before.requires(), after.requires());
        predicates(found, "negates", before.negates(), after.negates());
        return List.copyOf(found);
    }

    private static void predicates(List<Disagreement> found, String field,
                                   List<PredicateRef> before, List<PredicateRef> after) {
        List<String> left = before.stream().map(RoundTripGate::predicate).toList();
        List<String> right = after.stream().map(RoundTripGate::predicate).toList();
        if (!left.equals(right)) {
            found.add(new Disagreement(field, left.toString(), right.toString()));
        }
    }

    private static List<Event> ordered(SpecModel model) {
        List<Event> events = new ArrayList<>(model.events());
        events.sort(Comparator.comparingInt(Event::declIndex));
        return events;
    }

    private static String objects(SpecModel model) {
        return new TreeSet<>(model.objects().stream()
                .map(object -> object.type() + " " + object.name()).toList()).toString();
    }

    private static String event(Event event) {
        return event.label().name() + " signatures=" + new TreeSet<>(event.signatures().stream()
                .map(s -> s.declaringType() + "." + s.name() + s.paramTypes() + ":" + s.returnType())
                .toList()) + " guard=" + event.guard().map(g -> g.text()).orElse("<none>")
                + " pointcut=" + event.pointcutText();
    }

    private static String order(Automaton automaton) {
        return "states=" + new TreeSet<>(automaton.states()) + " initial=" + automaton.initial()
                + " accepting=" + new TreeSet<>(automaton.accepting())
                + " transitions=" + automaton.transitions().size();
    }

    /** A reference by what it says, not by where it was written; see the class comment. */
    private static String predicate(PredicateRef ref) {
        return (ref.polarity() == Polarity.NEGATED ? "!" : "")
                + ref.name() + ref.arguments();
    }

    /**
     * The rule's language, for Layer 2.
     *
     * <p>It arrives as an argument rather than being read here: this module lifts {@code .mop} and
     * nothing else, and reaching for {@code CrySLParser} from it would put the whole Xtext tree on
     * the classpath whose dependency discipline asserts that Guava is absent (INV-CONF-16).
     *
     * @param rule           the rule the specification was paired with, named for the report
     * @param order          its order automaton, over signatures
     * @param normalizations what both sides were compared modulo; empty states that none were, which
     *                       is a real and stronger claim (INV-CONF-08)
     */
    public record LanguageOracle(String rule, Automaton order, List<Normalization> normalizations) {

        public LanguageOracle {
            Objects.requireNonNull(rule, "LanguageOracle.rule is mandatory");
            Objects.requireNonNull(order, "LanguageOracle.order is mandatory");
            normalizations = List.copyOf(normalizations);
        }
    }

    /**
     * What Layer 2 saw. Evidence, never a verdict on the generation.
     *
     * @param rule           the rule compared against
     * @param verdict        the relation between the two languages
     * @param witness        the shortest distinguishing word, absent when they agree
     * @param normalizations the transformations the comparison was made modulo, printed beside the
     *                       verdict because a specification that passes only under N3 and N4 is
     *                       saying something (design D-10)
     */
    public record Evidence(String rule, M2Result.Verdict verdict, Optional<Witness> witness,
                           List<Normalization> normalizations) {

        public Evidence {
            Objects.requireNonNull(rule, "Evidence.rule is mandatory");
            Objects.requireNonNull(verdict, "Evidence.verdict is mandatory");
            Objects.requireNonNull(witness, "Evidence.witness is mandatory (use Optional.empty())");
            normalizations = List.copyOf(normalizations);
        }
    }

    /**
     * One field on which the re-lifted model disagrees with the one that was lowered.
     *
     * @param field the field, indexed where it is a list — {@code events[3]} and not {@code events}
     * @param before what the model said before it was lowered
     * @param after  what the model says after being lowered and lifted back
     */
    public record Disagreement(String field, String before, String after) {

        public Disagreement {
            Objects.requireNonNull(field, "Disagreement.field is mandatory");
            Objects.requireNonNull(before, "Disagreement.before is mandatory");
            Objects.requireNonNull(after, "Disagreement.after is mandatory");
        }

        @Override
        public String toString() {
            return field + ": " + before + "  !=  " + after;
        }
    }

    /**
     * Everything one run of the gate produced.
     *
     * @param specification the specification, named by its file
     * @param generated     the {@code .mop} that was written and lifted back
     * @param layer1        the Layer 1 violations, one line each, empty when the generation is clean
     * @param roundTrip     the fields the round trip disagreed on, empty when it is faithful
     * @param layer2        what the product search saw, absent when no rule was supplied
     * @param notes         the standing caveats this run emitted
     */
    public record Report(String specification, Path generated, List<String> layer1,
                         List<Disagreement> roundTrip, Optional<Evidence> layer2,
                         List<String> notes) {

        public Report {
            Objects.requireNonNull(specification, "Report.specification is mandatory");
            Objects.requireNonNull(generated, "Report.generated is mandatory");
            Objects.requireNonNull(layer2, "Report.layer2 is mandatory (use Optional.empty())");
            layer1 = List.copyOf(layer1);
            roundTrip = List.copyOf(roundTrip);
            notes = List.copyOf(notes);
        }

        /**
         * Whether the generation passes the gate.
         *
         * <p>Layer 1 and nothing else. Layer 2 is evidence and does not decide, and the round trip
         * answers a different question — {@link #faithful()} — about whether the emitter lost
         * anything, which is not the same as whether what it emitted is sound.
         */
        public boolean passed() {
            return layer1.isEmpty();
        }

        /** Whether the model survived the trip through text unchanged, on all six fields. */
        public boolean faithful() {
            return roundTrip.isEmpty();
        }
    }
}
