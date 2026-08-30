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
 * <h2>The admitted values, and the one place they move</h2>
 *
 * <p>
 * The value clauses here are {@link CipherTransformationUtil}'s, reproduced, with one addition
 * the researcher ratified separately: the eight {@code PBEWithHmacSHA*AndAES_*} families
 * {@code Cipher.crysl:90-93} admits (decision D-20.1). Everything else about the inherited
 * {@code {AES, RSA}} collapse stands, and alias resolution and case folding remain what the
 * decision of 2026-08-25 licensed -- the mechanism D-15 already ratified for the other eleven
 * specifications. One known gap against the expert rule is left exactly as it is, because
 * closing it would be a value decision of its own:
 *
 * <ul>
 *   <li>For {@code AES} with {@code CCM/GCM/CTR/CTS/CFB/OFB} the expert admits
 *       {@code NoPadding} alone, while this list also admits the empty padding. The extra
 *       value is inert: a two-part transformation such as {@code "AES/GCM"} is not a name the
 *       JCA resolves, so no program reaches the clause with it.</li>
 * </ul>
 *
 * <p>
 * {@code Api30CipherTransformationUtil} is not revived for this and must not be: it transcribes
 * the api30 catalogue D-15 withdrew -- {@code AES/ECB}, {@code ARC4}, {@code BLOWFISH},
 * {@code ChaCha20} --
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

    /**
     * The eight algorithms {@code Cipher.crysl:90-93} admits beside {@code AES} for a
     * {@code SecretKey}, folded. Read off the RAW transformation and never off the resolved
     * one: Conscrypt files ten PBE services under these two canonical names, and the two the
     * expert rule does NOT list -- {@code PBEWithHmacSHA1AndAES_128} and its 256 twin
     * ({@code ConscryptAliasTable:103}, {@code :110}) -- resolve to the same
     * {@code AES_128/CBC/PKCS5PADDING} as the ones it does. After resolution the eight and the
     * two are the same string, so a check that ran on the canonical form would admit SHA-1 key
     * derivation the oracle refuses.
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
     * The algorithm to compare a key's own algorithm against, for the transformation this
     * {@code Cipher} was built with -- the value side of {@code generatedKey[key,
     * alg(transformation)]} ({@code Cipher.crysl:135}).
     *
     * <p>
     * It is {@link #alg} with one fold on top: {@code AES_128} and {@code AES_256} answer
     * {@code AES}. Conscrypt files keysize-suffixed services for the PBE transformations --
     * {@code PBEWithHmacSHA1AndAES_128} resolves to {@code AES_128/CBC/PKCS5PADDING} -- while a
     * key generated for that use reports the family name, {@code AES}, because that is the
     * service its own generator was asked for. Comparing the suffixed name against the family
     * name answers VIOLATED for a program that did nothing wrong, and the clause then accuses a
     * key origin that is in fact the one the rule wants (researcher decision D-20.2).
     *
     * <p>
     * The fold is here and not in {@link #alg} on purpose. {@link #isValid} reads {@code alg} to
     * decide which value list applies, and folding there would silently admit
     * {@code AES_128/CBC/PKCS5PADDING} as an AES transformation -- a different decision, about a
     * different clause, which the PBE families of {@code Cipher.crysl:90-105} are admitted by on
     * their own terms.
     */
    public static String keyAlgorithm(String transformation) {
        String algorithm = alg(transformation);
        if ("AES_128".equals(algorithm) || "AES_256".equals(algorithm)) {
            return "AES";
        }
        return algorithm;
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
        // The PBE families are decided on the raw spelling, ahead of resolution, for the
        // reason PBE_AES_ALGORITHMS records: resolution erases the difference between the
        // eight the rule admits and the two it does not. The rule pairs them with
        // `mode in {"CBC"}` (:98-100) and `pad in {"PKCS5Padding"}` (:104-106); a program
        // that names the service alone writes neither, and Conscrypt resolves it to exactly
        // that pair, so the one-word form conforms by construction.
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
