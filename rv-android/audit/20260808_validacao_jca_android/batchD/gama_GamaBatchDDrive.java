package gama;

/*
 * GAMA batch D harness: drives the generated static event methods of the five
 * round monitors (MAC, MDG, KPG, SRD, SIG) exactly as the generated advices do,
 * in the merged monitorCall order verified in the *MonitorAspect.aj / .json:
 *   Mac.getInstance(String)            -> g1Event then g3Event   (one advice)
 *   MessageDigest.getInstance(String)  -> g1Event then g4Event   (one advice)
 *   KeyPairGenerator.getInstance(String)-> g1Event then g3Event  (one advice)
 *   KeyPairGenerator.initialize(int)   -> init1Event then initErrorEvent (one advice)
 *   Signature.getInstance(String)      -> g1Event then g3Event   (one advice)
 *   SecureRandom.getInstance(String)   -> g1 advice then g4 advice (two advices,
 *                                         declaration order g1 before g4 in the .aj)
 * Each scenario MUST run in its own JVM (monitor maps are static). Real JDK
 * objects; upstream predicate writers are simulated via ExecutionContext
 * .setProperty where a scenario needs isolation. Every event call sits on its
 * own source line so __LOC separates records; loops are used only where the
 * dedupe collapse itself is under test.
 */

import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.Signature;
import java.security.spec.AlgorithmParameterSpec;
import javax.crypto.Mac;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import mop.KeyPairGeneratorSpecRuntimeMonitor;
import mop.MacSpecRuntimeMonitor;
import mop.MessageDigestSpecRuntimeMonitor;
import mop.SecureRandomSpecRuntimeMonitor;
import mop.SignatureSpecRuntimeMonitor;

public class GamaBatchDDrive {

    static void dump(String scenario) {
        System.out.println("== scenario " + scenario + ": "
                + ErrorCollector.instance().getErrors().size() + " record(s)");
        for (ErrorDescription e : ErrorCollector.instance().getErrors()) {
            System.out.println("   " + e);
        }
    }

    public static void main(String[] args) throws Exception {
        String s = args[0];

        // Real JDK objects.
        Mac mac1 = Mac.getInstance("HmacSHA256");
        Mac mac2 = Mac.getInstance("HmacSHA256");
        MessageDigest md1 = MessageDigest.getInstance("SHA-256");
        MessageDigest md2 = MessageDigest.getInstance("SHA-256");
        KeyPairGenerator kpg1 = KeyPairGenerator.getInstance("RSA");
        SecureRandom rnd = new SecureRandom();
        Signature sig1 = Signature.getInstance("SHA256withRSA");
        SecretKeySpec hmacKey = new SecretKeySpec(new byte[32], "HmacSHA256");
        KeyPairGenerator realGen = KeyPairGenerator.getInstance("RSA");
        realGen.initialize(2048);
        KeyPair realPair = realGen.generateKeyPair();
        PrivateKey priv = realPair.getPrivate();
        PublicKey pub = realPair.getPublic();
        byte[] buf = new byte[32];
        AlgorithmParameterSpec ivParams = new IvParameterSpec(new byte[16]);

        switch (s) {

        // ---------------- MAC ----------------
        case "mac_a": {
            // H2 immediate: unsafe 1-arg getInstance, then init with a marked key.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY, hmacKey);
            MacSpecRuntimeMonitor.MacSpec_g1Event("DES", mac1);
            MacSpecRuntimeMonitor.MacSpec_g3Event("DES", mac1);
            MacSpecRuntimeMonitor.MacSpec_i1Event(hmacKey, mac1);
            dump(s);
            break;
        }
        case "mac_b": {
            // Extra-oracle GENERATED_KEY gate: safe algorithm, key NOT marked.
            // Rule-conformant trace (api30 Mac has no generatedKey REQUIRES).
            MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_i1Event(hmacKey, mac1);   // suppressed (gate)
            byte[] out1 = new byte[32];
            MacSpecRuntimeMonitor.MacSpec_f1Event(mac1, out1);      // displaced accusation here
            dump(s);
            System.out.println("   GENERATED_MAC(out1) after @fail remove = "
                    + ExecutionContext.instance().validate(Property.GENERATED_MAC, out1));
            break;
        }
        case "mac_c": {
            // H4 live route: init is the monitor's first event (2-arg/Provider
            // creation invisible), field currentAlgorithmInstance == "".
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY, hmacKey);
            MacSpecRuntimeMonitor.MacSpec_i1Event(hmacKey, mac1);
            dump(s);
            break;
        }
        case "mac_d": {
            // f3 empty-slice broadcast: two independent conformant Macs; one
            // doFinal(byte[],int) event broadcast to every monitor.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY, hmacKey);
            MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac2);
            MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac2);
            MacSpecRuntimeMonitor.MacSpec_i1Event(hmacKey, mac1);
            MacSpecRuntimeMonitor.MacSpec_i1Event(hmacKey, mac2);
            System.out.println("   -- before f3 broadcast: 0 records expected: "
                    + ErrorCollector.instance().getErrors().size());
            MacSpecRuntimeMonitor.MacSpec_f3Event(buf, 0);          // broadcast
            byte[] out1 = new byte[32];
            MacSpecRuntimeMonitor.MacSpec_f1Event(mac2, out1);      // mac2's own doFinal
            dump(s);
            break;
        }
        case "mac_e": {
            // PASS side: i2 PREPARED_HMAC read reports alone; conformant finish;
            // MACED / GENERATED_MAC writers verified.
            ExecutionContext.instance().setProperty(Property.GENERATED_KEY, hmacKey);
            MacSpecRuntimeMonitor.MacSpec_g1Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_g3Event("HmacSHA256", mac1);
            MacSpecRuntimeMonitor.MacSpec_i2Event(hmacKey, ivParams, mac1);
            byte[] data = new byte[16];
            MacSpecRuntimeMonitor.MacSpec_uArrEvent(data, mac1);
            byte[] direct = new byte[8];
            byte[] out1 = new byte[32];
            MacSpecRuntimeMonitor.MacSpec_f2Event(direct, mac1, out1);
            dump(s);
            System.out.println("   MACED(pending data) = "
                    + ExecutionContext.instance().validate(Property.MACED, data));
            System.out.println("   MACED(direct input) = "
                    + ExecutionContext.instance().validate(Property.MACED, direct));
            System.out.println("   GENERATED_MAC(out1) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_MAC, out1));
            System.out.println("   isInAcceptingState(mac1) = "
                    + ExecutionContext.instance().isInAcceptingState(mac1));
            break;
        }

        // ---------------- MDG ----------------
        case "mdg_a": {
            // H4 live route: update as first event on an unseen digest (clone /
            // 2-arg-unsafe / Provider-unsafe routes), field == "".
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md1);
            dump(s);
            break;
        }
        case "mdg_b": {
            // Oracle realignment control: MD5 is SAFE under the api30 rule.
            // Also exercises the g1-before-g4 masking of g4's field-not-arg condition.
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event("MD5", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event("MD5", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md1);
            byte[] out = new byte[32];
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(md1, out);
            dump(s);
            break;
        }
        case "mdg_c": {
            // H2 immediate + cascade: unsafe algorithm, then two updates on
            // distinct lines and a digest.
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event("FOO", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event("FOO", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md1);
            byte[] out = new byte[32];
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d2Event(md1, out);
            dump(s);
            break;
        }
        case "mdg_d": {
            // Conformant control.
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event("SHA-256", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event("SHA-256", md1);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md1);
            byte[] out = new byte[32];
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(md1, out);
            dump(s);
            System.out.println("   DIGESTED(out) = "
                    + ExecutionContext.instance().validate(Property.DIGESTED, out));
            break;
        }
        case "mdg_e": {
            // Dedupe collapse control: unsafe algorithm, THREE updates from the
            // SAME source line (loop) -> the per-site key collapses repeats.
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event("FOO", md2);
            MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event("FOO", md2);
            for (int i = 0; i < 3; i++) {
                MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(md2);
            }
            dump(s);
            break;
        }

        // ---------------- KPG ----------------
        case "kpg_a": {
            // H2 immediate: EC is outside the derived allow-list, 256 is a valid
            // EC key size, so init1 fires (validate true) from the g3 state.
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("EC", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("EC", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(256, kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(256, kpg1);
            dump(s);
            break;
        }
        case "kpg_b": {
            // H2 delayed + no-__RESET cascade: RSA with invalid 1024, then gen
            // twice on distinct lines.
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("RSA", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("RSA", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(1024, kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(1024, kpg1);
            System.out.println("   -- after initError (specific alone expected): "
                    + ErrorCollector.instance().getErrors().size() + " record(s)");
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kpg1, realPair);
            System.out.println("   GENERATED_KEY_PAIR(realPair) after gen-fail = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY_PAIR, realPair));
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kpg1, realPair);
            dump(s);
            break;
        }
        case "kpg_c": {
            // NPE probe: initialize(int) as the FIRST event on an unseen
            // generator (the (String,Provider) creation route) -> validate(int)
            // does switch(algorithm) with algorithm == null.
            try {
                KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(2048, kpg1);
                System.out.println("   no exception");
            } catch (Throwable t) {
                System.out.println("   THROWN from init1Event: " + t);
            }
            try {
                KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(2048, kpg1);
                System.out.println("   no exception");
            } catch (Throwable t) {
                System.out.println("   THROWN from initErrorEvent: " + t);
            }
            dump(s);
            break;
        }
        case "kpg_d": {
            // PASS side: DH + unmarked params -> PREPARED_DH read reports alone;
            // conformant gen reaches match.
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("DH", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("DH", kpg1);
            AlgorithmParameterSpec dhParams = new javax.crypto.spec.DHGenParameterSpec(512, 64);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init3Event(dhParams, kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kpg1, realPair);
            dump(s);
            System.out.println("   GENERATED_KEY_PAIR(realPair) = "
                    + ExecutionContext.instance().validate(Property.GENERATED_KEY_PAIR, realPair));
            System.out.println("   isInAcceptingState(kpg1) = "
                    + ExecutionContext.instance().isInAcceptingState(kpg1));
            break;
        }
        case "kpg_f": {
            // Missing initError twin for initialize(int, SecureRandom): invalid
            // size via init2 -> suppressed, nothing matches -> displaced fail at gen.
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("RSA", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event("RSA", kpg1);
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init2Event(1024, rnd, kpg1);
            System.out.println("   -- after init2(1024) (0 records = no InvalidKeySize channel): "
                    + ErrorCollector.instance().getErrors().size() + " record(s)");
            KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(kpg1, realPair);
            dump(s);
            break;
        }

        // ---------------- SRD ----------------
        case "srd_a": {
            // Headline FP: rule ORDER is Ins, Seeds?, Ends* -- nextBytes any
            // number of times. The fsm's end state has no next2 row.
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(rnd);
            byte[] b1 = new byte[16];
            byte[] b2 = new byte[16];
            byte[] b3 = new byte[16];
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b1);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b2);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b3);
            dump(s);
            System.out.println("   RANDOMIZED(b2) despite fail = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, b2));
            break;
        }
        case "srd_a2": {
            // Control: nextInt (next1) has an end->end row; three calls are clean.
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(rnd);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(rnd, 200);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(rnd, 300);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(rnd, 400);
            dump(s);
            break;
        }
        case "srd_b": {
            // Unsafe 1-arg getInstance: specific report alone (unsafeInit
            // philosophy), then nextBytes marks RANDOMIZED from unsafeInit.
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g1Event("FOO", rnd);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_g4Event("FOO", rnd);
            byte[] b1 = new byte[16];
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b1);
            byte[] b2 = new byte[16];
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b2);
            dump(s);
            System.out.println("   RANDOMIZED(b1) from unsafeInit = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, b1));
            System.out.println("   RANDOMIZED(b2) from unsafeInit = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, b2));
            break;
        }
        case "srd_c": {
            // Displaced route: nextBytes as first event (2-arg unsafe getInstance
            // matched nothing).
            byte[] b1 = new byte[16];
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next2Event(rnd, b1);
            dump(s);
            System.out.println("   RANDOMIZED(b1) on the fail path = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, b1));
            break;
        }
        case "srd_d": {
            // Integer-cache over-marking: next1 marks the boxed RANGE argument.
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(rnd);
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(rnd, 100);
            System.out.println("   RANDOMIZED(new box of 100) = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, Integer.valueOf(100)));
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_next1Event(rnd, 1000);
            System.out.println("   RANDOMIZED(new box of 1000) = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, Integer.valueOf(1000)));
            dump(s);
            break;
        }
        case "srd_e": {
            // PASS side: ENSURES randomized[this] after Ins.
            SecureRandomSpecRuntimeMonitor.SecureRandomSpec_c1Event(rnd);
            dump(s);
            System.out.println("   RANDOMIZED(rnd) after c1 = "
                    + ExecutionContext.instance().validate(Property.RANDOMIZED, rnd));
            System.out.println("   isInAcceptingState(rnd) = "
                    + ExecutionContext.instance().isInAcceptingState(rnd));
            break;
        }

        // ---------------- SIG ----------------
        case "sig_a": {
            // H4 + H2 immediate + 3-type same-call stack: initSign as the first
            // event, key NOT marked -> UnsafeAlgorithm "but found ." +
            // UnsatisfiedConstraint + InvalidSequenceOfMethodCalls, one call.
            SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, sig1);
            dump(s);
            break;
        }
        case "sig_b": {
            // Dead s1/s2 consequence: fully conformant sign flow, sign() event
            // can never fire (no `byte sign()` member exists in android-30).
            ExecutionContext.instance().setProperty(Property.GENERATED_PRIVATE_KEY, priv);
            SignatureSpecRuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_i1Event(priv, sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(sig1);
            // s1Event NOT called: the production pointcut cannot match.
            dump(s);
            System.out.println("   isInAcceptingState(sig1) = "
                    + ExecutionContext.instance().isInAcceptingState(sig1));
            byte[] anyOut = new byte[8];
            System.out.println("   SIGNED(anyOut ever) = "
                    + ExecutionContext.instance().validate(Property.SIGNED, anyOut));
            break;
        }
        case "sig_c": {
            // Boolean-cache VERIFIED marking via v1's bound boxed return.
            ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
            SignatureSpecRuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(sig1);
            byte[] sg = new byte[8];
            SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(sg, sig1, true);
            dump(s);
            System.out.println("   VERIFIED(Boolean.TRUE global) = "
                    + ExecutionContext.instance().validate(Property.VERIFIED, Boolean.TRUE));
            System.out.println("   isInAcceptingState(sig1) = "
                    + ExecutionContext.instance().isInAcceptingState(sig1));
            break;
        }
        case "sig_d": {
            // H2 immediate on the verify branch: unsafe algorithm, then initVerify.
            ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
            SignatureSpecRuntimeMonitor.SignatureSpec_g1Event("ECDSAwithFOO", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_g3Event("ECDSAwithFOO", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, sig1);
            dump(s);
            break;
        }
        case "sig_e": {
            // PASS side: conformant verify flow.
            ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, pub);
            SignatureSpecRuntimeMonitor.SignatureSpec_g1Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_g3Event("SHA256withRSA", sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_i4Event(pub, sig1);
            SignatureSpecRuntimeMonitor.SignatureSpec_updateEvent(sig1);
            byte[] sg = new byte[8];
            SignatureSpecRuntimeMonitor.SignatureSpec_v1Event(sg, sig1, true);
            dump(s);
            break;
        }

        default:
            System.out.println("unknown scenario " + s);
        }
    }
}
