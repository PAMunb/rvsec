package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Polarity;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * The producer/consumer graph of one or more specifications, keyed by predicate.
 *
 * <p>It is built over a <em>set</em> of specifications and not over one, because the questions it
 * answers are not local. Whether a {@code REQUIRES} has a producer at all is a fact about the whole
 * corpus: {@code CipherSpec} reads {@code GENERATED_KEY} and {@code KeyGeneratorSpec} writes it, so
 * a graph built one file at a time would report every cross-file read as an orphan and every
 * cross-file write as a dead end. Both of those are real findings when they are real, and a
 * per-file graph would drown them in false ones.
 *
 * <p>Names are compared canonically, which is a mechanical rule with a stated limit. The two
 * languages spell the same predicate differently - {@code GENERATED_KEY} against
 * {@code generatedKey} - and lowercasing with the underscores removed aligns most of them.
 * It does not align all of them: {@code MACED} against {@code macced},
 * {@code GENERATED_PUBLIC_KEY} against {@code generatedPubkey}, {@code GENERATE_SSL_CONTEXT}
 * against {@code generatedSSLContext} are pairings a person made, not a rule. Those cross the
 * boundary as declared aliases and the rows they produce are marked inherited; the canonical rule
 * never invents them. Inside one corpus, where both ends are written in the same vocabulary, the
 * canonical rule is exact.
 */
public final class PredicateGraph {

    /** How predicate names are matched, stated because it decides which rows can be derived. */
    public static final String CANONICAL_RULE =
            "predicate names are matched after lowercasing and removing '_'; a pair that needs "
                    + "more than that is a declared alias, not a derivation";

    /**
     * Expressions that build a new value at the site.
     *
     * <p>The list is the set of conversions the corpora actually write, not a general grammar of
     * Java: a pattern that matched any method call would report every predicate argument as
     * recreated, and the finding would stop meaning anything.
     */
    private static final Pattern RECREATION = Pattern.compile(
            "\\.toCharArray\\s*\\(|\\.getBytes\\s*\\(|String\\s*\\.\\s*valueOf\\s*\\(|\\bnew\\s"
                    + "|\\.clone\\s*\\(|\\.toString\\s*\\(|\\.getEncoded\\s*\\(|\\.toByteArray\\s*\\("
                    + "|Arrays\\s*\\.\\s*copyOf");

    /** Type names that say nothing, so a difference against them decides nothing. */
    private static final List<String> UNINFORMATIVE_TYPES =
            List.of("", "object", "java.lang.object", "?", "_");

    private final List<PredicateSiteFacts> sites;
    private final Map<String, List<PredicateSiteFacts>> byPredicate;

    private PredicateGraph(List<PredicateSiteFacts> sites) {
        this.sites = List.copyOf(sites);
        Map<String, List<PredicateSiteFacts>> index = new LinkedHashMap<>();
        for (PredicateSiteFacts site : this.sites) {
            index.computeIfAbsent(canonical(site.predicate()), key -> new ArrayList<>()).add(site);
        }
        this.byPredicate = index;
    }

    /** Build the graph over every site of every specification the caller wants compared. */
    public static PredicateGraph of(List<PredicateSiteFacts> sites) {
        return new PredicateGraph(sites);
    }

    /** The canonical form a predicate name is matched under. */
    public static String canonical(String name) {
        return name.toLowerCase(Locale.ROOT).replace("_", "");
    }

    /** Every site the graph was built over, in the order it was given them. */
    public List<PredicateSiteFacts> sites() {
        return sites;
    }

    /** The sites that write {@code predicate}. */
    public List<PredicateSiteFacts> producers(String predicate) {
        return of(predicate, PredicateSiteFacts.Section.ENSURES);
    }

    /** The sites that read {@code predicate} as a precondition, of either polarity. */
    public List<PredicateSiteFacts> consumers(String predicate) {
        return of(predicate, PredicateSiteFacts.Section.REQUIRES);
    }

    /** The sites that withdraw {@code predicate}. */
    public List<PredicateSiteFacts> withdrawals(String predicate) {
        return of(predicate, PredicateSiteFacts.Section.NEGATES);
    }

    /** Whether anything in the graph writes {@code predicate}. */
    public boolean hasProducer(String predicate) {
        return !producers(predicate).isEmpty();
    }

    /** Whether anything in the graph reads {@code predicate}. */
    public boolean hasConsumer(String predicate) {
        return !consumers(predicate).isEmpty();
    }

    /**
     * Reads whose predicate nothing in the graph writes.
     *
     * <p>A read with no reachable producer answers the same thing on every trace, so the clause it
     * translates cannot be violated by any program. The specification is not wrong in any line one
     * could point at; the graph is what makes it visible.
     */
    public List<PredicateSiteFacts> orphanReads() {
        return sites.stream()
                .filter(site -> site.section() == PredicateSiteFacts.Section.REQUIRES)
                .filter(site -> !hasProducer(site.predicate()))
                .toList();
    }

    /**
     * Writes whose predicate nothing in the graph reads.
     *
     * <p>The dual of {@link #orphanReads()}, and the mechanical half of the {@code omission}
     * disposition of {@code predicate_graph.csv}: a write nothing consumes changes no verdict.
     */
    public List<PredicateSiteFacts> deadEndWrites() {
        return sites.stream()
                .filter(site -> site.section() == PredicateSiteFacts.Section.ENSURES)
                .filter(site -> !hasConsumer(site.predicate()))
                .toList();
    }

    /**
     * Every producer/consumer pair the graph can show is not about the same object.
     *
     * <p>Only positive reads are paired. A negated read asks for the predicate to be <em>absent</em>,
     * and a write that fails to reach it makes it answer "absent" - which is what it wanted. That is
     * a false negative of a different shape and belongs to the polarity comparison, not here;
     * reporting it as a broken bridge would put two findings under one name.
     */
    public List<PropagationBridge> bridges() {
        List<PropagationBridge> found = new ArrayList<>();
        for (String predicate : byPredicate.keySet()) {
            for (PredicateSiteFacts producer : producers(predicate)) {
                for (PredicateSiteFacts consumer : consumers(predicate)) {
                    if (consumer.ref().polarity() != Polarity.POSITIVE) {
                        continue;
                    }
                    addBridges(predicate, producer, consumer, found);
                }
            }
        }
        return List.copyOf(found);
    }

    private void addBridges(String predicate, PredicateSiteFacts producer,
                            PredicateSiteFacts consumer, List<PropagationBridge> out) {
        incompatibleType(producer, consumer).ifPresent(detail -> out.add(new PropagationBridge(
                predicate, producer, consumer, PropagationBridge.Cause.INCOMPATIBLE_TYPES, detail)));
        recreatedValue(producer, consumer).ifPresent(detail -> out.add(new PropagationBridge(
                predicate, producer, consumer, PropagationBridge.Cause.RECREATED_VALUE, detail)));
    }

    /** The first argument position at which both ends declare a type and the two types differ. */
    private java.util.Optional<String> incompatibleType(PredicateSiteFacts producer,
                                                        PredicateSiteFacts consumer) {
        int positions = Math.min(producer.argumentTypes().size(), consumer.argumentTypes().size());
        for (int i = 0; i < positions; i++) {
            String written = producer.argumentTypes().get(i);
            String read = consumer.argumentTypes().get(i);
            if (informativeType(written) && informativeType(read) && !written.trim().equals(read.trim())) {
                return java.util.Optional.of("position " + i + " is written over '" + written
                        + "' at " + producer.ref().site() + " and read over '" + read + "' at "
                        + consumer.ref().site() + "; the two are different types, so the value the "
                        + "write keyed is not the value the read looks up, and the conversion "
                        + "between them carries no property of the original");
            }
        }
        return java.util.Optional.empty();
    }

    /** Whether either end names a value built at the site, and what that costs under its keying. */
    private java.util.Optional<String> recreatedValue(PredicateSiteFacts producer,
                                                      PredicateSiteFacts consumer) {
        for (PredicateSiteFacts end : List.of(producer, consumer)) {
            for (String argument : end.ref().arguments()) {
                if (!RECREATION.matcher(argument).find()) {
                    continue;
                }
                boolean identity =
                        end.substrate().keying() == PredicateSubstrate.Keying.IDENTITY;
                return java.util.Optional.of("the argument '" + argument + "' at "
                        + end.ref().site() + " builds a value at the site; the substrate is "
                        + end.substrate() + ", keyed by " + end.substrate().keying()
                        + (identity
                                ? ", so the reconstructed object is a different key and the "
                                        + "predicate does not arrive at all"
                                : ", so the predicate arrives carrying whatever the conversion "
                                        + "produced rather than a property of the original value"));
            }
        }
        return java.util.Optional.empty();
    }

    /**
     * Whether a declared type says anything a comparison can use.
     *
     * <p>{@code Object} and the CrySL wildcard are not types a difference can be read off: every
     * value is an {@code Object}, so "written over Object, read over char[]" is not evidence of
     * anything. Treating them as informative would turn the type route into a generator of
     * findings nobody can act on.
     */
    public static boolean informativeType(String type) {
        return type != null
                && !UNINFORMATIVE_TYPES.contains(type.trim().toLowerCase(Locale.ROOT));
    }

    /** The last segment of a type name, so {@code java.security.Key} compares with {@code Key}. */
    public static String simpleName(String type) {
        if (type == null) {
            return "";
        }
        String trimmed = type.trim();
        int dot = trimmed.lastIndexOf('.');
        return dot < 0 ? trimmed : trimmed.substring(dot + 1);
    }

    private List<PredicateSiteFacts> of(String predicate, PredicateSiteFacts.Section section) {
        return byPredicate.getOrDefault(canonical(predicate), List.of()).stream()
                .filter(site -> site.section() == section)
                .toList();
    }
}
