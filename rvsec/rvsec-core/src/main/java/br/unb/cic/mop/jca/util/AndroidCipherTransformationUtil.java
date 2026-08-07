package br.unb.cic.mop.jca.util;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Which {@code Cipher} transformations the jca_android specification set admits.
 *
 * <p>{@code CipherSpec} is the only specification in either set with an algorithm
 * constraint and no allow-list of its own: it delegates to a Java utility. The
 * frozen {@link CipherTransformationUtil} covers two algorithm families with
 * tables rebuilt as method locals on every call, while the generated CrySL rule
 * for API 30 admits eight. That left the derived set contradicting itself --
 * {@code KeyGeneratorSpec} accepting {@code ChaCha20}, {@code DESede},
 * {@code BLOWFISH} and {@code ARC4} because the platform publishes them, while
 * any {@code Cipher.getInstance} over one of them was reported as a misuse.
 *
 * <p>This class holds the derived set's tables, transcribed from the three layers
 * of implication the generated rule states: the catalogue of algorithms, the
 * modes each algorithm admits, and the paddings each (algorithm, mode) pair
 * admits. The frozen class is not touched -- the {@code jca} set produced
 * published measurements and its verdict is preserved by there being no edit to
 * it, rather than by a test asserting it did not change.
 *
 * <p>Parsing is not restated. {@code alg}, {@code mode} and {@code pad} are
 * correct and live one class away in this same package, so a transformation
 * string is decomposed in one place for both sets.
 *
 * <p>Three decisions are not transcription and are worth stating:
 *
 * <ul>
 * <li><b>Comparison folds case and hyphens.</b> The JCA resolves algorithm names
 *     case-insensitively at {@code getInstance} and a string comparison does not.
 *     The frozen class already folds the padding, and one call site in the
 *     corpus -- {@code Cipher.getInstance("AES/CBC/PKCS5PADDING")} -- is accepted
 *     only because of it, so comparing the rule's literals exactly would have
 *     been a regression. Here all three components fold, and the hyphen folds
 *     with them: the campaign observed
 *     {@code RSA/ECB/OAEPWithSHA1AndMGF1Padding}, which is the rule's
 *     {@code OAEPwithSHA-1andMGF1Padding} spelled without the dash. Folding the
 *     hyphen merges no two literals of this rule -- the OAEP family is the only
 *     place one appears, and its members stay distinct. The underscore is
 *     deliberately not folded, because {@code AES_128} and {@code AES_256} are
 *     real JCA names and {@code AES128} is not. The same gap in the other
 *     specifications is recorded rather than repaired; see
 *     {@code data/gh101/algorithm_naming.md}.</li>
 * <li><b>An unspecified component is unconstrained.</b> A transformation naming
 *     no mode or no padding asks for the provider's default, and the rule
 *     constrains only what is written. This is also what keeps bare
 *     {@code "RSA"} admissible: CrySL 1.5.2 stated it as
 *     {@code mode in {""} => pad in {""}}, and the generated rule lost the
 *     per-mode split, keeping only the eight-padding consequent.</li>
 * <li><b>A pair with no padding implication admits any padding.</b> The rule
 *     places no constraint on the padding of {@code AES/ECB}, {@code AES/CTS},
 *     {@code DESede/ECB}, {@code DESede/CTS}, {@code BLOWFISH/ECB} or
 *     {@code BLOWFISH/CTS}. Following it means admitting them, which differs
 *     from the frozen class -- whose mode list carries no {@code ECB} at all, so
 *     it rejects {@code AES/ECB/NoPadding}, a transformation the corpus
 *     contains.</li>
 * </ul>
 *
 * @see <a href="https://github.com/PAMunb/rvsec/issues/101">issue #101</a>
 */
public final class AndroidCipherTransformationUtil {

    /** Padding table key for an algorithm whose padding does not depend on the mode. */
    private static final String ANY_MODE = "*";

    /** Algorithm to the modes it admits. Membership in this map is the catalogue. */
    private static final Map<String, Set<String>> MODES;

    /** Algorithm to mode to admissible paddings. A missing entry means unconstrained. */
    private static final Map<String, Map<String, Set<String>>> PADDINGS;

    // Everything is held upper case and without hyphens, so a lookup folds both
    // by construction, and as immutable class-level data rather than locals
    // rebuilt per call. The empty mode of ChaCha20 and RSA is deliberately
    // absent: an unspecified component is handled before any table is consulted.
    static {
        Map<String, Set<String>> modes = new HashMap<String, Set<String>>();
        modes.put("AES", set("CBC", "CFB", "CTR", "CTS", "ECB", "GCM", "OFB"));
        modes.put("AES_128", set("CBC", "ECB", "GCM"));
        modes.put("AES_256", set("CBC", "ECB", "GCM"));
        modes.put("ARC4", set("ECB"));
        modes.put("BLOWFISH", set("CBC", "CFB", "CTR", "CTS", "ECB", "OFB"));
        modes.put("CHACHA20", set("POLY1305"));
        modes.put("DESEDE", set("CBC", "CFB", "CTR", "CTS", "ECB", "OFB"));
        modes.put("RSA", set("ECB"));
        MODES = Collections.unmodifiableMap(modes);

        Set<String> blockPaddings = set("ISO10126PADDING", "PKCS5PADDING", "PKCS7PADDING");
        Set<String> noPadding = set("NOPADDING");

        Map<String, Map<String, Set<String>>> paddings = new HashMap<String, Map<String, Set<String>>>();

        Map<String, Set<String>> aes = new HashMap<String, Set<String>>();
        aes.put("CBC", blockPaddings);
        aes.put("CFB", noPadding);
        aes.put("CTR", noPadding);
        aes.put("GCM", noPadding);
        aes.put("OFB", noPadding);
        paddings.put("AES", Collections.unmodifiableMap(aes));

        // AES_128 and AES_256 are the fixed-key-length names, and the rule gives
        // them a narrower padding set for CBC than plain AES gets.
        Map<String, Set<String>> aesSized = new HashMap<String, Set<String>>();
        aesSized.put("CBC", set("NOPADDING", "PKCS5PADDING"));
        aesSized.put("ECB", set("NOPADDING", "PKCS5PADDING"));
        aesSized.put("GCM", noPadding);
        Map<String, Set<String>> aesSizedView = Collections.unmodifiableMap(aesSized);
        paddings.put("AES_128", aesSizedView);
        paddings.put("AES_256", aesSizedView);

        Map<String, Set<String>> blowfish = new HashMap<String, Set<String>>();
        blowfish.put("CBC", blockPaddings);
        blowfish.put("CFB", noPadding);
        blowfish.put("CTR", noPadding);
        blowfish.put("OFB", noPadding);
        paddings.put("BLOWFISH", Collections.unmodifiableMap(blowfish));

        Map<String, Set<String>> desede = new HashMap<String, Set<String>>();
        desede.put("CBC", blockPaddings);
        desede.put("CFB", noPadding);
        desede.put("CTR", noPadding);
        desede.put("OFB", noPadding);
        paddings.put("DESEDE", Collections.unmodifiableMap(desede));

        paddings.put("ARC4", anyMode(noPadding));
        paddings.put("CHACHA20", anyMode(noPadding));
        paddings.put("RSA", anyMode(set(
                "NOPADDING",
                "OAEPPADDING",
                "OAEPWITHSHA1ANDMGF1PADDING",
                "OAEPWITHSHA224ANDMGF1PADDING",
                "OAEPWITHSHA256ANDMGF1PADDING",
                "OAEPWITHSHA384ANDMGF1PADDING",
                "OAEPWITHSHA512ANDMGF1PADDING",
                "PKCS1PADDING")));

        PADDINGS = Collections.unmodifiableMap(paddings);
    }

    private AndroidCipherTransformationUtil() {
    }

    /**
     * Whether the algorithm, mode and padding of a transformation are jointly
     * admissible under the generated API 30 {@code Cipher} rule.
     *
     * <p>Never raises: the call site is a monitor guard, and a guard that throws
     * would take the monitored application down with it. A malformed
     * transformation is not admissible, which is the same answer the frozen
     * utility gives.
     */
    public static boolean isValid(String transformation) {
        if (transformation == null) {
            return false;
        }
        // `mode` reads split("/")[1] without checking, so a transformation
        // carrying a separator with nothing after it would raise inside it.
        if (transformation.indexOf('/') >= 0 && transformation.split("/").length < 2) {
            return false;
        }

        Set<String> admissibleModes = MODES.get(fold(CipherTransformationUtil.alg(transformation)));
        if (admissibleModes == null) {
            return false;
        }

        String mode = fold(CipherTransformationUtil.mode(transformation));
        if (!mode.isEmpty() && !admissibleModes.contains(mode)) {
            return false;
        }

        String padding = fold(CipherTransformationUtil.pad(transformation));
        if (padding.isEmpty()) {
            return true;
        }

        Set<String> admissiblePaddings =
                paddingsFor(fold(CipherTransformationUtil.alg(transformation)), mode);
        return admissiblePaddings == null || admissiblePaddings.contains(padding);
    }

    /** The paddings admissible for a pair, or {@code null} where the rule states none. */
    private static Set<String> paddingsFor(String algorithm, String mode) {
        Map<String, Set<String>> byMode = PADDINGS.get(algorithm);
        if (byMode == null) {
            return null;
        }
        Set<String> regardlessOfMode = byMode.get(ANY_MODE);
        return regardlessOfMode != null ? regardlessOfMode : byMode.get(mode);
    }

    /** Upper case with hyphens removed -- the form every table above is held in. */
    private static String fold(String value) {
        return value == null ? "" : value.toUpperCase().replace("-", "");
    }

    private static Set<String> set(String... values) {
        return Collections.unmodifiableSet(new HashSet<String>(Arrays.asList(values)));
    }

    private static Map<String, Set<String>> anyMode(Set<String> paddings) {
        return Collections.singletonMap(ANY_MODE, paddings);
    }
}
