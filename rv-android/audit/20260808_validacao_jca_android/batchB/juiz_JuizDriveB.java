package juiz;

// JUDGE batch B - J2-B: independent end-to-end re-execution of the decisive
// counterexamples of the round, driving the ROUND-INPUT generated monitors
// (byte-identical to batchB/generation_manifest.md) through their public static
// event methods - the exact calls the generated advices make - against the
// production runtime jars (rvsec-core 7b4d72aa..., rvsec-logger-csv 6787f411...,
// rv-monitor-rt 0fa65fbc...). Class sits OUTSIDE package mop so __LOC behaves
// as in a woven app (ViolationRecorder filters mop.* frames).
//
// Scenarios (each prints deltas of ErrorCollector.getErrors()):
//  J2a  CIS: two sequential CrySL-legal streams -> FP cascade on the 2nd
//  J2b  CIS: constructor with unmarked cipher -> extra-oracle UnsatisfiedConstraint
//  J2c  COS: [construct,flush,close] -> 0 errors (FN vs Writes+); flush-after-close -> FP
//  J2d  KPR: KeyPairGenerator.generateKeyPair() route -> spurious fail at first getPublic
//  J2e  KPR: two legal constructions -> broadcast contamination + @match marks null
//  J2f  KPR: both REQUIRES violated at ONE line -> dedupe keeps 1 of 2 clauses
//  J2g  SKY: unmarked key ge suppressed (no RANDOMIZED); d;ge;d violations silent;
//            re-marked key ge in dead state still writes RANDOMIZED
//  J2h  PBK: user-typed password + randomized salt + iter=10000 -> accused + SPECCED_KEY
//            withheld; legal clearPassword adds spurious InvalidSeq (delayed residue)
//  J2i  PBK: err1 message text "1000" vs enforced 10000; 1-line vs 3-line dedupe control

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.PBEKeySpec;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.ArrayList;
import java.util.List;

import mop.CipherInputStreamSpecRuntimeMonitor;
import mop.CipherOutputStreamSpecRuntimeMonitor;
import mop.KeyPairSpecRuntimeMonitor;
import mop.SecretKeySpecRuntimeMonitor;
import mop.PBEKeySpecSpecRuntimeMonitor;

public class JuizDriveB {

    static java.util.Set<ErrorDescription> seen = new java.util.HashSet<>();

    static List<ErrorDescription> delta() {
        List<ErrorDescription> d = new ArrayList<>();
        for (ErrorDescription e : ErrorCollector.instance().getErrors())
            if (!seen.contains(e)) d.add(e);
        seen = new java.util.HashSet<>(ErrorCollector.instance().getErrors());
        d.sort(java.util.Comparator.comparing(e -> e.getErrorSummary().toString()));
        return d;
    }

    static void show(String tag, List<ErrorDescription> d) {
        System.out.println(tag + " deltaErrors=" + d.size());
        for (ErrorDescription e : d)
            System.out.println("    " + e.getErrorSummary() + " expecting=[" + e.getExpecting() + "]");
    }

    public static void main(String[] args) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();
        ErrorCollector.instance(); // init
        seen = new java.util.HashSet<>(ErrorCollector.instance().getErrors());

        // ---------- J2a CIS: two sequential legal streams ----------
        Cipher aes = Cipher.getInstance("AES");
        ctx.setProperty(Property.GENERATED_CIPHER, aes); // oracle-legal cipher, marked
        ByteArrayInputStream in1 = new ByteArrayInputStream(new byte[]{1, 2});
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in1, aes);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        show("J2a CIS stream1 (legal)", delta());
        ByteArrayInputStream in2 = new ByteArrayInputStream(new byte[]{3, 4});
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(in2, aes);
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_r1Event();
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_cl1Event();
        show("J2a CIS stream2 (legal, same process)", delta());

        // ---------- J2b CIS: unmarked cipher at construction ----------
        Cipher aes2 = Cipher.getInstance("AES"); // NOT marked: raw api30 rule has no REQUIRES
        CipherInputStreamSpecRuntimeMonitor.CipherInputStreamSpec_c1Event(new ByteArrayInputStream(new byte[]{9}), aes2);
        show("J2b CIS ctor with unmarked cipher (oracle-legal)", delta());

        // ---------- J2c COS: flush both directions ----------
        ctx.setProperty(Property.GENERATED_CIPHER, aes);
        ByteArrayOutputStream out1 = new ByteArrayOutputStream();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(out1, aes);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        show("J2c COS [construct,flush,close] NO write (rule rejects: Writes+)", delta());
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_c1Event(new ByteArrayOutputStream(), aes);
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_w1Event();
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_clEvent();
        show("J2c COS legal cycle (may inherit global-monitor state)", delta());
        CipherOutputStreamSpecRuntimeMonitor.CipherOutputStreamSpec_flEvent();
        show("J2c COS flush AFTER close (rule does not observe flush)", delta());

        // ---------- J2d KPR: canonical generator route ----------
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
        kpg.initialize(256);
        KeyPair kpGen = kpg.generateKeyPair();
        KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kpGen, kpGen.getPublic());
        show("J2d KPR generateKeyPair() then getPublic() (CrySL-legal: co?)", delta());

        // ---------- J2e KPR: two legal constructions, broadcast ----------
        KeyPair kpSrc1 = kpg.generateKeyPair();
        KeyPair kpSrc2 = kpg.generateKeyPair();
        ctx.setProperty(Property.GENERATED_PUBLIC_KEY, kpSrc1.getPublic());
        ctx.setProperty(Property.GENERATED_PRIVATE_KEY, kpSrc1.getPrivate());
        ctx.setProperty(Property.GENERATED_PUBLIC_KEY, kpSrc2.getPublic());
        ctx.setProperty(Property.GENERATED_PRIVATE_KEY, kpSrc2.getPrivate());
        KeyPair kp1 = new KeyPair(kpSrc1.getPublic(), kpSrc1.getPrivate());
        KeyPair kp2 = new KeyPair(kpSrc2.getPublic(), kpSrc2.getPrivate());
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(kp1.getPublic(), kp1.getPrivate(), kp1);
        show("J2e KPR construction 1 (legal, keys marked)", delta());
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(kp2.getPublic(), kp2.getPrivate(), kp2);
        show("J2e KPR construction 2 (legal)", delta());
        KeyPairSpecRuntimeMonitor.KeyPairSpec_gpuEvent(kp2, kp2.getPublic());
        show("J2e KPR kp2.getPublic() after its own legal c1", delta());
        System.out.println("J2e KPR @match probe: isInAcceptingState(kp1)=" + ctx.isInAcceptingState(kp1)
                + " isInAcceptingState(kp2)=" + ctx.isInAcceptingState(kp2)
                + " isInAcceptingState(null)=" + ctx.isInAcceptingState(null));

        // ---------- J2f KPR: dedupe of the two REQUIRES clauses ----------
        KeyPair kpU = kpg.generateKeyPair(); // keys NOT marked -> both REQUIRES bodies report
        KeyPairSpecRuntimeMonitor.KeyPairSpec_c1Event(kpU.getPublic(), kpU.getPrivate(), new KeyPair(kpU.getPublic(), kpU.getPrivate()));
        show("J2f KPR both REQUIRES violated at ONE __LOC (2 addError calls)", delta());

        // ---------- J2g SKY ----------
        KeyGenerator kg = KeyGenerator.getInstance("AES");
        SecretKey k1 = kg.generateKey(); // oracle-legal key, NOT carrying GENERATED_KEY
        byte[] enc1 = k1.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(k1, enc1);
        System.out.println("J2g SKY unmarked key: RANDOMIZED(enc1)=" + ctx.validate(Property.RANDOMIZED, enc1)
                + " (rule ENSURES preparedKeyMaterial UNCONDITIONALLY)");
        show("J2g SKY unmarked-key getEncoded", delta());
        SecretKey k2 = kg.generateKey();
        ctx.setProperty(Property.GENERATED_KEY, k2);
        SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(k2);           // legal destroy
        SecretKeySpecRuntimeMonitor.SecretKeySpec_dEvent(k2);           // VIOLATION: 2nd destroy
        ctx.setProperty(Property.GENERATED_KEY, k2);                     // re-mark to pass the gate
        byte[] enc2 = k2.getEncoded();
        SecretKeySpecRuntimeMonitor.SecretKeySpec_e1Event(k2, enc2);    // VIOLATION: ge after d
        show("J2g SKY double-destroy + ge-after-destroy (2 oracle violations)", delta());
        System.out.println("J2g SKY dead-state body write: RANDOMIZED(enc2)=" + ctx.validate(Property.RANDOMIZED, enc2));

        // ---------- J2h PBK: canonical user-password case ----------
        char[] pwd = "correct horse battery staple".toCharArray(); // user-typed
        byte[] salt = new byte[16];
        java.security.SecureRandom sr = new java.security.SecureRandom();
        sr.nextBytes(salt);
        ctx.setProperty(Property.RANDOMIZED, salt); // salt randomized, as the rule REQUIRES
        PBEKeySpec spec1 = new PBEKeySpec(pwd, salt, 10000, 256);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c1Event(pwd, salt, 10000, 256, spec1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pwd, salt, 10000, 256, spec1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pwd, salt, 10000, 256, spec1);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err3Event(pwd, salt, 10000, 256, spec1);
        show("J2h PBK user password + random salt + iter=10000 (rule-CONFORMANT)", delta());
        System.out.println("J2h PBK SPECCED_KEY(spec1)=" + ctx.validate(Property.SPECCED_KEY, spec1)
                + " (rule ENSURES speccedKey after c1)");
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_c2Event(spec1);      // the rule's OWN mandatory cP
        show("J2h PBK legal clearPassword after the accused construction", delta());

        // ---------- J2i PBK: message text + dedupe control ----------
        PBEKeySpec spec2 = new PBEKeySpec(pwd, salt, 500, 256);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pwd, salt, 500, 256, spec2); PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pwd, salt, 500, 256, spec2); // ONE line: err1+err2
        show("J2i PBK err1+err2 same __LOC (2 clauses violated)", delta());
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err1Event(pwd, salt, 500, 256, spec2);
        PBEKeySpecSpecRuntimeMonitor.PBEKeySpecSpec_err2Event(pwd, salt, 500, 256, spec2);
        show("J2i PBK err1,err2 on DISTINCT lines (control)", delta());

        System.out.println("TOTAL errors recorded: " + ErrorCollector.instance().getErrors().size());
    }
}
