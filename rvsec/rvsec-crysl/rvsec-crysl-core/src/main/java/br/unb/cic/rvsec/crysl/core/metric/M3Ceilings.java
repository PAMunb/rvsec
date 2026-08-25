package br.unb.cic.rvsec.crysl.core.metric;

import java.util.Objects;

/**
 * The two ceilings of an M3 run, reported side by side and never added together.
 *
 * <p>They are different kinds of thing and they err in different places.
 *
 * <ul>
 *   <li>The <strong>ceiling of the subject</strong> counts clauses of upstream rules that have no
 *       {@code .mop} specification at all. Nothing is wrong with the instrument there; the coverage
 *       debt is real and belongs to the specification set. Measured over the upstream oracle it is
 *       large — 27 of the 49 rules have no specification — and it grew when the generated {@code
 *       api30} corpus was abandoned, because the upstream rules state more.
 *   <li>The <strong>ceiling of the instrument</strong> counts clauses this reader declined to
 *       decide: the shapes it does not follow. Nothing is proven about the specification there. It
 *       is a debt of this component and it falls when the reader learns a shape.
 * </ul>
 *
 * <p>A single "not covered" figure adding the two would describe neither, and would let a reader
 * improve the number by breaking the reader. There is deliberately no {@code total()} on this
 * record.
 *
 * <p>A third ceiling existed while the generated {@code api30} corpus was an oracle — the clauses it
 * had lost relative to upstream. With the single-oracle decision (D-06) that measurement is no
 * longer a report line: it is the method note recording <em>why</em> {@code api30} was abandoned,
 * and it belongs in the method appendix rather than here, because this component does not read that
 * corpus at all.
 *
 * <h2>The method note, recorded and deliberately not asserted</h2>
 *
 * <p>What follows is history. It is written here rather than in a test because the component never
 * reads {@code api30}: a test asserting these numbers would be asserting something no code path can
 * produce, which is the same failure as a number without its counting rule.
 *
 * <p>Measured under {@link CountingRule#R1}, the {@code api30} generation lost <strong>−33</strong>
 * clauses net across 16 rules over the full sets, of which <strong>25 deleted across 12 of the 22
 * paired rules</strong>: {@code CipherInputStream} 3→1, {@code CipherOutputStream} 3→1,
 * {@code DHGenParameterSpec} 1→0, {@code GCMParameterSpec} 4→1, {@code IvParameterSpec} 3→0,
 * {@code KeyManagerFactory} 3→2, {@code KeyStore} 5→4, {@code Mac} 5→3, {@code MessageDigest} 7→3,
 * {@code PBEKeySpec} 3→2, {@code SecretKeySpec} 3→1, {@code Signature} 4→1. No rule gained a clause.
 * The paired denominator was {@code 55} against upstream's {@code 80}.
 *
 * <p>The losses come in three modes, each with a witness:
 *
 * <ol>
 *   <li><strong>Deletion.</strong> {@code DHGenParameterSpec}: upstream states
 *       {@code exponentSize < primeSize}, {@code api30} states nothing, and
 *       {@code jca_android/DHGenParameterSpecSpec.mop} implements it. Against {@code api30} the
 *       specification was therefore reported as checking something "without base" — the accusation
 *       mode that a wrong oracle produces, and the reason D-06 exists.
 *   <li><strong>Operator corruption.</strong> {@code api30/Cipher.cryptsl:131,133,135} write
 *       {@code length(x) <= off} where upstream writes {@code >=} in all four of the corresponding
 *       clauses. A comparison inverted in the oracle inverts every verdict taken against it.
 *   <li><strong>Predicate substitution.</strong> The upstream triad
 *       {@code length[x] >= off + len; off >= 0; len > 0} is replaced by the single {@code len > off},
 *       which is neither of the three and is not implied by them.
 * </ol>
 *
 * @param subject      clauses in rules that have no specification
 * @param instrument   clauses whose idiom the reader does not follow
 * @param countingRule the rule behind both, stated so neither travels without it
 */
public record M3Ceilings(int subject, int instrument, CountingRule countingRule) {

    public M3Ceilings {
        Objects.requireNonNull(countingRule, "M3Ceilings.countingRule is mandatory (INV-CONF-02)");
        if (subject < 0 || instrument < 0) {
            throw new IllegalArgumentException("a ceiling counts clauses and cannot be negative");
        }
    }

    @Override
    public String toString() {
        return "subject=" + subject + " instrument=" + instrument + " [" + countingRule + "]";
    }
}
