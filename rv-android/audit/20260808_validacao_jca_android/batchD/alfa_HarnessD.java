// Batch D / Agent ALFA — JVM drive over the round monitors with production jars.
// The static *Event methods of the generated RuntimeMonitor classes are called in
// exactly the sequence the generated MonitorAspect.aj advices emit for each
// simulated Java call (merged advices reproduced: Mac g1;g3 — MacSpecMonitorAspect.aj:45-51,
// MDG g1;g4 — :41-46, KPG g1;g3 and init1;initError — :41-59, SRD separate g1/g4
// advices both firing on a 1-arg call — :64-79, SIG g1;g3 — :70-72).
// KeyPairSpec monitor (batch B round artifact, same frozen .mop) is included for
// the KPG -> KeyPair -> Signature predicate-chain drive.
// Deterministic; 3 reps by shell wrapper; ErrorCollector+ExecutionContext reset per trace.
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.security.*;
import java.security.spec.AlgorithmParameterSpec;
import java.util.*;

public class AlfaHarnessD {

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

    static boolean has(Property p, Object o) { return ExecutionContext.instance().validate(p, o); }

    // ---------------- MAC call classes ----------------
    static Mac macG1(String alg) throws Exception {           // 1-arg getInstance: merged advice g1;g3
        Mac m = Mac.getInstance("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_g1Event(alg, m);
        MacSpecRuntimeMonitor.MacSpec_g3Event(alg, m);
        return m;
    }
    static Mac macG2(String alg, String prov) throws Exception {
        Mac m = Mac.getInstance("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_g2Event(alg, prov, m);
        return m;
    }
    static Mac macInvisible() throws Exception {              // (String,Provider) overload: no advice
        return Mac.getInstance("HmacSHA256");
    }

    // ---------------- MDG call classes ----------------
    static MessageDigest mdgG1(String alg) throws Exception { // merged g1;g4
        MessageDigest d = MessageDigest.getInstance("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event(alg, d);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event(alg, d);
        return d;
    }
    static MessageDigest mdgG3(String alg) throws Exception {
        MessageDigest d = MessageDigest.getInstance("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g3Event(alg, null, d);
        return d;
    }

    // ---------------- KPG call classes ----------------
    static KeyPairGenerator kpgG1(String alg) throws Exception {  // merged g1;g3
        KeyPairGenerator k = KeyPairGenerator.getInstance("RSA");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event(alg, k);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event(alg, k);
        return k;
    }
    static void kpgInit1(int size, KeyPairGenerator k) {          // merged init1;initError
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(size, k);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(size, k);
    }

    // ---------------- SRD call classes ----------------
    static SecureRandom srdC1() {
        SecureRandom r = new SecureRandom();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(r);
        return r;
    }
    static SecureRandom srdC(byte[] seed) {                   // merged c2;c3
        SecureRandom r = new SecureRandom();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c2Event(seed, r);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c3Event(seed, r);
        return r;
    }
    static SecureRandom srdG1(String alg) {                   // separate advices g1 and g4, both on 1-arg call
        SecureRandom r = new SecureRandom();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g1Event(alg, r);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g4Event(alg, r);
        return r;
    }
    static void srdNB(SecureRandom r, byte[] b) { SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(r, b); }

    // ---------------- SIG call classes ----------------
    static Signature sigG1(String alg) throws Exception {     // merged g1;g3
        Signature s = Signature.getInstance("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_g1Event(alg, s);
        SignatureSpecRuntimeMonitor.SignatureSpec_g3Event(alg, s);
        return s;
    }

    public static void main(String[] args) throws Exception {
        // fixed seed material (pre-declared; identity is what matters, not values)
        byte[] data = new byte[]{1,2,3,4};
        byte[] data2 = new byte[]{9,9,9};
        Key markedKey = new SecretKeySpec(new byte[]{5,6,7,8,9,1,2,3,4,5,6,7,8,9,0,1}, "HmacSHA256");
        Key unmarkedKey = new SecretKeySpec(new byte[]{9,8,7,6,5,4,3,2,1,0,9,8,7,6,5,4}, "HmacSHA256");
        KeyPairGenerator realKpg = KeyPairGenerator.getInstance("RSA");
        realKpg.initialize(2048);
        KeyPair realKp = realKpg.generateKeyPair();
        PrivateKey priv = realKp.getPrivate();
        PublicKey pub = realKp.getPublic();

        // ===================== MAC =====================
        fresh("MAC-T1 conformant: g1(HmacSHA256) i1(markedKey) uArr f1");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m1 = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m1);
        MacSpecRuntimeMonitor.MacSpec_uArrEvent(data, m1);
        byte[] macOut1 = new byte[]{42,42};
        MacSpecRuntimeMonitor.MacSpec_f1Event(m1, macOut1);
        snap("after f1");
        System.out.println("  MACED[data]=" + has(Property.MACED, data)
                + " GENERATED_MAC[out]=" + has(Property.GENERATED_MAC, macOut1)
                + " accepting(mac)=" + ExecutionContext.instance().isInAcceptingState(m1));

        fresh("MAC-T2 unsafe 1-arg carrier: g3(DES) i1(markedKey) uArr f1");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m2 = macG1("DES");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m2);
        snap("after i1");
        MacSpecRuntimeMonitor.MacSpec_uArrEvent(data, m2);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m2, new byte[]{1});
        snap("after f1");

        fresh("MAC-T3 extra-oracle key gate: g1(HmacSHA256) i1(UNMARKED) uArr f1");
        Mac m3 = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(unmarkedKey, m3);
        snap("after suppressed i1");
        MacSpecRuntimeMonitor.MacSpec_uArrEvent(data, m3);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m3, new byte[]{2});
        snap("after f1 (expect InvalidSequence only, no UnsatisfiedConstraint)");

        fresh("MAC-T4 two-arg safe (String,String): g2 i1(marked) f1 (rule models no 2-arg Gets)");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m4 = macG2("HmacSHA256", "AnyProvider");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m4);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m4, new byte[]{3});
        snap("after f1");

        fresh("MAC-T5 (String,Provider) overload invisible: i1(marked) uArr f1 born-at-i1");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m5 = macInvisible();
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m5);
        MacSpecRuntimeMonitor.MacSpec_uArrEvent(data, m5);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m5, new byte[]{4});
        snap("after f1 (spurious InvalidSequence on rule-silent object)");

        fresh("MAC-T6 uBuf FN: g1 i1(marked) uBuf f1 -> buffer data never MACED-marked");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m6 = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m6);
        ByteBuffer buf = ByteBuffer.wrap(data2);
        MacSpecRuntimeMonitor.MacSpec_uBufEvent(buf, m6);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m6, new byte[]{5});
        snap("after f1");
        System.out.println("  MACED[buf]=" + has(Property.MACED, buf)
                + " MACED[buf.array]=" + has(Property.MACED, data2) + "  (registered FN if both false)");

        fresh("MAC-T7 uByte Byte-cache: g1 i1(marked) uByte(42) f1");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m7 = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, m7);
        MacSpecRuntimeMonitor.MacSpec_uByteEvent((byte)42, m7);
        MacSpecRuntimeMonitor.MacSpec_f1Event(m7, new byte[]{6});
        snap("after f1");
        System.out.println("  MACED[Byte.valueOf(42)]=" + has(Property.MACED, Byte.valueOf((byte)42))
                + "  (true = cache-wide mark, D-S13 over-marking mechanism)");

        fresh("MAC-T8 preparedHMAC read at i2 (writer unwritable per batch A HMC)");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac m8 = macG1("HmacSHA256");
        AlgorithmParameterSpec aps = new java.security.spec.MGF1ParameterSpec("SHA-256");
        MacSpecRuntimeMonitor.MacSpec_i2Event(markedKey, aps, m8);
        snap("after i2 (guaranteed-fire UnsatisfiedConstraint)");

        fresh("MAC-T9 f3 unbound broadcast: two Macs, one doFinal(byte[],int)");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        Mac mA = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, mA);   // mA at state 1 (ready for finals)
        Mac mB = macG1("HmacSHA256");                            // mB at state 2 (awaiting init)
        MacSpecRuntimeMonitor.MacSpec_f3Event(new byte[]{7,7}, 0); // one call, NO Mac bound
        snap("after single f3 (any InvalidSequence here hit the innocent mB)");
        System.out.println("  accepting(mA)=" + ExecutionContext.instance().isInAcceptingState(mA)
                + " accepting(mB)=" + ExecutionContext.instance().isInAcceptingState(mB));

        fresh("MAC-T10 !encrypted live read at f3: output buffer marked ENCRYPTED");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, markedKey);
        byte[] encBuf = new byte[]{8,8};
        ExecutionContext.instance().setProperty(Property.ENCRYPTED, encBuf);
        Mac mC = macG1("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(markedKey, mC);
        MacSpecRuntimeMonitor.MacSpec_f3Event(encBuf, 0);
        snap("after f3 (expect UnsatisfiedConstraint: Mac over Cipher output)");

        // ===================== MDG =====================
        fresh("MDG-T1 conformant with reuse: g1(SHA-256) u d1 u d1");
        MessageDigest d1 = mdgG1("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d1);
        byte[] dig1 = new byte[]{1};
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d1, dig1);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d1);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d1, new byte[]{2});
        snap("after 2 cycles");
        System.out.println("  DIGESTED[out1]=" + has(Property.DIGESTED, dig1));

        fresh("MDG-T2 one-shot: g1(SHA-256) d2");
        MessageDigest d2 = mdgG1("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d2Event(d2, new byte[]{3});
        snap("after d2");

        fresh("MDG-T3 unsafe 1-arg carrier: g4(MD2) u d1");
        MessageDigest d3 = mdgG1("MD2");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d3);
        snap("after update");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d3, new byte[]{4});
        snap("after d1");

        fresh("MDG-T4 invisible unsafe 2-arg: (no g) u d1 -> empty-label UnsafeAlgorithm");
        MessageDigest d4 = MessageDigest.getInstance("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d4);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d4, new byte[]{5});
        snap("after u d1 (H4 'but found .' shape)");

        fresh("MDG-T5 (String,Provider) safe captured: g3 u d1");
        MessageDigest d5 = mdgG3("SHA-256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d5);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d5, new byte[]{6});
        snap("after d1 (expect 0)");

        fresh("MDG-T6 folding/alias FN vs raw list: g1(\"md5\") u d1 and g1(\"SHA256\") u d1");
        MessageDigest d6 = mdgG1("md5");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d6);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d6, new byte[]{7});
        MessageDigest d7 = mdgG1("SHA256");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(d7);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(d7, new byte[]{8});
        snap("after both (0 errors = 2 FN witnesses vs raw literal set)");

        // ===================== KPG =====================
        fresh("KPG-T1 conformant: g1(RSA) initialize(2048) generateKeyPair()");
        KeyPairGenerator k1 = kpgG1("RSA");
        kpgInit1(2048, k1);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k1, realKp);
        snap("after gen");
        System.out.println("  GENERATED_KEY_PAIR[kp]=" + has(Property.GENERATED_KEY_PAIR, realKp)
                + " accepting=" + ExecutionContext.instance().isInAcceptingState(k1));

        fresh("KPG-T2 gen-without-init + fail-sink cascade: g1(RSA) gen gen");
        KeyPairGenerator k2 = kpgG1("RSA");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k2, realKp);
        snap("after first gen (flag consistent with rule)");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k2, realKp);
        snap("after second gen (sink: one more InvalidSequence, no __RESET)");
        System.out.println("  GENERATED_KEY_PAIR[kp] after sink removes=" + has(Property.GENERATED_KEY_PAIR, realKp));

        fresh("KPG-T3 bad size then gen: g1(RSA) initialize(1024) gen");
        KeyPairGenerator k3 = kpgG1("RSA");
        kpgInit1(1024, k3);
        snap("after initError (expect InvalidKeySize only)");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k3, realKp);
        snap("after gen (spurious InvalidSequence: rule ORDER is Gets,Inits,Gen and i3 IS an Inits)");

        fresh("KPG-T4 bad size 2-arg suppressed: g1(RSA) initialize(1024, sr) gen");
        KeyPairGenerator k4 = kpgG1("RSA");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init2Event(1024, new SecureRandom(), k4);
        snap("after suppressed init2 (expect NO InvalidKeySize - FN of the specific error)");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k4, realKp);
        snap("after gen (spurious InvalidSequence instead)");

        fresh("KPG-T5 NPE on invisible creation: (no g) initialize(2048)");
        KeyPairGenerator k5 = KeyPairGenerator.getInstance("RSA");
        try {
            kpgInit1(2048, k5);
            snap("no exception");
        } catch (Throwable t) {
            System.out.println("  THROWN to caller: " + t.getClass().getName() + ": " + t.getMessage());
            StackTraceElement top = t.getStackTrace()[0];
            System.out.println("  at " + top);
        }

        fresh("KPG-T6 carrier EC: g3(EC) initialize(256) gen");
        KeyPairGenerator k6 = kpgG1("EC");
        kpgInit1(256, k6);
        snap("after init (UnsafeAlgorithm + spurious InvalidSequence, pilot H2 shape)");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k6, realKp);
        snap("after gen (sink cascade)");

        fresh("KPG-T7 initError-then-good over-acceptance: g1(RSA) init(1024) init(2048) gen");
        KeyPairGenerator k7 = kpgG1("RSA");
        kpgInit1(1024, k7);
        kpgInit1(2048, k7);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k7, realKp);
        snap("expect InvalidKeySize only; rule ORDER (exactly one Inits) is violated silently");
        System.out.println("  accepting=" + ExecutionContext.instance().isInAcceptingState(k7));

        fresh("KPG-CHAIN-T1 edge KPG->KeyPairSpec->SignatureSpec (generateKeyPair route)");
        KeyPairGenerator k8 = kpgG1("RSA");
        kpgInit1(2048, k8);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k8, realKp);
        snap("KPG accepted");
        // app now calls realKp.getPrivate(): KeyPairSpec monitor born at gpr (c1 is the
        // constructor, which generateKeyPair never runs through app code)
        KeyPairSpecRuntimeMonitor.KeyPairSpec_gprEvent(realKp, priv);
        snap("after KeyPairSpec gpr (batch B shape: InvalidSequence FP from the reader spec)");
        System.out.println("  GENERATED_PRIVATE_KEY[priv]=" + has(Property.GENERATED_PRIVATE_KEY, priv));
        Signature sg = sigG1("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, sg);
        snap("after SIG initSign (expect NO UnsatisfiedConstraint: mark delivered)");

        // ===================== SRD =====================
        fresh("SRD-T1 nextBytes twice: c1 nB nB nB");
        SecureRandom r1 = srdC1();
        srdNB(r1, new byte[8]);
        snap("after 1st nextBytes (expect 0)");
        srdNB(r1, new byte[8]);
        snap("after 2nd nextBytes (missing end->next2 row: expect InvalidSequence FP)");
        srdNB(r1, new byte[8]);
        snap("after 3rd nextBytes");

        fresh("SRD-T2 conformant: c1 nB; writer semantics");
        SecureRandom r2 = srdC1();
        byte[] rnd = new byte[8];
        srdNB(r2, rnd);
        snap("after nB");
        System.out.println("  RANDOMIZED[sr]=" + has(Property.RANDOMIZED, r2)
                + " RANDOMIZED[bytes]=" + has(Property.RANDOMIZED, rnd)
                + " accepting=" + ExecutionContext.instance().isInAcceptingState(r2));

        fresh("SRD-T3 seed-after-use over-acceptance: c1 nB setSeed(long)");
        SecureRandom r3 = srdC1();
        srdNB(r3, new byte[8]);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_setSeed1Event(r3);
        snap("after setSeed (raw ORDER Ins,Seeds?,Ends* is violated; expect silence = FN)");

        fresh("SRD-T4 c3 silent: new SecureRandom(unrandomizedSeed) nB");
        byte[] plainSeed = new byte[]{1,1,1,1};
        SecureRandom r4 = srdC(plainSeed);
        srdNB(r4, rnd);
        snap("whole trace (REQUIRES randomized[seed] violated; expect ZERO reports = silent FN)");
        System.out.println("  RANDOMIZED[sr]=" + has(Property.RANDOMIZED, r4)
                + " RANDOMIZED[bytes-from-unsafe]=" + has(Property.RANDOMIZED, rnd));

        fresh("SRD-T5 unsafe getInstance admitted: g4(NativePRNG) nB setSeed1");
        SecureRandom r5 = srdG1("NativePRNG");
        byte[] rnd5 = new byte[8];
        srdNB(r5, rnd5);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_setSeed1Event(r5);
        snap("expect exactly 1 UnsafeAlgorithm, no InvalidSequence (gh101 unsafeInit verified)");
        System.out.println("  RANDOMIZED[sr]=" + has(Property.RANDOMIZED, r5)
                + " RANDOMIZED[bytes-from-unsafe-alg]=" + has(Property.RANDOMIZED, rnd5));

        fresh("SRD-T6 invisible unsafe 2-arg: (no g) nB");
        SecureRandom r6 = new SecureRandom();
        srdNB(r6, new byte[8]);
        snap("expect InvalidSequence FP and NO UnsafeAlgorithm");

        fresh("SRD-T7 canonical seeded use: c1 setSeed(long) nB");
        SecureRandom r7 = srdC1();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_setSeed1Event(r7);
        snap("after setSeed (expect 0)");
        srdNB(r7, new byte[8]);
        snap("after nextBytes (rule-conformant Ins,Seeds,Ends: expect InvalidSequence FP)");

        fresh("SRD-T8 nextInt writes + Integer cache: c1 nextInt(16) nB");
        SecureRandom r8 = srdC1();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(r8, 16);
        System.out.println("  RANDOMIZED[Integer.valueOf(16)]=" + has(Property.RANDOMIZED, Integer.valueOf(16)));
        srdNB(r8, new byte[8]);
        snap("after nextInt then nextBytes (nextInt not a rule event; expect InvalidSequence FP)");

        // ===================== SIG =====================
        fresh("SIG-T1 sign path: g1 i1(marked) u [sign() invisible]");
        ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, priv);
        Signature s1 = sigG1("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, s1);
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(s1);
        // app calls s1.sign(): pointcut return type `byte` vs real byte[] -> no event
        snap("whole trace (0 errors, but no acceptance and SIGNED never marked)");
        System.out.println("  accepting=" + ExecutionContext.instance().isInAcceptingState(s1));

        fresh("SIG-T2 verify path + VERIFIED wrong slot: g1 i4(markedPub) u v1(true)");
        ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
        Signature s2 = sigG1("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, s2);
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(s2);
        byte[] signBytes = new byte[]{7,7,7};
        SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(signBytes, s2, true);
        snap("after v1");
        System.out.println("  VERIFIED[Boolean.TRUE]=" + has(Property.VERIFIED, Boolean.TRUE)
                + " VERIFIED[signBytes]=" + has(Property.VERIFIED, signBytes)
                + " accepting=" + ExecutionContext.instance().isInAcceptingState(s2)
                + "  (rule ensures verified[sign] over the BYTES)");

        fresh("SIG-T3 sign-without-update: g1 i1(marked) [sign() invisible]");
        ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, priv);
        Signature s3 = sigG1("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, s3);
        snap("whole trace (raw ORDER requires Updates+ before Signs: violation is silent = FN)");

        fresh("SIG-T4 unmarked private key: g1 i1(unmarked)");
        Signature s4 = sigG1("SHA256withRSA");
        KeyPairGenerator otherKpg = KeyPairGenerator.getInstance("RSA");
        otherKpg.initialize(2048);
        PrivateKey stranger = otherKpg.generateKeyPair().getPrivate();
        SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(stranger, s4);
        snap("expect exactly 1 UnsatisfiedConstraint and NO InvalidSequence (read in body, gh101)");

        fresh("SIG-T5 unsafe carrier: g3(MD2withRSA) i4(marked) u v1");
        ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
        Signature s5 = sigG1("MD2withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, s5);
        snap("after i4 (UnsafeAlgorithm + spurious InvalidSequence, H2 shape)");
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(s5);
        SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(signBytes, s5, true);
        snap("after u v1 (post-__RESET cascade)");

        fresh("SIG-T6 (String,Provider) safe invisible: (no g) i4(marked) u v1");
        ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
        Signature s6 = Signature.getInstance("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, s6);
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(s6);
        SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(signBytes, s6, true);
        snap("empty-label UnsafeAlgorithm + InvalidSequence storm on conformant usage");

        fresh("SIG-T7 branch exclusivity: g1 i1(marked) u v1");
        ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, priv);
        Signature s7 = sigG1("SHA256withRSA");
        SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, s7);
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(s7);
        SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(signBytes, s7, true);
        snap("verify-after-initSign (both oracles flag: consistent InvalidSequence)");

        System.out.println("\nDONE");
    }
}
