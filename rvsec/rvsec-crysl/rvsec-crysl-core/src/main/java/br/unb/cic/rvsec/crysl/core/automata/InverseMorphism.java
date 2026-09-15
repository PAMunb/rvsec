package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;

/**
 * The morphism {@code h} from signature words to label words, and the preimage {@code h-inverse(L)}
 * of a label language under it.
 *
 * <p>{@code h} carries one signature to the concatenation, in declaration order, of every label
 * whose pointcut matches it. Concatenation rather than choice, because the alphabet is not disjoint
 * in the corpus and one call really does emit several letters: in {@code IvChainJunction} both
 * {@code use} and {@code useRandomSpec} match a single
 * {@code Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)} call and neither declares a
 * {@code condition}, so that one call drives the monitor through two transitions. A representation
 * that maps a label to a set of signatures has already lost this before any comparison runs, which
 * is why it is forbidden (INV-CONF-03) and why this construction is a construction step rather than
 * a normalization applied afterwards.
 *
 * <p>Declaration order is dispatch order, so {@link Event#declIndex()} is what orders the image.
 * Two events reordered in the file produce a different morphism and a different language, and that
 * is a real difference rather than an artefact.
 *
 * <p>The preimage is an automaton because inverse morphism preserves regularity: over the states of
 * the label automaton, the edge for signature {@code s} out of state {@code q} goes to every state
 * that reading the whole word {@code h(s)} from {@code q} reaches. The comparison therefore stays
 * decidable and stays cheap.
 *
 * @param images   for each signature of the alphabet, the labels it emits, in declaration order
 * @param refusals the overlaps this module could not resolve
 */
public record InverseMorphism(Map<Signature, List<Label>> images, List<Unknown> refusals) {

    /** AspectJ's "any remaining parameters" pattern, as {@code PointcutExpander} writes it. */
    private static final String ELLIPSIS = "..";

    /** AspectJ's single-parameter wildcard, as {@code PointcutExpander} writes it. */
    private static final String ANY = "*";

    public InverseMorphism {
        images = Map.copyOf(images);
        refusals = List.copyOf(refusals);
    }

    /**
     * Builds {@code h} from the events of one specification.
     *
     * <p>Where two or more labels match one signature and any of them carries a guard, the result
     * is a refusal rather than a choice. This module has no guard solver, so a guard here is by
     * construction not statically decidable, and the single point that would consult a solver if
     * one ever existed is this method. Picking one of the overlapping labels and continuing is
     * precisely the silent failure the {@code Unknown} taxonomy exists to prevent: the report would
     * then be confidently wrong about how many letters the call emits, with nothing in the output
     * saying a choice was made.
     *
     * @param events the events of the specification, in any order - {@code declIndex} is what
     *               orders them here
     * @param site   where a refusal is reported to have happened, normally the specification file
     */
    public static InverseMorphism of(List<Event> events, Provenance site) {
        Objects.requireNonNull(site, "InverseMorphism.of needs a site to attribute refusals to");

        List<Event> ordered = new ArrayList<>(events);
        ordered.sort(Comparator.comparingInt(Event::declIndex));

        // Two passes, because matching is not equality. The first fixes the alphabet - every
        // signature any event names - and the second asks, of each letter, which events name
        // something that denotes it. One pass keyed on equality would miss the pattern case below.
        Map<Signature, List<Event>> matching = new TreeMap<>(Alphabet.ORDER);
        for (Event event : ordered) {
            for (Signature signature : event.signatures()) {
                matching.computeIfAbsent(signature, key -> new ArrayList<>());
            }
        }
        for (Map.Entry<Signature, List<Event>> entry : matching.entrySet()) {
            for (Event event : ordered) {
                if (event.signatures().stream().anyMatch(s -> denotes(s, entry.getKey()))) {
                    entry.getValue().add(event);
                }
            }
        }

        Map<Signature, List<Label>> images = new LinkedHashMap<>();
        List<Unknown> refusals = new ArrayList<>();
        for (Map.Entry<Signature, List<Event>> entry : matching.entrySet()) {
            List<Event> matched = entry.getValue();
            boolean overlapping = matched.size() > 1;
            boolean guarded = matched.stream().anyMatch(event -> event.guard().isPresent());
            if (overlapping && guarded) {
                refusals.add(new OverlappingDispatch(
                        matched.stream().map(event -> event.label().name()).toList(),
                        entry.getKey(), site));
                continue;
            }
            images.put(entry.getKey(), matched.stream().map(Event::label).toList());
        }
        return new InverseMorphism(images, refusals);
    }

    /**
     * This morphism with every refused overlap that the given erasures reduce to a single label
     * resolved to that label.
     *
     * <p>The overlap the corpus refuses is the negated-twin idiom: an admitting event and a refused
     * twin over one call, separated by complementary {@code condition}s. The twin stands for the
     * value the rule rejects in {@code CONSTRAINTS}, and the alphabet map erases it because an
     * {@code ORDER} has no symbol for such a call. With the twin read as &epsilon;, the labels the
     * call can emit in the order are the survivor's alone, so the call is the survivor's letter and
     * the guard that chose between the two is left to M3, as every other guard is. An overlap with
     * two or more surviving labels stays refused: which of them fires is still a guard this module
     * cannot decide. An overlap whose labels are all erased stays refused too; the corpus has none,
     * and no rule is offered for a shape nothing exercises.
     *
     * @param erased the labels the alphabet map erases, for the specification this morphism belongs
     *               to. The map is read by M2 alone (INV-CONF-10), which is why this is a parameter
     *               and not something the lift decides
     */
    public InverseMorphism resolvedBy(Set<Label> erased) {
        Map<Signature, List<Label>> resolved = new LinkedHashMap<>(images);
        List<Unknown> remaining = new ArrayList<>();
        for (Unknown refusal : refusals) {
            if (refusal instanceof OverlappingDispatch overlap) {
                List<String> survivors = overlap.labels().stream()
                        .filter(label -> !erased.contains(new Label(label)))
                        .toList();
                if (survivors.size() == 1) {
                    resolved.put(overlap.signature(), List.of(new Label(survivors.get(0))));
                    continue;
                }
            }
            remaining.add(refusal);
        }
        return new InverseMorphism(resolved, remaining);
    }

    /**
     * Whether {@code pattern} denotes {@code letter}: position by position the parameter types are
     * equal or the pattern writes AspectJ's single-parameter {@code *} there, and the arities agree
     * - exactly, or at least up to the prefix when the pattern ends in AspectJ's {@code ..}.
     *
     * <p>Without the ellipsis rule the motivating case of design D-02 does not occur in the corpus
     * at all. {@code IvChainJunction} writes {@code use} as
     * {@code call(public void Cipher.init(int, Key, AlgorithmParameterSpec, ..))} and
     * {@code useRandomSpec} as
     * {@code call(public void Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom))}: one
     * call really does match both and really does emit two letters, and comparing the two
     * signatures for equality answers that it does not. The letters of the alphabet stay exactly
     * the signatures the lift writes - this widens which events claim a letter, never how many
     * letters there are.
     *
     * <p>The {@code .mop} files write a {@code ..} only last and never write a {@code *} in a
     * parameter position; the {@code *} comes from the lift, which narrows a trailing {@code ..} to
     * the arity of the {@code args(...)} clause beside it, so {@code getInstance(String, ..)} with
     * {@code args(alg, *)} is {@code getInstance(String, *)} and claims the two-argument letters
     * only. A CrySL signature carries neither, which makes both rules inert on that side rather
     * than a MOP-ism the model has to know about.
     */
    private static boolean denotes(Signature pattern, Signature letter) {
        if (!pattern.declaringType().equals(letter.declaringType())
                || !pattern.name().equals(letter.name())
                || !pattern.returnType().equals(letter.returnType())) {
            return false;
        }
        List<String> declared = pattern.paramTypes();
        List<String> actual = letter.paramTypes();
        boolean tail = !declared.isEmpty() && ELLIPSIS.equals(declared.get(declared.size() - 1));
        List<String> prefix = tail ? declared.subList(0, declared.size() - 1) : declared;
        if (tail ? actual.size() < prefix.size() : actual.size() != prefix.size()) {
            return false;
        }
        for (int i = 0; i < prefix.size(); i++) {
            if (!ANY.equals(prefix.get(i)) && !prefix.get(i).equals(actual.get(i))) {
                return false;
            }
        }
        return true;
    }

    /**
     * The preimage {@code h-inverse(L)}: a signature automaton accepting exactly the signature
     * words whose image under {@code h} is in {@code language}.
     *
     * <p>Guards do not travel into the result. They are a side condition on the event and deciding
     * one is M3's subject, not M2's; the one case where a guard changes which letters a call emits
     * is the overlap, and that case was already refused by {@link #of}.
     *
     * @throws IllegalStateException when the morphism carries refusals. A language computed from a
     *                               morphism that does not know what some call emits would be a
     *                               confident answer built on an admitted gap, so the refusals have
     *                               to be read and reported rather than stepped over.
     */
    public Automaton preimage(LabelAutomaton language) {
        if (!refusals.isEmpty()) {
            throw new IllegalStateException(
                    "the morphism refused " + refusals.size() + " overlapping dispatch(es); read "
                            + "refusals() and report them - a preimage computed over an unresolved "
                            + "overlap would be a confident answer built on an admitted gap");
        }
        // States and letters are walked in a fixed order so that two runs over the same input
        // produce the same record: Automaton holds its edges in a List, so an unstable order would
        // make two equal languages compare unequal.
        List<String> states = new ArrayList<>(language.states());
        states.sort(Comparator.naturalOrder());
        List<Signature> alphabet = Alphabet.sorted(images.keySet());

        List<Transition> transitions = new ArrayList<>();
        for (String state : states) {
            for (Signature symbol : alphabet) {
                List<String> targets = new ArrayList<>(language.follow(Set.of(state), images.get(symbol)));
                targets.sort(Comparator.naturalOrder());
                for (String target : targets) {
                    transitions.add(new Transition(state, symbol, Optional.empty(), target));
                }
            }
        }
        return new Automaton(language.states(), language.initial(), language.accepting(),
                transitions);
    }
}
