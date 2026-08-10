// Batch C / Agent ALFA — D-piloto-2 test (a): folding x JCA case-insensitive
// getInstance resolution, for the five getInstance-family factories.
// For each probe string: does the JCA provider lookup resolve it (case-insensitive
// per Provider.getService), what does the spec guard decide, and what does the raw
// api30 CONSTRAINT literal set decide. Divergence threat declared: executed on the
// host JDK (Temurin 25), not on the Android 30 runtime (Conscrypt/BC); rows whose
// resolution is provider-dependent are marked in the report.
import java.util.*;
import java.util.function.Predicate;

public class AlfaFoldingC {
    interface Res { boolean get(String s) throws Exception; }

    static void probe(String spec, List<String> mopList, boolean mopFolds,
                      List<String> rawList, Res resolver, String... probes) {
        System.out.println("== " + spec + " ==");
        for (String p : probes) {
            boolean resolved;
            String exc = "";
            try { resolved = resolver.get(p); }
            catch (Exception e) { resolved = false; exc = e.getClass().getSimpleName(); }
            boolean mopSafe = mopFolds ? mopList.contains(p.toUpperCase()) : mopList.contains(p);
            boolean rawOk = rawList.contains(p);
            String verdict;
            if (resolved && mopSafe && !rawOk) verdict = "FN vs raw rule (spec safe, raw constraint violated)";
            else if (resolved && !mopSafe && rawOk) verdict = "spec flags, raw ok (FP on constraint clause)";
            else verdict = "consistent";
            System.out.printf("  %-14s resolvesJDK=%-5s%s mopGuardSafe=%-5s rawLiteralOk=%-5s -> %s%n",
                '"'+p+'"', resolved, exc.isEmpty()?"":"("+exc+")", mopSafe, rawOk, verdict);
        }
    }

    public static void main(String[] a) {
        List<String> kgnMop = Arrays.asList("AES","ARC4","BLOWFISH","ChaCha20","DESede","HmacMD5","HmacSHA1","HmacSHA224","HmacSHA256","HmacSHA384","HmacSHA512","HMAC-SHA256","HMAC/SHA256","HMAC-SHA384","HMAC/SHA384","HMAC/SHA512","HMAC-SHA512");
        List<String> kgnRaw = Arrays.asList("ChaCha20","ARC4","HmacSHA224","DESede","HmacSHA256","HmacMD5","HmacSHA1","HmacSHA512","AES","BLOWFISH","HmacSHA384");
        probe("KeyGeneratorSpec (exact contains)", kgnMop, false, kgnRaw,
              s -> { javax.crypto.KeyGenerator.getInstance(s); return true; },
              "AES", "aes", "Aes", "HmacSHA256", "hmacsha256", "HMAC-SHA256", "HMAC/SHA256", "DES", "ChaCha20");

        List<String> fac = Arrays.asList("PKIX");
        probe("KeyManagerFactorySpec (exact contains)", fac, false, fac,
              s -> { javax.net.ssl.KeyManagerFactory.getInstance(s); return true; },
              "PKIX", "pkix", "Pkix", "SunX509", "X509", "NewSunX509");
        probe("TrustManagerFactorySpec (exact contains)", fac, false, fac,
              s -> { javax.net.ssl.TrustManagerFactory.getInstance(s); return true; },
              "PKIX", "pkix", "SunX509", "X509");

        List<String> sslMop = Arrays.asList("DEFAULT","SSL","TLS","TLSV1","TLSV1.1","TLSV1.2","TLSV1.3");
        List<String> sslRaw = Arrays.asList("Default","TLSv1.2","TLSv1.1","SSL","TLSv1","TLS","TLSv1.3");
        probe("SSLContextSpec (folds toUpperCase)", sslMop, true, sslRaw,
              s -> { javax.net.ssl.SSLContext.getInstance(s); return true; },
              "TLS", "tls", "TLSv1.2", "tlsv1.2", "TLSV1.2", "Default", "default", "DEFAULT", "SSLv3", "DTLS");

        List<String> kstMop = Arrays.asList("AndroidCAStore","AndroidKeyStore","BKS","BouncyCastle","PKCS12");
        probe("KeyStoreSpec (exact contains)", kstMop, false, kstMop,
              s -> { java.security.KeyStore.getInstance(s); return true; },
              "PKCS12", "pkcs12", "Pkcs12", "JKS", "jks", "BKS", "AndroidKeyStore");
    }
}
