package gama;

// GAMA discriminating tests, batch B (2026-08-09).
// Drives the round's generated RuntimeMonitors (common batch-B input, hashes in
// batchB/generation_manifest.md) exactly as the generated advices do, on real JDK
// classes, with the production rvsec-core ExecutionContext and the JVM (csv-logger)
// ErrorCollector. Each scenario runs in its own JVM invocation (arg 1) so the
// monitors' static indexing state never leaks between scenarios.
//
// Scenarios:
//   cis    - CipherInputStreamSpec: (a) REQUIRES read stands alone; (b) global-monitor
//            false InvalidSequenceOfMethodCalls on a second, fully conformant stream.
//   cos    - CipherOutputStreamSpec: flush-after-close (rule does not observe flush)
//            -> false InvalidSequenceOfMethodCalls.
//   kpr_a  - KeyPairSpec: getPublic/getPrivate on a KeyPairGenerator-produced pair
//            (rule ORDER co? makes this oracle-legal) -> false InvalidSeq.
//   kpr_b  - KeyPairSpec: second constructor-built pair -> empty-slice broadcast fail;
//            @match marks null, never the KeyPair.
//   kpr_c  - KeyPairSpec: both REQUIRES violated at one site -> dedupe collapses the
//            two clause reports into one record.
//   pbk    - PBEKeySpecSpec: same-__LOC collapse of err1/err2/err3; spurious @fail at
//            clearPassword; forbidden-ctor f1 indistinguishable from @fail.
//   sky    - SecretKeySpec (SecretKey): ge-after-destroy violation is silent; the
//            non-rule GENERATED_KEY condition suppresses the ENSURES write.

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import javax.crypto.Cipher;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

public class GamaBatchBDrive {

    static int lastCount = 0;

    static void dump(String label) {
        int n = ErrorCollector.instance().getErrors().size();
        System.out.println(label + " | errors=" + n + (n != lastCount ? "  <-- +" + (n - lastCount) : ""));
        lastCount = n;
    }

    static void dumpAll(String label) {
        System.out.println("---- " + label + " full error set:");
        for (ErrorDescription e : ErrorCollector.instance().getErrors()) {
            System.out.println("  [" + e.getType() + "] spec=" + e.getSpec()
                    + " loc=" + e.getLocation() + " expecting=" + e.getExpecting());
        }
    }

    public static void main(String[] args) throws Exception {
        String sc = args[0];
        if (sc.equals("cis")) cis();
        if (sc.equals("cos")) cos();
        if (sc.equals("kpr_a")) kprA();
        if (sc.equals("kpr_b")) kprB();
        if (sc.equals("kpr_c")) kprC();
        if (sc.equals("pbk")) pbk();
        if (sc.equals("sky")) sky();
        System.out.flush();
        System.exit(0);
    }

    // ---------------------------------------------------------------- CIS
    static void cis() throws Exception {
        Cipher unmarked = Cipher.getInstance("AES/GCM/NoPadding");
        InputStream in1 = new ByteArrayInputStream(new byte[16]);

        System.out.println("== CIS (a): c1 with cipher lacking GENERATED_CIPHER (repair check)");
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in1, unmarked);
        dump("after c1(unmarked)");            // expect exactly 1 UnsatisfiedConstraint
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        dump("after r1");                       // expect no new error
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        dump("after cl1");                      // expect no new error
        dumpAll("CIS (a)");

        System.out.println("== CIS (b): two fully conformant sequential streams, marked cipher");
        ErrorCollector.instance().reset();
        lastCount = 0;
        ExecutionContext.instance().reset();
        Cipher marked = Cipher.getInstance("AES/GCM/NoPadding");
        ExecutionContext.instance().setProperty(Property.GENERATED_CIPHER, marked);
        InputStream sA = new ByteArrayInputStream(new byte[16]);
        InputStream sB = new ByteArrayInputStream(new byte[16]);
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(sA, marked);
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        dump("stream A complete (construct,read,close)");   // expect 0
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(sB, marked);
        dump("stream B c1");                     // FALSE InvalidSeq expected here
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        dump("stream B r1");                     // and here
        mop.CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        dump("stream B cl1");                    // and here
        dumpAll("CIS (b)");
    }

    // ---------------------------------------------------------------- COS
    static void cos() throws Exception {
        Cipher marked = Cipher.getInstance("AES/GCM/NoPadding");
        ExecutionContext.instance().setProperty(Property.GENERATED_CIPHER, marked);
        OutputStream out = new ByteArrayOutputStream();
        System.out.println("== COS: construct, write, close (conformant), then flush");
        mop.CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(out, marked);
        mop.CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w1Event();
        mop.CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        dump("after construct+write+close");     // expect 0
        mop.CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent();
        dump("after flush-after-close");         // FALSE InvalidSeq (rule has no flush event)
        dumpAll("COS");
    }

    // ---------------------------------------------------------------- KPR
    static void kprA() throws Exception {
        System.out.println("== KPR (a): KeyPairGenerator-produced pair; rule ORDER 'co?' accepts this");
        KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
        g.initialize(2048);
        KeyPair kp = g.generateKeyPair();
        PublicKey pub = kp.getPublic();
        PrivateKey priv = kp.getPrivate();
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp, pub);
        dump("after getPublic()");               // FALSE InvalidSeq expected
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_gprEvent(kp, priv);
        dump("after getPrivate()");              // second FALSE InvalidSeq expected
        dumpAll("KPR (a)");
    }

    static void kprB() throws Exception {
        System.out.println("== KPR (b): two constructor-built pairs; broadcast + null accepting mark");
        KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
        g.initialize(2048);
        KeyPair src1 = g.generateKeyPair();
        KeyPair src2 = g.generateKeyPair();
        // mark the keys so the REQUIRES reads are satisfied and cannot contribute errors
        ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, src1.getPublic());
        ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, src1.getPrivate());
        ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, src2.getPublic());
        ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, src2.getPrivate());
        KeyPair kp1 = new KeyPair(src1.getPublic(), src1.getPrivate());
        KeyPair kp2 = new KeyPair(src2.getPublic(), src2.getPrivate());

        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(src1.getPublic(), src1.getPrivate(), kp1);
        dump("after c1(kp1)");                   // expect 0 errors; automaton at match
        System.out.println("  isInAcceptingState(kp1) = "
                + ExecutionContext.instance().isInAcceptingState(kp1)
                + "   isInAcceptingState(null) = "
                + ExecutionContext.instance().isInAcceptingState(null));
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp1, kp1.getPublic());
        dump("after kp1.getPublic()");           // expect 0 (bound monitor cloned at match)
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(src2.getPublic(), src2.getPrivate(), kp2);
        dump("after c1(kp2)");                   // FALSE InvalidSeq expected (broadcast)
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp2, kp2.getPublic());
        dump("after kp2.getPublic()");
        System.out.println("  isInAcceptingState(kp1) = "
                + ExecutionContext.instance().isInAcceptingState(kp1)
                + "   isInAcceptingState(kp2) = "
                + ExecutionContext.instance().isInAcceptingState(kp2)
                + "   isInAcceptingState(null) = "
                + ExecutionContext.instance().isInAcceptingState(null));
        dumpAll("KPR (b)");
    }

    static void kprC() throws Exception {
        System.out.println("== KPR (c): both REQUIRES violated at ONE site -> dedupe collapse");
        KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
        g.initialize(2048);
        KeyPair src = g.generateKeyPair();       // keys deliberately NOT marked
        KeyPair kp = new KeyPair(src.getPublic(), src.getPrivate());
        mop.KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(src.getPublic(), src.getPrivate(), kp);
        dump("after c1 with BOTH keys unmonitored"); // two addError attempted, expect 1 kept
        dumpAll("KPR (c)");                      // which clause survived? (arrival order)
    }

    // ---------------------------------------------------------------- PBK
    static void pbk() throws Exception {
        char[] pw = "hunter2".toCharArray();
        byte[] salt = new byte[]{1, 2, 3, 4, 5, 6, 7, 8};

        System.out.println("== PBK (a): weak construction, all four events from one line (as the merged advice does)");
        PBEKeySpec s1 = new PBEKeySpec(pw, salt, 500, 256);
        // one source line = one __LOC, exactly like the single woven joinpoint:
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pw, salt, 500, 256, s1); mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pw, salt, 500, 256, s1); mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pw, salt, 500, 256, s1); mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pw, salt, 500, 256, s1);
        dump("after 4-arg ctor with 3 violated clauses (same __LOC)"); // expect ONE record
        dumpAll("PBK (a) - which clause survived?");
        System.out.println("== PBK (a2): clearPassword on the weak spec (rule ORDER c1, cP is satisfied)");
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s1);
        dump("after clearPassword()");           // spurious @fail InvalidSeq expected
        dumpAll("PBK (a2)");

        System.out.println("== PBK (b): control - the three err events from THREE distinct lines");
        ErrorCollector.instance().reset();
        lastCount = 0;
        PBEKeySpec s2 = new PBEKeySpec(pw, salt, 500, 256);
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pw, salt, 500, 256, s2);
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pw, salt, 500, 256, s2);
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pw, salt, 500, 256, s2);
        dump("after err1+err2+err3 on distinct lines");  // 3 records -> proves the key is __LOC
        dumpAll("PBK (b)");

        System.out.println("== PBK (c): forbidden 1-arg ctor, then clearPassword");
        ErrorCollector.instance().reset();
        lastCount = 0;
        PBEKeySpec s3 = new PBEKeySpec(pw);
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_f1Event(pw, s3);
        dump("after forbidden PBEKeySpec(char[])");  // InvalidSeq 'unknown' from f1 body
        mop.PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s3);
        dump("after clearPassword()");               // second InvalidSeq 'unknown' from @fail
        dumpAll("PBK (c) - two records, same category, both 'unknown'");
    }

    // ---------------------------------------------------------------- SKY
    static void sky() throws Exception {
        SecretKeySpec key = new SecretKeySpec(new byte[16], "AES");
        byte[] enc1 = key.getEncoded();

        System.out.println("== SKY (a): getEncoded on a key without GENERATED_KEY (rule has no such REQUIRES)");
        mop.SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key, enc1);
        System.out.println("  RANDOMIZED(enc1) = "
                + ExecutionContext.instance().validate(Property.RANDOMIZED, enc1)
                + "  (rule ENSURES preparedKeyMaterial unconditionally)");
        dump("after suppressed e1");             // expect 0 errors AND no mark

        System.out.println("== SKY (b): marked key; getEncoded, destroy, getEncoded-after-destroy");
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, key);
        byte[] enc2 = key.getEncoded();
        mop.SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key, enc2);
        System.out.println("  RANDOMIZED(enc2) = "
                + ExecutionContext.instance().validate(Property.RANDOMIZED, enc2));
        mop.SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(key);
        System.out.println("  after d: GENERATED_KEY(key) = "
                + ExecutionContext.instance().validate(Property.GENERATED_KEY, key)
                + "  (NEGATES honoured)");
        byte[] enc3 = key.getEncoded();
        mop.SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(key, enc3);   // ORDER ge*, d? VIOLATED
        System.out.println("  RANDOMIZED(enc3) = "
                + ExecutionContext.instance().validate(Property.RANDOMIZED, enc3));
        dump("after getEncoded-after-destroy (an ORDER violation)");  // expect 0 errors: SILENT
        mop.SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(key);          // second destroy: also violation
        dump("after second destroy()");                               // expect 0 errors: SILENT
        dumpAll("SKY");
    }
}
