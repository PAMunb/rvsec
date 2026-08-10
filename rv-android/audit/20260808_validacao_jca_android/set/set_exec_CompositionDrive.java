// EXEC-SET composition drive (protocol section 19.5, G7 set half).
// Drives the MERGED MultiSpec_1RuntimeMonitor static event methods exactly as the
// merged descriptor's advices emit them for real production-woven calls (advice ->
// monitorCalls order taken from MultiSpec_1MonitorAspect.json; only events whose
// pointcut the production dexlib2 weave actually captures are emitted -- dead
// pointcuts (SIG sign, SSL createSSLEngine, SRD nextInt()/ints) emit nothing, as
// measured by the set weave probe). Real JDK objects; JVM (not ART) -- declared threat.
// Chains: S1 SRD->RANDOMIZED->SKSS/PBK; S2 KGN->GENERATED_KEY->MAC/SKY;
// S3 KPG->generatedKeyPair->KPR->SIG; S4 KST->GENERATED_KEY_STORE->KMF/TMF->SSL;
// S5 KPG NPE (crash class) -- last, since it throws.
// 3 reps must be byte-identical (no identity hashes or raw toString printed).
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.MultiSpec_1RuntimeMonitor;

import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import javax.net.ssl.*;
import java.lang.reflect.Field;
import java.security.*;
import java.util.*;
import java.util.stream.Collectors;

public class SetExecCompositionDrive {
    static Set<ErrorDescription> seen = new HashSet<>();
    static final IdentityHashMap<Object, String> LABELS = new IdentityHashMap<>();
    static void label(Object o, String s) { LABELS.put(o, s); }

    static void delta(String step) {
        Set<ErrorDescription> now = new HashSet<>(ErrorCollector.instance().getErrors());
        List<String> fresh = now.stream().filter(e -> !seen.contains(e))
                .map(e -> e.getType() + "/" + e.getSpec() + " expecting=" + e.getExpecting())
                .sorted().collect(Collectors.toList());
        seen = now;
        System.out.println("  DELTA " + step + " (" + fresh.size() + "): " + fresh);
    }

    @SuppressWarnings("unchecked")
    static void store(String step) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();
        Field fc = ExecutionContext.class.getDeclaredField("context"); fc.setAccessible(true);
        Field fa = ExecutionContext.class.getDeclaredField("acceptingState"); fa.setAccessible(true);
        Map<Property, Set<Object>> c = (Map<Property, Set<Object>>) fc.get(ctx);
        Set<Object> acc = (Set<Object>) fa.get(ctx);
        List<String> rows = new ArrayList<>();
        for (Map.Entry<Property, Set<Object>> e : c.entrySet()) {
            List<String> objs = new ArrayList<>();
            for (Object o : e.getValue())
                objs.add(LABELS.containsKey(o) ? LABELS.get(o)
                        : "?" + (o == null ? "null" : o.getClass().getSimpleName()));
            Collections.sort(objs);
            rows.add(e.getKey() + "=" + objs);
        }
        Collections.sort(rows);
        List<String> accL = new ArrayList<>();
        for (Object o : acc) if (LABELS.containsKey(o)) accL.add(LABELS.get(o));
        Collections.sort(accL);
        System.out.println("  STORE " + step + ": " + rows);
        System.out.println("  ACCEPTING(labeled) " + step + ": " + accL);
    }

    public static void main(String[] args) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();

        System.out.println("== S1: SRD -> RANDOMIZED -> SKSS/PBK (object vs material split, writer->reader end to end) ==");
        SecureRandom r1 = new SecureRandom(); label(r1, "r1(safe:new)");
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_c1Event(r1);
        byte[] salt = new byte[16]; label(salt, "salt<-r1");
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_next2Event(r1, salt); // before advice
        r1.nextBytes(salt);
        byte[] km1 = new byte[32]; label(km1, "km1<-r1");
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_next2Event(r1, km1);
        r1.nextBytes(km1);
        delta("S1a srd-safe"); store("S1a");
        System.out.println("  RANDOMIZED[r1]=" + ctx.validate(Property.RANDOMIZED, r1)
                + " RANDOMIZED[salt]=" + ctx.validate(Property.RANDOMIZED, salt)
                + " RANDOMIZED[km1]=" + ctx.validate(Property.RANDOMIZED, km1));

        // S1b: reader SKSS over randomized material (real ctor emits c1;c3 in advice order)
        SecretKeySpec sks1 = new SecretKeySpec(km1, "AES"); label(sks1, "sks1(km1,AES)");
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event(km1, "AES", sks1);
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c3Event(km1, "AES", sks1);
        delta("S1b skss-randomized-material"); store("S1b");
        System.out.println("  SPECCED_KEY[sks1]=" + ctx.validate(Property.SPECCED_KEY, sks1)
                + " GENERATED_KEY[sks1]=" + ctx.validate(Property.GENERATED_KEY, sks1));

        // S1c: REJECTED randomness route: unsafe alg instance, its bytes still satisfy readers
        SecureRandom r2 = SecureRandom.getInstance("NativePRNG"); label(r2, "r2(unsafe:NativePRNG)");
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_g1Event("NativePRNG", r2);
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_g4Event("NativePRNG", r2);
        byte[] km2 = new byte[32]; label(km2, "km2<-r2(rejected)");
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_next2Event(r2, km2);
        r2.nextBytes(km2);
        delta("S1c srd-rejected"); store("S1c");
        System.out.println("  RANDOMIZED[r2]=" + ctx.validate(Property.RANDOMIZED, r2)
                + " RANDOMIZED[km2]=" + ctx.validate(Property.RANDOMIZED, km2)
                + "  <- material-level mark from a rejected instance");
        SecretKeySpec sks2 = new SecretKeySpec(km2, "AES"); label(sks2, "sks2(km2,AES)");
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event(km2, "AES", sks2);
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c3Event(km2, "AES", sks2);
        delta("S1c2 skss-from-rejected-material"); store("S1c2");
        System.out.println("  SPECCED_KEY[sks2]=" + ctx.validate(Property.SPECCED_KEY, sks2)
                + "  <- reader satisfied by rejected randomness = executed FN direction");

        // S1d: SKSS over NEVER-monitored material (negative control)
        byte[] kmRaw = new byte[32]; label(kmRaw, "kmRaw(unmonitored)");
        SecretKeySpec sks3 = new SecretKeySpec(kmRaw, "AES"); label(sks3, "sks3(kmRaw,AES)");
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event(kmRaw, "AES", sks3);
        MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c3Event(kmRaw, "AES", sks3);
        delta("S1d skss-unmonitored-material"); store("S1d");
        System.out.println("  SPECCED_KEY[sks3]=" + ctx.validate(Property.SPECCED_KEY, sks3));

        // S1e: PBK reader over randomized salt (4-arg ctor advice emits c1;err1;err2;err3)
        char[] pw = "correct horse".toCharArray();
        PBEKeySpec pbk1 = new PBEKeySpec(pw, salt, 65536, 256); label(pbk1, "pbk1(salt<-r1,65536,256)");
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_c1Event(pw, salt, 65536, 256, pbk1);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err1Event(pw, salt, 65536, 256, pbk1);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err2Event(pw, salt, 65536, 256, pbk1);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err3Event(pw, salt, 65536, 256, pbk1);
        delta("S1e pbk-randomized-salt"); store("S1e");
        // S1f: PBK over unmonitored salt + weak params
        byte[] saltRaw = new byte[8]; label(saltRaw, "saltRaw(unmonitored)");
        PBEKeySpec pbk2 = new PBEKeySpec(pw, saltRaw, 10, 64); label(pbk2, "pbk2(saltRaw,10,64)");
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_c1Event(pw, saltRaw, 10, 64, pbk2);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err1Event(pw, saltRaw, 10, 64, pbk2);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err2Event(pw, saltRaw, 10, 64, pbk2);
        MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err3Event(pw, saltRaw, 10, 64, pbk2);
        delta("S1f pbk-raw-salt-weak-params"); store("S1f");

        System.out.println("== S2: KGN -> GENERATED_KEY -> MAC / SKY gates ==");
        KeyGenerator kg = KeyGenerator.getInstance("HmacSHA256"); label(kg, "kg(HmacSHA256)");
        MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_g1Event("HmacSHA256", kg);
        MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_g3Event("HmacSHA256", kg);
        MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_i1Event(256, kg); // before
        kg.init(256);
        SecretKey skH = kg.generateKey(); label(skH, "skH(kg-generated)");
        MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_gk1Event(kg, skH);
        delta("S2a kgn-generate"); store("S2a");
        System.out.println("  GENERATED_KEY[skH]=" + ctx.validate(Property.GENERATED_KEY, skH));

        // S2b: MAC with the KGN-generated key (gate should open)
        Mac mac1 = Mac.getInstance("HmacSHA256"); label(mac1, "mac1");
        MultiSpec_1RuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac1);
        MultiSpec_1RuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac1);
        MultiSpec_1RuntimeMonitor.MacSpec_i1Event(skH, mac1); // before
        mac1.init(skH);
        byte[] macIn = new byte[8]; label(macIn, "macIn");
        MultiSpec_1RuntimeMonitor.MacSpec_uArrEvent(macIn, mac1);
        mac1.update(macIn);
        byte[] macOut1 = mac1.doFinal(); label(macOut1, "macOut1");
        MultiSpec_1RuntimeMonitor.MacSpec_f1Event(mac1, macOut1);
        delta("S2b mac-with-generated-key"); store("S2b");
        System.out.println("  acc(mac1)=" + ctx.isInAcceptingState(mac1)
                + " GENERATED_MAC[macOut1]=" + ctx.validate(Property.GENERATED_MAC, macOut1));

        // S2c: MAC with the fully-monitored SKSS-built key sks1 (does MacSpec's GENERATED_KEY gate see it?)
        Mac mac2 = Mac.getInstance("HmacSHA256"); label(mac2, "mac2");
        MultiSpec_1RuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac2);
        MultiSpec_1RuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac2);
        MultiSpec_1RuntimeMonitor.MacSpec_i1Event(sks1, mac2); // condition: validate(GENERATED_KEY, sks1)
        mac2.init(sks1);
        byte[] macOut2 = mac2.doFinal(macIn); label(macOut2, "macOut2");
        MultiSpec_1RuntimeMonitor.MacSpec_f2Event(macIn, mac2, macOut2);
        delta("S2c mac-with-skss-key"); store("S2c");
        System.out.println("  acc(mac2)=" + ctx.isInAcceptingState(mac2)
                + " GENERATED_KEY[sks1]=" + ctx.validate(Property.GENERATED_KEY, sks1)
                + "  <- gate outcome depends on whether SecretKeySpecSpec also wrote GENERATED_KEY (second writer)");

        // S2d: SKY reader: getEncoded on generated vs SKSS-built key
        byte[] enc1 = skH.getEncoded(); label(enc1, "enc1(skH bytes)");
        MultiSpec_1RuntimeMonitor.SecretKeySpec_e1Event(skH, enc1);
        delta("S2d sky-getEncoded-generated"); store("S2d");
        byte[] enc2 = sks1.getEncoded(); label(enc2, "enc2(sks1 bytes)");
        MultiSpec_1RuntimeMonitor.SecretKeySpec_e1Event(sks1, enc2);
        delta("S2d2 sky-getEncoded-skss"); store("S2d2");

        System.out.println("== S3: KPG -> generatedKeyPair -> KPR -> SIG (FP-toll edge) ==");
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA"); label(kpg, "kpg(RSA)");
        MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_g1Event("RSA", kpg);
        MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_g3Event("RSA", kpg);
        kpg.initialize(2048);
        MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init1Event(2048, kpg);
        MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(2048, kpg);
        KeyPair kp = kpg.generateKeyPair(); label(kp, "kp");
        MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_genEvent(kpg, kp);
        delta("S3a kpg-generate"); store("S3a");
        System.out.println("  GENERATED_KEY_PAIR[kp]=" + ctx.validate(Property.GENERATED_KEY_PAIR, kp)
                + " acc(kpg)=" + ctx.isInAcceptingState(kpg));

        PrivateKey priv = kp.getPrivate(); label(priv, "priv");
        MultiSpec_1RuntimeMonitor.KeyPairSpec_gprEvent(kp, priv);
        delta("S3b kpr-getPrivate (FP toll?)"); store("S3b");
        PublicKey pub = kp.getPublic(); label(pub, "pub");
        MultiSpec_1RuntimeMonitor.KeyPairSpec_gpuEvent(kp, pub);
        delta("S3c kpr-getPublic (FP toll?)"); store("S3c");
        System.out.println("  GENERATED_PRIVATE_KEY[priv]=" + ctx.validate(Property.GENERATED_PRIVATE_KEY, priv)
                + " GENERATED_PUBLIC_KEY[pub]=" + ctx.validate(Property.GENERATED_PUBLIC_KEY, pub));

        Signature sig = Signature.getInstance("SHA256withRSA"); label(sig, "sig(sign)");
        MultiSpec_1RuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sig);
        MultiSpec_1RuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sig);
        MultiSpec_1RuntimeMonitor.SignatureSpec_i1Event(priv, sig); // before
        sig.initSign(priv);
        MultiSpec_1RuntimeMonitor.SignatureSpec_updateEvent(sig); // before
        sig.update(macIn);
        byte[] sigBytes = sig.sign(); label(sigBytes, "sigBytes");
        // NO s1 event: production pointcut declares 'byte' return, sign() returns byte[] -> dead (weave-probe UNTOUCHED)
        delta("S3d sig-sign (s1 dead: no event emitted)"); store("S3d");
        System.out.println("  acc(sig)=" + ctx.isInAcceptingState(sig)
                + " SIGNED[sigBytes]=" + ctx.validate(Property.SIGNED, sigBytes)
                + "  <- dead s1 => SIGNED never written");

        Signature sigV = Signature.getInstance("SHA256withRSA"); label(sigV, "sigV(verify)");
        MultiSpec_1RuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sigV);
        MultiSpec_1RuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sigV);
        MultiSpec_1RuntimeMonitor.SignatureSpec_i4Event(pub, sigV); // before
        sigV.initVerify(pub);
        MultiSpec_1RuntimeMonitor.SignatureSpec_updateEvent(sigV);
        sigV.update(macIn);
        boolean ok = sigV.verify(sigBytes);
        MultiSpec_1RuntimeMonitor.SignatureSpec_v1Event(sigBytes, sigV, ok);
        delta("S3e sig-verify"); store("S3e");
        System.out.println("  verify-returned=" + ok
                + " VERIFIED[sigBytes]=" + ctx.validate(Property.VERIFIED, sigBytes)
                + " VERIFIED[Boolean.TRUE]=" + ctx.validate(Property.VERIFIED, Boolean.TRUE));

        System.out.println("== S4: KST -> GENERATED_KEY_STORE -> KMF/TMF -> SSL init ==");
        KeyStore ks = KeyStore.getInstance("PKCS12"); label(ks, "ks(PKCS12)");
        MultiSpec_1RuntimeMonitor.KeyStoreSpec_g1Event("PKCS12", ks);
        MultiSpec_1RuntimeMonitor.KeyStoreSpec_g2Event("PKCS12", ks); // 1-arg getInstance advice emits g1 AND g2
        MultiSpec_1RuntimeMonitor.KeyStoreSpec_loadEvent(ks); // before
        ks.load(null, null);
        delta("S4a kst-load"); store("S4a");
        System.out.println("  GENERATED_KEY_STORE[ks]=" + ctx.validate(Property.GENERATED_KEY_STORE, ks)
                + " acc(ks)=" + ctx.isInAcceptingState(ks));

        KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        label(kmf, "kmf(default-alg)");
        MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g1Event(KeyManagerFactory.getDefaultAlgorithm(), kmf);
        MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g3Event(KeyManagerFactory.getDefaultAlgorithm(), kmf);
        MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_i1Event(ks, new char[0], kmf); // before
        kmf.init(ks, new char[0]);
        KeyManager[] kms = kmf.getKeyManagers(); label(kms, "kms");
        MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_gkm1Event(kmf, kms);
        delta("S4b kmf"); store("S4b");

        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        label(tmf, "tmf(default-alg)");
        MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g1Event(TrustManagerFactory.getDefaultAlgorithm(), tmf);
        MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g3Event(TrustManagerFactory.getDefaultAlgorithm(), tmf);
        MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_i1Event(ks, tmf); // before
        tmf.init(ks);
        TrustManager[] tms = tmf.getTrustManagers(); label(tms, "tms");
        MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_gtm1Event(tmf, tms);
        delta("S4c tmf"); store("S4c");
        System.out.println("  GENERATED_KEY_MANAGERS[kms]=" + ctx.validate(Property.GENERATED_KEY_MANAGERS, kms)
                + " GENERATED_TRUST_MANAGERS[tms]=" + ctx.validate(Property.GENERATED_TRUST_MANAGERS, tms));

        SSLContext ctx1 = SSLContext.getInstance("TLSv1.3"); label(ctx1, "ctx1(TLSv1.3)");
        MultiSpec_1RuntimeMonitor.SSLContextSpec_g1Event("TLSv1.3", ctx1);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLSv1.3", ctx1);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(ctx1, kms, tms, r1); // r1: monitored-safe SecureRandom
        ctx1.init(kms, tms, r1);
        delta("S4d ssl-init-with-r1"); store("S4d");
        System.out.println("  acc(ctx1)=" + ctx.isInAcceptingState(ctx1)
                + " GENERATE_SSL_CONTEXT[ctx1]=" + ctx.validate(Property.GENERATE_SSL_CONTEXT, ctx1));

        SSLContext ctx2 = SSLContext.getInstance("TLSv1.3"); label(ctx2, "ctx2(TLSv1.3)");
        MultiSpec_1RuntimeMonitor.SSLContextSpec_g1Event("TLSv1.3", ctx2);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLSv1.3", ctx2);
        SecureRandom rFresh = new SecureRandom(); label(rFresh, "rFresh(unmonitored)");
        MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(ctx2, kms, tms, rFresh);
        ctx2.init(kms, tms, rFresh);
        delta("S4e ssl-init-with-unmonitored-sr"); store("S4e");
        // createSSLEngine: production pointcut declares void return; real method returns SSLEngine -> dead.
        SSLEngine eng = ctx1.createSSLEngine();
        System.out.println("  createSSLEngine executed; NO engine event exists in production weave (dead pointcut) -> GENERATE_SSL_ENGINE never written; engine-null-check: " + (eng != null));
        delta("S4f ssl-engine-dead"); store("S4f");

        System.out.println("== S5: KPG NPE crash class over the MERGED monitor (initialize(int) first event) ==");
        KeyPairGenerator kNpe = KeyPairGenerator.getInstance("RSA"); label(kNpe, "kNpe");
        // Provider-route creation is uncaptured (weave probe: kpg_gi2p UNTOUCHED) -> no creation event.
        try {
            MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init1Event(2048, kNpe);
            System.out.println("  init1Event(first): NO exception");
        } catch (Throwable t) {
            System.out.println("  init1Event(first) threw to caller: " + t.getClass().getName());
        }
        try {
            MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(2048, kNpe);
            System.out.println("  initErrorEvent(first): NO exception");
        } catch (Throwable t) {
            System.out.println("  initErrorEvent(first) threw to caller: " + t.getClass().getName());
        }
        delta("S5 kpg-npe"); store("S5");

        System.out.println("== done ==");
    }
}
