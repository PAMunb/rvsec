package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.List;
import java.util.Objects;

/**
 * Which label of the specification corresponds to which symbol of the rule, derived from the
 * signature-set intersection and from nothing else.
 *
 * <p>This is the piece M2 consumes. M2 compares languages, and the two artifacts write their
 * alphabets under different names, so before any product search can run something has to say which
 * letter of one side is which letter of the other. That "something" is this table, and it is
 * computed from signatures because <strong>no name heuristic gets the corpus right</strong>. Two
 * measured witnesses, both in {@code jca_android/SecureRandomSpec.mop} against
 * {@code SecureRandom.crysl}:
 *
 * <ul>
 *   <li>the specification's {@code g3} is {@code getInstanceStrong()}, which the rule calls
 *       {@code gI}. A prefix or edit-distance heuristic pairs {@code g3} with the rule's
 *       {@code g1} or {@code g2}, both of which are {@code getInstance(...)} — a different method;
 *   <li>the specification's {@code setSeed1} is {@code setSeed(long)}, which the rule calls
 *       {@code s2}. The name suggests {@code s1}, and {@code s1} is {@code setSeed(byte[])} — the
 *       other overload, so the heuristic does not merely miss, it pairs the wrong one.
 * </ul>
 *
 * <p>The intersection also expands aggregates without being told to. On
 * {@code jca_android/MessageDigestSpec.mop} the single event {@code update}, written
 * {@code call(void MessageDigest.update(..))}, intersects four declared rule signatures at once, so
 * its entry lists four rule symbols — the rule's {@code u1} to {@code u4}. That is one label
 * standing for four letters, which is exactly the fact M2 needs and exactly the fact a name-based
 * table cannot hold.
 *
 * <p>Entries are a {@code List} and never a map keyed by {@link Label} (INV-CONF-03): declaration
 * order is dispatch order, and {@code declIndex} travels with each entry so M2 can build the
 * morphism {@code h} in the order the specification declares.
 *
 * @param specification         the specification the labels belong to
 * @param rule                  the rule the symbols belong to, paired by declared type
 *                              (INV-CONF-11)
 * @param entries               one entry per declared event of the specification, in declaration
 *                              order; an event whose signatures meet no rule signature keeps an
 *                              entry with empty lists, because "this label corresponds to nothing
 *                              in the rule" is a fact M2 needs stated, not omitted
 * @param unalignedRuleSymbols  the rule symbols no label of the specification reaches
 * @param countingRule          the rule behind the intersection, stated in full (INV-CONF-02)
 */
public record LabelAlignment(String specification, String rule, List<Entry> entries,
                             List<Label> unalignedRuleSymbols, String countingRule) {

    public LabelAlignment {
        Objects.requireNonNull(specification, "LabelAlignment.specification is mandatory");
        Objects.requireNonNull(rule, "LabelAlignment.rule is mandatory");
        Objects.requireNonNull(countingRule,
                "LabelAlignment.countingRule is mandatory (INV-CONF-02)");
        entries = List.copyOf(entries);
        unalignedRuleSymbols = List.copyOf(unalignedRuleSymbols);
    }

    /**
     * One label of the specification and the rule symbols its signatures meet.
     *
     * @param mopLabel       the label as the specification declares it
     * @param declIndex      0-based declaration index, which is dispatch order
     * @param ruleSymbols    the labels of the rule events whose signatures the label matches
     * @param sharedSignatures the rule signatures that produced the correspondence — the witness,
     *                       so a reader can check the alignment instead of trusting it
     */
    public record Entry(Label mopLabel, int declIndex, List<Label> ruleSymbols,
                        List<Signature> sharedSignatures) {

        public Entry {
            Objects.requireNonNull(mopLabel, "Entry.mopLabel is mandatory");
            ruleSymbols = List.copyOf(ruleSymbols);
            sharedSignatures = List.copyOf(sharedSignatures);
            if (declIndex < 0) {
                throw new IllegalArgumentException("Entry.declIndex is 0-based, got " + declIndex);
            }
        }

        /** True when this label meets no symbol of the rule. */
        public boolean unaligned() {
            return ruleSymbols.isEmpty();
        }
    }
}
