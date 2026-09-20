package br.unb.cic.mop.jca.util;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;

import org.junit.Test;

/**
 * The successor set's Cipher tables against the generated API 30 rule.
 *
 * <p>The tests are organised the way the rule is: a catalogue of eight
 * algorithms, then the mode and padding implications that are transcribed, then
 * the ones that are deferred. The distinction matters and is asserted, because a
 * deferred clause is not a gap that slipped through -- it is a recorded decision
 * that the set stays as silent there as its seed was, and a test that quietly
 * admitted a deferred case as if it were transcribed would hide the difference.
 *
 * <p>There is deliberately no pinning test for the frozen
 * {@link CipherTransformationUtil} or for the archived
 * {@code AndroidCipherTransformationUtil}. Their behaviour is preserved by the
 * files not being edited.
 */
public class Api30CipherTransformationUtilTest {

    // --- the algorithm catalogue (Cipher.cryptsl:121) ---

    @Test
    public void admitsTheEightAlgorithmsOfTheCatalogue() {
        assertEquals(Arrays.asList("ChaCha20", "AES_128", "ARC4", "RSA", "DESede", "AES", "BLOWFISH",
                "AES_256"), Api30CipherTransformationUtil.ALGORITHMS);
    }

    @Test
    public void rejectsAnAlgorithmOutsideTheCatalogue() {
        assertFalse(Api30CipherTransformationUtil.isValid("DES/CBC/PKCS5Padding"));
        assertFalse(Api30CipherTransformationUtil.isValid("RC2/CBC/PKCS5Padding"));
        assertFalse(Api30CipherTransformationUtil.isValid(""));
        assertFalse(Api30CipherTransformationUtil.isValid(null));
    }

    // --- AES, whose mode and padding clauses are transcribed ---

    @Test
    public void admitsTheAesTransformationsTheRuleStates() {
        assertTrue(Api30CipherTransformationUtil.isValid("AES/GCM/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CBC/PKCS5Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CBC/PKCS7Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CBC/ISO10126Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CTR/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/OFB/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CFB/NoPadding"));
    }

    @Test
    public void rejectsAnAesModeTheRuleDoesNotList() {
        // PCBC is in the frozen set's mode list and not in the api30 AES clause.
        assertFalse(Api30CipherTransformationUtil.isValid("AES/PCBC/PKCS5Padding"));
        assertFalse(Api30CipherTransformationUtil.isValid("AES/CCM/NoPadding"));
    }

    @Test
    public void rejectsAnAesPaddingTheRuleDoesNotList() {
        assertFalse(Api30CipherTransformationUtil.isValid("AES/CBC/NoPadding"));
        assertFalse(Api30CipherTransformationUtil.isValid("AES/GCM/PKCS5Padding"));
        assertFalse(Api30CipherTransformationUtil.isValid("AES/CTR/PKCS5Padding"));
    }

    // --- RSA, whose mode and padding clauses are transcribed ---

    @Test
    public void admitsTheRsaPaddingsTheRuleStates() {
        assertTrue(Api30CipherTransformationUtil.isValid("RSA/ECB/PKCS1Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("RSA/ECB/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("RSA/ECB/OAEPPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("RSA/ECB/OAEPwithSHA-1andMGF1Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("RSA/ECB/OAEPWithSHA-256AndMGF1Padding"));
    }

    @Test
    public void rejectsTheRsaPaddingTheFrozenSetInventedAndTheRuleDoesNotList() {
        // OAEPWithMD5AndMGF1Padding is in the frozen list and in no api30 clause.
        assertFalse(Api30CipherTransformationUtil.isValid("RSA/ECB/OAEPWithMD5AndMGF1Padding"));
    }

    /**
     * The 109-event case of the publishable tier. The observed string has no hyphen
     * in {@code SHA1}, no Conscrypt registration carries that spelling, and the
     * hyphen is deliberately not folded, so it is still reported here and is
     * recorded as a behavioural divergence instead.
     */
    @Test
    public void doesNotSilentlyNormaliseTheUnhyphenatedOaepSpelling() {
        assertFalse(Api30CipherTransformationUtil.isValid("RSA/ECB/OAEPWithSHA1AndMGF1Padding"));
    }

    /**
     * The one narrowing of this transcription: the rule's RSA padding clause does
     * not list the empty string, and the frozen class accepted a bare {@code "RSA"}
     * through a branch of its own.
     */
    @Test
    public void narrowsTheBareRsaTransformationTheFrozenClassAdmitted() {
        assertTrue(CipherTransformationUtil.isValid("RSA"));
        assertFalse(Api30CipherTransformationUtil.isValid("RSA"));
        assertFalse(Api30CipherTransformationUtil.isValid("RSA/ECB"));
    }

    // --- case folding, and only case ---

    @Test
    public void comparisonFoldsCase() {
        assertTrue(Api30CipherTransformationUtil.isValid("AES/CBC/PKCS5PADDING"));
        assertTrue(Api30CipherTransformationUtil.isValid("aes/gcm/nopadding"));
    }

    // --- the algorithms admitted by the catalogue whose clauses stay deferred ---

    @Test
    public void admitsTheSixAlgorithmsTheCatalogueAddsWithoutApplyingTheirDeferredClauses() {
        assertTrue(Api30CipherTransformationUtil.isValid("ChaCha20/Poly1305/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("ARC4/ECB/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("BLOWFISH/CBC/PKCS5Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES_128/CBC/PKCS5Padding"));
        assertTrue(Api30CipherTransformationUtil.isValid("AES_256/GCM/NoPadding"));
        // A mode the DESede clause (Cipher.cryptsl:139) excludes: deferred, so admitted.
        assertTrue(Api30CipherTransformationUtil.isValid("DESede/GCM/NoPadding"));
        // A mode the BLOWFISH clause (:151) excludes: deferred, so admitted.
        assertTrue(Api30CipherTransformationUtil.isValid("BLOWFISH/GCM/NoPadding"));
    }

    @Test
    public void appliesTheCbcAndStreamPaddingClausesToDesedeBecauseTheyAreTranscribed() {
        // :141 and :143 name DESede beside AES, so they bind here even though the
        // DESede mode clause (:139) is deferred.
        assertTrue(Api30CipherTransformationUtil.isValid("DESede/CBC/PKCS5Padding"));
        assertFalse(Api30CipherTransformationUtil.isValid("DESede/CBC/NoPadding"));
        assertTrue(Api30CipherTransformationUtil.isValid("DESede/CTR/NoPadding"));
        assertFalse(Api30CipherTransformationUtil.isValid("DESede/CTR/PKCS5Padding"));
    }
}
