package br.unb.cic.mop.jca.util;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Reads a {@code Cipher} transformation the way the rest of this specification set reads a
 * value: resolve the pinned Conscrypt alias first, fold case, and only then compare.
 *
 * <h2>Why this class exists beside {@link CipherTransformationUtil}</h2>
 *
 * <p>
 * {@code CipherSpec} was the one value-carrying specification of the set that did not
 * normalise. The other eleven compare through {@link ConscryptAliasTable#matches}, which folds
 * case and resolves aliases; {@code CipherSpec} called the frozen
 * {@link CipherTransformationUtil#isValid} instead, and that method compares raw:
 * {@code alg(t).equals("AES")} and {@code modes.contains(mode(t))} are case-sensitive (only the
 * padding calls {@code toUpperCase()}), and no alias is resolved anywhere. So four spellings the
 * platform accepts were accused:
 *
 * <ul>
 *   <li>{@code AES/CBC/PKCS7Padding} -- a pinned alias of {@code AES/CBC/PKCS5Padding}
 *       ({@code OpenSSLProvider.java:380})</li>
 *   <li>{@code RSA/None/PKCS1Padding} -- a pinned alias of {@code RSA/ECB/PKCS1Padding}
 *       ({@code OpenSSLProvider.java:334})</li>
 *   <li>{@code aes/cbc/pkcs5padding} and {@code AES/cbc/PKCS5Padding} -- the JCA resolves
 *       transformation names case-insensitively</li>
 * </ul>
 *
 * <h2>What this does NOT change: the admitted values</h2>
 *
 * <p>
 * The value clauses here are {@link CipherTransformationUtil}'s, reproduced. That is deliberate
 * and it is the whole reason this repair does not reopen D-15: what the researcher's decision of
 * 2026-08-25 licensed is alias resolution and case folding -- the mechanism D-15 already
 * ratified for the other eleven specifications -- and not a new value set. Two known gaps
 * against the expert rule are therefore left exactly as they are, each of which would be a
 * value decision of its own:
 *
 * <ul>
 *   <li>{@code Cipher.crysl:89-92} admits eight {@code PBEWithHmacSHA*AndAES_*} algorithms;
 *       neither this class nor the frozen one implements them, so they stay accused.</li>
 *   <li>For {@code AES} with {@code CCM/GCM/CTR/CTS/CFB/OFB} the expert admits
 *       {@code NoPadding} alone, while this list also admits the empty padding. The extra
 *       value is inert: a two-part transformation such as {@code "AES/GCM"} is not a name the
 *       JCA resolves, so no program reaches the clause with it.</li>
 * </ul>
 *
 * <p>
 * {@code Api30CipherTransformationUtil} is not revived for this and must not be: it transcribes
 * the api30 catalogue -- {@code AES/ECB}, {@code ARC4}, {@code BLOWFISH}, {@code ChaCha20} --
 * which is exactly the anchor D-15 withdrew, and its own documentation closes with "It is not to
 * be given a caller again."
 */
public final class CipherTransformationNormalizer {

    /** The service name the alias table files {@code Cipher} rows under. */
    private static final String SERVICE = "Cipher";

    private static final List<String> AES_MODES =
            Arrays.asList("CBC", "CCM", "GCM", "PCBC", "CTR", "CTS", "CFB", "OFB");

    /** mode (folded) -> the paddings admitted with it, folded. */
    private static final Map<String, List<String>> AES_PADDINGS = aesPaddings();

    private static final List<String> RSA_ECB_PADDINGS = Arrays.asList(
            "NOPADDING", "PKCS1PADDING", "OAEPWITHMD5ANDMGF1PADDING",
            "OAEPWITHSHA-224ANDMGF1PADDING", "OAEPWITHSHA-256ANDMGF1PADDING",
            "OAEPWITHSHA-384ANDMGF1PADDING", "OAEPWITHSHA-512ANDMGF1PADDING");

    private CipherTransformationNormalizer() {
    }

    private static Map<String, List<String>> aesPaddings() {
        Map<String, List<String>> padding = new LinkedHashMap<>();
        padding.put("CBC", Arrays.asList("PKCS5PADDING", "ISO10126PADDING"));
        padding.put("PCBC", Arrays.asList("PKCS5PADDING", "ISO10126PADDING"));
        padding.put("GCM", Arrays.asList("", "NOPADDING"));
        padding.put("CTR", Arrays.asList("", "NOPADDING"));
        padding.put("CTS", Arrays.asList("", "NOPADDING"));
        padding.put("CFB", Arrays.asList("", "NOPADDING"));
        padding.put("OFB", Arrays.asList("", "NOPADDING"));
        padding.put("CCM", Arrays.asList("", "NOPADDING"));
        return padding;
    }

    /**
     * The transformation this one denotes: its pinned Conscrypt canonical name when a row
     * explains it, and itself otherwise. Case is left alone here -- {@link #alg},
     * {@link #mode} and {@link #pad} fold what they return, so a caller that wants to report
     * the value still has the spelling the program wrote.
     */
    public static String canonical(String transformation) {
        return ConscryptAliasTable.canonical(SERVICE, transformation);
    }

    /** The algorithm of the resolved transformation, folded. */
    public static String alg(String transformation) {
        return fold(CipherTransformationUtil.alg(nonNull(canonical(transformation))));
    }

    /**
     * The mode of the resolved transformation, folded.
     *
     * <p>
     * Resolving before the split is what this method is for. {@code IvChainJunction} read the
     * mode off the raw string, so an alias spelling such as {@code PBEWithHmacSHA1AndAES_128} --
     * one word, canonical {@code AES_128/CBC/PKCS5PADDING} -- answered the empty string and
     * slipped past the IV and GCM clauses in silence.
     */
    public static String mode(String transformation) {
        return fold(CipherTransformationUtil.mode(nonNull(canonical(transformation))));
    }

    /** The padding of the resolved transformation, folded. */
    public static String pad(String transformation) {
        return fold(CipherTransformationUtil.pad(nonNull(canonical(transformation))));
    }

    /**
     * Whether the transformation is one the expert rule's value clauses admit, read after alias
     * resolution and case folding.
     *
     * <p>
     * A null transformation is not valid rather than a {@code NullPointerException}: the guard
     * sites call this from inside an event body, where a throw would take down the program under
     * test instead of reporting about it.
     */
    public static boolean isValid(String transformation) {
        if (transformation == null) {
            return false;
        }
        String algorithm = alg(transformation);
        String mode = mode(transformation);
        String padding = pad(transformation);

        if ("AES".equals(algorithm)) {
            if (!AES_MODES.contains(mode)) {
                return false;
            }
            return AES_PADDINGS.get(mode).contains(padding);
        }
        if ("RSA".equals(algorithm)) {
            if (mode.isEmpty()) {
                return padding.isEmpty();
            }
            return "ECB".equals(mode) && RSA_ECB_PADDINGS.contains(padding);
        }
        return false;
    }

    private static String nonNull(String s) {
        return s == null ? "" : s;
    }

    private static String fold(String s) {
        return s == null ? "" : s.trim().toUpperCase(Locale.ROOT);
    }
}
