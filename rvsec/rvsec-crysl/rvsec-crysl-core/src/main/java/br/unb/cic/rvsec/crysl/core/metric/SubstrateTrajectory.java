package br.unb.cic.rvsec.crysl.core.metric;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * The measured history of {@code jca_android}'s predicate substrate, carried as data.
 *
 * <p>It is emitted beside every M4 aggregate for one reason: the signature moved five times in four
 * days, and two runs of this component a day apart are not comparable without knowing which of
 * those states each ran over. Printing the trajectory turns the commit stamp from a formality a
 * reader skips into a fact a reader can check - the same corpus name, five different corpora.
 *
 * <p>Each step reproduces exactly at the commit it names, under the counting rule in
 * {@link #COUNTING_RULE}. That is what makes it evidence rather than an anecdote: the numbers were
 * re-measured against the five commits and the current head when this class was written, not copied
 * from a report.
 */
public final class SubstrateTrajectory {

    /**
     * How the three numbers of a signature are counted.
     *
     * <p>Stated in full because the same corpus yields different triples under different rules -
     * call sites against occurrences, files against specifications - and a triple without its rule
     * is not a measurement. The rule counts textual occurrences of the two singleton accessors,
     * comments included, which is the rule the published triples were taken under.
     */
    public static final String COUNTING_RULE =
            "occurrences of 'ExecutionContext.instance()' and of 'PredicateStore.instance()' in "
                    + "jca_android/*.mop, and the number of files with at least one "
                    + "'PredicateStore.instance()' occurrence ('migrated')";

    /**
     * One measured state of the corpus.
     *
     * @param commit                the commit the triple reproduces at
     * @param executionContextSites occurrences of {@code ExecutionContext.instance()}
     * @param predicateStoreSites   occurrences of {@code PredicateStore.instance()}
     * @param migratedFiles         files with at least one {@code PredicateStore.instance()}
     */
    public record Signature(String commit, int executionContextSites, int predicateStoreSites,
                            int migratedFiles) {

        public Signature {
            Objects.requireNonNull(commit, "Signature.commit is mandatory (INV-CONF-02)");
        }

        /** The triple as it is published, e.g. {@code 0/70/21}. */
        public String triple() {
            return executionContextSites + "/" + predicateStoreSites + "/" + migratedFiles;
        }

        @Override
        public String toString() {
            return triple() + " (" + commit + ")";
        }
    }

    /** The five states measured over four days, oldest first. */
    public static final List<Signature> JCA_ANDROID = List.of(
            new Signature("d64f3a40", 64, 21, 5),
            new Signature("c12f4689", 47, 26, 7),
            new Signature("f188c55b", 28, 35, 12),
            new Signature("8a33bc41", 0, 45, 19),
            new Signature("5fbe8173", 0, 70, 21));

    /**
     * The state the calibration targets of this change are pinned at.
     *
     * <p>{@code 5fbe8173} is an ancestor of the head this component was written against, not the
     * head. Re-measured at {@code 86a8f178}: the triple is still {@code 0/70/21} and the per-file
     * distribution of the 70 sites is unchanged, so the substrate did not move under M4. The
     * {@code file:line} of the sites did move, in 13 of the 24 files, which is why a row is keyed
     * by its provenance and its stamp together and never by provenance alone.
     */
    public static final Signature PINNED = JCA_ANDROID.get(JCA_ANDROID.size() - 1);

    private SubstrateTrajectory() {
    }

    /** The trajectory as one line, for the header of an emitted table. */
    public static String rendered() {
        return JCA_ANDROID.stream().map(Signature::toString).collect(Collectors.joining(" -> "));
    }
}
