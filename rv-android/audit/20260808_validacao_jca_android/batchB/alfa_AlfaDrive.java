package mop;

/*
 * ALFA batch B - executed drive over the ROUND-INPUT generated monitors
 * (hashes in batchB/generation_manifest.md), compiled against the production
 * runtime jars. Same method as batch A J2/J3: call the generated static event
 * methods exactly as the generated aspect advice does (aspect bodies verified:
 * each advice is a single dispatch call, except PBEKeySpecSpec's 4-arg ctor
 * advice which calls c1,err1,err2,err3 in that order).
 *
 * Every scenario is a trace whose per-object CrySL projection under the RAW
 * api30 rule is stated in the expectation line. ErrorCollector is reset before
 * each event call; the per-call delta is printed, so set-dedupe cannot mask
 * repeated emissions.
 */

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

public class AlfaDrive {

    static int step(String label, Runnable r) {
        ErrorCollector.instance().reset();
        r.run();
        int n = ErrorCollector.instance().getErrors().size();
        StringBuilder sb = new StringBuilder();
        for (ErrorDescription e : ErrorCollector.instance().getErrors())
            sb.append(" [").append(e.getErrorSummary()).append(" expecting=").append(e.getExpecting()).append("]");
        System.out.println("    " + label + " -> errors=" + n + sb);
        return n;
    }

    public static void main(String[] args) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();

        System.out.println("== CIS-a: one legal stream, cipher marked (oracle: legal; expect 0 errors)");
        Cipher c1 = Cipher.getInstance("AES");
        ctx.setProperty(Property.GENERATED_CIPHER, c1); // simulates CipherSpec's init-time write
        InputStream in1 = new ByteArrayInputStream(new byte[]{1, 2, 3});
        int a = 0;
        a += step("c1(is1,cipher_marked)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in1, c1));
        a += step("r1(read)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event());
        a += step("cl1(close)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event());
        System.out.println("  CIS-a total=" + a + " (oracle expects 0)");

        System.out.println("== CIS-b: SECOND legal stream, same process (oracle: legal; global monitor cascade expected)");
        Cipher c2 = Cipher.getInstance("AES");
        ctx.setProperty(Property.GENERATED_CIPHER, c2);
        InputStream in2 = new ByteArrayInputStream(new byte[]{4, 5});
        int b = 0;
        b += step("c1(is2,cipher_marked)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in2, c2));
        b += step("r1(read)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event());
        b += step("cl1(close)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event());
        System.out.println("  CIS-b total=" + b + " (oracle expects 0; every error is a false positive)");

        System.out.println("== CIS-c: ctor with UNMARKED cipher (raw api30 rule has no REQUIRES; oracle: legal)");
        Cipher c3 = Cipher.getInstance("AES"); // never marked
        InputStream in3 = new ByteArrayInputStream(new byte[]{6});
        int cc = step("c1(is3,cipher_unmarked)", () -> CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in3, c3));
        System.out.println("  CIS-c total=" + cc + " (oracle expects 0)");

        System.out.println("== COS-a: construct, flush, close - NO write (oracle: Writes+ unmet, VIOLATION; expect a report)");
        Cipher c4 = Cipher.getInstance("AES");
        ctx.setProperty(Property.GENERATED_CIPHER, c4);
        OutputStream os1 = new ByteArrayOutputStream();
        int d = 0;
        d += step("c1(os1,cipher_marked)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os1, c4));
        d += step("fl(flush)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent());
        d += step("cl(close)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent());
        System.out.println("  COS-a total=" + d + " (oracle expects >=1: close before any write; 0 = false negative)");

        System.out.println("== COS-b: flush AFTER close on a second, fully legal stream (write then close then flush)");
        Cipher c5 = Cipher.getInstance("AES");
        ctx.setProperty(Property.GENERATED_CIPHER, c5);
        OutputStream os2 = new ByteArrayOutputStream();
        int e = 0;
        e += step("c1(os2,cipher_marked)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(os2, c5));
        e += step("w1(write)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w1Event());
        e += step("cl(close)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent());
        e += step("fl(flush after close)", () -> CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent());
        System.out.println("  COS-b total=" + e + " (flush is not in the rule's alphabet; oracle expects 0)");

        System.out.println("== KPR-a: generator-obtained KeyPair, getPublic() first (rule ORDER co?,... : legal)");
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
        KeyPair kpA = kpg.generateKeyPair();
        int f = step("gpu(kpA.getPublic)", () -> KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kpA, kpA.getPublic()));
        System.out.println("  KPR-a total=" + f + " (oracle expects 0)");

        System.out.println("== KPR-b: two constructed KeyPairs, both predicates held (oracle: both legal)");
        PublicKey pub = kpA.getPublic();
        PrivateKey priv = kpA.getPrivate();
        ctx.setProperty(Property.GENERATED_PUBLIC_KEY, pub);
        ctx.setProperty(Property.GENERATED_PRIVATE_KEY, priv);
        KeyPair kp1 = new KeyPair(pub, priv);
        KeyPair kp2 = new KeyPair(pub, priv);
        int g = 0;
        g += step("c1(kp1)", () -> KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(pub, priv, kp1));
        g += step("c1(kp2)", () -> KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(pub, priv, kp2));
        g += step("gpu(kp1.getPublic)", () -> KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp1, pub));
        System.out.println("  KPR-b total=" + g + " (oracle expects 0)");

        System.out.println("== PBK-a: iter=500, salt+password RANDOMIZED, then clearPassword (oracle: exactly 1 ConstraintError at ctor, cP legal)");
        char[] pwd1 = {'a', 'b'};
        byte[] salt1 = {9, 9};
        ctx.setProperty(Property.RANDOMIZED, pwd1);
        ctx.setProperty(Property.RANDOMIZED, salt1);
        PBEKeySpec s1 = new PBEKeySpec(pwd1, salt1, 500, 128);
        int h = 0;
        h += step("ctor4 iter=500 (advice: c1,err1,err2,err3)", () -> {
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pwd1, salt1, 500, 128, s1);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pwd1, salt1, 500, 128, s1);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pwd1, salt1, 500, 128, s1);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pwd1, salt1, 500, 128, s1);
        });
        h += step("c2(clearPassword) [LEGAL]", () -> PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s1));
        System.out.println("  PBK-a total=" + h + " (oracle expects 1; anything at the c2 step is a false positive)");

        System.out.println("== PBK-b: iter=10000, salt RANDOMIZED, password NOT (oracle: fully legal - only randomized[salt] is required)");
        char[] pwd2 = {'u', 's', 'e', 'r'}; // user-typed password: never RANDOMIZED
        byte[] salt2 = {1, 2, 3};
        ctx.setProperty(Property.RANDOMIZED, salt2);
        PBEKeySpec s2 = new PBEKeySpec(pwd2, salt2, 10000, 128);
        int i = 0;
        i += step("ctor4 iter=10000 pwd-user (advice: c1,err1,err2,err3)", () -> {
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pwd2, salt2, 10000, 128, s2);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pwd2, salt2, 10000, 128, s2);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pwd2, salt2, 10000, 128, s2);
            PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pwd2, salt2, 10000, 128, s2);
        });
        i += step("c2(clearPassword) [LEGAL]", () -> PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s2));
        System.out.println("  PBK-b total=" + i + " (oracle expects 0; SPECCED_KEY earned=" + ctx.validate(Property.SPECCED_KEY, s2) + ", oracle grants speccedKey)");

        System.out.println("== PBK-c: FORBIDDEN 1-arg ctor then clearPassword (oracle: 1 ForbiddenMethodError; f1=>c1 so cP is legal)");
        char[] pwd3 = {'x'};
        PBEKeySpec s3 = new PBEKeySpec(pwd3);
        int j = 0;
        j += step("f1(ctor1)", () -> PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_f1Event(pwd3, s3));
        j += step("c2(clearPassword) [LEGAL under f1=>c1]", () -> PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(s3));
        System.out.println("  PBK-c total=" + j + " (oracle expects 1, category forbidden-method)");

        System.out.println("== SKY: gate + silent order violations (oracle: ge legal; ge-after-d and d-after-d are violations)");
        SecretKey k1 = new SecretKeySpec(new byte[]{1, 2, 3, 4}, "AES"); // no GENERATED_KEY mark
        byte[] enc1 = k1.getEncoded();
        int k = 0;
        k += step("e1(getEncoded) unmarked key [oracle LEGAL, ensures preparedKeyMaterial]",
                () -> SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(k1, enc1));
        System.out.println("    -> RANDOMIZED(preparedKeyMaterial surrogate) written for enc1: " + ctx.validate(Property.RANDOMIZED, enc1) + " (oracle: must hold)");
        SecretKey k2 = new SecretKeySpec(new byte[]{5, 6, 7, 8}, "AES");
        ctx.setProperty(Property.GENERATED_KEY, k2); // simulates KeyGeneratorSpec/SecretKeySpecSpec write
        byte[] enc2 = k2.getEncoded();
        k += step("e1(getEncoded) marked key [oracle LEGAL]", () -> SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(k2, enc2));
        System.out.println("    -> RANDOMIZED written for enc2: " + ctx.validate(Property.RANDOMIZED, enc2));
        k += step("d(destroy) [oracle LEGAL]", () -> SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(k2));
        byte[] enc3 = k2.getEncoded();
        k += step("e1(getEncoded) AFTER destroy [oracle VIOLATION ge after d]", () -> SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(k2, enc3));
        k += step("d(destroy) AGAIN [oracle VIOLATION d twice]", () -> SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(k2));
        System.out.println("  SKY total=" + k + " (oracle expects 2 violations reported; 0 = two false negatives)");

        System.out.println("== done");
    }
}
