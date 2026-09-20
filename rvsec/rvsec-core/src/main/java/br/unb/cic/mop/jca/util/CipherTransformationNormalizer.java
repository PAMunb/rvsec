package br.unb.cic.mop.jca.util;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * A {@code Cipher} transformation read the way the rest of this specification set reads a value:
 * the pinned Conscrypt alias is resolved first, case is folded, and only then is anything
 * compared.
 *
 * <h2>What it resolves and folds before it delegates</h2>
 *
 * <p>
 * Every accessor here first sends the transformation through {@link ConscryptAliasTable} for the
 * {@code Cipher} service, then hands the resolved string to {@link CipherTransformationUtil} for
 * the split into algorithm, mode and padding, and finally folds what comes back to upper case.
 * That order is the point of the class. {@link CipherTransformationUtil} compares raw:
 * {@code alg(t).equals("AES")} and {@code modes.contains(mode(t))} are case-sensitive (only the
 * padding calls {@code toUpperCase()}), and it resolves no alias anywhere, so spellings the
 * platform accepts would be accused:
 *
 * <ul>
 *   <li>{@code AES/CBC/PKCS7Padding} -- a pinned Conscrypt alias of
 *       {@code AES/CBC/PKCS5Padding}</li>
 *   <li>{@code RSA/None/PKCS1Padding} -- a pinned Conscrypt alias of
 *       {@code RSA/ECB/PKCS1Padding}</li>
 *   <li>{@code aes/cbc/pkcs5padding} and {@code AES/cbc/PKCS5Padding} -- the JCA resolves
 *       transformation names case-insensitively</li>
 * </ul>
 *
 * <p>
 * This is the same normalisation the other eleven value-carrying specifications of the set get
 * from {@link ConscryptAliasTable#matches}; {@code CipherSpec} reaches it through this class
 * because a transformation is three values in one string and has to be split before it can be
 * compared.
 *
 * <h2>The admitted values</h2>
 *
 * <p>
 * The value lists are {@link CipherTransformationUtil}'s {@code {AES, RSA}} lists, reproduced,
 * plus the eight {@code PBEWithHmacSHA*AndAES_*} families the {@code CONSTRAINTS} of
 * {@code Cipher.crysl} admit for a {@code SecretKey}:
 * `instanceOf[key, javax.crypto.SecretKey] => alg(transformation) in {"AES",
 * "PBEWithHmacSHA224AndAES_128", ...}`. One gap against that rule is left exactly as it is,
 * because closing it would change which programs the set accuses:
 *
 * <ul>
 *   <li>For {@code AES} with {@code CCM/GCM/CTR/CTS/CFB/OFB} the expert rule admits
 *       {@code NoPadding} alone, while this list also admits the empty padding. The extra
 *       value is inert: a two-part transformation such as {@code "AES/GCM"} is not a name the
 *       JCA resolves, so no program reaches the clause with it.</li>
 * </ul>
 */
public final class CipherTransformationNormalizer {

    /** The service name the alias table files {@code Cipher} rows under. */
    private static final String SERVICE = "Cipher";

    private static final List<String> AES_MODES =
            Arrays.asList("CBC", "CCM", "GCM", "PCBC", "CTR", "CTS", "CFB", "OFB");

    /** mode (folded) -> the paddings admitted with it, folded. */
    private static final Map<String, List<String>> AES_PADDINGS = aesPaddings();

    /**
     * The eight algorithms the {@code CONSTRAINTS} of {@code Cipher.crysl} admit beside
     * {@code AES} for a {@code SecretKey}, folded. Read off the RAW transformation and never off
     * the resolved one: Conscrypt files ten PBE services under two canonical names, and the two
     * the expert rule does NOT list -- {@code PBEWithHmacSHA1AndAES_128} and its 256 twin --
     * carry rows in {@link ConscryptAliasTable} that resolve to the same
     * {@code AES_128/CBC/PKCS5PADDING} as the ones it does. After resolution the eight and the
     * two are the same string, so a check that ran on the canonical form would admit the SHA-1
     * key derivation the rule refuses.
     */
    private static final List<String> PBE_AES_ALGORITHMS = Arrays.asList(
            "PBEWITHHMACSHA224ANDAES_128", "PBEWITHHMACSHA256ANDAES_128",
            "PBEWITHHMACSHA384ANDAES_128", "PBEWITHHMACSHA512ANDAES_128",
            "PBEWITHHMACSHA224ANDAES_256", "PBEWITHHMACSHA256ANDAES_256",
            "PBEWITHHMACSHA384ANDAES_256", "PBEWITHHMACSHA512ANDAES_256");

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
     * Resolve the transformation this one denotes: its pinned Conscrypt canonical name when a
     * row explains it, and itself otherwise. Case is left alone here -- {@link #alg},
     * {@link #mode} and {@link #pad} fold what they return, so a caller that wants to report
     * the value still has the spelling the program wrote.
     */
    public static String canonical(String transformation) {
        return ConscryptAliasTable.canonical(SERVICE, transformation);
    }

    /** Return the algorithm of the resolved transformation, folded. */
    public static String alg(String transformation) {
        return fold(CipherTransformationUtil.alg(nonNull(canonical(transformation))));
    }

    /**
     * Return the mode of the resolved transformation, folded.
     *
     * <p>
     * Resolving before the split is what this method is for. A one-word alias spelling such as
     * {@code PBEWithHmacSHA1AndAES_128} -- canonical {@code AES_128/CBC/PKCS5PADDING} -- carries
     * no mode of its own, so a caller that split the raw string would read the empty string and
     * let the call slip past the IV and GCM clauses in silence.
     */
    public static String mode(String transformation) {
        return fold(CipherTransformationUtil.mode(nonNull(canonical(transformation))));
    }

    /** Return the padding of the resolved transformation, folded. */
    public static String pad(String transformation) {
        return fold(CipherTransformationUtil.pad(nonNull(canonical(transformation))));
    }

    /**
     * Return the algorithm to compare a key's own algorithm against, for the transformation this
     * {@code Cipher} was built with -- the value side of the {@code REQUIRES} clause
     * `generatedKey[key, alg(transformation)]` of {@code Cipher.crysl}.
     *
     * <p>
     * It is {@link #alg} with one fold on top: {@code AES_128} and {@code AES_256} answer
     * {@code AES}. Conscrypt files keysize-suffixed services for the PBE transformations --
     * {@code PBEWithHmacSHA1AndAES_128} resolves to {@code AES_128/CBC/PKCS5PADDING} -- while a
     * key generated for that use reports the family name, {@code AES}, because that is the
     * service its own generator is asked for. Comparing the suffixed name against the family
     * name answers VIOLATED for a program that did nothing wrong, and the clause then accuses a
     * key origin that is in fact the one the rule wants.
     *
     * <p>
     * The fold is here and not in {@link #alg} on purpose. {@link #isValid} reads {@code alg} to
     * decide which value list applies, and folding there would silently admit
     * {@code AES_128/CBC/PKCS5PADDING} as an AES transformation; the PBE families have value
     * clauses of their own in {@code Cipher.crysl} and are admitted on those terms, not as AES.
     */
    public static String keyAlgorithm(String transformation) {
        String algorithm = alg(transformation);
        if ("AES_128".equals(algorithm) || "AES_256".equals(algorithm)) {
            return "AES";
        }
        return algorithm;
    }

    /**
     * Decide whether the transformation is one the expert rule's value clauses admit, read after
     * alias resolution and case folding.
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
        // The PBE families are decided on the raw spelling, ahead of resolution, for the
        // reason PBE_AES_ALGORITHMS records: resolution erases the difference between the
        // eight the rule admits and the two it does not. The CONSTRAINTS of Cipher.crysl pair
        // those families with `mode(transformation) in {"CBC"}` and
        // `pad(transformation) in {"PKCS5Padding"}`; a program that names the service alone
        // writes neither, and Conscrypt resolves it to exactly that pair, so the one-word
        // form conforms by construction.
        String rawAlgorithm = fold(CipherTransformationUtil.alg(transformation));
        if (PBE_AES_ALGORITHMS.contains(rawAlgorithm)) {
            String rawMode = fold(CipherTransformationUtil.mode(transformation));
            String rawPadding = fold(CipherTransformationUtil.pad(transformation));
            if (rawMode.isEmpty() && rawPadding.isEmpty()) {
                return true;
            }
            return "CBC".equals(rawMode) && "PKCS5PADDING".equals(rawPadding);
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
