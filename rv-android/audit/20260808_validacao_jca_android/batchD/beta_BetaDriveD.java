import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.Signature;
import java.util.*;

/**
 * Agent Beta batch D - ajc-woven dynamic drive. Compile-time woven by ajc
 * 1.9.25.1 with the production merged MultiSpec_1MonitorAspect.aj (23 specs):
 * every call reaches the generated monitors through the REAL AspectJ capture
 * path with real JDK objects. PASS/FAIL lines are harness expectations;
 * MEASURE lines record findings (expected defect behavior).
 */
public class BetaDriveD {
    static int failures = 0;
    static ExecutionContext ec = ExecutionContext.instance();
    static List<ErrorDescription> snapshot = new ArrayList<>();

    static void check(String label, boolean cond, String detail) {
        System.out.println((cond ? "PASS " : "FAIL ") + label + (detail.isEmpty() ? "" : "  [" + detail + "]"));
        if (!cond) failures++;
    }
    static List<ErrorDescription> errs() { return new ArrayList<>(ErrorCollector.instance().getErrors()); }
    static List<ErrorDescription> deltaList() {
        List<ErrorDescription> now = errs();
        List<ErrorDescription> d = new ArrayList<>();
        List<ErrorDescription> seen = new ArrayList<>(snapshot);
        for (ErrorDescription e : now) { if (!seen.remove(e)) d.add(e); }
        return d;
    }
    static String delta() {
        StringBuilder sb = new StringBuilder();
        for (ErrorDescription e : deltaList()) sb.append(e.getType()).append("/").append(e.getSpec()).append(" ");
        return sb.toString().trim();
    }
    static int countDelta(String type, String spec) {
        int n = 0;
        for (ErrorDescription e : deltaList())
            if (e.getType().toString().equals(type) && e.getSpec().equals(spec)) n++;
        return n;
    }
    static void snap() { snapshot = errs(); }

    public static void main(String[] args) throws Exception {
        // KGN feeder: monitored key so Mac.init's GENERATED_KEY gate opens.
        KeyGenerator kg = KeyGenerator.getInstance("AES");
        SecretKey key = kg.generateKey();
        snap();
        byte[] data1 = "batchD-data-1".getBytes();
        byte[] data2 = "batchD-data-2".getBytes();

        // ---- MAC-a: two-object interleaving, happy paths (f2 and f1) ----
        Mac A = Mac.getInstance("HmacSHA256");
        Mac B = Mac.getInstance("HmacSHA256");
        A.init(key); B.init(key);
        A.update(data1);
        byte[] outB = B.doFinal(data2);          // B: g1 i1 f2 -> match
        byte[] outA = A.doFinal();               // A: g1 i1 uArr f1 -> match
        check("MAC-a1 no errors on two interleaved legal Macs", deltaList().isEmpty(), delta());
        check("MAC-a2 A accepting", ec.isInAcceptingState(A), "");
        check("MAC-a3 B accepting", ec.isInAcceptingState(B), "");
        check("MAC-a4 MACED(data1) written at A.doFinal", ec.validate(Property.MACED, data1), "");
        check("MAC-a5 MACED(data2) written at B.doFinal", ec.validate(Property.MACED, data2), "");
        check("MAC-a6 GENERATED_MAC(outA)", ec.validate(Property.GENERATED_MAC, outA), "");
        check("MAC-a7 GENERATED_MAC(outB)", ec.validate(Property.GENERATED_MAC, outB), "");
        snap();

        // ---- MAC-b: f3 route doFinal(byte[],int) — dead pointcut on ajc ----
        Mac C = Mac.getInstance("HmacSHA256");
        C.init(key);
        byte[] data3 = "batchD-data-3".getBytes();
        C.update(data3);
        byte[] outC = new byte[C.getMacLength()];
        C.doFinal(outC, 0);                      // CrySL f3; expect NO event (ajc)
        System.out.println("MEASURE MAC-b1 f3 fired? GENERATED_MAC(outC)=" + ec.validate(Property.GENERATED_MAC, outC)
                + " MACED(data3)=" + ec.validate(Property.MACED, data3)
                + " C accepting=" + ec.isInAcceptingState(C) + " delta=[" + delta() + "]");
        C.update(data3);                          // would be fail after a seen f3
        System.out.println("MEASURE MAC-b2 update after doFinal(out,0) delta=[" + delta() + "] (empty => monitor never saw f3)");
        snap();

        // ---- MAC-c: unsafe algorithm route g3 then init (residue check) ----
        Mac D = Mac.getInstance("HmacSHA3-256"); // available in JDK, not in safe list -> g3
        D.init(key);                              // i1: UnsafeAlgorithm in body; automaton g3 i1 -> ?
        System.out.println("MEASURE MAC-c1 unsafe route delta=[" + delta() + "] UnsafeAlg=" + countDelta("UnsafeAlgorithm", "MacSpec")
                + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "MacSpec"));
        snap();

        // ---- MAC-d: init with unmonitored key — i1 condition suppression ----
        Mac E = Mac.getInstance("HmacSHA256");
        SecretKey rawKey = new SecretKeySpec(new byte[32], "HmacSHA256");
        E.init(rawKey);                           // i1 condition(validate GENERATED_KEY)=false -> suppressed
        byte[] outE = E.doFinal();                // f1 straight after g1 -> fail expected
        System.out.println("MEASURE MAC-d1 unmonitored-key init delta=[" + delta() + "] UnsatisfiedConstraint="
                + countDelta("UnsatisfiedConstraint", "MacSpec") + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "MacSpec"));
        snap();

        // ---- MDG-a: happy update+digest ----
        MessageDigest d1 = MessageDigest.getInstance("SHA-256");
        d1.update(data1);
        byte[] h1 = d1.digest();
        check("MDG-a1 no errors on legal digest", deltaList().isEmpty(), delta());
        check("MDG-a2 accepting", ec.isInAcceptingState(d1), "");
        check("MDG-a3 DIGESTED(h1)", ec.validate(Property.DIGESTED, h1), "");
        snap();

        // ---- MDG-b: unsafe algorithm (MD2), update reports; residue check ----
        MessageDigest d2 = MessageDigest.getInstance("MD2"); // not in list -> g4 (g1 suppressed)
        d2.update(data1);                                     // body reports UnsafeAlgorithm
        System.out.println("MEASURE MDG-b1 unsafe route delta=[" + delta() + "] UnsafeAlg=" + countDelta("UnsafeAlgorithm", "MessageDigestSpec")
                + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "MessageDigestSpec"));
        snap();

        // ---- MDG-c: g1/g4 merged-advice order on a safe first call ----
        MessageDigest d3 = MessageDigest.getInstance("sha-256"); // folding; g1 sets field before g4's condition reads it
        byte[] h3 = d3.digest(data1);                            // d2 direct (DWOU) - legal
        check("MDG-c1 lowercase safe alg: no UnsafeAlgorithm, no InvalidSeq", deltaList().isEmpty(), delta());
        check("MDG-c2 accepting after d2", ec.isInAcceptingState(d3), "");
        snap();

        // ---- KPG-a: RSA happy path ----
        KeyPairGenerator k1 = KeyPairGenerator.getInstance("RSA");
        k1.initialize(2048);
        KeyPair kp = k1.generateKeyPair();
        System.out.println("MEASURE KPG-a0 delta after happy KPG (KeyPairSpec may interject)=[" + delta() + "]");
        check("KPG-a1 GENERATED_KEY_PAIR(kp)", ec.validate(Property.GENERATED_KEY_PAIR, kp), "");
        check("KPG-a2 accepting", ec.isInAcceptingState(k1), "");
        snap();

        // ---- KPG-b: unsafe algorithm EC + valid-for-EC key size (H2 shape) ----
        KeyPairGenerator k2 = KeyPairGenerator.getInstance("EC"); // not in {DH,DSA,RSA} -> g3
        k2.initialize(256);                                       // validate("EC",256)=true -> init1 fires + UnsafeAlgorithm body
        System.out.println("MEASURE KPG-b1 EC route delta=[" + delta() + "] UnsafeAlg=" + countDelta("UnsafeAlgorithm", "KeyPairGeneratorSpec")
                + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "KeyPairGeneratorSpec")
                + " InvalidKeySize=" + countDelta("InvalidKeySize", "KeyPairGeneratorSpec"));
        snap();

        // ---- KPG-c: initError admitted before a corrected initialize (gh101 repair) ----
        KeyPairGenerator k3 = KeyPairGenerator.getInstance("RSA");
        try { k3.initialize(1024); } catch (Exception ex) { }      // validate false -> initError (InvalidKeySize), admitted by initError*
        System.out.println("MEASURE KPG-c1 after initialize(1024) delta=[" + delta() + "]");
        k3.initialize(2048);                                       // init1
        KeyPair kp3 = k3.generateKeyPair();
        System.out.println("MEASURE KPG-c2 corrected-size trace delta=[" + delta() + "] accepting=" + ec.isInAcceptingState(k3));
        snap();

        // ---- KPG-d: genKeyPair() alias route (ajc captures; dexlib2 contrast in dex drive) ----
        KeyPairGenerator k4 = KeyPairGenerator.getInstance("RSA");
        k4.initialize(2048);
        KeyPair kp4 = k4.genKeyPair();
        check("KPG-d1 genKeyPair captured on ajc: GENERATED_KEY_PAIR(kp4)", ec.validate(Property.GENERATED_KEY_PAIR, kp4), "");
        check("KPG-d2 accepting", ec.isInAcceptingState(k4), "");
        check("KPG-d3 no errors", deltaList().isEmpty(), delta());
        snap();

        // ---- SRD-a: constructor route + nextBytes writer ----
        SecureRandom sr1 = new SecureRandom();       // c1 -> init (match1)
        check("SRD-a1 accepting after c1 (match1=init)", ec.isInAcceptingState(sr1), "");
        check("SRD-a2 RANDOMIZED(sr1) written by match1", ec.validate(Property.RANDOMIZED, sr1), "");
        byte[] rb = new byte[16];
        sr1.nextBytes(rb);                            // next2 -> end
        check("SRD-a3 RANDOMIZED(rb) written by next2 (writer of the set-wide edge)", ec.validate(Property.RANDOMIZED, rb), "");
        byte[] gs = sr1.generateSeed(16);             // genSeed -> end
        check("SRD-a4 RANDOMIZED(generateSeed ret)", ec.validate(Property.RANDOMIZED, gs), "");
        check("SRD-a5 no errors on legal SecureRandom", deltaList().isEmpty(), delta());
        snap();

        // ---- SRD-b: 1-arg getInstance safe (ajc: g1 only; dexlib2 contrast fires g2 too) ----
        SecureRandom sr2 = SecureRandom.getInstance("SHA1PRNG");
        check("SRD-b1 no error on getInstance(\"SHA1PRNG\") via ajc", deltaList().isEmpty(), delta());
        check("SRD-b2 accepting", ec.isInAcceptingState(sr2), "");
        snap();

        // ---- SRD-c: 1-arg getInstance unsafe -> g4 (repaired branch), body of next2 still writes ----
        SecureRandom sr3 = SecureRandom.getInstance("NativePRNG"); // not in {SHA1PRNG} -> g4 -> unsafeInit
        byte[] rb3 = new byte[16];
        sr3.nextBytes(rb3);                                        // admitted in unsafeInit
        System.out.println("MEASURE SRD-c1 unsafe 1-arg delta=[" + delta() + "] UnsafeAlg=" + countDelta("UnsafeAlgorithm", "SecureRandomSpec")
                + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "SecureRandomSpec"));
        System.out.println("MEASURE SRD-c2 RANDOMIZED(bytes from unsafe PRNG)=" + ec.validate(Property.RANDOMIZED, rb3)
                + " accepting(sr3)=" + ec.isInAcceptingState(sr3));
        snap();

        // ---- SRD-d: 2-arg getInstance unsafe -> NO event on ajc (args(alg) arity, args(alg,*) condition) ----
        SecureRandom sr4 = SecureRandom.getInstance("NativePRNG", "SUN");
        System.out.println("MEASURE SRD-d1 unsafe 2-arg delta=[" + delta() + "] (empty => silent FN on ajc)"
                + " monitored=" + ec.isInAcceptingState(sr4));
        snap();

        // ---- SRD-e: seeded constructor with unrandomized bytes -> c3, silent; setSeed contrast ----
        byte[] rawSeed = new byte[]{1,2,3,4,5,6,7,8};
        SecureRandom sr5 = new SecureRandom(rawSeed);              // c3 -> unsafeInit, no report
        System.out.println("MEASURE SRD-e1 unrandomized ctor seed delta=[" + delta() + "] (empty => REQUIRES randomized[seed] violation is silent)");
        SecureRandom sr6 = new SecureRandom();                     // c1
        sr6.setSeed(rawSeed);                                      // setSeed3 -> UnsatisfiedConstraint reported
        System.out.println("MEASURE SRD-e2 unrandomized setSeed delta=[" + delta() + "] UnsatisfiedConstraint="
                + countDelta("UnsatisfiedConstraint", "SecureRandomSpec"));
        snap();

        // ---- SRD-f: nextInt(int) marks the BOXED BOUND ----
        SecureRandom sr7 = new SecureRandom();
        int v = sr7.nextInt(100);
        System.out.println("MEASURE SRD-f1 after nextInt(100): RANDOMIZED(Integer 100)=" + ec.validate(Property.RANDOMIZED, 100)
                + " RANDOMIZED(result)=" + ec.validate(Property.RANDOMIZED, v));
        int w = sr7.nextInt() | (1 << 20);                         // force |w| > 127: outside the Integer cache
        // next3 (after returning) marked the boxed RETURN of nextInt(); validate re-boxes:
        System.out.println("MEASURE SRD-f2 after nextInt(): RANDOMIZED(re-boxed non-cached result)="
                + ec.validate(Property.RANDOMIZED, w) + " (false => identity store loses non-cached boxes)");
        snap();

        // ---- SIG-a: verify branch happy (public key from monitored KeyPair) ----
        Signature s1 = Signature.getInstance("SHA256withRSA");
        s1.initVerify(kp.getPublic());
        System.out.println("MEASURE SIG-a0 initVerify delta=[" + delta() + "] (UnsatisfiedConstraint here = generatedPubkey mark state)");
        s1.update(data1);
        byte[] fakeSig = new byte[256];
        boolean ok;
        try { ok = s1.verify(fakeSig); } catch (Exception ex) { ok = false; }
        System.out.println("MEASURE SIG-a1 verify branch delta=[" + delta() + "] accepting=" + ec.isInAcceptingState(s1));
        snap();

        // ---- SIG-b: sign() DEAD event -> silent, then induced spurious fail ----
        Signature s2 = Signature.getInstance("SHA256withRSA");
        s2.initSign(kp.getPrivate());
        System.out.println("MEASURE SIG-b0 initSign delta=[" + delta() + "] (UnsatisfiedConstraint here = generatedPrivkey mark state)");
        snap();
        s2.update(data1);
        byte[] sig = s2.sign();                    // CrySL s1; EXPECT NO EVENT (dead pointcut)
        System.out.println("MEASURE SIG-b1 after sign(): SIGNED(sig)=" + ec.validate(Property.SIGNED, sig)
                + " accepting=" + ec.isInAcceptingState(s2) + " delta=[" + delta() + "]");
        s2.initSign(kp.getPrivate());              // legal restart after a completed sign; monitor never saw s1
        System.out.println("MEASURE SIG-b2 re-initSign after sign delta=[" + delta() + "] InvalidSeq="
                + countDelta("InvalidSequenceOfMethodCalls", "SignatureSpec") + " (>0 => dead s1 turned a legal trace into a violation)");
        snap();

        // ---- SIG-c: unsafe algorithm residue ----
        Signature s3 = Signature.getInstance("MD2withRSA"); // not in list -> g3 (RSA-compatible key)
        s3.initVerify(kp.getPublic());                          // i4 body reports UnsafeAlgorithm; automaton g3 i4 -> ?
        System.out.println("MEASURE SIG-c1 unsafe route delta=[" + delta() + "] UnsafeAlg=" + countDelta("UnsafeAlgorithm", "SignatureSpec")
                + " InvalidSeq=" + countDelta("InvalidSequenceOfMethodCalls", "SignatureSpec"));
        snap();

        // ---- SIG-d: two-object isolation on the verify branch ----
        Signature sA = Signature.getInstance("SHA256withRSA");
        Signature sB = Signature.getInstance("SHA256withRSA");
        sA.initVerify(kp.getPublic()); sB.initVerify(kp.getPublic());
        sA.update(data1); sB.update(data2);
        try { sA.verify(fakeSig); } catch (Exception ex) { }
        try { sB.verify(fakeSig); } catch (Exception ex) { }
        System.out.println("MEASURE SIG-d1 interleaved verify delta=[" + delta() + "] A.accepting=" + ec.isInAcceptingState(sA)
                + " B.accepting=" + ec.isInAcceptingState(sB));

        System.out.println("HARNESS " + (failures == 0 ? "OK" : failures + " failures"));
    }
}
