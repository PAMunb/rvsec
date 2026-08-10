// JuizDriveC — batch C judge drive (J2-C).
// Compiles the five ROUND monitors (KGN patched with exactly one import line,
// documented) against the production jars and drives the generated static event
// methods in the advice order verified from the frozen descriptors
// (g1 before g3/g2/unsafe_protocol on shared pointcuts). Class sits OUTSIDE
// package mop so __LOC resolves to this file's lines.
// Scenarios S1..S18 — see juiz_sintese_batchC.md §0.
import mop.*;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.net.ssl.*;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.util.*;

public class JuizDriveC {

    static Set<String> seen = new HashSet<>();

    static List<String> drain() {
        List<String> fresh = new ArrayList<>();
        for (ErrorDescription e : ErrorCollector.instance().getErrors()) {
            String s = e.getErrorSummary() + " | expecting=" + e.getExpecting();
            if (seen.add(s)) fresh.add(s);
        }
        Collections.sort(fresh);
        return fresh;
    }

    static void show(String tag, List<String> recs) {
        System.out.println("== " + tag + " : " + recs.size() + " record(s)");
        for (String r : recs) System.out.println("   " + r);
    }

    static boolean val(Property p, Object o) { return ExecutionContext.instance().validate(p, o); }

    public static void main(String[] a) throws Exception {
        ExecutionContext ec = ExecutionContext.instance();

        // ---------------- S1: TMF carrier pairing (getInstance("X509"), init, getTrustManagers)
        {
            TrustManagerFactory mf = TrustManagerFactory.getInstance("X509");
            KeyStore ks = KeyStore.getInstance("PKCS12"); // raw object; mark directly to isolate TMF
            ec.setProperty(Property.GENERATED_KEY_STORE, ks);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("X509", mf); // cond false -> suppressed
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("X509", mf); // fires
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ks, mf);     // body: UnsafeAlgorithm; transition: fail
            List<String> afterI1 = drain();
            show("S1a TMF i1 (rule-ORDER-conformant trace, constraint-only misuse)", afterI1);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(mf, new TrustManager[0]);
            show("S1b TMF gtm1 after __RESET (delayed residue at the rule's own gtm?)", drain());
        }

        // ---------------- S2: KMF carrier pairing
        {
            KeyManagerFactory k = KeyManagerFactory.getInstance("SunX509");
            KeyStore ks = KeyStore.getInstance("PKCS12");
            ec.setProperty(Property.GENERATED_KEY_STORE, ks);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("SunX509", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("SunX509", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks, "pw".toCharArray(), k);
            show("S2a KMF i1", drain());
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(k, new KeyManager[0]);
            show("S2b KMF gkm1 after __RESET", drain());
        }

        // ---------------- S3: SSL carrier pairing
        {
            SSLContext ctx = SSLContext.getInstance("TLS"); // object identity only; protocol string emulated
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("SSLv3", ctx);              // cond false
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("SSLv3", ctx); // fires
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, null, null, null);
            show("S3 SSL init after unsafe_protocol (UnsafeProtocol + spurious InvalidSeq, same call)", drain());
        }

        // ---------------- S4: KGN carrier pairing
        {
            KeyGenerator kg = KeyGenerator.getInstance("DES");
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("DES", kg); // cond false
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("DES", kg); // fires
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(56, kg);
            show("S4a KGN i1 (spurious InvalidSeq)", drain());
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, kg.generateKey());
            show("S4b KGN gk1 (UnsafeAlgorithm + second spurious InvalidSeq, same call)", drain());
        }

        // ---------------- S5: KST unsafe-type pairing
        {
            KeyStore ks = KeyStore.getInstance("JKS");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("JKS", ks); // cond false
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("JKS", ks); // fires
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ks);
            show("S5a KST load (spurious InvalidSeq; rule ORDER satisfied)", drain());
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(ks, null);
            show("S5b KST getKey (InvalidKeyStoreType + spurious InvalidSeq)", drain());
        }

        // ---------------- S6: KST global monitor — two conformant interleaved stores
        {
            ec.remove(Property.GENERATED_KEY_STORE, null); // hygiene
            KeyStore A = KeyStore.getInstance("PKCS12");
            KeyStore B = KeyStore.getInstance("PKCS12");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", B);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", B);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(A);
            System.out.println("S6 after load(A): validate(GKS,A)=" + val(Property.GENERATED_KEY_STORE, A)
                    + " validate(GKS,B)=" + val(Property.GENERATED_KEY_STORE, B) + "  <- wrong-object identity (field, not receiver)");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(B);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(A, null);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_gk1Event(B, null);
            show("S6 KST two individually conformant interleaved stores (all records spurious)", drain());
        }

        // ---------------- S7: KST cross-object erasure -> TMF chain FP
        {
            KeyStore A = KeyStore.getInstance("PKCS12");
            KeyStore B = KeyStore.getInstance("PKCS12");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(A);
            System.out.println("S7 A loaded: validate(GKS,A)=" + val(Property.GENERATED_KEY_STORE, A));
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_storeEvent(B); // B's own violation, global monitor
            System.out.println("S7 after B's store: validate(GKS,A)=" + val(Property.GENERATED_KEY_STORE, A)
                    + "  <- A's granted ENSURES erased by B's @fail (shared field)");
            show("S7a records from B's store", drain());
            TrustManagerFactory mf = TrustManagerFactory.getInstance("PKIX");
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", mf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", mf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(A, mf);
            show("S7b fully conformant TMF over A -> chained UnsatisfiedConstraint (FP)", drain());
        }

        // ---------------- S8: KST 2-arg getInstance omission -> displaced chain FP
        {
            java.security.Provider p = KeyStore.getInstance("PKCS12").getProvider();
            KeyStore ks2 = KeyStore.getInstance("PKCS12", p); // rule-conformant g2; NO spec event exists
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ks2); // first event -> creation at start
            System.out.println("S8 after load(ks2): validate(GKS,ks2)=" + val(Property.GENERATED_KEY_STORE, ks2)
                    + "  <- real store never marked (stale field marked instead)");
            show("S8a KST load on 2-arg-created store (spurious InvalidSeq)", drain());
            KeyManagerFactory k = KeyManagerFactory.getInstance("PKIX");
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("PKIX", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("PKIX", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks2, "pw".toCharArray(), k);
            show("S8b conformant KMF over ks2 -> displaced UnsatisfiedConstraint (FP)", drain());
        }

        // ---------------- S9: KST Entries omission — skE1 unobserved, store accused (displaced)
        {
            KeyStore A = KeyStore.getInstance("PKCS12");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(A);
            // app calls setKeyEntry(alias, key, pw, chain) here -> rule event skE1; spec has NO event: silence
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_storeEvent(A);
            show("S9a KST load,[setKeyEntry unobserved],store -> accusation lands displaced at store", drain());
            // control: the captured sE route
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_se1Event(A);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_storeEvent(A);
            show("S9b control: load,setEntry(captured),store -> clean", drain());
        }

        // ---------------- S10: KMF remove cascade -> SSL chain FP (zero NEGATES in the rules)
        {
            KeyStore ks = KeyStore.getInstance("PKCS12");
            ec.setProperty(Property.GENERATED_KEY_STORE, ks);
            KeyManagerFactory k = KeyManagerFactory.getInstance("PKIX");
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("PKIX", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("PKIX", k);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ks, "pw".toCharArray(), k);
            KeyManager[] kms1 = new KeyManager[1];
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(k, kms1);
            System.out.println("S10 kms1 granted: validate(GKMS,kms1)=" + val(Property.GENERATED_KEY_MANAGERS, kms1));
            KeyManager[] kms2 = new KeyManager[1];
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(k, kms2); // 2nd gkm -> genuine ORDER violation
            System.out.println("S10 after gkm#2 fail: validate(GKMS,kms2)=" + val(Property.GENERATED_KEY_MANAGERS, kms2)
                    + " validate(GKMS,kms1)=" + val(Property.GENERATED_KEY_MANAGERS, kms1)
                    + "  <- handed-out kms2 revoked though the rules carry zero NEGATES");
            show("S10a records at gkm#2 (true positive)", drain());
            SSLContext ctx = SSLContext.getInstance("TLS");
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms2, null, null);
            show("S10b SSL init(kms2) -> chained UnsatisfiedConstraint (FP: granted ENSURES revoked)", drain());
        }

        // ---------------- S11: TMF twin (closes the symmetry single-route of ALFA-TMF-07)
        {
            KeyStore ks = KeyStore.getInstance("PKCS12");
            ec.setProperty(Property.GENERATED_KEY_STORE, ks);
            TrustManagerFactory mf = TrustManagerFactory.getInstance("PKIX");
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", mf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", mf);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ks, mf);
            TrustManager[] tms1 = new TrustManager[1];
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(mf, tms1);
            TrustManager[] tms2 = new TrustManager[1];
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(mf, tms2);
            System.out.println("S11 validate(GTMS,tms2)=" + val(Property.GENERATED_TRUST_MANAGERS, tms2)
                    + " validate(GTMS,tms1)=" + val(Property.GENERATED_TRUST_MANAGERS, tms1));
            show("S11a records at gtm#2", drain());
            SSLContext ctx = SSLContext.getInstance("TLS");
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, null, tms2, null);
            show("S11b SSL init(tms2) -> chained UnsatisfiedConstraint (FP)", drain());
        }

        // ---------------- S12: SSL randomized read — rule binds `_`, sr unbound (extra-oracle)
        {
            KeyManager[] kms = new KeyManager[1];
            TrustManager[] tms = new TrustManager[1];
            ec.setProperty(Property.GENERATED_KEY_MANAGERS, kms);
            ec.setProperty(Property.GENERATED_TRUST_MANAGERS, tms);
            SSLContext ctx = SSLContext.getInstance("TLS");
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, kms, tms, new SecureRandom());
            show("S12 SSL fully conformant init with fresh SecureRandom (extra-oracle randomized FP)", drain());
        }

        // ---------------- S13: SSL 3-clause dedupe collapse at one __LOC
        {
            SSLContext ctx = SSLContext.getInstance("TLS");
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", ctx);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, new KeyManager[1], new TrustManager[1], new SecureRandom());
            show("S13 three REQUIRES violated at one init call -> records surviving dedupe", drain());
        }

        // ---------------- S14: SSL (String, Provider) overload invisible -> conformant trace accused
        {
            SSLContext tmp = SSLContext.getInstance("TLS");
            SSLContext ctx = SSLContext.getInstance("TLS", tmp.getProvider()); // real conformant creation; NO event matches
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, null, null, null); // first event -> creation at start
            show("S14 SSL getInstance(String,Provider)+init (fully conformant) -> empty-label UnsafeProtocol + InvalidSeq", drain());
        }

        // ---------------- S15: SSL folding FN + Engine? cardinality FN
        {
            SSLContext ctx = SSLContext.getInstance("tls"); // resolves case-insensitively on the JCA
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("tls", ctx);             // toUpperCase -> accepted
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("tls", ctx); // cond false
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(ctx, null, null, null);
            List<String> r15 = drain();
            show("S15a getInstance(\"tls\") — raw literal set rejects, spec accepts (FN if empty)", r15);
            ctx.init(null, null, null); // real platform init so createSSLEngine is legal
            SSLEngine e1 = ctx.createSSLEngine();
            SSLEngine e2 = ctx.createSSLEngine();
            SSLContextSpecRuntimeMonitor.SSLContextSpec_engineEvent(ctx, e1);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_engineEvent(ctx, e2); // rule: Engine? at most once
            show("S15b second createSSLEngine (ORDER violation) — silent = FN", drain());
        }

        // ---------------- S16: KGN keySize constraint omitted (executed FN)
        {
            KeyGenerator kg = KeyGenerator.getInstance("AES");
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(64, kg); // rule: AES => keySize in {128,192,256}
            show("S16 KGN AES init(64) — silent = FN of the keySize implication", drain());
        }

        // ---------------- S17: KGN HMAC alias accepted (executed FN vs raw 11-literal list)
        {
            KeyGenerator kg = KeyGenerator.getInstance("AES"); // object identity only; alias string emulated
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("HMAC-SHA256", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("HMAC-SHA256", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, null);
            show("S17 KGN getInstance(\"HMAC-SHA256\") + generateKey — silent = FN vs raw oracle", drain());
        }

        // ---------------- S18: positive controls
        {
            // (a) KGN conformant
            KeyGenerator kg = KeyGenerator.getInstance("AES");
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i1Event(128, kg);
            SecretKey sk = kg.generateKey();
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, sk);
            System.out.println("S18a KGN conformant: validate(GENERATED_KEY, sk)=" + val(Property.GENERATED_KEY, sk));
            show("S18a KGN conformant lifecycle", drain());
            // (b) KGN unrandomized SecureRandom at i2 -> exactly one specific error, no spurious fail
            KeyGenerator kg2 = KeyGenerator.getInstance("AES");
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event("AES", kg2);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event("AES", kg2);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_i2Event(128, new SecureRandom(), kg2);
            KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_gk1Event(kg2, kg2.generateKey());
            show("S18b KGN i2 with unmarked SecureRandom (expect 1 UnsatisfiedConstraint, 0 InvalidSeq)", drain());
            // (c) TMF conformant + two-factory isolation of the 2-arg remove
            KeyStore ks = KeyStore.getInstance("PKCS12");
            ec.setProperty(Property.GENERATED_KEY_STORE, ks);
            TrustManagerFactory t1 = TrustManagerFactory.getInstance("PKIX");
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", t1);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", t1);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ks, t1);
            TrustManager[] tA = new TrustManager[1];
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(t1, tA);
            TrustManagerFactory t2 = TrustManagerFactory.getInstance("PKIX");
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", t2);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", t2);
            TrustManager[] tB = new TrustManager[1];
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(t2, tB); // t2: gtm without init -> its own fail
            System.out.println("S18c isolation: validate(GTMS,tA)=" + val(Property.GENERATED_TRUST_MANAGERS, tA)
                    + " (t1's grant survives t2's fail) validate(GTMS,tB)=" + val(Property.GENERATED_TRUST_MANAGERS, tB));
            show("S18c t2 records (true positive, self-scoped)", drain());
            // (d) full conformant chain KST -> KMF -> SSL (sr null: guard skips)
            KeyStore ck = KeyStore.getInstance("PKCS12");
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", ck);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", ck);
            KeyStoreSpecRuntimeMonitor.KeyStoreSpec_loadEvent(ck);
            KeyManagerFactory ckm = KeyManagerFactory.getInstance("PKIX");
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g1Event("PKIX", ckm);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_g3Event("PKIX", ckm);
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_i1Event(ck, "pw".toCharArray(), ckm);
            KeyManager[] ckms = new KeyManager[1];
            KeyManagerFactorySpecRuntimeMonitor.KeyManagerFactorySpec_gkm1Event(ckm, ckms);
            TrustManagerFactory ctm = TrustManagerFactory.getInstance("PKIX");
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g1Event("PKIX", ctm);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_g3Event("PKIX", ctm);
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_i1Event(ck, ctm);
            TrustManager[] ctms = new TrustManager[1];
            TrustManagerFactorySpecRuntimeMonitor.TrustManagerFactorySpec_gtm1Event(ctm, ctms);
            SSLContext cs = SSLContext.getInstance("TLS");
            SSLContextSpecRuntimeMonitor.SSLContextSpec_g1Event("TLS", cs);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLS", cs);
            SSLContextSpecRuntimeMonitor.SSLContextSpec_initEvent(cs, ckms, ctms, null);
            show("S18d full captured TLS chain, sr=null (expect 0 records)", drain());
        }
        System.out.println("DONE");
    }
}
