// J2-D — judge independent drive, batch D (MAC, MDG, KPG, SRD, SIG).
// Drives the FROZEN round RuntimeMonitors' static event methods exactly as the
// generated merged advices emit them (advice order verified in the .aj files),
// with real JDK objects. No weaving; each scenario prints the error DELTA
// (type/spec/expecting) plus the decisive ExecutionContext marks.
// Scenarios D1..D9; 3 reps must be byte-identical.
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.Signature;
import java.util.*;
import java.util.stream.Collectors;

public class JuizDriveD {
    static Set<ErrorDescription> seen = new HashSet<>();

    static void delta(String label) {
        Set<ErrorDescription> now = new HashSet<>(ErrorCollector.instance().getErrors());
        List<String> fresh = now.stream().filter(e -> !seen.contains(e))
                .map(e -> e.getType() + "/" + e.getSpec() + " expecting=" + e.getExpecting())
                .sorted().collect(Collectors.toList());
        seen = now;
        System.out.println("  DELTA " + label + " (" + fresh.size() + "): " + fresh);
    }

    public static void main(String[] args) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();

        System.out.println("== D1: KPG NPE — initialize(int) as first event on an unseen generator ==");
        KeyPairGenerator kA = KeyPairGenerator.getInstance("RSA"); // creation UNSEEN (Provider route has no event)
        try {
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(2048, kA);
            System.out.println("  init1Event: NO exception");
        } catch (Throwable t) {
            System.out.println("  init1Event threw to caller: " + t.getClass().getName());
        }
        try {
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(2048, kA);
            System.out.println("  initErrorEvent: NO exception");
        } catch (Throwable t) {
            System.out.println("  initErrorEvent threw to caller: " + t.getClass().getName());
        }
        delta("D1");

        System.out.println("== D2: SRD repeated nextBytes (canonical usage) ==");
        SecureRandom r1 = new SecureRandom();
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(r1);
        byte[] b1 = new byte[16];
        r1.nextBytes(b1); SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(r1, b1); // call 1
        delta("D2 after nextBytes#1");
        r1.nextBytes(b1); SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(r1, b1); // call 2 (distinct line)
        delta("D2 after nextBytes#2");
        r1.nextBytes(b1); SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(r1, b1); // call 3 (distinct line)
        delta("D2 after nextBytes#3");

        System.out.println("== D3: SRD unsafe getInstance (g1-then-g4 advice) — unsafeInit sink, no pairing; overgrant probe ==");
        SecureRandom r2 = SecureRandom.getInstance("NativePRNG");
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g1Event("NativePRNG", r2);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g4Event("NativePRNG", r2);
        byte[] b2 = new byte[16];
        r2.nextBytes(b2); SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(r2, b2);
        SecureRandomSpecRuntimeMonitor.SecureRandomSpec_setSeed1Event(r2);
        delta("D3");
        System.out.println("  RANDOMIZED[bytes-from-unsafe-instance]=" + ctx.validate(Property.RANDOMIZED, b2)
                + " RANDOMIZED[unsafe sr object]=" + ctx.validate(Property.RANDOMIZED, r2));

        System.out.println("== D4: MAC key gate — safe alg, UNMARKED key: i1 suppressed, doFinal accused ==");
        Mac mA = Mac.getInstance("HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA256", mA);
        MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA256", mA);
        SecretKeySpec unmarked = new SecretKeySpec(new byte[32], "HmacSHA256");
        MacSpecRuntimeMonitor.MacSpec_i1Event(unmarked, mA); // condition validate(GENERATED_KEY,key)=false -> suppressed
        mA.init(unmarked);
        byte[] macOut = mA.doFinal();
        MacSpecRuntimeMonitor.MacSpec_f1Event(mA, macOut);
        delta("D4");

        System.out.println("== D5: MAC alias FN — getInstance(\"HMAC-SHA256\") spec-safe, raw-violating ==");
        Mac mB = Mac.getInstance("HmacSHA256"); // carrier object; alg STRING drives the events
        SecretKeySpec marked = new SecretKeySpec(new byte[32], "HmacSHA256");
        mB.init(marked);
        ctx.setProperty(Property.GENERATED_KEY, marked);
        MacSpecRuntimeMonitor.MacSpec_g1Event("HMAC-SHA256", mB);
        MacSpecRuntimeMonitor.MacSpec_g3Event("HMAC-SHA256", mB);
        MacSpecRuntimeMonitor.MacSpec_i1Event(marked, mB);
        MacSpecRuntimeMonitor.MacSpec_uArrEvent(new byte[8], mB);
        MacSpecRuntimeMonitor.MacSpec_f1Event(mB, mB.doFinal(new byte[8]));
        delta("D5");
        System.out.println("  isInAcceptingState(mB)=" + ctx.isInAcceptingState(mB)
                + "  <- 0 errors + acceptance on an alg the raw 12-literal list rejects = executed FN");

        System.out.println("== D6: MDG carrier — unsafe alg then update/update/digest at distinct sites ==");
        MessageDigest md = MessageDigest.getInstance("MD5"); // carrier object; unsafe STRING drives events
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event("MD2", md);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event("MD2", md);
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md); // site 1
        delta("D6 after update#1");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md); // site 2
        delta("D6 after update#2");
        MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d2Event(md, md.digest(new byte[4])); // site 3
        delta("D6 after d2");

        System.out.println("== D7a: KPG delayed pairing — bad size, then generate (no correction) ==");
        KeyPairGenerator kB = KeyPairGenerator.getInstance("RSA");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("RSA", kB);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("RSA", kB);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(1024, kB);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(1024, kB);
        delta("D7a after initialize(1024)");
        kB.initialize(2048);
        KeyPair kpB = kB.generateKeyPair();
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kB, kpB);
        delta("D7a after generateKeyPair");

        System.out.println("== D7b: KPG correction route — bad size, corrected, then generate ==");
        KeyPairGenerator kC = KeyPairGenerator.getInstance("RSA");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("RSA", kC);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("RSA", kC);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(1024, kC);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(1024, kC);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(2048, kC);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(2048, kC);
        kC.initialize(2048);
        KeyPair kpC = kC.generateKeyPair();
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kC, kpC);
        delta("D7b (expect InvalidKeySize only, no InvalidSeq)");
        System.out.println("  isInAcceptingState(kpgC)=" + ctx.isInAcceptingState(kC)
                + " GENERATED_KEY_PAIR[kpC]=" + ctx.validate(Property.GENERATED_KEY_PAIR, kpC)
                + "  <- CrySL forbids the 2nd Inits: monitor acceptance here = FN direction");

        System.out.println("== D8: SIG VERIFIED written on the boxed Boolean, not the sign bytes ==");
        Signature sV = Signature.getInstance("SHA256withRSA");
        java.security.PublicKey pub = kpC.getPublic();
        ctx.setProperty(Property.GENERATED_PUBLIC_KEY, pub);
        SignatureSpecRuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sV);
        SignatureSpecRuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sV);
        SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, sV);
        SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(sV);
        byte[] signBytes = new byte[64];
        SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(signBytes, sV, true);
        delta("D8");
        System.out.println("  VERIFIED[Boolean.TRUE]=" + ctx.validate(Property.VERIFIED, Boolean.TRUE)
                + " VERIFIED[signBytes]=" + ctx.validate(Property.VERIFIED, signBytes)
                + "  <- rule says verified[sign] (the bytes)");

        System.out.println("== D9: MAC f3 broadcast — one unbound f3 event touches every live Mac monitor ==");
        Mac mX = Mac.getInstance("HmacSHA1");
        SecretKeySpec keyX = new SecretKeySpec(new byte[20], "HmacSHA1");
        ctx.setProperty(Property.GENERATED_KEY, keyX);
        MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA1", mX);
        MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA1", mX);
        MacSpecRuntimeMonitor.MacSpec_i1Event(keyX, mX); // mX at state 1 (in progress: updates position)
        Mac mY = Mac.getInstance("HmacSHA1");
        MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA1", mY);
        MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA1", mY); // mY at state 2 (before init)
        boolean accBefore = ctx.isInAcceptingState(mX);
        MacSpecRuntimeMonitor.MacSpec_f3Event(new byte[16], 0); // NO Mac argument exists to pass
        delta("D9 after one f3Event");
        System.out.println("  isInAcceptingState(mX) before=" + accBefore + " after=" + ctx.isInAcceptingState(mX)
                + "  <- foreign monitor advanced to accepting by an event it never received; innocent mY accused");

        System.out.println("== done ==");
    }
}
