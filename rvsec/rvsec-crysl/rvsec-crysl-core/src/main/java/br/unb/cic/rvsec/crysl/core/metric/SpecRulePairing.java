package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * Which rule is the oracle of which specification (INV-CONF-11).
 *
 * <h2>By declared type, and never by file name</h2>
 *
 * <p>The rule's {@code SPEC} fully-qualified name is matched against the type the specification
 * declares — the type of its declared parameter, or, for a parameterless specification, the
 * declaring type of its pointcuts, which is the fallback {@code MopLifter} already resolves into
 * {@link SpecModel#type()}.
 *
 * <p>Pairing by file name is forbidden and the corpus proves why rather than merely asserting it.
 * {@code jca_android/SecretKeySpec.mop} declares {@code SecretKeySpec(SecretKey secretKey)} and its
 * oracle is {@code SecretKey.crysl}; {@code jca_android/SecretKeySpecSpec.mop} declares
 * {@code SecretKeySpecSpec(SecretKeySpec secretKeySpec)} and its oracle is
 * {@code SecretKeySpec.crysl}. A name match sends the first file to the second rule and finds two
 * candidates for it. Five files of the set also declare a specification whose name is not the file
 * name at all ({@code IvChainJunction.mop} declares {@code IvChainJunctionSpec},
 * {@code IvParameterSpec.mop} declares {@code IvParameterSpecSpec}, and so on), so neither the file
 * name nor the specification name is a reliable key.
 *
 * <h2>The declared type arrives unqualified, and that is not a defect</h2>
 *
 * <p>{@code MopLifter} keeps the declared parameter type exactly as the file writes it, so
 * {@code CipherSpec} carries {@code Cipher} and not {@code javax.crypto.Cipher}; the two
 * parameterless specifications carry a fully-qualified name because it came from a resolved
 * pointcut. Matching therefore folds to the simple name when one side is unqualified, which is
 * unambiguous here for a checkable reason: the 49 upstream rules have 49 distinct simple names. Two
 * qualified names that differ never fold, so a specification that named a genuinely different
 * package would not be paired.
 *
 * <h2>A rule is the oracle of one specification</h2>
 *
 * <p>The pairing is <strong>injective</strong>: a rule pairs with at most one specification. This
 * is not tidiness. Every aggregate of this component is stated over "the paired rules" — the
 * denominator M3 counts clauses in, the set M4 counts predicates over — and a rule read twice is a
 * rule counted twice in each of them.
 *
 * <p>The corpus forces the question. {@code CipherSpec.mop} and {@code IvChainJunction.mop} both
 * declare {@code Cipher c}, so by declared type both reach {@code Cipher.crysl}, and the type alone
 * cannot say which of them the rule is the oracle of. The tie is broken by <em>which specification
 * covers more of the rule's declared signatures</em>, under the same match relation M1 measures
 * with ({@link M1Events#matches}) — a signature-derived criterion, never a name. Where coverage
 * ties, the specification declaring more events wins; where that ties too, the lexicographically
 * first name wins, so a run is reproducible.
 *
 * <p>Measured on {@code jca_android} against the upstream rules, that resolves as
 * {@code CipherSpec} taking {@code Cipher.crysl} and {@code IvChainJunction} left unpaired — which
 * is what the junction is: it reads three of {@code Cipher}'s {@code REQUIRES} clauses over
 * arguments {@code CipherSpec} cannot bind, its {@code ere} accepts every sequence of its own
 * events, and it translates no rule. The loser is not dropped in silence: it appears in
 * {@link Result#unpaired()} with {@link Reason#RULE_CLAIMED_BY_ANOTHER_SPECIFICATION} and the name
 * of the specification that took the rule.
 */
public final class SpecRulePairing {

    /** The pairing rule, stated in full for the report header every metric emits (INV-CONF-11). */
    public static final String PAIRING_RULE =
            "INV-CONF-11: by declared type - the rule's SPEC fully-qualified name against the type "
                    + "of the specification's declared parameter, or the declaring type of its "
                    + "pointcuts when it declares none. Names fold to the simple name only when one "
                    + "side is unqualified (the 49 upstream rules have 49 distinct simple names); "
                    + "two qualified names that differ never fold. Pairing is injective - a rule is "
                    + "the oracle of at most one specification - and a rule two specifications "
                    + "declare the type of goes to the one covering more of its declared "
                    + "signatures under R-M1, then to the one declaring more events, then to the "
                    + "lexicographically first name. Pairing by file name is forbidden.";

    private SpecRulePairing() {
    }

    /** Why a specification has no rule. */
    public enum Reason {
        /** No rule of the oracle declares the type the specification is about. */
        NO_RULE_DECLARES_THE_TYPE,
        /** The rule for that type is the oracle of another specification of the same corpus. */
        RULE_CLAIMED_BY_ANOTHER_SPECIFICATION
    }

    /**
     * One artifact and the identifier the corpus knows it by.
     *
     * @param name  the corpus identifier, e.g. {@code MessageDigestSpec} or {@code MessageDigest}
     * @param model the lifted model
     */
    public record Candidate(String name, SpecModel model) {

        public Candidate {
            Objects.requireNonNull(name, "Candidate.name is mandatory");
            Objects.requireNonNull(model, "Candidate.model is mandatory");
        }
    }

    /**
     * One specification and the rule that is its oracle.
     *
     * @param specification the specification
     * @param rule          the rule it was paired with
     * @param covered       how many of the rule's declared signatures the specification monitors,
     *                      which is also what broke the tie when the rule was contested
     */
    public record Pair(Candidate specification, Candidate rule, int covered) {
    }

    /**
     * A specification with no rule, and why.
     *
     * @param specification the specification
     * @param reason        which of the two causes applies
     * @param detail        the declared type, or the specification that took the rule
     */
    public record Miss(Candidate specification, Reason reason, String detail) {
    }

    /**
     * The outcome, with the pairing rule that produced it.
     *
     * @param pairs       the pairs, in specification-name order
     * @param unpaired    the specifications with no rule, in specification-name order
     * @param pairingRule the rule behind both lists (INV-CONF-11)
     */
    public record Result(List<Pair> pairs, List<Miss> unpaired, String pairingRule) {

        public Result {
            Objects.requireNonNull(pairingRule, "Result.pairingRule is mandatory (INV-CONF-11)");
            pairs = List.copyOf(pairs);
            unpaired = List.copyOf(unpaired);
        }

        /** How many rules of the oracle are the oracle of some specification. */
        public int pairedRules() {
            return (int) pairs.stream().map(pair -> pair.rule().name()).distinct().count();
        }

        /** The names of the unpaired specifications, in order. */
        public List<String> unpairedNames() {
            return unpaired.stream().map(miss -> miss.specification().name()).toList();
        }
    }

    /**
     * Pairs a corpus of specifications with a corpus of rules.
     *
     * @param specifications the lifted specifications
     * @param rules          the lifted rules of the single oracle
     * @return the pairs, the misses and the rule that produced them
     */
    public static Result pair(List<Candidate> specifications, List<Candidate> rules) {
        Objects.requireNonNull(specifications, "specifications is mandatory");
        Objects.requireNonNull(rules, "rules is mandatory");

        // First pass: the rule each specification reaches by declared type, with the coverage that
        // will decide a contested rule. A specification reaching more than one rule takes the one
        // it covers best; over this oracle that never happens, because the simple names are
        // distinct, and the branch exists so a corpus where they are not fails loudly at the
        // measurement rather than at an arbitrary iteration order.
        Map<String, Pair> best = new LinkedHashMap<>();
        List<Miss> unpaired = new ArrayList<>();
        for (Candidate specification : sortedByName(specifications)) {
            Comparator<Pair> byCoverageThenName = Comparator
                    .<Pair>comparingInt(Pair::covered)
                    .thenComparing(pair -> pair.rule().name(), Comparator.reverseOrder());
            Optional<Pair> reached = sortedByName(rules).stream()
                    .filter(rule -> typesAgree(specification.model().type(), rule.model().type()))
                    .map(rule -> new Pair(specification, rule, covered(specification, rule)))
                    .max(byCoverageThenName);
            if (reached.isEmpty()) {
                unpaired.add(new Miss(specification, Reason.NO_RULE_DECLARES_THE_TYPE,
                        "no rule declares " + specification.model().type()));
            } else {
                best.put(specification.name(), reached.get());
            }
        }

        // Second pass: a rule claimed by two specifications is the oracle of one of them.
        Map<String, Pair> byRule = new LinkedHashMap<>();
        for (Pair candidate : best.values()) {
            Pair standing = byRule.get(candidate.rule().name());
            if (standing == null || beats(candidate, standing)) {
                byRule.put(candidate.rule().name(), candidate);
            }
        }
        for (Pair candidate : best.values()) {
            Pair winner = byRule.get(candidate.rule().name());
            if (!winner.specification().name().equals(candidate.specification().name())) {
                unpaired.add(new Miss(candidate.specification(),
                        Reason.RULE_CLAIMED_BY_ANOTHER_SPECIFICATION,
                        candidate.rule().name() + " is the oracle of "
                                + winner.specification().name()));
            }
        }

        List<Pair> pairs = new ArrayList<>(byRule.values());
        pairs.sort(Comparator.comparing(pair -> pair.specification().name()));
        unpaired.sort(Comparator.comparing(miss -> miss.specification().name()));
        return new Result(pairs, unpaired, PAIRING_RULE);
    }

    /**
     * Whether the challenger takes the rule from the standing pair.
     *
     * <p>Coverage first, then the number of declared events, then the name. The last two are there
     * only to make the outcome independent of iteration order; the decision the corpus actually
     * exercises is the first.
     */
    private static boolean beats(Pair challenger, Pair standing) {
        if (challenger.covered() != standing.covered()) {
            return challenger.covered() > standing.covered();
        }
        int challengerEvents = challenger.specification().model().events().size();
        int standingEvents = standing.specification().model().events().size();
        if (challengerEvents != standingEvents) {
            return challengerEvents > standingEvents;
        }
        return challenger.specification().name().compareTo(standing.specification().name()) < 0;
    }

    /** How many of the rule's declared signatures the specification monitors, under R-M1. */
    private static int covered(Candidate specification, Candidate rule) {
        List<Signature> monitored = specification.model().events().stream()
                .flatMap(event -> event.signatures().stream())
                .distinct()
                .toList();
        return (int) rule.model().events().stream()
                .flatMap(event -> event.signatures().stream())
                .distinct()
                .filter(declared -> monitored.stream().anyMatch(m -> M1Events.matches(m, declared)))
                .count();
    }

    /**
     * The declared type of the specification denotes the type the rule is about.
     *
     * <p>Equal names agree. Otherwise the simple names are compared, and only when one of the two
     * is unqualified — the case {@code MopLifter} produces for the 22 specifications that declare a
     * parameter with a simple type name. Two qualified names that differ stay different.
     */
    private static boolean typesAgree(String specificationType, String ruleType) {
        if (specificationType.equals(ruleType)) {
            return true;
        }
        if (specificationType.indexOf('.') >= 0 && ruleType.indexOf('.') >= 0) {
            return false;
        }
        return simpleName(specificationType).equals(simpleName(ruleType));
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }

    private static List<Candidate> sortedByName(List<Candidate> candidates) {
        List<Candidate> sorted = new ArrayList<>(candidates);
        sorted.sort(Comparator.comparing(Candidate::name));
        return sorted;
    }
}
