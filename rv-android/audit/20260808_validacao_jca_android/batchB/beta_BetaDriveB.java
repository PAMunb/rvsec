import mop.CipherInputStreamSpecRuntimeMonitor;
import mop.CipherOutputStreamSpecRuntimeMonitor;
import mop.KeyPairSpecRuntimeMonitor;
import mop.SecretKeySpecRuntimeMonitor;
import mop.PBEKeySpecSpecRuntimeMonitor;
import mop.SecretKeySpecSpecRuntimeMonitor;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.Cipher;
import javax.crypto.CipherInputStream;
import javax.crypto.CipherOutputStream;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;

/**
 * Agent Beta (batch B) drive harness. Compiles the FIVE batch-B generated
 * RuntimeMonitor.java artifacts unmodified (package mop) plus batch A's
 * SecretKeySpecSpecRuntimeMonitor (cross-spec object-flow check), and drives
 * their public static wrappers in the exact order the generated
 * MonitorAspect.aj advices call them, feeding only real JDK objects produced
 * by normally-returning calls (mirrors `after`/`after returning`).
 *
 * Every check prints PASS/FAIL; exit code 1 on any FAIL.
 */
public class BetaDriveB {

    static int failures = 0;
    static ExecutionContext ec = ExecutionContext.instance();

    static void check(String label, boolean cond) {
        System.out.println((cond ? "PASS " : "FAIL ") + label);
        if (!cond) failures++;
    }

    static int errCount() { return ErrorCollector.instance().getErrors().size(); }

    static String lastTypes() {
        java.util.TreeSet<String> t = new java.util.TreeSet<>();
        for (ErrorDescription d : ErrorCollector.instance().getErrors())
            t.add(d.getType().toString());
        return String.join("|", t);
    }

    /** Reflectively fetch the per-object monitor from a MapOfMonitor static field. */
    static Object monitorOf(Class<?> rtm, String mapField, Object key) throws Exception {
        Field f = rtm.getDeclaredField(mapField);
        f.setAccessible(true);
        Object map = f.get(null);
        java.lang.reflect.Method get = map.getClass().getMethod("getNodeWithStrongRef", Object.class);
        get.setAccessible(true);
        return get.invoke(map, key);
    }

    static int stateOf(Object monitor) throws Exception {
        java.lang.reflect.Method m = monitor.getClass().getMethod("getState");
        m.setAccessible(true);
        return (Integer) m.invoke(monitor);
    }

    /** State of the KPR empty-binding leaf monitor (Tuple2 value2). */
    static Object kprEmptyLeaf() throws Exception {
        Field f = KeyPairSpecRuntimeMonitor.class.getDeclaredField("KeyPairSpec__Map");
        f.setAccessible(true);
        Object tuple = f.get(null);
        java.lang.reflect.Method m = tuple.getClass().getMethod("getValue2");
        m.setAccessible(true);
        return m.invoke(tuple);
    }

    public static void main(String[] args) throws Exception {
        cis();
        cos();
        kpr();
        sky();
        pbk();
        System.out.println(failures == 0 ? "ALL PASS" : failures + " FAILURES");
        System.exit(failures == 0 ? 0 : 1);
    }

    // ---------------------------------------------------------------- CIS
    static void cis() throws Exception {
        System.out.println("== CIS (global monitor; ere c1 (r1|r2)+ cl1)");
        Cipher seeded = Cipher.getInstance("AES");
        seeded.init(Cipher.ENCRYPT_MODE, KeyGenerator.getInstance("AES").generateKey());
        Cipher unseeded = Cipher.getInstance("AES");
        unseeded.init(Cipher.ENCRYPT_MODE, KeyGenerator.getInstance("AES").generateKey());
        ec.setProperty(Property.GENERATED_CIPHER, seeded); // as CipherSpec.mop:161 writes

        byte[] data = new byte[32];
        // s1: REQUIRES reader works (cipher without GENERATED_CIPHER accused), then lifecycle proceeds
        InputStream is0 = new ByteArrayInputStream(data);
        CipherInputStream str0 = new CipherInputStream(is0, unseeded);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(is0, unseeded);
        check("CIS-f c1(unvalidated cipher) emits UnsatisfiedConstraint (errs=1)", errCount() == 1);
        int r = str0.read();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        str0.close();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        check("CIS-f full lifecycle after accusation adds no sequence error (errs=1)", errCount() == 1);

        // s2: SECOND stream, CrySL-legal per-object trace -> global-monitor FP
        InputStream is1 = new ByteArrayInputStream(data);
        CipherInputStream str1 = new CipherInputStream(is1, seeded);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(is1, seeded);
        check("CIS-b c1 of 2nd legal stream -> spurious InvalidSequenceOfMethodCalls (errs=2)",
                errCount() == 2);
        r = str1.read();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        check("CIS-b2 its read also faults after reset (errs=3)", errCount() == 3);
        str1.close();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        check("CIS-b3 its close also faults (errs=4)", errCount() == 4);

        // s3: len<=off CrySL CONSTRAINT (len > off) is unchecked -> silent
        InputStream is2 = new ByteArrayInputStream(data);
        CipherInputStream str2 = new CipherInputStream(is2, seeded);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(is2, seeded);
        byte[] buf = new byte[16];
        int n = str2.read(buf, 5, 3); // returns normally on the JDK, len<=off violates the rule
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r2Event(buf, 5, 3);
        check("CIS-e read(b,5,3) violating len>off is silent (errs=4)", errCount() == 4);
        str2.close();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();

        // s4: close-without-read correctly accused (from clean state after forced fail)
        InputStream is3 = new ByteArrayInputStream(data);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(is3, seeded); // 2->4 FP
        check("CIS-b4 3rd stream ctor faults again (errs=5)", errCount() == 5);
        InputStream is4 = new ByteArrayInputStream(data);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(is4, seeded); // 0->3
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();           // 3->4
        check("CIS-d close-without-read accused (errs=6)", errCount() == 6);
    }

    // ---------------------------------------------------------------- COS
    static void cos() throws Exception {
        System.out.println("== COS (global monitor; ere c1 (w1|w2|fl)+ cl)");
        int base = errCount();
        Cipher seeded = Cipher.getInstance("AES");
        seeded.init(Cipher.ENCRYPT_MODE, KeyGenerator.getInstance("AES").generateKey());
        ec.setProperty(Property.GENERATED_CIPHER, seeded);
        byte[] data = new byte[16];

        OutputStream os1 = new ByteArrayOutputStream();
        CipherOutputStream cs1 = new CipherOutputStream(os1, seeded);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os1, seeded);
        cs1.write(7);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w1Event();
        cs1.close();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        check("COS-a compliant lifecycle, no errors", errCount() == base);

        OutputStream os2 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os2, seeded);
        check("COS-b 2nd legal stream ctor -> spurious fail (+1)", errCount() == base + 1);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w2Event(data, 0, 8);
        check("COS-b2 its write faults after reset (+2)", errCount() == base + 2);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        check("COS-b3 its close faults (+3)", errCount() == base + 3);

        // flush-only lifecycle ACCEPTED though CrySL requires Writes+
        OutputStream os3 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os3, seeded);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        check("COS-c c1 fl cl accepted silently (CrySL demands a write) (+3)",
                errCount() == base + 3);

        // close-without-write correctly accused
        OutputStream os4 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os4, seeded); // 3->4 FP
        check("COS-b4 4th stream ctor faults (+4)", errCount() == base + 4);
        OutputStream os5 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os5, seeded); // 0->2
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();            // 2->4
        check("COS-d close-without-write accused (+5)", errCount() == base + 5);

        // w2 len<=off unchecked
        OutputStream os6 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os6, seeded);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w2Event(data, 5, 3);
        check("COS-e write(b,5,3) violating len>off silent (+5)", errCount() == base + 5);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
    }

    // ---------------------------------------------------------------- KPR
    static void kpr() throws Exception {
        System.out.println("== KPR (partial binding: c1 binds no spec parameter)");
        int base = errCount();
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
        kpg.initialize(256);

        // k1: THE standard JCA route — kp from generateKeyPair(), then getPublic()
        KeyPair kp0 = kpg.generateKeyPair();
        PublicKey pub0 = kp0.getPublic();
        KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp0, pub0);
        check("KPR-a getPublic on generator-produced KeyPair -> spurious fail (+1)",
                errCount() == base + 1);
        check("KPR-a2 GENERATED_PUBLIC_KEY still granted despite fail state",
                ec.validate(Property.GENERATED_PUBLIC_KEY, pub0));

        // k2: ctor route; c1 body validates REQUIRES and runs per set member
        KeyPair kpSrc = kpg.generateKeyPair();
        PublicKey pub1 = kpSrc.getPublic();
        PrivateKey priv1 = kpSrc.getPrivate();
        ec.setProperty(Property.GENERATED_PUBLIC_KEY, pub1);
        ec.setProperty(Property.GENERATED_PRIVATE_KEY, priv1);
        KeyPair kp1 = new KeyPair(pub1, priv1);
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(pub1, priv1, kp1);
        check("KPR-b ctor with validated keys adds no error (+1)", errCount() == base + 1);
        check("KPR-b2 @match marked null, not the KeyPair (monitor-var shadowed by param local)",
                !ec.isInAcceptingState(kp1) && ec.isInAcceptingState(null));

        KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp1, kp1.getPublic());
        check("KPR-b3 gpu after c1 chains via empty-leaf clone, no error (+1)",
                errCount() == base + 1);
        Object kp1mon = monitorOf(KeyPairSpecRuntimeMonitor.class, "KeyPairSpec_keyPair_Map", kp1);
        check("KPR-b4 kp1 monitor in state 1 (match)", kp1mon != null && stateOf(kp1mon) == 1);

        // k4: SECOND construction — c1 dispatches to the WHOLE monitor set
        int kp1Before = stateOf(kp1mon);
        Object emptyBefore = kprEmptyLeaf();
        int emptyStateBefore = stateOf(emptyBefore);
        KeyPair kpSrc2 = kpg.generateKeyPair();
        PublicKey pub2 = kpSrc2.getPublic();
        PrivateKey priv2 = kpSrc2.getPrivate();
        ec.setProperty(Property.GENERATED_PUBLIC_KEY, pub2);
        ec.setProperty(Property.GENERATED_PRIVATE_KEY, priv2);
        KeyPair kp2 = new KeyPair(pub2, priv2);
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(pub2, priv2, kp2);
        int kp1After = stateOf(kp1mon);
        check("KPR-c 2nd legal construction fails EVERY live monitor (+at least 1 error)",
                errCount() >= base + 2);
        int errsAfterK4 = errCount();
        check("KPR-c2 kp1's monitor was dragged from state " + kp1Before + " to "
                + kp1After + " (reset after fail) by kp2's c1",
                kp1Before == 1 && kp1After == 0);
        check("KPR-c3 identical simultaneous fails DEDUPED to one errors.csv row "
                + "(errs=" + (errsAfterK4 - base) + ", monitors failed>=2)",
                errsAfterK4 == base + 2);

        // k5: kp2's own getPublic then faults (clone of reset empty leaf)
        KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp2, kp2.getPublic());
        check("KPR-d getPublic of kp2 after cascade -> another spurious fail (+3)",
                errCount() == base + 3);

        // k6: body re-execution per set member duplicates REQUIRES accusations (deduped)
        KeyPair kpSrc3 = kpg.generateKeyPair();
        KeyPair kp3 = new KeyPair(kpSrc3.getPublic(), kpSrc3.getPrivate()); // NOT seeded
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(kpSrc3.getPublic(), kpSrc3.getPrivate(), kp3);
        check("KPR-e unvalidated ctor: pubkey+privkey accusations collapse to ONE row "
                + "(ErrorSummary drops `expecting`; also deduped across 4 set members) (+4)",
                errCount() == base + 4);
    }

    // ---------------------------------------------------------------- SKY
    static void sky() throws Exception {
        System.out.println("== SKY (SecretKey interface; ere e1* (d|epsilon))");
        int base = errCount();
        KeyGenerator kg = KeyGenerator.getInstance("AES");
        SecretKey key1 = kg.generateKey();
        SecretKey key2 = kg.generateKey();

        // a: granted key -> e1 writes RANDOMIZED
        ec.setProperty(Property.GENERATED_KEY, key1); // as KeyGeneratorSpec.mop:114 writes
        byte[] enc1 = key1.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key1, enc1);
        check("SKY-a getEncoded of granted key writes RANDOMIZED, no error",
                ec.validate(Property.RANDOMIZED, enc1) && errCount() == base);

        // b: ungranted key (rule has NO REQUIRES; ENSURES is unconditional) -> suppressed
        byte[] enc2 = key2.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key2, enc2);
        check("SKY-b getEncoded of ungranted key: no error AND preparedKeyMaterial surrogate DENIED",
                !ec.validate(Property.RANDOMIZED, enc2) && errCount() == base);

        // c: destroy withdraws GENERATED_KEY (NEGATES edge)
        SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(key1);
        check("SKY-c d removes GENERATED_KEY", !ec.validate(Property.GENERATED_KEY, key1));
        Object m1 = monitorOf(SecretKeySpecRuntimeMonitor.class, "SecretKeySpec_secretKey_Map", key1);
        check("SKY-c2 monitor state 1 after d", stateOf(m1) == 1);

        // d: getEncoded AFTER destroy: ORDER violation invisible; body writes anyway
        ec.setProperty(Property.GENERATED_KEY, key1); // re-grant (e.g. an equals-based or new grant)
        byte[] enc1b = key1.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key1, enc1b);
        check("SKY-d ge-after-d: dead state, NO error emitted (violation invisible)",
                errCount() == base && stateOf(m1) == 2);
        check("SKY-d2 body still granted RANDOMIZED in dead state (writes are state-independent)",
                ec.validate(Property.RANDOMIZED, enc1b));

        // e: double destroy silent
        SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(key1);
        check("SKY-e second destroy silent (state 2, no error)",
                errCount() == base && stateOf(m1) == 2);

        // f: per-object independence
        SecretKey key3 = kg.generateKey();
        ec.setProperty(Property.GENERATED_KEY, key3);
        byte[] enc3 = key3.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key3, enc3);
        check("SKY-f other key unaffected (per-object MapOfMonitor)",
                ec.validate(Property.RANDOMIZED, enc3) && errCount() == base);

        // g: cross-spec object flow with batch A SecretKeySpecSpec (same runtime object)
        byte[] km = new byte[16];
        new SecureRandom().nextBytes(km);
        ec.setProperty(Property.RANDOMIZED, km); // as SecureRandomSpec.mop:121 writes
        SecretKeySpec sks = new SecretKeySpec(km, "AES");
        // merged advice order in batch A aspect: c1Event then c3Event
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c1Event(km, "AES", sks);
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c3Event(km, "AES", sks);
        check("SKY-g1 SKS grants GENERATED_KEY to the SecretKeySpec object, no error",
                ec.validate(Property.GENERATED_KEY, sks) && errCount() == base);
        byte[] encS = sks.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(sks, encS);
        check("SKY-g2 SKY e1 accepts the SKS-granted object; RANDOMIZED(encoded) written",
                ec.validate(Property.RANDOMIZED, encS) && errCount() == base);
        SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(sks);
        check("SKY-g3 SKY d withdraws the mark SKS granted (NEGATES generatedKey[this,_])",
                !ec.validate(Property.GENERATED_KEY, sks) && errCount() == base);
    }

    // ---------------------------------------------------------------- PBK
    static void pbk() throws Exception {
        System.out.println("== PBK (per-object; ere (f1|f2|err1|err2|err3)* c1 c2)");
        int base = errCount();
        SecureRandom sr = new SecureRandom();

        // a: compliant 4-arg with randomized password AND salt
        char[] pw1 = new char[12];
        byte[] salt1 = new byte[16];
        sr.nextBytes(salt1);
        ec.setProperty(Property.RANDOMIZED, pw1);
        ec.setProperty(Property.RANDOMIZED, salt1);
        PBEKeySpec s1 = new PBEKeySpec(pw1, salt1, 10000, 256);
        // advice order: c1, err1, err2, err3
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pw1, salt1, 10000, 256, s1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pw1, salt1, 10000, 256, s1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pw1, salt1, 10000, 256, s1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pw1, salt1, 10000, 256, s1);
        check("PBK-a compliant construction: SPECCED_KEY granted, no error",
                ec.validate(Property.SPECCED_KEY, s1) && errCount() == base);
        s1.clearPassword();
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s1);
        check("PBK-a2 clearPassword: SPECCED_KEY removed, @match marks the spec object",
                !ec.validate(Property.SPECCED_KEY, s1) && ec.isInAcceptingState(s1)
                        && errCount() == base);

        // b: user-typed password (never RANDOMIZED) + randomized salt + iter ok
        char[] pw2 = "hunter2hunter2".toCharArray();
        byte[] salt2 = new byte[16];
        sr.nextBytes(salt2);
        ec.setProperty(Property.RANDOMIZED, salt2);
        PBEKeySpec s2 = new PBEKeySpec(pw2, salt2, 10000, 256);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pw2, salt2, 10000, 256, s2);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pw2, salt2, 10000, 256, s2);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pw2, salt2, 10000, 256, s2);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pw2, salt2, 10000, 256, s2);
        check("PBK-b oracle-legal user password accused by extra-oracle randomized[password] (+1)",
                errCount() == base + 1 && !ec.validate(Property.SPECCED_KEY, s2));

        // c: iter<10000, nothing randomized: err1+err2+err3 fire; then cP -> extra @fail
        char[] pw3 = "p".toCharArray();
        byte[] salt3 = new byte[8];
        PBEKeySpec s3 = new PBEKeySpec(pw3, salt3, 500, 128);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pw3, salt3, 500, 128, s3);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pw3, salt3, 500, 128, s3);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pw3, salt3, 500, 128, s3);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pw3, salt3, 500, 128, s3);
        check("PBK-c three overlapping err branches fire for one construction (+4)",
                errCount() == base + 4);
        s3.clearPassword();
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s3);
        check("PBK-c2 clearPassword after violating ctor adds a SEQUENCE error on top (+5)",
                errCount() == base + 5);

        // d: FORBIDDEN 1-arg ctor; then its clearPassword faults again
        char[] pw4 = "abc".toCharArray();
        PBEKeySpec s4 = new PBEKeySpec(pw4);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_f1Event(pw4, s4);
        check("PBK-d forbidden 1-arg ctor reported (+6)", errCount() == base + 6);
        s4.clearPassword();
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s4);
        check("PBK-d2 its clearPassword adds sequence error (FORBIDDEN=>c1 reading would accept) (+7)",
                errCount() == base + 7);

        // e: double clearPassword on the compliant object: correct accusation
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s1);
        check("PBK-e second clearPassword accused (+8)", errCount() == base + 8);

        // f: FORBIDDEN 3-arg ctor
        byte[] salt5 = new byte[8];
        PBEKeySpec s5 = new PBEKeySpec(pw4, salt5, 10000);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_f2Event(pw4, salt5, 10000, s5);
        check("PBK-f forbidden 3-arg ctor reported (+9)", errCount() == base + 9);

        // g: per-object independence: s1's monitor unaffected by s3/s4 histories
        Object s1mon = monitorOf(PBEKeySpecSpecRuntimeMonitor.class, "PBEKeySpecSpec_s_Map", s1);
        check("PBK-g monitors are per-object (s1 in post-match/fail state, isolated)",
                s1mon != null);
    }
}
