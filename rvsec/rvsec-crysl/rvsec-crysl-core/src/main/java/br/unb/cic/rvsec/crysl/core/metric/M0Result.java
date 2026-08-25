package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.List;
import java.util.Objects;

/**
 * Monitor vitality: whether the specification can accuse anything at all, answered before M1-M4 are
 * allowed to run.
 *
 * <p>M0.1 asks whether the generated monitor indexes - a specification with {@code 0/N} parameter
 * binding, or none declared, compiles to one monitor for the whole program and parametric slicing
 * is a no-op in it. M0.2 asks whether the accusation site is reachable - an empty {@code @match}
 * with no {@code @fail} cannot accuse under any trace. M0.3 checks each resolved signature against
 * the {@code android.jar} index. {@code astViolations} carries the non-normalized AST check:
 * duplicate identifiers, an alphabet not contained in the declared identifiers, an unreachable
 * declared event, a {@code @match} with no {@code @fail}. That class of defect passes parser,
 * monitor generator and Java compiler with zero errors, so neither "it parsed" nor "it compiled" is
 * an oracle of sanity.
 *
 * <p>{@code silences} is the part the behavioural run paid for. "Does not build a
 * {@code MapOfMonitor}" fuses three different phenomena and only one of them is a repairable defect
 * of a file, so each one is typed by its {@link SilenceCause} and each cause carries its own
 * disposition: a divergence row, a typed {@code Unknown}, or the refusal (design D-04).
 *
 * <p>{@code refusals} and {@code silences} are not the same list and are not interchangeable.
 * {@code refusals} is the emission: every typed {@code Unknown} this result produced, counted with
 * the other refusals of the report. It holds two kinds, and holding both is the point of having one
 * vocabulary — the signature-level {@code UnresolvedSignature} findings M0.3 produced, which do
 * <em>not</em> stop the comparison, and the {@code UnreachableAccusationSite} of a specification
 * that can never accuse, which does. So membership in {@code refusals} decides nothing on its own:
 * {@link #refused()} consults {@code silences}, where the disposition of each cause is recorded,
 * and the only disposition that stops M1-M4 is the one attached to a specification with no
 * accusation site at all.
 *
 * @param specification           the specification examined
 * @param indexes                 M0.1 - the generated monitor builds a {@code MapOfMonitor}
 * @param accusationSiteReachable M0.2 - some trace can reach an accusation site
 * @param absorption              whether misuse is reported from inside an event body, and where
 * @param silences                the measured causes of silence, each with its disposition
 * @param astViolations           the findings of the non-normalized AST check, empty when clean
 * @param refusals                every typed {@code Unknown} this result emitted: M0.3's
 *                                unresolved signatures, and the unreachable accusation site
 *                                when M0.2 refuses
 * @param notes                   the standing caveats emitted with this result
 * @param countingRule            the rule behind {@code indexes} and every count derived from it
 */
public record M0Result(String specification, boolean indexes, boolean accusationSiteReachable,
                       MisuseAbsorption absorption, List<Silence> silences,
                       List<String> astViolations, List<Unknown> refusals, List<String> notes,
                       String countingRule)
        implements MetricResult {

    public M0Result {
        Objects.requireNonNull(specification, "M0Result.specification is mandatory");
        Objects.requireNonNull(absorption, "M0Result.absorption is mandatory");
        Objects.requireNonNull(countingRule, "M0Result.countingRule is mandatory (INV-CONF-02)");
        silences = List.copyOf(silences);
        astViolations = List.copyOf(astViolations);
        refusals = List.copyOf(refusals);
        notes = List.copyOf(notes);
    }

    @Override
    public String metric() {
        return "M0";
    }

    /**
     * True when M1-M4 must not emit a verdict for this specification (INV-CONF-09).
     *
     * <p>Only a {@link SilenceCause.Disposition#REFUSAL} silence stops the comparison. A live
     * monitor whose target class is absent from the platform still has an order, an event set and
     * constraints worth comparing against the rule; refusing it would mean publishing nothing about
     * a specification whose only defect is that Android does not carry the class it names. A live
     * monitor blind to the end of a trace is not even a defect of the file. Design D-04 is explicit
     * that only the third cause is an M0 refusal.
     */
    public boolean refused() {
        return silences.stream().anyMatch(Silence::refusal);
    }

    /** The silences that belong in {@code divergence_record.csv} rather than in any verdict. */
    public List<Silence> divergences() {
        return silences.stream()
                .filter(s -> s.cause().disposition() == SilenceCause.Disposition.DIVERGENCE_RECORD)
                .toList();
    }
}
