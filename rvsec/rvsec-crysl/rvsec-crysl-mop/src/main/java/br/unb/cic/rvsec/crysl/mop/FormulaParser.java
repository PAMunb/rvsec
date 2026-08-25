package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Label;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Reads the two formula syntaxes the corpora use — {@code ere} and {@code fsm} — into a
 * {@link LabelAutomaton}.
 *
 * <p>A label automaton and not a signature automaton, because a formula is written over the names
 * the {@code event} declarations introduce and that is all this class can see. Turning those names
 * into the signatures {@link br.unb.cic.rvsec.crysl.core.model.SpecModel#order()} is defined over
 * is the inverse morphism, and it happens once, in {@link MopLifter}, where the events are also in
 * hand.
 *
 * <p>Measured over the five corpora: 65 specifications declare {@code ere}, 133 declare {@code fsm},
 * 17 declare no formula at all, and nothing declares any other logic. {@code ptltl} is refused with
 * {@link UnsupportedLogic} rather than read, because reading a past-time temporal
 * formula with a regular-expression parser produces an automaton over a language nobody wrote, and
 * an automaton is exactly the artifact a reader would trust.
 *
 * <p>The {@code ere} route is the Glushkov (position) construction. It is chosen over Thompson's
 * because it is ε-free by construction, and {@link LabelTransition} has no ε symbol: a Thompson
 * automaton would have to be ε-eliminated before it could be represented at all. The result may be
 * non-deterministic — {@code (g3* g1 | g3* g2)} has two {@code g3} edges out of the start position
 * — which is expected: G03 determinizes before comparing rather than assuming the corpus happens
 * to be deterministic.
 */
public final class FormulaParser {

    /** The identifier {@code ere} uses for the empty word. */
    private static final String EPSILON = "epsilon";

    private static final Pattern FSM_STATE_BLOCK =
            Pattern.compile("([A-Za-z_$][\\w$]*)\\s*\\[([^\\]]*)\\]");
    private static final Pattern FSM_TRANSITION =
            Pattern.compile("([A-Za-z_$][\\w$]*)\\s*->\\s*([A-Za-z_$][\\w$]*)");
    private static final Pattern FSM_ALIAS =
            Pattern.compile("alias\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*([^\\r\\n]*)");

    private FormulaParser() {
    }

    /**
     * Builds the automaton of one formula.
     *
     * @param file        the file, for the message of a refusal
     * @param logic       the declared logic identifier, {@code Property.getType()}
     * @param formulaText the formula as written, {@code Formula.getFormula()}
     * @return the language the formula denotes, over the labels it names
     * @throws UnsupportedLogic if the logic is neither {@code ere} nor {@code fsm}
     * @throws LiftFailure      if the formula does not read in the logic it declares
     */
    public static LabelAutomaton parse(Path file, String logic, String formulaText)
            throws LiftFailure {
        String kind = logic == null ? "" : logic.trim().toLowerCase();
        return switch (kind) {
            case "ere" -> parseEre(file, formulaText);
            case "fsm" -> parseFsm(file, formulaText);
            default -> throw new UnsupportedLogic(file, logic);
        };
    }

    /**
     * The automaton of a specification that declares no formula at all: one accepting state with a
     * self-loop on every declared label.
     *
     * <p>Seventeen files of {@code generic_new} are of this shape — they carry events and handlers
     * and no property. Their language is every word over their own alphabet, and that is what this
     * builds. The alternative that suggests itself, a single state with no transitions, would be
     * the language {ε}, i.e. "this specification forbids every call it declares", which is the
     * opposite of what the file says.
     */
    public static LabelAutomaton unconstrained(Collection<Label> labels) {
        List<LabelTransition> transitions = new ArrayList<>();
        for (Label label : labels) {
            transitions.add(new LabelTransition("q0", label, "q0"));
        }
        return new LabelAutomaton(Set.of("q0"), "q0", Set.of("q0"), transitions);
    }

    // ── ere ──────────────────────────────────────────────────────────────────────────────────

    private static LabelAutomaton parseEre(Path file, String formulaText) throws LiftFailure {
        Node root = new EreReader(file, formulaText == null ? "" : formulaText).parse();
        return glushkov(root);
    }

    /** The regular-expression tree. Sealed so that {@link #glushkov} cannot miss a shape. */
    private sealed interface Node {
    }

    /** The empty word, written {@code epsilon} in the corpus. */
    private record Empty() implements Node {
    }

    /** One label occurrence; {@code position} is what makes the Glushkov states distinct. */
    private record Sym(String label, int position) implements Node {
    }

    private record Concat(Node left, Node right) implements Node {
    }

    private record Alt(Node left, Node right) implements Node {
    }

    /** {@code *} when {@code nullable}, {@code +} when not. */
    private record Repeat(Node body, boolean nullable) implements Node {
    }

    /** {@code ?}. */
    private record Option(Node body) implements Node {
    }

    /** Recursive-descent reader for {@code alt := concat ('|' concat)*}. */
    private static final class EreReader {

        private final Path file;
        private final String text;
        private int index;
        private int nextPosition;

        EreReader(Path file, String text) {
            this.file = file;
            this.text = text;
        }

        Node parse() throws LiftFailure {
            Node node = alt();
            skipSpace();
            if (index < text.length()) {
                throw new LiftFailure(file,
                        "unexpected '" + text.charAt(index) + "' at offset " + index
                                + " of ere formula: " + text.trim());
            }
            return node;
        }

        private Node alt() throws LiftFailure {
            Node left = concat();
            while (peek() == '|') {
                index++;
                left = new Alt(left, concat());
            }
            return left;
        }

        private Node concat() throws LiftFailure {
            Node left = null;
            while (true) {
                skipSpace();
                char c = peek();
                if (c == 0 || c == '|' || c == ')') {
                    break;
                }
                Node next = repeat();
                left = left == null ? next : new Concat(left, next);
            }
            return left == null ? new Empty() : left;
        }

        private Node repeat() throws LiftFailure {
            Node node = atom();
            while (true) {
                skipSpace();
                char c = peek();
                if (c == '*') {
                    index++;
                    node = new Repeat(node, true);
                } else if (c == '+') {
                    index++;
                    node = new Repeat(node, false);
                } else if (c == '?') {
                    index++;
                    node = new Option(node);
                } else {
                    return node;
                }
            }
        }

        private Node atom() throws LiftFailure {
            skipSpace();
            char c = peek();
            if (c == '(') {
                index++;
                Node inner = alt();
                skipSpace();
                if (peek() != ')') {
                    throw new LiftFailure(file,
                            "unbalanced '(' in ere formula: " + text.trim());
                }
                index++;
                return inner;
            }
            if (Character.isJavaIdentifierStart(c)) {
                int start = index;
                while (index < text.length() && Character.isJavaIdentifierPart(text.charAt(index))) {
                    index++;
                }
                String identifier = text.substring(start, index);
                return EPSILON.equals(identifier) ? new Empty() : new Sym(identifier, nextPosition++);
            }
            throw new LiftFailure(file,
                    "unexpected '" + c + "' at offset " + index + " of ere formula: " + text.trim());
        }

        private void skipSpace() {
            while (index < text.length() && Character.isWhitespace(text.charAt(index))) {
                index++;
            }
        }

        private char peek() {
            skipSpace();
            return index < text.length() ? text.charAt(index) : 0;
        }
    }

    /**
     * The Glushkov construction: states are {@code q0} plus one per symbol occurrence, and the
     * language of the automaton is the language of the expression, with no ε edges anywhere.
     */
    private static LabelAutomaton glushkov(Node root) {
        Map<Integer, String> symbolAt = new LinkedHashMap<>();
        positions(root, symbolAt);

        Set<Integer> first = new LinkedHashSet<>();
        Set<Integer> last = new LinkedHashSet<>();
        Map<Integer, Set<Integer>> follow = new LinkedHashMap<>();
        first(root, first);
        last(root, last);
        follow(root, follow);

        Set<String> states = new LinkedHashSet<>();
        states.add("q0");
        symbolAt.keySet().forEach(p -> states.add("q" + (p + 1)));

        List<LabelTransition> transitions = new ArrayList<>();
        for (Integer p : first) {
            transitions.add(edge("q0", symbolAt.get(p), "q" + (p + 1)));
        }
        for (Map.Entry<Integer, Set<Integer>> entry : follow.entrySet()) {
            for (Integer target : entry.getValue()) {
                transitions.add(edge("q" + (entry.getKey() + 1), symbolAt.get(target),
                        "q" + (target + 1)));
            }
        }

        Set<String> accepting = new LinkedHashSet<>();
        last.forEach(p -> accepting.add("q" + (p + 1)));
        if (nullable(root)) {
            accepting.add("q0");
        }
        return new LabelAutomaton(states, "q0", accepting, transitions);
    }

    private static LabelTransition edge(String from, String label, String to) {
        return new LabelTransition(from, new Label(label), to);
    }

    private static void positions(Node node, Map<Integer, String> out) {
        switch (node) {
            case Sym s -> out.put(s.position(), s.label());
            case Concat c -> {
                positions(c.left(), out);
                positions(c.right(), out);
            }
            case Alt a -> {
                positions(a.left(), out);
                positions(a.right(), out);
            }
            case Repeat r -> positions(r.body(), out);
            case Option o -> positions(o.body(), out);
            case Empty ignored -> {
                // no positions
            }
        }
    }

    private static boolean nullable(Node node) {
        return switch (node) {
            case Empty ignored -> true;
            case Sym ignored -> false;
            case Concat c -> nullable(c.left()) && nullable(c.right());
            case Alt a -> nullable(a.left()) || nullable(a.right());
            case Repeat r -> r.nullable() || nullable(r.body());
            case Option ignored -> true;
        };
    }

    private static void first(Node node, Set<Integer> out) {
        switch (node) {
            case Empty ignored -> {
                // nothing can start an empty word
            }
            case Sym s -> out.add(s.position());
            case Concat c -> {
                first(c.left(), out);
                if (nullable(c.left())) {
                    first(c.right(), out);
                }
            }
            case Alt a -> {
                first(a.left(), out);
                first(a.right(), out);
            }
            case Repeat r -> first(r.body(), out);
            case Option o -> first(o.body(), out);
        }
    }

    private static void last(Node node, Set<Integer> out) {
        switch (node) {
            case Empty ignored -> {
                // nothing can end an empty word
            }
            case Sym s -> out.add(s.position());
            case Concat c -> {
                last(c.right(), out);
                if (nullable(c.right())) {
                    last(c.left(), out);
                }
            }
            case Alt a -> {
                last(a.left(), out);
                last(a.right(), out);
            }
            case Repeat r -> last(r.body(), out);
            case Option o -> last(o.body(), out);
        }
    }

    private static void follow(Node node, Map<Integer, Set<Integer>> out) {
        switch (node) {
            case Concat c -> {
                follow(c.left(), out);
                follow(c.right(), out);
                Set<Integer> lastOfLeft = new LinkedHashSet<>();
                last(c.left(), lastOfLeft);
                Set<Integer> firstOfRight = new LinkedHashSet<>();
                first(c.right(), firstOfRight);
                for (Integer p : lastOfLeft) {
                    out.computeIfAbsent(p, k -> new LinkedHashSet<>()).addAll(firstOfRight);
                }
            }
            case Alt a -> {
                follow(a.left(), out);
                follow(a.right(), out);
            }
            case Repeat r -> {
                follow(r.body(), out);
                Set<Integer> lastOfBody = new LinkedHashSet<>();
                last(r.body(), lastOfBody);
                Set<Integer> firstOfBody = new LinkedHashSet<>();
                first(r.body(), firstOfBody);
                for (Integer p : lastOfBody) {
                    out.computeIfAbsent(p, k -> new LinkedHashSet<>()).addAll(firstOfBody);
                }
            }
            case Option o -> follow(o.body(), out);
            case Sym ignored -> {
                // a single position follows nothing on its own
            }
            case Empty ignored -> {
                // likewise
            }
        }
    }

    // ── fsm ──────────────────────────────────────────────────────────────────────────────────

    /**
     * Reads the {@code fsm} syntax: a sequence of {@code state [ label -> state ... ]} blocks
     * followed by optional {@code alias name = state} lines.
     *
     * <p>The initial state is the first block declared, which is JavaMOP's own rule. The accepting
     * set comes from the {@code match} aliases when the specification declares any: measured over
     * the corpora, every alias written is {@code match1} or {@code match2} and names exactly one
     * state, and all 18 of them live in the three JCA sets. The 118 {@code generic} specifications
     * declare no alias at all and accuse only through {@code @fail}, whose semantics is "the trace
     * left the machine": there every declared state is accepting and a transition into a state that
     * no block declares is the sink. Those two rules are the same rule seen from the two sides of
     * the corpus, and collapsing them into "accepting = all states" would make every {@code
     * match1} specification accept its own violating traces.
     */
    private static LabelAutomaton parseFsm(Path file, String formulaText) throws LiftFailure {
        String text = formulaText == null ? "" : formulaText;

        Map<String, List<String[]>> blocks = new LinkedHashMap<>();
        Matcher blockMatcher = FSM_STATE_BLOCK.matcher(text);
        while (blockMatcher.find()) {
            String state = blockMatcher.group(1);
            List<String[]> edges = new ArrayList<>();
            Matcher edgeMatcher = FSM_TRANSITION.matcher(blockMatcher.group(2));
            while (edgeMatcher.find()) {
                edges.add(new String[] {edgeMatcher.group(1), edgeMatcher.group(2)});
            }
            blocks.computeIfAbsent(state, k -> new ArrayList<>()).addAll(edges);
        }
        if (blocks.isEmpty()) {
            throw new LiftFailure(file, "fsm formula declares no state block: " + text.trim());
        }

        Set<String> declared = new LinkedHashSet<>(blocks.keySet());
        Set<String> states = new LinkedHashSet<>(declared);
        List<LabelTransition> transitions = new ArrayList<>();
        for (Map.Entry<String, List<String[]>> block : blocks.entrySet()) {
            for (String[] edge : block.getValue()) {
                states.add(edge[1]);
                transitions.add(edge(block.getKey(), edge[0], edge[1]));
            }
        }

        Set<String> accepting = new LinkedHashSet<>();
        boolean sawMatchAlias = false;
        Matcher aliasMatcher = FSM_ALIAS.matcher(text);
        while (aliasMatcher.find()) {
            if (!aliasMatcher.group(1).toLowerCase().startsWith("match")) {
                continue;
            }
            sawMatchAlias = true;
            for (String state : aliasMatcher.group(2).trim().split("[\\s,]+")) {
                if (states.contains(state)) {
                    accepting.add(state);
                }
            }
        }
        if (!sawMatchAlias) {
            accepting.addAll(declared);
        }

        String initial = blocks.keySet().iterator().next();
        return new LabelAutomaton(states, initial, accepting, transitions);
    }
}
