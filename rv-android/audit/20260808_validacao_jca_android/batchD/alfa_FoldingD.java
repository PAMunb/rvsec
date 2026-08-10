// Batch D / Agent ALFA — D-piloto-2 test (a): folding x JCA resolution.
// For each candidate algorithm string: does the host JCA resolve it (getInstance
// succeeds), does the spec guard accept it (exact contains / toUpperCase contains,
// transcribed from the frozen .mop), and does the RAW api30 literal list contain it?
// Divergence spec-safe vs raw-violating on a resolvable string = FN witness;
// spec-unsafe vs raw-safe on a resolvable string = FP witness.
// Host JDK resolution is a lower bound for Android (declared threat: Conscrypt/BC
// aliases differ; unresolvable-here strings remain Android-side pending).
import java.security.*;
import javax.crypto.Mac;
import java.util.*;

public class AlfaFoldingD {
    static List<String> MAC_SPEC = Arrays.asList("HmacMD5","HmacSHA1","HmacSHA224","HmacSHA256","HmacSHA384","HmacSHA512","PBEwithHmacSHA","PBEwithHmacSHA1","PBEwithHmacSHA224","PBEwithHmacSHA256","PBEwithHmacSHA384","PBEwithHmacSHA512","HMAC-SHA256","HMAC/SHA256","HMAC-SHA384","HMAC/SHA384","HMAC/SHA512","HMAC-SHA512");
    static List<String> MAC_RAW = Arrays.asList("PBEwithHmacSHA256","PBEwithHmacSHA1","HmacSHA224","HmacSHA256","HmacMD5","HmacSHA512","PBEwithHmacSHA512","HmacSHA384","PBEwithHmacSHA384","PBEwithHmacSHA224","PBEwithHmacSHA","HmacSHA1");
    static List<String> MDG_SPEC = Arrays.asList("MD5","SHA-1","SHA-224","SHA-256","SHA-384","SHA-512","SHA256","SHA384","SHA512");
    static List<String> MDG_RAW = Arrays.asList("MD5","SHA-224","SHA-256","SHA-1","SHA-512","SHA-384");
    static List<String> KPG_SPEC = Arrays.asList("DH","DSA","RSA");
    static List<String> KPG_RAW = Arrays.asList("DSA","DH","RSA");
    static List<String> SRD_SPEC = Arrays.asList("SHA1PRNG");
    static List<String> SRD_RAW = Arrays.asList("SHA1PRNG");
    static List<String> SIG_SPEC = Arrays.asList("DSA","DSAwithSHA1","DSS","MD5withRSA","NONEwithDSA","NONEwithRSA","SHA1withDSA","SHA1withRSA","SHA1withRSA/PSS","SHA224withDSA","SHA224withECDSA","SHA224withRSA","SHA224withRSA/PSS","SHA256withDSA","SHA256withRSA","SHA256withRSA/PSS","SHA384withRSA","SHA384withRSA/PSS","SHA512withRSA","SHA512withRSA/PSS");
    static List<String> SIG_RAW = Arrays.asList("NONEwithRSA","SHA1withDSA","SHA224withECDSA","MD5withRSA","SHA256withDSA","SHA384withRSA/PSS","DSAwithSHA1","SHA384withRSA","SHA512withRSA/PSS","SHA1withRSA/PSS","SHA512withRSA","SHA1withRSA","NONEwithDSA","SHA256withRSA/PSS","SHA224withRSA/PSS","SHA256withRSA","DSA","SHA224withRSA","SHA224withDSA","DSS");

    interface Resolver { void get(String alg) throws Exception; }

    static void probe(String label, String[] candidates, List<String> specList, boolean specFolds,
                      List<String> rawList, Resolver r) {
        System.out.println("=== " + label + " ===");
        System.out.printf("%-18s %-9s %-10s %-9s %s%n", "candidate", "resolves", "spec-safe", "raw-safe", "verdict");
        for (String c : candidates) {
            boolean resolves;
            try { r.get(c); resolves = true; } catch (Exception e) { resolves = false; }
            boolean spec = specFolds ? specList.contains(c.toUpperCase()) : specList.contains(c);
            boolean raw = rawList.contains(c);
            String verdict = !resolves ? "unresolvable-on-host (Android pending)"
                : (spec && !raw) ? "FN witness (spec accepts, raw rejects)"
                : (!spec && raw) ? "FP witness (spec rejects, raw accepts)"
                : "consistent";
            System.out.printf("%-18s %-9s %-10s %-9s %s%n", c, resolves, spec, raw, verdict);
        }
    }

    public static void main(String[] a) throws Exception {
        probe("MAC (MacSpec.mop:13-16 exact contains vs Mac.cryptsl:71)",
            new String[]{"HmacSHA256","hmacsha256","HMACSHA256","HMAC-SHA256","HMAC/SHA256","HMAC-SHA512","PBEwithHmacSHA256","PBEWithHmacSHA256"},
            MAC_SPEC, false, MAC_RAW, alg -> Mac.getInstance(alg));
        probe("MDG (MessageDigestSpec.mop:16-17 toUpperCase contains vs MessageDigest.cryptsl:63)",
            new String[]{"SHA-256","sha-256","md5","MD5","SHA256","SHA384","SHA512","sha256","SHA-1","sha1","SHA1"},
            MDG_SPEC, true, MDG_RAW, alg -> MessageDigest.getInstance(alg));
        probe("KPG (KeyPairGeneratorSpec.mop:22 exact vs KeyPairGenerator.cryptsl:45)",
            new String[]{"RSA","rsa","DiffieHellman","DH","dsa","EC"},
            KPG_SPEC, false, KPG_RAW, alg -> KeyPairGenerator.getInstance(alg));
        probe("SRD (SecureRandomSpec.mop:23 exact vs SecureRandom.cryptsl:61)",
            new String[]{"SHA1PRNG","sha1prng","NativePRNG","DRBG"},
            SRD_SPEC, false, SRD_RAW, alg -> SecureRandom.getInstance(alg));
        probe("SIG (SignatureSpec.mop:23-27 exact vs Signature.cryptsl:75)",
            new String[]{"SHA256withRSA","sha256withrsa","SHA256WithRSA","DSS","DSA","MD5withRSA","SHA1withRSA","SHA256withECDSA"},
            SIG_SPEC, false, SIG_RAW, alg -> Signature.getInstance(alg));
    }
}
