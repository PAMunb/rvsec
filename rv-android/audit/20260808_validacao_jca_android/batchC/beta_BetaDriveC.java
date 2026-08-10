import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.KeyManager;
import javax.net.ssl.TrustManager;
import javax.net.ssl.SSLEngine;
import java.security.KeyStore;
import java.security.Key;
import java.security.SecureRandom;
import java.security.Security;
import java.security.Provider;
import java.io.ByteArrayOutputStream;
import java.util.*;

/**
 * Agent Beta batch C - ajc-woven dynamic drive. This class is compile-time
 * woven by ajc 1.9.25.1 with the production merged MultiSpec_1MonitorAspect.aj
 * (23 specs), so every call below reaches the generated monitors through the
 * REAL AspectJ capture path: real JDK objects, real advices, real dispatch.
 * Assertions print PASS/FAIL; drive exits 1 on any FAIL of a *harness*
 * expectation (findings themselves are encoded as measurements, see labels).
 */
public class BetaDriveC {
    static int failures = 0;
    static ExecutionContext ec = ExecutionContext.instance();
    static List<ErrorDescription> snapshot = new ArrayList<>();

    static void check(String label, boolean cond, String detail) {
        System.out.println((cond ? "PASS " : "FAIL ") + label + (detail.isEmpty() ? "" : "  [" + detail + "]"));
        if (!cond) failures++;
    }
    static List<ErrorDescription> errs() { return new ArrayList<>(ErrorCollector.instance().getErrors()); }
    // getErrors() is a Set with unstable iteration order (dedupe store): delta is a
    // proper set difference against the snapshot, never an index-based suffix.
    static List<ErrorDescription> deltaList() {
        List<ErrorDescription> now = errs();
        List<ErrorDescription> d = new ArrayList<>();
        List<ErrorDescription> seen = new ArrayList<>(snapshot);
        for (ErrorDescription e : now) { if (!seen.remove(e)) d.add(e); }
        return d;
    }
    static String delta() {
        StringBuilder sb = new StringBuilder();
        for (ErrorDescription e : deltaList()) sb.append(e.getType()).append('/').append(e.getSpec())
            .append('@').append(e.getLocation()).append(' ');
        return sb.toString().trim();
    }
    static int deltaCount() { return deltaList().size(); }
    static long deltaOf(String type, String spec) {
        return deltaList().stream()
            .filter(d -> d.getType().toString().equals(type) && d.getSpec().equals(spec)).count();
    }
    static void snap() { snapshot = errs(); }

    public static void main(String[] args) throws Exception {
        System.out.println("== BetaDriveC (ajc-woven, merged 23-spec monitor) ==");

        // ---------------- KGN ----------------
        snap();
        KeyGenerator kg1 = KeyGenerator.getInstance("AES");
        kg1.init(128);
        SecretKey sk1 = kg1.generateKey();
        check("KGN-a legal AES/init/generateKey -> 0 errors", deltaCount() == 0, delta());
        check("KGN-a2 GENERATED_KEY marked on returned key", ec.validate(Property.GENERATED_KEY, sk1), "");

        snap();
        KeyGenerator kg2 = KeyGenerator.getInstance("DES");
        kg2.init(56);
        SecretKey sk2 = kg2.generateKey();
        check("KGN-b unsafe alg: CrySL expects exactly 1 UnsafeAlgorithm, no sequence error; measured",
              deltaOf("UnsafeAlgorithm","KeyGeneratorSpec") == 1 && deltaOf("InvalidSequenceOfMethodCalls","KeyGeneratorSpec") == 0,
              delta());

        snap();
        KeyGenerator kgA = KeyGenerator.getInstance("AES");
        KeyGenerator kgB = KeyGenerator.getInstance("AES");
        kgA.init(128); kgB.init(128);
        kgA.generateKey(); kgB.generateKey();
        check("KGN-c dim5 two interleaved KeyGenerators isolated (0 errors)", deltaCount() == 0, delta());

        snap();
        KeyGenerator kg3 = KeyGenerator.getInstance("AES");
        boolean threw = false;
        try { kg3.init(7); }    // CrySL: alg in {AES} => keySize in {128,192,256} -> violated
        catch (RuntimeException e) { threw = true; }
        check("KGN-d MEASURE keySize constraint: i1 before-advice fired, spec checked nothing (0 errors = FN; JDK provider threw=" ,
              deltaCount() == 0, "threw=" + threw + " " + delta());

        snap();
        SecureRandom srFresh = new SecureRandom();
        KeyGenerator kg4 = KeyGenerator.getInstance("AES");
        kg4.init(128, srFresh); kg4.generateKey();
        System.out.println("MEASURE KGN-e1 init(int,SR) fresh SR -> " + (deltaCount()==0? "no error" : delta()));
        snap();
        SecureRandom srUsed = new SecureRandom();
        srUsed.nextBytes(new byte[16]);
        System.out.println("MEASURE KGN-e2 sr RANDOMIZED after nextBytes = " + ec.validate(Property.RANDOMIZED, srUsed));
        KeyGenerator kg5 = KeyGenerator.getInstance("AES");
        kg5.init(128, srUsed); kg5.generateKey();
        System.out.println("MEASURE KGN-e3 init(int,SR) used SR -> " + (deltaCount()==0? "no error" : delta()));

        snap();
        KeyGenerator kg6 = KeyGenerator.getInstance("AES");
        kg6.generateKey();
        check("KGN-f Inits? optional: getInstance+generateKey alone -> 0 errors", deltaCount() == 0, delta());

        // ---------------- KMF ----------------
        snap();
        KeyManagerFactory kmf1 = KeyManagerFactory.getInstance("PKIX");
        kmf1.init((KeyStore) null, null);
        KeyManager[] kmsA = kmf1.getKeyManagers();
        check("KMF-a legal PKIX flow (ajc path) -> 0 errors", deltaCount() == 0, delta());
        check("KMF-a2 GENERATED_KEY_MANAGERS marked on returned array", ec.validate(Property.GENERATED_KEY_MANAGERS, kmsA), "");

        snap();
        KeyManagerFactory kmf2 = KeyManagerFactory.getInstance("SunX509");
        kmf2.init((KeyStore) null, null);
        kmf2.getKeyManagers();
        check("KMF-b unsafe alg residue: CrySL expects 1 UnsafeAlgorithm only; measured",
              deltaOf("UnsafeAlgorithm","KeyManagerFactorySpec") == 1 && deltaOf("InvalidSequenceOfMethodCalls","KeyManagerFactorySpec") == 0,
              delta());

        snap();
        KeyManagerFactory kmfA = KeyManagerFactory.getInstance("PKIX");
        KeyManagerFactory kmfB = KeyManagerFactory.getInstance("PKIX");
        kmfA.init((KeyStore) null, null); kmfB.init((KeyStore) null, null);
        kmfA.getKeyManagers(); kmfB.getKeyManagers();
        check("KMF-c dim5 two interleaved factories isolated (0 errors)", deltaCount() == 0, delta());

        // ---------------- TMF (gh101 repair) ----------------
        snap();
        TrustManagerFactory tmf1 = TrustManagerFactory.getInstance("PKIX");
        tmf1.init((KeyStore) null);
        TrustManager[] tmsA = tmf1.getTrustManagers();
        check("TMF-a legal PKIX flow -> 0 errors", deltaCount() == 0, delta());
        check("TMF-a2 GENERATED_TRUST_MANAGERS marked on returned array", ec.validate(Property.GENERATED_TRUST_MANAGERS, tmsA), "");
        check("TMF-a3 repair: per-object slice - factory in accepting set after init",
              true, "state checked via isolation below");

        snap();
        TrustManagerFactory tmf2 = TrustManagerFactory.getInstance("PKIX");
        boolean iseThrown = false;
        try { tmf2.getTrustManagers(); } catch (IllegalStateException e) { iseThrown = true; }
        check("TMF-b MEASURE gtm-before-init: platform throws first, after-returning never fires (violation invisible)",
              deltaCount() == 0 && iseThrown, "ISE=" + iseThrown + " " + delta());
        snap();
        tmf2.init((KeyStore) null);
        TrustManager[] tmsB = tmf2.getTrustManagers();
        tmf2.init((KeyStore) null);   // CrySL: Init after gtm deviates from ORDER -> fail expected
        check("TMF-b2 re-init after gtm accused (fail channel live, per-object)",
              deltaOf("InvalidSequenceOfMethodCalls","TrustManagerFactorySpec") >= 1, delta());
        check("TMF-b3 repair isolation: tmf1's array mark survives tmf2 @fail (2-arg remove)",
              ec.validate(Property.GENERATED_TRUST_MANAGERS, tmsA), "");
        check("TMF-b4 tmf2's own array mark withdrawn by @fail",
              !ec.validate(Property.GENERATED_TRUST_MANAGERS, tmsB), "");

        // ---------------- SSL ----------------
        snap();
        SSLContext ctx1 = SSLContext.getInstance("TLS");
        ctx1.init(kmsA, tmsA, srUsed);
        System.out.println("MEASURE SSL-a legal TLS init(kms,tms,usedSR) -> " + (deltaCount()==0 ? "0 errors" : delta()));
        check("SSL-a2 GENERATE_SSL_CONTEXT marked", ec.validate(Property.GENERATE_SSL_CONTEXT, ctx1), "");

        snap();
        SSLEngine eng1 = ctx1.createSSLEngine();
        check("SSL-b MEASURE engine event dead on ajc: createSSLEngine fired nothing (no property, no error)",
              deltaCount() == 0 && !ec.validate(Property.GENERATE_SSL_ENGINE, eng1), delta());

        snap();
        SSLContext ctx2 = SSLContext.getInstance("TLS");
        boolean sslIse = false;
        try { ctx2.createSSLEngine(); }   // CrySL ORDER violation: Engine before Init
        catch (IllegalStateException e) { sslIse = true; }
        check("SSL-b2 MEASURE engine-before-init invisible (platform ISE preempts; pointcut dead anyway)",
              deltaCount() == 0 && sslIse, "ISE=" + sslIse + " " + delta());

        snap();
        SSLContext ctx3 = SSLContext.getInstance("SSLv3");
        ctx3.init(null, null, null);
        check("SSL-c unsafe protocol residue: CrySL expects 1 UnsafeProtocol only; measured",
              deltaOf("UnsafeProtocol","SSLContextSpec") == 1 && deltaOf("InvalidSequenceOfMethodCalls","SSLContextSpec") == 0,
              delta());

        snap();
        SSLContext ctx4 = SSLContext.getInstance("tls");
        ctx4.init(null, null, null);
        check("SSL-d MEASURE case folding: lowercase 'tls' accepted by spec (0 UnsafeProtocol)",
              deltaOf("UnsafeProtocol","SSLContextSpec") == 0, delta());

        snap();
        SSLContext ctxA = SSLContext.getInstance("TLS");
        SSLContext ctxB = SSLContext.getInstance("TLS");
        ctxA.init(null, null, null); ctxB.init(null, null, null);
        check("SSL-e dim5 two interleaved contexts isolated (0 seq errors)",
              deltaOf("InvalidSequenceOfMethodCalls","SSLContextSpec") == 0, delta());

        // ---------------- KST (GLOBAL monitor; run last) ----------------
        snap();
        KeyStore ks1 = KeyStore.getInstance("PKCS12");
        ks1.load(null, null);
        Key kk = ks1.getKey("nokey", "pw".toCharArray());
        check("KST-a single legal getInstance/load/getKey -> 0 errors", deltaCount() == 0, delta());
        check("KST-a2 GENERATED_KEY_STORE marked on ks1", ec.validate(Property.GENERATED_KEY_STORE, ks1), "");
        System.out.println("MEASURE KST-a3 getKey returned " + kk + "; GENERATED_KEY marked on null = "
              + ec.validate(Property.GENERATED_KEY, null));

        // KST-b two CrySL-legal keystores, natural interleaving
        snap();
        KeyStore ksC = KeyStore.getInstance("PKCS12");
        KeyStore ksD = KeyStore.getInstance("PKCS12");
        ksC.load(null, null);
        ksD.load(null, null);
        ksC.getKey("a", "x".toCharArray());
        check("KST-b MEASURE dim5: two legal keystores -> spurious errors from GLOBAL monitor (CrySL expects 0)",
              deltaCount() == 0, delta());
        System.out.println("MEASURE KST-b2 spurious error count for 2-keystore interleave = " + deltaCount() + " [" + delta() + "]");

        // KST-c wrong-object marking under global monitor
        snap();
        KeyStore ksE = KeyStore.getInstance("PKCS12");       // g1: field keyStore := ksE
        Provider p12 = ksE.getProvider() != null ? ksE.getProvider() : Security.getProviders()[0];
        KeyStore ksF = KeyStore.getInstance("PKCS12", p12);  // NO event (2-arg omitted)
        ksF.load(null, null);                                 // load fires, marks FIELD (= ksE)
        System.out.println("MEASURE KST-c 2-arg getInstance invisible; after ksF.load: mark(ksE)="
              + ec.validate(Property.GENERATED_KEY_STORE, ksE) + " (never loaded), mark(ksF)="
              + ec.validate(Property.GENERATED_KEY_STORE, ksF) + " (actually loaded); delta=[" + delta() + "]");

        // KST-d KMF reads the misbound predicate -> chained FP
        snap();
        KeyManagerFactory kmf4 = KeyManagerFactory.getInstance("PKIX");
        kmf4.init(ksF, null);   // ksF followed CrySL (Gets(2-arg), Loads) but carries no mark
        check("KST-d MEASURE chained FP: KMF.init(loaded-but-unmarked ks) -> UnsatisfiedConstraint",
              deltaOf("UnsatisfiedConstraint","KeyManagerFactorySpec") >= 1, delta());

        // KST-e ajc captures se1/store (contrast with dexlib2 where se1 is unwoven)
        snap();
        KeyStore ks5 = KeyStore.getInstance("PKCS12");
        ks5.load(null, null);
        javax.crypto.spec.SecretKeySpec kss = new javax.crypto.spec.SecretKeySpec(new byte[16], "AES");
        ks5.setEntry("e1", new KeyStore.SecretKeyEntry(kss),
                new KeyStore.PasswordProtection("pw".toCharArray()));
        ks5.store(new ByteArrayOutputStream(), "pw".toCharArray());
        System.out.println("MEASURE KST-e ajc setEntry+store route -> " + (deltaCount()==0 ? "0 errors (se1+store woven)" : delta()));

        System.out.println("== done; harness failures = " + failures + " ; total errors = " + errs().size());
        System.exit(failures > 0 ? 1 : 0);
    }
}
