package br.unb.cic.mop.jca.util;

import static br.unb.cic.mop.jca.util.CipherTransformationUtil.alg;
import static br.unb.cic.mop.jca.util.CipherTransformationUtil.mode;
import static br.unb.cic.mop.jca.util.CipherTransformationUtil.pad;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/**
 * Which {@code Cipher} transformations the {@code jca_android} specification set
 * admits, transcribed from the {@code CONSTRAINTS} of
 * {@code MetaCrySL/generated/api30/Cipher.cryptsl}.
 *
 * <p>{@code CipherSpec} is the one specification of any JCA set with an algorithm
 * constraint and no allow-list of its own: it delegates to a Java utility, and
 * the specification names the utility it calls rather than a runtime switch
 * selecting between tables. Three sets, three utilities, none selected at run
 * time -- {@link CipherTransformationUtil} belongs to the frozen {@code jca} and
 * {@code AndroidCipherTransformationUtil} to the archived
 * {@code jca_android_bug_predicate}; both are read-only, so the successor set
 * needs its own class.
 *
 * <p>Parsing is not restated: {@code alg}, {@code mode} and {@code pad} are
 * correct and live one class away in this package.
 *
 * <p><b>What is transcribed and what is deferred.</b> The api30 rule states
 * twenty-five clauses. Seven of them are transcribed here -- the ones the frozen
 * {@code jca} already answered, over the {@code AES} and {@code RSA} families:
 * the algorithm catalogue ({@code Cipher.cryptsl:121}), the {@code AES} modes
 * ({@code :137}), the {@code CBC} paddings of {@code AES}/{@code DESede}
 * ({@code :141}), their stream-mode paddings ({@code :143}), the {@code RSA}
 * modes ({@code :145}) and paddings ({@code :147}), and the {@code AES/GCM}
 * padding ({@code :149}). The other eighteen are {@code deferred-constant} rows
 * of {@code data/jca_android/conformance_record.csv}: the frozen set never
 * tested them, transcribing them would add checks whose false-positive behaviour
 * on the corpus is unmeasured, and leaving them out adds no accusation -- the
 * successor is exactly as silent there as its seed was. Concretely, the six
 * algorithms the catalogue adds ({@code ChaCha20}, {@code AES_128},
 * {@code AES_256}, {@code ARC4}, {@code DESede}, {@code BLOWFISH}) are admitted
 * at {@code part(0)} and their mode/padding implications are not yet applied.
 *
 * <p><b>Comparison folds case and nothing else.</b> The JCA resolves algorithm
 * names case-insensitively at {@code getInstance}, so comparing the rule's
 * literals exactly would report a misuse on {@code AES/CBC/PKCS5PADDING}. The
 * hyphen is deliberately <i>not</i> folded, which is the difference from the
 * archived class: the campaign observed
 * {@code RSA/ECB/OAEPWithSHA1AndMGF1Padding}, the rule's
 * {@code OAEPwithSHA-1andMGF1Padding} spelled without the dash, and no Conscrypt
 * registration carries that spelling. Folding the hyphen would close the case by
 * a rule no primary source supports; instead it is recorded in
 * {@code data/jca_android/divergence_record.csv} with behavioural evidence, and
 * identifying the provider that accepts the spelling is execution work.
 *
 * <p><b>An absent component is the empty string.</b> The rule writes {@code ""}
 * explicitly where it means to admit a missing component
 * ({@code part(1) in {"", "ECB"}} for {@code RSA},
 * {@code part(1) in {"Poly1305", ""}} for {@code ChaCha20}), so a padding clause
 * that does not list {@code ""} is not satisfied by a transformation with no
 * padding. This narrows one case the frozen class admitted: bare {@code "RSA"}
 * and {@code "RSA/ECB"}, which the frozen class accepted through its own
 * {@code mode.equals("") && pad.equals("")} branch. The narrowing is a
 * transcription hunk, recorded in the conformance record against
 * {@code CipherSpec}, and the differential harness sizes it.
 */
public final class Api30CipherTransformationUtil {

    /** {@code Cipher.cryptsl:121} -- {@code part(0,"/",transformation) in {...}}. */
    static final List<String> ALGORITHMS = Arrays.asList(
            "ChaCha20", "AES_128", "ARC4", "RSA", "DESede", "AES", "BLOWFISH", "AES_256");

    /** {@code Cipher.cryptsl:137} -- {@code part(0) in {AES} => part(1) in {...}}. */
    static final List<String> AES_MODES = Arrays.asList(
            "CFB", "GCM", "OFB", "CTS", "CTR", "ECB", "CBC");

    /** {@code Cipher.cryptsl:145} -- {@code part(0) in {RSA} => part(1) in {...}}. */
    static final List<String> RSA_MODES = Arrays.asList("", "ECB");

    /** {@code Cipher.cryptsl:141} -- {@code {DESede,AES} && CBC => part(2) in {...}}. */
    static final List<String> CBC_PADDINGS = Arrays.asList(
            "PKCS5Padding", "PKCS7Padding", "ISO10126Padding");

    /** {@code Cipher.cryptsl:143} and {@code :149} -- {@code => part(2) in {NoPadding}}. */
    static final List<String> NO_PADDING = Arrays.asList("NoPadding");

    /** {@code Cipher.cryptsl:147} -- {@code part(0) in {RSA} => part(2) in {...}}. */
    static final List<String> RSA_PADDINGS = Arrays.asList(
            "OAEPwithSHA-512andMGF1Padding", "OAEPwithSHA-224andMGF1Padding", "PKCS1Padding",
            "OAEPwithSHA-256andMGF1Padding", "OAEPwithSHA-1andMGF1Padding", "OAEPPadding",
            "OAEPwithSHA-384andMGF1Padding", "NoPadding");

    /** {@code Cipher.cryptsl:143} -- the stream modes whose padding must be {@code NoPadding}. */
    static final List<String> STREAM_MODES = Arrays.asList("OFB", "CTR", "CFB");

    private Api30CipherTransformationUtil() {
    }

    /**
     * Whether the api30 rule admits {@code transformation}. Every comparison folds
     * case; an absent mode or padding is the empty string.
     */
    public static boolean isValid(String transformation) {
        if (transformation == null) {
            return false;
        }
        String algorithm = alg(transformation);
        String operationMode = mode(transformation);
        String padding = pad(transformation);

        // :121 -- the algorithm catalogue. Everything outside it is a misuse.
        if (!contains(ALGORITHMS, algorithm)) {
            return false;
        }

        // :145 and :147 -- RSA constrains its mode and its padding and nothing else.
        if (eq(algorithm, "RSA")) {
            return contains(RSA_MODES, operationMode) && contains(RSA_PADDINGS, padding);
        }

        // :137 -- only AES has a transcribed mode clause; the mode clauses of DESede,
        // BLOWFISH, ARC4, AES_128/AES_256 and ChaCha20 are deferred constants.
        if (eq(algorithm, "AES") && !contains(AES_MODES, operationMode)) {
            return false;
        }

        boolean aesFamily = eq(algorithm, "AES") || eq(algorithm, "DESede");
        // :141 -- the CBC paddings of AES and DESede.
        if (aesFamily && eq(operationMode, "CBC")) {
            return contains(CBC_PADDINGS, padding);
        }
        // :143 -- the stream-mode paddings of AES and DESede.
        if (aesFamily && contains(STREAM_MODES, operationMode)) {
            return contains(NO_PADDING, padding);
        }
        // :149 -- AES/GCM.
        if (eq(algorithm, "AES") && eq(operationMode, "GCM")) {
            return contains(NO_PADDING, padding);
        }

        // No transcribed clause constrains this pair: the rule says nothing, so
        // neither does the set (deferred constant).
        return true;
    }

    private static boolean contains(List<String> entries, String value) {
        for (String entry : entries) {
            if (eq(entry, value)) {
                return true;
            }
        }
        return false;
    }

    private static boolean eq(String a, String b) {
        return fold(a).equals(fold(b));
    }

    private static String fold(String s) {
        return s == null ? "" : s.trim().toUpperCase(Locale.ROOT);
    }
}
