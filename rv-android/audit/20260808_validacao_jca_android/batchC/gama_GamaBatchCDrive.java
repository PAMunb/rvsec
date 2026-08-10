package gama;

/*
 * GAMA batch C harness: drives the generated static event methods of the five
 * round monitors (KGN, KMF, TMF, SSL, KST) exactly as the generated advices do
 * (same call order as the merged monitorCalls in the *MonitorAspect.json:
 * g1 then g3 / g2 / unsafe_protocol on the shared getInstance joinpoint).
 * Each scenario MUST run in its own JVM (monitor maps are static; KST's monitor
 * is process-global). Real JDK objects; upstream predicate writers are simulated
 * via ExecutionContext.setProperty where a scenario needs isolation.
 */

import java.security.Key;
import java.security.KeyStore;
import java.security.SecureRandom;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import javax.net.ssl.KeyManager;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import mop.KeyGeneratorSpecRuntimeMonitor;
import mop.KeyManagerFactorySpecRuntimeMonitor;
import mop.KeyStoreSpecRuntimeMonitor;
import mop.SSLContextSpecRuntimeMonitor;
import mop.TrustManagerFactorySpecRuntimeMonitor;

public class GamaBatchCDrive {

    static void dump(String scenario) {
        System.out.println("== scenario " + scenario + ": " + ErrorCollector.instance().getErrors().size() + " record(s)");
        for (ErrorDescription e : ErrorCollector.instance().getErrors()) {
            System.out.println("   " + e);
        }
    }

    public static void main(String[] args) throws Exception {
        String s = args[0];
        // Real JDK objects.
        KeyGenerator kg = KeyGenerator.getInstance("AES");
        KeyStore ksA = KeyStore.getInstance(KeyStore.getDefaultType());
        KeyStore ksB = KeyStore.getInstance(KeyStore.getDefaultType());
        KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        SSLContext ctx = SSLContext.getInstance("TLS");
        SecureRandom rnd = new SecureRandom();
        KeyManager[] kms = new KeyManager[0];
        TrustManager[] tms = new TrustManager[0];
        SecretKey sk = new SecretKeySpec(new byte[16], "AES");
        Key key = sk;

        switch (s) {

        // ---------- TMF ----------
        case "tmf_a": {
            // H2 headline: unsafe algorithm ("X509" - MemorizingTrustManager route), then the
            // rule-conformant init and getTrustManagers. KeyStore pre-marked to isolate.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_STORE, ksA);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("X509", tmf);   // advice order:
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("X509", tmf);   // g1 then g3
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ksA, tmf);      // line L1
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(tmf, tms);    // line L2
            dump(s);
            break;
        }
        case "tmf_b": {
            // Control: fully conformant PKIX flow over a marked KeyStore.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_STORE, ksA);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", tmf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", tmf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ksA, tmf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(tmf, tms);
            dump(s);
            System.out.println("   validate(GENERATED_TRUST_MANAGERS, tms) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_TRUST_MANAGERS, tms));
            break;
        }
        case "tmf_c": {
            // Missed-creation route: init is the first observed event (e.g. factory obtained via
            // an unmatched getInstance route, or capture lost). Historical empty-label shape.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_STORE, ksA);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ksA, tmf);
            dump(s);
            break;
        }

        // ---------- KMF ----------
        case "kmf_a": {
            // "SunX509" was whitelisted in jca, removed in jca_android; the ORDER-conformant
            // init after it must not be InvalidSeq per the rule. KeyStore pre-marked.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_STORE, ksA);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("SunX509", kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("SunX509", kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ksA, "pw".toCharArray(), kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf, kms);
            dump(s);
            break;
        }
        case "kmf_b": {
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_STORE, ksA);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("PKIX", kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("PKIX", kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ksA, "pw".toCharArray(), kmf);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf, kms);
            dump(s);
            System.out.println("   validate(GENERATED_KEY_MANAGERS, kms) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY_MANAGERS, kms));
            break;
        }

        // ---------- SSL ----------
        case "ssl_a": {
            // Unsafe protocol then rule-conformant init/engine; all three REQUIRES pre-marked
            // to isolate the sequencing channel.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_MANAGERS, kms);
            ExecutionContext.instance().setProperty(Property.GENERATED_TRUST_MANAGERS, tms);
            ExecutionContext.instance().setProperty(Property.RANDOMIZED, rnd);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("SSLv3", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("SSLv3", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, rnd);
            dump(s);
            break;
        }
        case "ssl_b": {
            // Three REQUIRES violated at one init call: same (type, spec, __LOC) three times.
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, rnd);
            dump(s);
            break;
        }
        case "ssl_c": {
            // Invisible-creation route: getInstance(String, Provider) matches no event, so init
            // is the monitor's first event. Predicates pre-marked to isolate.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_MANAGERS, kms);
            ExecutionContext.instance().setProperty(Property.GENERATED_TRUST_MANAGERS, tms);
            ExecutionContext.instance().setProperty(Property.RANDOMIZED, rnd);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, rnd);
            dump(s);
            break;
        }
        case "ssl_d": {
            // Control: conformant TLS flow, marked predicates; then a second engine call
            // (monitor loops; driven directly - production capture of engine is a separate
            // question, see the createSSLEngine return-type finding).
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY_MANAGERS, kms);
            ExecutionContext.instance().setProperty(Property.GENERATED_TRUST_MANAGERS, tms);
            ExecutionContext.instance().setProperty(Property.RANDOMIZED, rnd);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, rnd);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_engineEvent(ctx, null);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_engineEvent(ctx, null);
            dump(s);
            break;
        }

        // ---------- KST ----------
        case "kst_a": {
            // Global-monitor interleaving: two distinct KeyStore objects created back to back,
            // each individually rule-conformant.
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", ksB);   // line LB
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", ksB);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksB);
            dump(s);
            break;
        }
        case "kst_b": {
            // Unsafe type ("JKS" outside the Android list): ORDER is rule-conformant, the type
            // constraint is the only violation.
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("JKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("JKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksA);   // line L1
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ksA, key); // line L2
            dump(s);
            break;
        }
        case "kst_c": {
            // Cross-object erasure: A completes a conformant Gets+Loads (marked); B's bogus
            // store() fails the GLOBAL monitor, whose @fail removes the mark of the LAST field
            // value - which is A's. Downstream TMF.init(A) then reports UnsatisfiedConstraint.
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksA);
            System.out.println("   after A load: validate(GENERATED_KEY_STORE, ksA) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY_STORE, ksA));
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_storeEvent(ksB);  // B misuse on the global monitor
            System.out.println("   after B store-fail: validate(GENERATED_KEY_STORE, ksA) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY_STORE, ksA));
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", tmf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", tmf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ksA, tmf);
            dump(s);
            break;
        }
        case "kst_d": {
            // Control: conformant single lifecycle.
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("BKS", ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ksA);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ksA, key);
            dump(s);
            System.out.println("   validate(GENERATED_KEY, key) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY, key));
            System.out.println("   validate(GENERATED_PRIVATE_KEY, key) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_PRIVATE_KEY, key));
            break;
        }

        // ---------- KGN ----------
        case "kgn_a": {
            // Unsafe algorithm; generateKey followed. Rule: constraint violation only.
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("DES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("DES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);  // line L1
            dump(s);
            break;
        }
        case "kgn_b": {
            // Control: conformant AES flow; also exercises the g1-then-g3 double-dispatch on
            // one joinpoint (g3's condition reads currentAlgorithmInstance, not the argument).
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(128, kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);
            dump(s);
            System.out.println("   validate(GENERATED_KEY, sk) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY, sk));
            break;
        }
        case "kgn_c": {
            // Spec-whitelisted, rule-forbidden algorithm (FN direction).
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("HMAC-SHA256", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("HMAC-SHA256", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);
            dump(s);
            break;
        }
        case "kgn_d": {
            // AES with keySize 64: rule constraint keySize in {128,192,256} violated.
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(64, kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);
            dump(s);
            break;
        }
        case "kgn_e": {
            // Unrandomized SecureRandom at init (the rule's REQUIRES randomized[ranGen]):
            // must be one specific record and NO InvalidSeq (body-read repair holds).
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i2Event(128, rnd, kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);
            dump(s);
            break;
        }
        default:
            throw new IllegalArgumentException(s);
        }
    }
}
