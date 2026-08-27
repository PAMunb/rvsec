package br.unb.cic.mop.jca.util;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * The two value decisions {@link CipherTransformationNormalizer} carries, and the line
 * between them.
 *
 * <p>Both are decisions about what the instrument accuses, so both are worth a test that
 * fails when someone moves them by accident. They are also easy to conflate, and conflating
 * them is a measurable mistake: {@link CipherTransformationNormalizer#keyAlgorithm} folds
 * {@code AES_128} onto {@code AES} (D-20.2) while {@link CipherTransformationNormalizer#alg}
 * does not, because {@link CipherTransformationNormalizer#isValid} reads {@code alg} to pick
 * a value list and the fold would silently admit a transformation on the wrong list.
 */
public class CipherTransformationNormalizerTest {

    // --- D-20.1: the eight PBE families the expert rule admits -------------------------

    /** The eight of {@code Cipher.crysl:90-93}, named alone -- Conscrypt resolves each to a
     *  CBC/PKCS5PADDING form of its AES family, which is the pair the rule requires of them. */
    @Test
    public void admitsTheEightExpertPbeFamiliesNamedAlone() {
        String[] admitted = {
                "PBEWithHmacSHA224AndAES_128", "PBEWithHmacSHA256AndAES_128",
                "PBEWithHmacSHA384AndAES_128", "PBEWithHmacSHA512AndAES_128",
                "PBEWithHmacSHA224AndAES_256", "PBEWithHmacSHA256AndAES_256",
                "PBEWithHmacSHA384AndAES_256", "PBEWithHmacSHA512AndAES_256" };
        for (String t : admitted) {
            assertTrue(t, CipherTransformationNormalizer.isValid(t));
        }
    }

    /** The same eight spelled in full. The rule states the mode and the padding separately
     *  ({@code :98-100}, {@code :104-106}), so a program that writes them must write these. */
    @Test
    public void admitsTheEightSpelledOutWithCbcAndPkcs5() {
        assertTrue(CipherTransformationNormalizer.isValid(
                "PBEWithHmacSHA256AndAES_128/CBC/PKCS5Padding"));
        assertTrue(CipherTransformationNormalizer.isValid(
                "pbewithhmacsha512andaes_256/cbc/pkcs5padding"));
    }

    /** A PBE family with a mode or padding the rule does not pair it with is still accused. */
    @Test
    public void refusesAPbeFamilyOutsideCbcPkcs5() {
        assertFalse(CipherTransformationNormalizer.isValid(
                "PBEWithHmacSHA256AndAES_128/ECB/PKCS5Padding"));
        assertFalse(CipherTransformationNormalizer.isValid(
                "PBEWithHmacSHA256AndAES_128/CBC/NoPadding"));
    }

    /**
     * The reason the check reads the RAW spelling. Conscrypt files ten PBE services under the
     * two canonical names and the expert rule lists eight: the SHA-1 pair
     * ({@code ConscryptAliasTable:103}, {@code :110}) resolves to the same
     * {@code AES_128/CBC/PKCS5PADDING} as the SHA-224 pair. A check that ran after resolution
     * could not tell them apart, and would admit SHA-1 key derivation the oracle refuses.
     */
    @Test
    public void refusesTheTwoSha1PbeFamiliesTheExpertRuleOmits() {
        assertEquals("AES_128/CBC/PKCS5PADDING",
                CipherTransformationNormalizer.canonical("PBEWithHmacSHA1AndAES_128"));
        assertEquals("AES_128/CBC/PKCS5PADDING",
                CipherTransformationNormalizer.canonical("PBEWithHmacSHA224AndAES_128"));

        assertFalse(CipherTransformationNormalizer.isValid("PBEWithHmacSHA1AndAES_128"));
        assertFalse(CipherTransformationNormalizer.isValid("PBEWithHmacSHA1AndAES_256"));
    }

    // --- D-20.2: the keysize-suffixed services fold onto their family -------------------

    /** A key generated for {@code AES} used with a Cipher built for a suffixed service is the
     *  same family and not a misuse, so the key check compares them equal. */
    @Test
    public void keyAlgorithmFoldsTheSuffixedServicesOntoAes() {
        assertEquals("AES", CipherTransformationNormalizer.keyAlgorithm("AES_128/CBC/PKCS5Padding"));
        assertEquals("AES", CipherTransformationNormalizer.keyAlgorithm("AES_256/CBC/PKCS5Padding"));
        assertEquals("AES", CipherTransformationNormalizer.keyAlgorithm("PBEWithHmacSHA256AndAES_128"));
        assertEquals("AES", CipherTransformationNormalizer.keyAlgorithm("AES/CBC/PKCS5Padding"));
        assertEquals("RSA", CipherTransformationNormalizer.keyAlgorithm("RSA/ECB/PKCS1Padding"));
    }

    /** The fold stays out of {@code alg}, which {@code isValid} routes on. */
    @Test
    public void algDoesNotFoldTheSuffixedServices() {
        assertEquals("AES_128", CipherTransformationNormalizer.alg("AES_128/CBC/PKCS5Padding"));
        assertEquals("AES_128", CipherTransformationNormalizer.alg("PBEWithHmacSHA256AndAES_128"));
    }

    // --- what neither decision moved ----------------------------------------------------

    /** The four spellings the alias resolution and case folding admit, unchanged. */
    @Test
    public void stillAdmitsTheAliasAndCaseSpellings() {
        assertTrue(CipherTransformationNormalizer.isValid("AES/CBC/PKCS7Padding"));
        assertTrue(CipherTransformationNormalizer.isValid("RSA/None/PKCS1Padding"));
        assertTrue(CipherTransformationNormalizer.isValid("aes/cbc/pkcs5padding"));
        assertTrue(CipherTransformationNormalizer.isValid("AES/cbc/PKCS5Padding"));
    }

    /** ECB over AES stays accused: it is not in the rule's mode list, and no decision here
     *  touched that list. */
    @Test
    public void stillRefusesAesEcbAndTheUnknownAlgorithms() {
        assertFalse(CipherTransformationNormalizer.isValid("AES/ECB/PKCS5Padding"));
        assertFalse(CipherTransformationNormalizer.isValid("DES/CBC/PKCS5Padding"));
        assertFalse(CipherTransformationNormalizer.isValid("Blowfish"));
    }

    /** A null transformation reports rather than throwing: the callers are event bodies. */
    @Test
    public void nullTransformationIsNotValid() {
        assertFalse(CipherTransformationNormalizer.isValid(null));
    }
}
