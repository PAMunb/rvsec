import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import mop.MonitorWrappers;
import mop.MultiSpec_1RuntimeMonitor;

import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.Signature;
import java.util.*;

/**
 * Agent Beta batch D - dexlib2-path dynamic drive. Calls the EXACT
 * mop/MonitorWrappers.java that WrapperEmitter emitted for the merged 23-spec
 * descriptor over android-30 (hash f01dc17d...), i.e. byte-for-byte what a
 * dexlib2-rewritten call site executes; inline BEFORE/ctor-AFTER events are
 * invoked in the order MonitorInvokeBuilder emits them (event call adjacent to
 * the original invoke). UNTOUCHED sites (per the production weave probe) are
 * exercised as plain calls - exactly what a device would run.
 */
public class BetaDexPathDriveD {
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
        byte[] data1 = "batchD-dex-1".getBytes();
        byte[] data2 = "batchD-dex-2".getBytes();

        // Monitored key via the KGN wrapper route (GENERATED_KEY writer).
        KeyGenerator kg = MonitorWrappers.javax_crypto_KeyGenerator_getInstance("AES");
        SecretKey key = MonitorWrappers.javax_crypto_KeyGenerator_generateKey(kg);
        snap();

        // ---- DX-MAC-anon: doFinal(byte[],int) on an UNMONITORED Mac fires the unbound f3 ----
        Mac anon = Mac.getInstance("HmacSHA256");   // plain call: pretend an unwoven library made it
        anon.init(key);
        byte[] outAnon = new byte[anon.getMacLength()];
        MonitorWrappers.javax_crypto_Mac_doFinal_2(anon, outAnon, 0); // woven site: fires f3Event(output,outOffset) - NO Mac binding
        System.out.println("MEASURE DX-MAC-anon f3 with no live monitors: delta=[" + delta() + "] InvalidSeq="
                + countDelta("InvalidSequenceOfMethodCalls", "MacSpec") + " (>0 => anonymous root monitor accused nobody's trace)");
        snap();

        // ---- DX-MAC-bcast: f3 broadcast reaches EVERY live Mac monitor ----
        Mac A = MonitorWrappers.javax_crypto_Mac_getInstance("HmacSHA256"); // g1(A)
        Mac B = MonitorWrappers.javax_crypto_Mac_getInstance("HmacSHA256"); // g1(B)
        MultiSpec_1RuntimeMonitor.MacSpec_i1Event(key, A); A.init(key);      // inline BEFORE + original call
        MultiSpec_1RuntimeMonitor.MacSpec_i1Event(key, B); B.init(key);
        MonitorWrappers.javax_crypto_Mac_update(A, data1);                   // uArr(A)
        byte[] outA2 = new byte[A.getMacLength()];
        MonitorWrappers.javax_crypto_Mac_doFinal_2(A, outA2, 0);             // f3 - broadcast to A AND B (and the anon root monitor)
        System.out.println("MEASURE DX-MAC-bcast1 after A.doFinal(out,0): delta=[" + delta() + "]"
                + " A.accepting=" + ec.isInAcceptingState(A)
                + " B.accepting=" + ec.isInAcceptingState(B) + " (B true => false accept by broadcast)");
        snap();
        MonitorWrappers.javax_crypto_Mac_update(B, data2);                   // B legal continuation: init then update
        System.out.println("MEASURE DX-MAC-bcast2 B.update after A's f3: delta=[" + delta() + "] InvalidSeq="
                + countDelta("InvalidSequenceOfMethodCalls", "MacSpec") + " (>0 => broadcast f3 poisoned B's monitor)");
        snap();

        // ---- DX-SRD-1: legal 1-arg getInstance fires g1+g2+g4 on the dexlib2 path ----
        SecureRandom sr = MonitorWrappers.java_security_SecureRandom_getInstance("SHA1PRNG");
        System.out.println("MEASURE DX-SRD-1 getInstance(\"SHA1PRNG\") via wrapper: delta=[" + delta() + "] InvalidSeq="
                + countDelta("InvalidSequenceOfMethodCalls", "SecureRandomSpec")
                + " (>0 => args()-ignored expansion fires g2 after g1: FP on the correct call)");
        snap();

        // ---- DX-SRD-2: inherited members are UNTOUCHED: nextInt()/ints() emit nothing ----
        SecureRandom sr2 = new SecureRandom();
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_c1Event(sr2);             // ctor inline-AFTER as woven
        snap();
        int x = sr2.nextInt();                                                // UNTOUCHED site (no wrapper exists)
        sr2.ints(4L);                                                         // UNTOUCHED site
        System.out.println("MEASURE DX-SRD-2 nextInt()/ints() on device path: delta=[" + delta() + "]"
                + " (empty + no RANDOMIZED writes => next3/ints events dead on dexlib2)");
        byte[] nb = new byte[8];
        MultiSpec_1RuntimeMonitor.SecureRandomSpec_next2Event(sr2, nb); sr2.nextBytes(nb); // inline BEFORE survives
        check("DX-SRD-2b nextBytes (declared member, inline) still writes RANDOMIZED", ec.validate(Property.RANDOMIZED, nb), "");
        snap();

        // ---- DX-KPG: genKeyPair() is dropped by findFirstCall; generateKeyPair() wrapped ----
        KeyPairGenerator k1 = MonitorWrappers.java_security_KeyPairGenerator_getInstance("RSA");
        MonitorWrappers.java_security_KeyPairGenerator_initialize(k1, 2048);
        KeyPair kpA = MonitorWrappers.java_security_KeyPairGenerator_generateKeyPair(k1);
        check("DX-KPG-1 generateKeyPair via wrapper marks GENERATED_KEY_PAIR", ec.validate(Property.GENERATED_KEY_PAIR, kpA), "");
        System.out.println("MEASURE DX-KPG-1 delta=[" + delta() + "] accepting=" + ec.isInAcceptingState(k1));
        snap();
        KeyPairGenerator k2 = MonitorWrappers.java_security_KeyPairGenerator_getInstance("RSA");
        MonitorWrappers.java_security_KeyPairGenerator_initialize(k2, 2048);
        KeyPair kpB = k2.genKeyPair();                                        // UNTOUCHED site on dexlib2
        System.out.println("MEASURE DX-KPG-2 genKeyPair (first-disjunct drop): GENERATED_KEY_PAIR(kpB)="
                + ec.validate(Property.GENERATED_KEY_PAIR, kpB) + " accepting(k2)=" + ec.isInAcceptingState(k2)
                + " delta=[" + delta() + "] (false/false/empty => silent FN)");
        snap();

        // ---- DX-SIG: sign() has no wrapper (wrong declared return type) - dead on this half too ----
        Signature sg = MonitorWrappers.java_security_Signature_getInstance("SHA256withRSA");
        MultiSpec_1RuntimeMonitor.SignatureSpec_i1Event(kpA.getPrivate(), sg); sg.initSign(kpA.getPrivate());
        snap();
        MultiSpec_1RuntimeMonitor.SignatureSpec_updateEvent(sg); sg.update(data1);
        byte[] sig = sg.sign();                                               // UNTOUCHED site
        System.out.println("MEASURE DX-SIG-1 after sign(): SIGNED=" + ec.validate(Property.SIGNED, sig)
                + " accepting=" + ec.isInAcceptingState(sg) + " delta=[" + delta() + "]");
        MultiSpec_1RuntimeMonitor.SignatureSpec_i1Event(kpA.getPrivate(), sg); sg.initSign(kpA.getPrivate());
        System.out.println("MEASURE DX-SIG-2 re-initSign: delta=[" + delta() + "] InvalidSeq="
                + countDelta("InvalidSequenceOfMethodCalls", "SignatureSpec") + " (>0 => same induced FP as ajc half)");
        snap();

        // ---- DX-MDG: parity happy path through wrappers ----
        MessageDigest md = MonitorWrappers.java_security_MessageDigest_getInstance("SHA-256");
        MonitorWrappers.java_security_MessageDigest_update_2(md, data1);
        byte[] h = MonitorWrappers.java_security_MessageDigest_digest(md);
        check("DX-MDG-1 legal digest clean", deltaList().isEmpty(), delta());
        check("DX-MDG-2 accepting", ec.isInAcceptingState(md), "");
        check("DX-MDG-3 DIGESTED", ec.validate(Property.DIGESTED, h), "");

        System.out.println("HARNESS " + (failures == 0 ? "OK" : failures + " failures"));
    }
}
