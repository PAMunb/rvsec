// Batch C / Agent ALFA — JVM drive over the round monitors with production jars.
// Style of batch A/B agents: the static *Event methods of the generated
// RuntimeMonitor classes are called in exactly the sequence the generated
// MonitorAspect.aj advices emit for each simulated Java call
// (merged advices reproduced: g1Event;g3Event etc.). Deterministic; 3 reps
// run by the shell wrapper; ExecutionContext+ErrorCollector reset per trace.
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.*;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.net.ssl.*;
import java.security.KeyStore;
import java.security.Key;
import java.security.SecureRandom;
import java.util.*;

public class AlfaHarnessC {
    static int shown = 0;

    static void snap(String label) {
        Set<ErrorDescription> errs = ErrorCollector.instance().getErrors();
        System.out.println("  [" + label + "] errors=" + errs.size());
        List<String> lines = new ArrayList<>();
        for (ErrorDescription e : errs) lines.add("    " + e.getErrorSummary() + " | expecting=" + e.getExpecting());
        Collections.sort(lines);
        for (String l : lines) System.out.println(l);
    }

    static void fresh(String name) {
        ErrorCollector.instance().reset();
        ExecutionContext.instance().reset();
        System.out.println("== " + name + " ==");
    }

    // ---- simulated call classes (each block = what the woven advice does) ----
    // KGN: aspect line 66-72 merges g1+g3 in ONE advice: g1Event then g3Event.
    static KeyGenerator kgnGet1(String alg) throws Exception {
        KeyGenerator k = KeyGenerator.getInstance("AES"); // real object, identity carrier
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event(alg, k);
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event(alg, k);
        return k;
    }
    static KeyGenerator kgnGet2(String alg, Object prov) throws Exception {
        KeyGenerator k = KeyGenerator.getInstance("AES");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g2Event(alg, prov, k); // sole advice
        return k;
    }

    static KeyManagerFactory kmfGet1(String alg) throws Exception {
        KeyManagerFactory k = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event(alg, k);
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event(alg, k);
        return k;
    }
    static TrustManagerFactory tmfGet1(String alg) throws Exception {
        TrustManagerFactory t = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event(alg, t);
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event(alg, t);
        return t;
    }
    static SSLContext sslGet1(String proto) throws Exception {
        SSLContext c = SSLContext.getInstance("TLS");
        SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event(proto, c);
        SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent(proto, c);
        return c;
    }
    static KeyStore kstGet1(String type) throws Exception {
        KeyStore ks = KeyStore.getInstance(KeyStore.getDefaultType());
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event(type, ks);
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event(type, ks);
        return ks;
    }

    public static void main(String[] a) throws Exception {
        // ---------------- KGN ----------------
        fresh("KGN-T1 happy: getInstance(\"AES\"); init(128); generateKey()");
        KeyGenerator k1 = kgnGet1("AES");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(128, k1);
        SecretKey sk1 = k1.generateKey() instanceof SecretKey ? (SecretKey) null : null;
        // use a real SecretKey object for identity checks:
        k1.init(128); SecretKey realKey = k1.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k1, realKey);
        snap("end");
        System.out.println("  GENERATED_KEY(realKey)=" + ExecutionContext.instance().validate(Property.GENERATED_KEY, realKey)
            + " accepting(k1)=" + ExecutionContext.instance().isInAcceptingState(k1));

        fresh("KGN-T2 FP: getInstance(\"DES\") [unsafe carrier]; init(56); generateKey() — rule-conformant ORDER");
        KeyGenerator k2 = kgnGet1("DES");
        snap("after getInstance");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(56, k2);
        snap("after init");
        k2.init(128); SecretKey rk2 = k2.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k2, rk2);
        snap("after generateKey");

        fresh("KGN-T3 FP: getInstance(\"DES\", provider) [2-arg unsafe: NO mop event]; init; generateKey");
        KeyGenerator k3 = kgnGet2("DES", "SomeProvider");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(56, k3);
        snap("after init");
        k3.init(128); SecretKey rk3 = k3.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k3, rk3);
        snap("after generateKey");

        fresh("KGN-T4 Inits? optional: getInstance(\"AES\"); generateKey()");
        KeyGenerator k4 = kgnGet1("AES");
        k4.init(128); SecretKey rk4 = k4.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k4, rk4);
        snap("end");

        fresh("KGN-T5 FN keySize constraint: getInstance(\"AES\"); init(64); generateKey() — alg in {AES} => keySize in {128,192,256} violated");
        KeyGenerator k5 = kgnGet1("AES");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(64, k5);
        k5.init(128); SecretKey rk5 = k5.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k5, rk5);
        snap("end (expect ZERO errors = FN vs CONSTRAINT 2)");

        fresh("KGN-T6 interleaving/isolation: k6a safe vs k6b unsafe");
        KeyGenerator k6a = kgnGet1("AES");
        KeyGenerator k6b = kgnGet1("DES");
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(128, k6a);
        k6a.init(128); SecretKey rk6 = k6a.generateKey();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(k6a, rk6);
        snap("k6a completed (errors here belong to k6b's monitor only if contaminated: expect 0)");
        System.out.println("  accepting(k6a)=" + ExecutionContext.instance().isInAcceptingState(k6a));

        fresh("KGN-T7 randomized read: init(int, new SecureRandom()) with unmarked SecureRandom");
        KeyGenerator k7 = kgnGet1("AES");
        SecureRandom srUnmarked = new SecureRandom();
        KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i2Event(128, srUnmarked, k7);
        snap("after init (expect UnsatisfiedConstraint: randomized[ranGen] is bound in rule => faithful read)");

        // ---------------- TLS chain (KST -> KMF/TMF -> SSL) ----------------
        fresh("CHAIN-T1 fully monitored happy chain + unmarked SecureRandom at SSLContext.init");
        KeyStore ks = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ks);
        System.out.println("  GENERATED_KEY_STORE(ks)=" + ExecutionContext.instance().validate(Property.GENERATED_KEY_STORE, ks));
        KeyManagerFactory kmf = kmfGet1("PKIX");
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks, "pw".toCharArray(), kmf);
        KeyManager[] kms = new KeyManager[0];
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf, kms);
        TrustManagerFactory tmf = tmfGet1("PKIX");
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ks, tmf);
        TrustManager[] tms = new TrustManager[0];
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(tmf, tms);
        SSLContext ctx = sslGet1("TLS");
        SecureRandom sr = new SecureRandom();
        SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, sr);
        snap("end (expect EXACTLY ONE UnsatisfiedConstraint: the randomized read — extra-oracle: rule binds `_`, not sr)");
        System.out.println("  accepting: kmf=" + ExecutionContext.instance().isInAcceptingState(kmf)
            + " tmf=" + ExecutionContext.instance().isInAcceptingState(tmf)
            + " ctx=" + ExecutionContext.instance().isInAcceptingState(ctx));
        System.out.println("  GENERATE_SSL_CONTEXT(ctx)=" + ExecutionContext.instance().validate(Property.GENERATE_SSL_CONTEXT, ctx));

        fresh("CHAIN-T2 rule-conformant 2-arg KeyStore.getInstance (NO mop event) -> FP cascade");
        KeyStore ks2 = KeyStore.getInstance(KeyStore.getDefaultType()); // simulates getInstance("PKCS12","BC"): no event exists
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ks2);
        snap("after load (expect InvalidSequenceOfMethodCalls FP)");
        System.out.println("  GENERATED_KEY_STORE(ks2)=" + ExecutionContext.instance().validate(Property.GENERATED_KEY_STORE, ks2));
        KeyManagerFactory kmf2 = kmfGet1("PKIX");
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks2, "pw".toCharArray(), kmf2);
        snap("after kmf.init (expect + UnsatisfiedConstraint FP: generatedKeyStore starved)");

        fresh("CHAIN-T3 second getKeyManagers(): raw-rule violation, but remove-cascade poisons SSL");
        KeyStore ks3 = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ks3);
        KeyManagerFactory kmf3 = kmfGet1("PKIX");
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks3, "pw".toCharArray(), kmf3);
        KeyManager[] kms3 = new KeyManager[0];
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf3, kms3);
        System.out.println("  after gkm#1: GENERATED_KEY_MANAGERS(kms3)=" + ExecutionContext.instance().validate(Property.GENERATED_KEY_MANAGERS, kms3));
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf3, kms3); // second call
        snap("after gkm#2 (sequence error itself is raw-consistent)");
        System.out.println("  after gkm#2: GENERATED_KEY_MANAGERS(kms3)=" + ExecutionContext.instance().validate(Property.GENERATED_KEY_MANAGERS, kms3)
            + "  <- mark revoked although ENSURES was already granted (no NEGATES in rule)");
        SSLContext ctx3 = sslGet1("TLS");
        SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx3, kms3, new TrustManager[0], null);
        snap("after ssl.init (UnsatisfiedConstraint on km = downstream FP; tm unmarked too here)");

        // ---------------- KMF / TMF ----------------
        fresh("KMF-T1 FP: getInstance(\"SunX509\"); init(ks,pw) — rule-conformant ORDER (constraint-only violation)");
        KeyStore ksK = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksK);
        KeyManagerFactory kmfU = kmfGet1("SunX509");
        snap("after getInstance (carrier: expect 0 sequence errors)");
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ksK, "pw".toCharArray(), kmfU);
        snap("after init (expect UnsafeAlgorithm + SPURIOUS InvalidSequenceOfMethodCalls)");
        KeyManager[] kmsU = new KeyManager[0];
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmfU, kmsU);
        snap("after getKeyManagers (expect a second InvalidSequence)");

        fresh("KMF-T2 acceptance end: g1 i1 gkm1 — CrySL-complete word");
        KeyStore ksA = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksA);
        KeyManagerFactory kmfA = kmfGet1("PKIX");
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ksA, "pw".toCharArray(), kmfA);
        System.out.println("  accepting after init=" + ExecutionContext.instance().isInAcceptingState(kmfA));
        KeyManager[] kmsA = new KeyManager[0];
        KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmfA, kmsA);
        System.out.println("  accepting after gkm1=" + ExecutionContext.instance().isInAcceptingState(kmfA)
            + " (monitor state left at 0 = start; mark persists only because gkm1 has no handler)");
        snap("end (expect 0 errors)");

        fresh("TMF-T1 FP: getInstance(\"X509\"); init(ks) — the campaign shape (frozen_set_debt: 8371 UnsafeAlgorithm events)");
        KeyStore ksT = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksT);
        TrustManagerFactory tmfU = tmfGet1("X509");
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ksT, tmfU);
        snap("after init (expect UnsafeAlgorithm + SPURIOUS InvalidSequence)");
        TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(tmfU, new TrustManager[0]);
        snap("after getTrustManagers (expect second InvalidSequence)");

        // ---------------- SSL ----------------
        fresh("SSL-T1 FP + null-write: getInstance(\"SSLv3\"-like unsafe); init(km,tm,null)");
        SSLContext ctxU = sslGet1("NOPROTO");
        snap("after getInstance (carrier: expect 0)");
        SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctxU, null, null, null);
        snap("after init (expect UnsafeProtocol + SPURIOUS InvalidSequence; null guards suppress the 3 reads)");
        System.out.println("  GENERATE_SSL_CONTEXT set for null (field never assigned): validate(P,null)=" +
            ExecutionContext.instance().validate(Property.GENERATE_SSL_CONTEXT, null));

        fresh("SSL-T2 engine channel: after init, createSSLEngine leaves no trace (pointcut declares void return)");
        SSLContext ctx2 = sslGet1("TLS");
        ctx2.init(null, null, null); // real init so the real createSSLEngine below succeeds
        SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx2, null, null, null);
        // No engineEvent call possible from weaving: call(public void SSLContext.createSSLEngine(..))
        // cannot match a method whose declared return type is SSLEngine (javap check in report).
        SSLEngine engReal = ctx2.createSSLEngine();
        snap("after real createSSLEngine (no event by construction)");
        System.out.println("  GENERATE_SSL_ENGINE(engReal)=" + ExecutionContext.instance().validate(Property.GENERATE_SSL_ENGINE, engReal)
            + " (ENSURES generatedSSLEngine[eng] never establishable)");

        // ---------------- KST ----------------
        fresh("KST-T1 happy: getInstance(\"PKCS12\"); load; getEntry; getKey");
        KeyStore ksH = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksH);
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_ge1Event(ksH);
        Key someKey = null;
        try { someKey = javax.crypto.KeyGenerator.getInstance("AES").generateKey(); } catch (Exception e) {}
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ksH, someKey);
        snap("end (expect 0)");
        System.out.println("  GENERATED_KEY=" + ExecutionContext.instance().validate(Property.GENERATED_KEY, someKey)
            + " GENERATED_PRIVATE_KEY=" + ExecutionContext.instance().validate(Property.GENERATED_PRIVATE_KEY, someKey)
            + " GENERATED_PUBLIC_KEY=" + ExecutionContext.instance().validate(Property.GENERATED_PUBLIC_KEY, someKey));

        fresh("KST-T2 FP: unsafe type carrier getInstance(\"JKS\"); load — rule flags CONSTRAINT only");
        KeyStore ksJ = kstGet1("JKS");
        snap("after getInstance (expect 0)");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksJ);
        snap("after load (expect SPURIOUS InvalidSequence)");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ksJ, someKey);
        snap("after getKey (expect InvalidKeyStoreType + another InvalidSequence)");

        fresh("KST-T3 FN: getInstance(\"PKCS12\"); load; setCertificateEntry [declared CrySL event scE, no pointcut]; getKey");
        KeyStore ksC = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksC);
        // setCertificateEntry: no MOP event exists — nothing to call
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ksC, someKey);
        snap("end (expect ZERO errors = FN: scE is a typestate violation of the raw ORDER)");

        fresh("KST-T4 store without setEntry: g1 load store — raw rule forbids, monitor should also flag (consistency check)");
        KeyStore ksS = kstGet1("PKCS12");
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksS);
        KeyStoreSpecRuntimeMonitor.KeyStoreSpec_storeEvent(ksS);
        snap("end (expect InvalidSequence — CONSISTENT with raw oracle)");

        System.out.println("\nDONE");
    }
}
