package br.unb.cic.mop.eh;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import javax.net.ssl.TrustManager;

/**
 * Evidence keys appended to a non-observation ({@code -NOBS-}) report envelope.
 *
 * <p>A non-observation report says the predicate store has no entry for the object a rule
 * constrains. The keys computed here let an analysis triage such reports without reading the
 * application's source: a fingerprint of a byte array that is identical across independent
 * installations points to a value embedded in the application, and the classes of a
 * trust-manager array name the managers worth reading. No guard, transition or predicate write
 * reads them; they follow {@code msg} in the envelope, so readers that locate {@code code},
 * {@code ev}, {@code val} and {@code exp} are unaffected.
 */
public final class Evidence {

    /** Longest value a key carries, the same bound the specifications apply to {@code val}. */
    private static final int MAX_VALUE_LENGTH = 512;

    private Evidence() {
    }

    /**
     * The evidence suffix for the object a {@code -NOBS-} site binds.
     *
     * @return {@code " vfp='sha256:<16 hex>'"} for a {@code byte[]}, {@code " vcls='<classes>'"}
     *         (runtime classes of the elements, comma-joined in array order) for a
     *         {@code TrustManager[]}, and {@code ""} for anything else, {@code null} included
     */
    public static String suffix(Object bound) {
        if (bound instanceof byte[]) {
            String fp = fingerprint((byte[]) bound);
            return fp.isEmpty() ? "" : " vfp='" + quote(fp) + "'";
        }
        if (bound instanceof TrustManager[]) {
            TrustManager[] managers = (TrustManager[]) bound;
            StringBuilder classes = new StringBuilder();
            for (int i = 0; i < managers.length; i++) {
                if (i > 0) {
                    classes.append(',');
                }
                classes.append(managers[i] == null ? "null" : managers[i].getClass().getName());
            }
            return " vcls='" + quote(classes.toString()) + "'";
        }
        return "";
    }

    /**
     * True when {@code element} is an instance of a class defined by a class loader other than
     * the one that defined {@code platformType}, i.e. a class of the application rather than of
     * the platform. Both loaders come from the same runtime, so the answer does not depend on
     * whether the platform reports its boot loader as {@code null} or as an object.
     * {@code null} is not application-defined.
     */
    public static boolean isApplicationDefined(Object element, Class<?> platformType) {
        return element != null && element.getClass().getClassLoader() != platformType.getClassLoader();
    }

    /**
     * {@code "sha256:"} followed by the first eight bytes of the SHA-256 of {@code bytes} in
     * lower-case hex, or {@code ""} when the runtime offers no SHA-256.
     */
    static String fingerprint(byte[] bytes) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder hex = new StringBuilder("sha256:");
            for (int i = 0; i < 8; i++) {
                hex.append(String.format("%02x", digest[i] & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            return "";
        }
    }

    /** The specifications' {@code q()} rule: at most 512 characters, {@code '} escaped as {@code \'}. */
    static String quote(String value) {
        String bounded = value.length() > MAX_VALUE_LENGTH ? value.substring(0, MAX_VALUE_LENGTH) : value;
        return bounded.replace("'", "\\'");
    }
}
