package br.unb.cic.mop.jca.util;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * The derived set's Cipher tables against the generated API 30 rule.
 *
 * <p>The rule states three layers of implication -- a catalogue of eight
 * algorithms, the modes each admits, and the paddings each (algorithm, mode)
 * pair admits -- so the tests are organised the same way: every algorithm is
 * shown admitted with a conforming transformation and rejected with a
 * non-conforming mode and a non-conforming padding.
 *
 * <p>Several cases carry a transformation the corpus of 348 applications
 * actually contains. Those are marked, because they are the ones where a verdict
 * changing has an observable consequence rather than a hypothetical one.
 *
 * <p>There is deliberately no pinning test for the frozen
 * {@link CipherTransformationUtil}. Its behaviour is preserved by the file not
 * being edited, and the freeze check is what guarantees that; a test asserting
 * an unedited function still returns what it returned guarantees nothing.
 */
public class AndroidCipherTransformationUtilTest {

    // --- the eight algorithms, each admitted with a conforming transformation ---

    @Test
    public void admitsAConformingTransformationForEveryAlgorithmInTheCatalogue() {
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/CBC/PKCS5Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES_128/CBC/PKCS5Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES_256/GCM/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("ARC4/ECB/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("BLOWFISH/CBC/ISO10126Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("ChaCha20/Poly1305/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("DESede/CBC/PKCS7Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA/ECB/OAEPPadding"));
    }

    /** In the corpus: 25 call sites, the single most common Cipher transformation. */
    @Test
    public void admitsTheMostCommonTransformationInTheCorpus() {
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/GCM/NoPadding"));
    }

    // --- rejected on the mode ---

    @Test
    public void rejectsAModeTheAlgorithmDoesNotAdmit() {
        assertFalse(AndroidCipherTransformationUtil.isValid("AES/PCBC/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("AES_128/CTR/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("AES_256/CFB/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("ARC4/CBC/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("BLOWFISH/GCM/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("ChaCha20/CBC/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("DESede/GCM/NoPadding"));
    }

    /**
     * In the corpus: one call site. The rule gives RSA the modes {@code ""} and
     * {@code ECB} only, so {@code NONE} -- the name Android documents -- is
     * rejected. The gap is upstream: CrySL 1.5.2 states the same two modes. It is
     * recorded in {@code data/gh101/algorithm_naming.md} rather than repaired,
     * because following the rule is what the derivation is for.
     */
    @Test
    public void rejectsTheAndroidSpellingRsaNoneWhichNoRuleAdmits() {
        assertFalse(AndroidCipherTransformationUtil.isValid("RSA/NONE/NoPadding"));
    }

    // --- rejected on the padding ---

    @Test
    public void rejectsAPaddingThePairDoesNotAdmit() {
        assertFalse(AndroidCipherTransformationUtil.isValid("AES/GCM/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("AES_128/GCM/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("ARC4/ECB/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("BLOWFISH/CFB/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("ChaCha20/Poly1305/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("DESede/CBC/NoPadding"));
        assertFalse(AndroidCipherTransformationUtil.isValid("RSA/ECB/ISO10126Padding"));
    }

    /**
     * In the corpus: 10 call sites. The rule gives AES/CBC the three block
     * paddings and not {@code NoPadding}, so this stays a misuse -- the same
     * verdict the frozen utility gives.
     */
    @Test
    public void rejectsAesCbcNoPaddingAsTheFrozenUtilityDoes() {
        assertFalse(AndroidCipherTransformationUtil.isValid("AES/CBC/NoPadding"));
    }

    // --- outside the catalogue ---

    @Test
    public void rejectsAnAlgorithmTheCatalogueDoesNotName() {
        // In the corpus: two call sites. DES is documented from API 1 for Cipher,
        // yet appears in no base specification and no tier -- the omission is
        // uniform across the profile, so it is a deliberate exclusion on security
        // grounds rather than an availability gap.
        assertFalse(AndroidCipherTransformationUtil.isValid("DES/ECB/NoPadding"));
        // AES128 is not a JCA name; AES_128 is. The underscore does not fold.
        assertFalse(AndroidCipherTransformationUtil.isValid("AES128/CBC/PKCS5Padding"));
    }

    // --- the folds ---

    /** In the corpus: one call site, admitted today only because padding folds. */
    @Test
    public void foldsCaseOnAllThreeComponents() {
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/CBC/PKCS5PADDING"));
        assertTrue(AndroidCipherTransformationUtil.isValid("aes/cbc/pkcs5padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA/ecb/pkcs1padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("chacha20/POLY1305/nopadding"));
    }

    /**
     * The campaign observed this transformation 109 times, in one application.
     * It is the rule's {@code OAEPwithSHA-1andMGF1Padding} written without the
     * dash, which the JCA resolves and a string comparison does not.
     */
    @Test
    public void foldsTheHyphenSoTheObservedOaepSpellingIsAdmitted() {
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA/ECB/OAEPWithSHA1AndMGF1Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA/ECB/OAEPwithSHA-1andMGF1Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA/ECB/OAEPWithSHA256AndMGF1Padding"));
    }

    // --- what the rule leaves unconstrained ---

    /**
     * In the corpus: one call site for {@code AES/ECB/NoPadding}. The rule places
     * no padding implication on these pairs, so following it admits them. The
     * frozen utility rejects them, because its mode list carries no ECB at all --
     * a real difference in verdict between the two sets, in the rule's favour.
     */
    @Test
    public void admitsAnyPaddingForAPairTheRuleDoesNotConstrain() {
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/ECB/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/ECB/PKCS5Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/CTS/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("DESede/ECB/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("BLOWFISH/CTS/NoPadding"));
    }

    /**
     * A component the application did not write is a request for the provider's
     * default, and the rule constrains only what is written. This is what keeps
     * bare {@code RSA} admissible after the generated rule lost CrySL 1.5.2's
     * {@code mode in {""} => pad in {""}} clause.
     */
    @Test
    public void treatsAnUnspecifiedComponentAsUnconstrained() {
        assertTrue(AndroidCipherTransformationUtil.isValid("RSA"));
        assertTrue(AndroidCipherTransformationUtil.isValid("ChaCha20"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES"));
        assertTrue(AndroidCipherTransformationUtil.isValid("AES/CBC"));
    }

    // --- malformed input ---

    /**
     * The call site is a monitor guard inside the application under test, so a
     * guard that throws takes that application down. Every malformed form has to
     * return a verdict, and the verdict is "not admissible".
     */
    @Test
    public void returnsFalseRatherThanRaisingOnMalformedInput() {
        assertFalse(AndroidCipherTransformationUtil.isValid(null));
        assertFalse(AndroidCipherTransformationUtil.isValid(""));
        assertFalse(AndroidCipherTransformationUtil.isValid("AES/"));
        assertFalse(AndroidCipherTransformationUtil.isValid("/"));
    }

    // --- the contradiction this closes (task 2.5) ---

    /**
     * KeyGeneratorSpec accepts these four in the derived set because API 30
     * publishes them, while CipherSpec reported every use of them as a misuse:
     * the set generated keys for algorithms whose use it rejected. Both sides now
     * follow the same derivation.
     */
    @Test
    public void acceptsTheAlgorithmsKeyGeneratorSpecAlreadyAccepted() {
        assertTrue(AndroidCipherTransformationUtil.isValid("ChaCha20/Poly1305/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("DESede/CBC/PKCS5Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("BLOWFISH/CBC/PKCS5Padding"));
        assertTrue(AndroidCipherTransformationUtil.isValid("ARC4/ECB/NoPadding"));

        // And the frozen utility rejects all four, which is the contradiction.
        assertFalse(CipherTransformationUtil.isValid("ChaCha20/Poly1305/NoPadding"));
        assertFalse(CipherTransformationUtil.isValid("DESede/CBC/PKCS5Padding"));
        assertFalse(CipherTransformationUtil.isValid("BLOWFISH/CBC/PKCS5Padding"));
        assertFalse(CipherTransformationUtil.isValid("ARC4/ECB/NoPadding"));
    }

    // --- the two conditional REQUIRES the specification reads (task 4.6) ---

    /**
     * {@code part(1,"/",transformation) in {CBC,CTS,CTR,CFB,PCBC,OFB} && encmode == 1
     * => preparedIV[params]}. Both halves of the guard decide: a decryption in the
     * same mode does not demand a monitored IV, because the IV it is given is the
     * one the encryption already produced.
     */
    @Test
    public void requiresAPreparedIvOnlyForAnEncryptionInACbcFamilyMode() {
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedIv("AES/CBC/PKCS5Padding", 1));
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedIv("AES/CTR/NoPadding", 1));
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedIv("DESede/OFB/NoPadding", 1));

        // PCBC is in the rule's list for this clause and in no algorithm's mode
        // catalogue: the two clauses are independent of one another.
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedIv("AES/PCBC/PKCS5Padding", 1));

        // Decryption, wrap and unwrap are modes 2, 3 and 4.
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv("AES/CBC/PKCS5Padding", 2));

        // Neither GCM nor ECB is in the list, whatever the direction.
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv("AES/GCM/NoPadding", 1));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv("AES/ECB/NoPadding", 1));
    }

    /**
     * {@code part(1,"/",transformation) in {GCM} => preparedGCM[params]}, which the
     * rule states without a direction, so it holds for a decryption too.
     */
    @Test
    public void requiresPreparedGcmParametersInBothDirections() {
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedGcm("AES/GCM/NoPadding"));
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedGcm("aes/gcm/nopadding"));
        assertTrue(AndroidCipherTransformationUtil.requiresPreparedGcm("AES_256/GCM/NoPadding"));

        assertFalse(AndroidCipherTransformationUtil.requiresPreparedGcm("AES/CBC/PKCS5Padding"));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedGcm("AES"));
    }

    /** Both predicates are read from a monitor guard, so neither may raise. */
    @Test
    public void answersRatherThanRaisingOnMalformedInputForBothRequirements() {
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv(null, 1));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv("AES/", 1));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedIv("/", 1));

        assertFalse(AndroidCipherTransformationUtil.requiresPreparedGcm(null));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedGcm("AES/"));
        assertFalse(AndroidCipherTransformationUtil.requiresPreparedGcm(""));
    }
}
