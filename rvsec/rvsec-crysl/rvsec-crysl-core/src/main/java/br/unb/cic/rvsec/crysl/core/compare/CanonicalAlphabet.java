package br.unb.cic.rvsec.crysl.core.compare;

import br.unb.cic.rvsec.crysl.core.metric.M1Events;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * The one alphabet two declared orders are compared over.
 *
 * <p>Both sides arrive as automata over real signatures - design D-20 put the inverse morphism at
 * lift time, so {@code SpecModel.order} is a signature language on the {@code .mop} side as much as
 * on the rule side. Two signature sets are still not one alphabet: a pointcut writes
 * {@code getInstance(String, Object+)} where the rule writes {@code getInstance(algorithm, _)}, and
 * comparing those letters for equality answers that the two languages disagree about every word
 * containing either.
 *
 * <p>So the letters are <em>identified</em> first, by the R-M1 match relation and by nothing else.
 * Identification is transitive here: the connected components of the bipartite match graph are the
 * canonical letters, and each component's representative is its smallest rule signature when it has
 * one and its smallest {@code .mop} signature otherwise. A component with more than one signature on
 * a side is the 1:N aggregate the corpus is full of - {@code update(..)} against {@code u1..u4} -
 * and the fact that it occurred is reported as {@link Normalizations#AGGREGATE} rather than left
 * implicit.
 *
 * <p>No name comparison of any kind takes part, on either side. On this corpus none is correct:
 * {@code SecureRandomSpec.g3} is the rule's {@code gI} and {@code setSeed1} is the rule's
 * {@code s2}. The label-level association the alphabet map declares is used for &epsilon;-erasure
 * and for reporting, and it is deliberately a second, independent route: the map is a hand-written
 * judgement with an owner, and the signature match is mechanical, so a disagreement between them is
 * a finding rather than a silent tie-break.
 *
 * @param mopToCanonical   every {@code .mop} letter to the canonical letter it was identified with
 * @param ruleToCanonical  every rule letter to the canonical letter it was identified with
 * @param aggregated       whether some canonical letter carries more than one signature on a side
 */
public record CanonicalAlphabet(Map<Signature, Signature> mopToCanonical,
                                Map<Signature, Signature> ruleToCanonical,
                                boolean aggregated) {

    /** Total order over signatures, so that the representative of a component is reproducible. */
    public static final Comparator<Signature> ORDER = Comparator
            .comparing(Signature::declaringType)
            .thenComparing(Signature::name)
            .thenComparing(s -> String.join(",", s.paramTypes()))
            .thenComparing(Signature::returnType);

    /** The counting rule behind the identification (INV-CONF-02). */
    public static final String COUNTING_RULE =
            "R-M2-alphabet: the canonical letters are the connected components of the bipartite "
                    + "graph whose edges are identifies(mopSignature, ruleSignature): the "
                    + "declaring types agree, the names are equal, and the parameter lists agree "
                    + "position by position, where a position agrees when the two type names "
                    + "denote the same type, or the .mop leaves it open ('*', or a trailing '..' "
                    + "consuming the rest), or the rule leaves it unbound ('_', rendered AnyType). "
                    + "This differs from R-M1 in the last clause, deliberately and only there. A "
                    + "component's representative is its smallest rule signature, or its smallest "
                    + ".mop signature when it contains none. A signature that identifies with "
                    + "nothing on the other side is its own letter and stays in the comparison, so "
                    + "a letter only one side has produces a distinguishing word rather than "
                    + "disappearing.";

    /**
     * Why the rule's hole widens here and does not widen in M1.
     *
     * <p>Printed beside the counting rule wherever an M2 aggregate is published, because the two
     * relations disagreeing is exactly the kind of thing a later reader would take for a bug.
     */
    public static final String HOLE_CAVEAT =
            "R-M2-alphabet widens at the rule's unbound argument where R-M1 refuses to. The two "
                    + "questions are different. M1 asks how much of the rule the specification "
                    + "covers, and there the oracle must not widen to fit the artifact under test: "
                    + "a .mop that monitors getInstance(String, String) has not covered the rule's "
                    + "getInstance(algorithm, _), which also names getInstance(String, Provider). "
                    + "M2 asks whether the two languages accept the same words, and there the "
                    + "rule's '_' really does accept whatever argument the call carried, so "
                    + "refusing to identify the two letters would invent a divergence in both "
                    + "directions over a call both languages accept - which is what it did when "
                    + "measured: SSLContextSpec, SignatureSpec and MessageDigestSpec each came out "
                    + "INCOMPARABLE on a getInstance overload the rule leaves open.";

    public CanonicalAlphabet {
        mopToCanonical = Map.copyOf(mopToCanonical);
        ruleToCanonical = Map.copyOf(ruleToCanonical);
    }

    /**
     * Identifies the two alphabets.
     *
     * @param mopLetters  the letters of the specification's order automaton
     * @param ruleLetters the letters of the rule's order automaton
     */
    public static CanonicalAlphabet of(Set<Signature> mopLetters, Set<Signature> ruleLetters) {
        List<Signature> mop = sorted(mopLetters);
        List<Signature> rule = sorted(ruleLetters);

        // Union-find over the disjoint union of the two sides. The side tag is part of the key
        // because a .mop signature and a rule signature can be equal records and still have to be
        // told apart when reporting which side an aggregate happened on.
        Map<String, String> parent = new LinkedHashMap<>();
        mop.forEach(s -> parent.put(key("mop", s), key("mop", s)));
        rule.forEach(s -> parent.put(key("rule", s), key("rule", s)));
        for (Signature m : mop) {
            for (Signature r : rule) {
                if (identifies(m, r)) {
                    union(parent, key("mop", m), key("rule", r));
                }
            }
        }

        Map<String, List<Signature>> mopMembers = new TreeMap<>();
        Map<String, List<Signature>> ruleMembers = new TreeMap<>();
        mop.forEach(s -> mopMembers.computeIfAbsent(find(parent, key("mop", s)),
                k -> new ArrayList<>()).add(s));
        rule.forEach(s -> ruleMembers.computeIfAbsent(find(parent, key("rule", s)),
                k -> new ArrayList<>()).add(s));

        Set<String> components = new LinkedHashSet<>();
        components.addAll(mopMembers.keySet());
        components.addAll(ruleMembers.keySet());

        Map<Signature, Signature> mopToCanonical = new LinkedHashMap<>();
        Map<Signature, Signature> ruleToCanonical = new LinkedHashMap<>();
        boolean aggregated = false;
        for (String component : components) {
            List<Signature> mopSide = mopMembers.getOrDefault(component, List.of());
            List<Signature> ruleSide = ruleMembers.getOrDefault(component, List.of());
            Signature representative = ruleSide.isEmpty()
                    ? sorted(mopSide).get(0)
                    : sorted(ruleSide).get(0);
            mopSide.forEach(s -> mopToCanonical.put(s, representative));
            ruleSide.forEach(s -> ruleToCanonical.put(s, representative));
            aggregated |= mopSide.size() > 1 || ruleSide.size() > 1;
        }
        return new CanonicalAlphabet(mopToCanonical, ruleToCanonical, aggregated);
    }

    /**
     * Whether a {@code .mop} letter and a rule letter denote the same call.
     *
     * <p>{@link M1Events#matches} decides everything except the rule's hole, and this method
     * delegates to it for everything except the rule's hole: the widening is one clause, applied at
     * one position kind, and stated in {@link #HOLE_CAVEAT}.
     */
    public static boolean identifies(Signature mop, Signature rule) {
        if (M1Events.matches(mop, rule)) {
            return true;
        }
        if (!mop.name().equals(rule.name())) {
            return false;
        }
        List<String> declared = mop.paramTypes();
        List<String> holed = new ArrayList<>(rule.paramTypes());
        for (int i = 0; i < holed.size(); i++) {
            if (M1Events.RULE_HOLE.equals(holed.get(i)) && i < declared.size()
                    && !M1Events.MOP_TAIL_WILDCARD.equals(declared.get(i))) {
                // The rule accepts whatever the call carried at this position, so the .mop's
                // concrete type is one of the arguments the hole stands for. Substituting it makes
                // the remaining comparison the ordinary one.
                holed.set(i, declared.get(i));
            }
        }
        return M1Events.matches(mop,
                new Signature(rule.declaringType(), rule.name(), holed, rule.returnType()));
    }

    private static List<Signature> sorted(java.util.Collection<Signature> signatures) {
        List<Signature> ordered = new ArrayList<>(new LinkedHashSet<>(signatures));
        ordered.sort(ORDER);
        return ordered;
    }

    private static String key(String side, Signature signature) {
        return side + "|" + signature.declaringType() + "#" + signature.name() + "("
                + String.join(",", signature.paramTypes()) + ")" + signature.returnType();
    }

    private static String find(Map<String, String> parent, String node) {
        String root = node;
        while (!parent.get(root).equals(root)) {
            root = parent.get(root);
        }
        String walk = node;
        while (!parent.get(walk).equals(root)) {
            String next = parent.get(walk);
            parent.put(walk, root);
            walk = next;
        }
        return root;
    }

    private static void union(Map<String, String> parent, String left, String right) {
        String a = find(parent, left);
        String b = find(parent, right);
        if (!a.equals(b)) {
            parent.put(a, b);
        }
    }
}
