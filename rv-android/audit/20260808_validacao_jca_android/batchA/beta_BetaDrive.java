package mop;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.crypto.spec.DHGenParameterSpec;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.PBEParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import javax.xml.crypto.dsig.spec.HMACParameterSpec;

import java.lang.reflect.Field;
import java.security.spec.AlgorithmParameterSpec;

/**
 * Agent Beta (batch A) drive harness. Compiles the FIVE generated RuntimeMonitor.java
 * artifacts unmodified (package mop) and drives their public static wrappers in the exact
 * sequence the generated MonitorAspect.aj advices would call them (merged advice = two
 * monitorCalls in descriptor order). Constructions use the REAL JDK classes so that only
 * normally-returning constructions feed events, mirroring `after returning`.
 *
 * Output: one PASS/FAIL line per assertion; exit code 1 if any assertion fails.
 */
public class BetaDrive {

    static int failures = 0;
    static ExecutionContext ec = ExecutionContext.instance();

    static void check(String label, boolean cond) {
        System.out.println((cond ? "PASS " : "FAIL ") + label);
        if (!cond) failures++;
    }

    static void resetAll() {
        ec.reset();
        ErrorCollector.instance().reset();
    }

    static int errCount() { return ErrorCollector.instance().getErrors().size(); }

    static String errTypes() {
        StringBuilder sb = new StringBuilder();
        for (ErrorDescription d : ErrorCollector.instance().getErrors())
            sb.append(d.getType()).append(";");
        return sb.toString();
    }

    /** Reflectively read a monitor Category flag for the monitor bound to obj. */
    static Boolean flag(Class<?> rtm, String mapField, Object key, String flagField) {
        try {
            Field f = rtm.getDeclaredField(mapField);
            f.setAccessible(true);
            Object map = f.get(null);
            java.lang.reflect.Method get = map.getClass().getMethod("getMonitor", Object.class);
            get.setAccessible(true);
            Object mon = get.invoke(map, key);
            if (mon == null) return null;
            Field ff = mon.getClass().getDeclaredField(flagField);
            ff.setAccessible(true);
            return ff.getBoolean(mon);
        } catch (Throwable t) {
            return null;
        }
    }

    public static void main(String[] args) {
        dhg();
        hmc();
        pbe();
        ivp();
        sks();
        System.out.println(failures == 0 ? "ALL PASS" : failures + " FAILURES");
        System.exit(failures == 0 ? 0 : 1);
    }

    // ---------------------------------------------------------------- DHG
    static void dhg() {
        System.out.println("== DHG ==");
        resetAll();
        // (a) compliant per .mop condition (exponentSize < primeSize)
        DHGenParameterSpec s = new DHGenParameterSpec(2048, 256);
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(2048, 256, s);
        check("DHG a: 0 errors on compliant ctor", errCount() == 0);
        check("DHG a: PREPARED_DH set", ec.validate(Property.PREPARED_DH, s));
        check("DHG a: accepting state", ec.isInAcceptingState(s));
        // (b) oracle-legal (CrySL has NO constraint) but suppressed by extra .mop condition
        resetAll();
        DHGenParameterSpec s2 = new DHGenParameterSpec(256, 2048); // JDK ctor: no validation
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(256, 2048, s2);
        check("DHG b: 0 errors on exp>=prime (silent suppression)", errCount() == 0);
        check("DHG b: PREPARED_DH NOT set (denied despite oracle-legal)",
                !ec.validate(Property.PREPARED_DH, s2));
        // (c) @fail reachable ONLY via artificial second event on same object
        resetAll();
        DHGenParameterSpec s3 = new DHGenParameterSpec(2048, 256);
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(2048, 256, s3);
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(2048, 256, s3);
        check("DHG c: artificial 2nd c1 on same object -> exactly the fail handler fires",
                errCount() == 1 && errTypes().contains("InvalidSequenceOfMethodCalls"));
    }

    // ---------------------------------------------------------------- HMC
    static void hmc() {
        System.out.println("== HMC ==");
        resetAll();
        HMACParameterSpec h = new HMACParameterSpec(128); // JDK java.xml.crypto class
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h);
        check("HMC a: 0 errors", errCount() == 0);
        check("HMC a: PREPARED_HMAC set", ec.validate(Property.PREPARED_HMAC, h));
        resetAll();
        HMACParameterSpec h2 = new HMACParameterSpec(64);
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h2);
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h2);
        check("HMC b: artificial 2nd c -> fail handler",
                errCount() == 1 && errTypes().contains("InvalidSequenceOfMethodCalls"));
    }

    // ---------------------------------------------------------------- PBE
    static void pbe() {
        System.out.println("== PBE ==");
        resetAll();
        byte[] salt = new byte[16];
        ec.setProperty(Property.RANDOMIZED, salt); // mimic SecureRandom writer
        // (a) compliant 2-arg; advice = c1Event then c3Event (descriptor order)
        PBEParameterSpec p1 = new PBEParameterSpec(salt, 10000);
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c1Event(salt, 10000, p1);
        // stale-flag probe: remove the mark @match just wrote, then deliver the suppressed c3
        ec.remove(Property.PREPARED_PBE, p1);
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c3Event(salt, 10000, p1);
        check("PBE a: 0 errors on compliant 2-arg", errCount() == 0);
        check("PBE a-stale: PREPARED_PBE RE-written by handler re-run on SUPPRESSED c3 "
                + "(stale Category_match flag)", ec.validate(Property.PREPARED_PBE, p1));
        // (b) 2-arg violating (iterationCount < 10000, salt randomized)
        resetAll();
        ec.setProperty(Property.RANDOMIZED, salt);
        PBEParameterSpec p2 = new PBEParameterSpec(salt, 100);
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c1Event(salt, 100, p2);
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c3Event(salt, 100, p2);
        check("PBE b: exactly 1 UnsafeAlgorithm on 2-arg violating",
                errCount() == 1 && errTypes().contains("UnsafeAlgorithm"));
        check("PBE b: no PREPARED_PBE", !ec.validate(Property.PREPARED_PBE, p2));
        // (c) 3-arg violating: REAL ctor returns normally; advice calls ONLY c2Event
        resetAll();
        ec.setProperty(Property.RANDOMIZED, salt);
        AlgorithmParameterSpec aps = new IvParameterSpec(new byte[16]);
        PBEParameterSpec p3 = new PBEParameterSpec(salt, 100, aps); // returns normally
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c2Event(salt, 100, aps, p3);
        check("PBE c: 3-arg violating construction is TOTALLY SILENT (0 errors)",
                errCount() == 0);
        check("PBE c: no PREPARED_PBE (silent denial, no local accusation)",
                !ec.validate(Property.PREPARED_PBE, p3));
        // (d) 3-arg compliant
        resetAll();
        ec.setProperty(Property.RANDOMIZED, salt);
        PBEParameterSpec p4 = new PBEParameterSpec(salt, 10000, aps);
        PBEParameterSpecSpecRuntimeMonitor.PBEParameterSpecSpec_c2Event(salt, 10000, aps, p4);
        check("PBE d: 3-arg compliant -> PREPARED_PBE", ec.validate(Property.PREPARED_PBE, p4)
                && errCount() == 0);
    }

    // ---------------------------------------------------------------- IVP
    static void ivp() {
        System.out.println("== IVP ==");
        // (a) 1-arg compliant
        resetAll();
        byte[] iv = new byte[16];
        ec.setProperty(Property.RANDOMIZED, iv);
        IvParameterSpec v1 = new IvParameterSpec(iv);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c1Event(iv, v1);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c3Event(iv, v1);
        check("IVP a: 0 errors, PREPARED_IV set",
                errCount() == 0 && ec.validate(Property.PREPARED_IV, v1));
        // (b) 1-arg non-randomized
        resetAll();
        byte[] iv2 = new byte[16];
        IvParameterSpec v2 = new IvParameterSpec(iv2);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c1Event(iv2, v2);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c3Event(iv2, v2);
        check("IVP b: 1 UnsatisfiedConstraint, no PREPARED_IV",
                errCount() == 1 && errTypes().contains("UnsatisfiedConstraint")
                && !ec.validate(Property.PREPARED_IV, v2));
        // (c) 3-arg compliant
        resetAll();
        ec.setProperty(Property.RANDOMIZED, iv);
        IvParameterSpec v3 = new IvParameterSpec(iv, 0, 16);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c2Event(iv, 0, 16, v3);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c4Event(iv, 0, 16, v3);
        check("IVP c: 0 errors, PREPARED_IV set",
                errCount() == 0 && ec.validate(Property.PREPARED_IV, v3));
        // (d) 3-arg non-randomized
        resetAll();
        byte[] iv4 = new byte[16];
        IvParameterSpec v4 = new IvParameterSpec(iv4, 0, 16);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c2Event(iv4, 0, 16, v4);
        IvParameterSpecRuntimeMonitor.IvParameterSpecSpec_c4Event(iv4, 0, 16, v4);
        check("IVP d: 1 UnsatisfiedConstraint on 3-arg non-randomized",
                errCount() == 1 && errTypes().contains("UnsatisfiedConstraint"));
        // (e) is the c2/c4 predicate hole (randomized iv + bad ranges) REALIZABLE
        //     through the real ctor? Each bad-range construction must throw.
        String[] outcome = new String[3];
        byte[] iv5 = new byte[16];
        ec.setProperty(Property.RANDOMIZED, iv5);
        try { new IvParameterSpec(iv5, -1, 4);  outcome[0] = "RETURNED"; }
        catch (Throwable t) { outcome[0] = t.getClass().getSimpleName(); }
        try { new IvParameterSpec(iv5, 0, 17);  outcome[1] = "RETURNED"; }
        catch (Throwable t) { outcome[1] = t.getClass().getSimpleName(); }
        try { new IvParameterSpec(iv5, Integer.MAX_VALUE, 2); outcome[2] = "RETURNED"; }
        catch (Throwable t) { outcome[2] = t.getClass().getSimpleName(); }
        System.out.println("      IVP e outcomes (JDK impl): offset=-1 -> " + outcome[0]
                + "; len>length -> " + outcome[1] + "; overflow -> " + outcome[2]);
        check("IVP e: every bad-range construction throws on the JDK impl "
                + "(predicate hole unreachable via after-returning)",
                !"RETURNED".equals(outcome[0]) && !"RETURNED".equals(outcome[1])
                && !"RETURNED".equals(outcome[2]));
    }

    // ---------------------------------------------------------------- SKS
    static void sks() {
        System.out.println("== SKS ==");
        // (a) 2-arg compliant + stale-flag re-run proof
        resetAll();
        byte[] km = new byte[32];
        ec.setProperty(Property.RANDOMIZED, km);
        SecretKeySpec k1 = new SecretKeySpec(km, "AES");
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c1Event(km, "AES", k1);
        ec.remove(Property.GENERATED_KEY, k1);
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c3Event(km, "AES", k1);
        check("SKS a: 0 errors on compliant", errCount() == 0);
        check("SKS a-stale: GENERATED_KEY RE-written by handler re-run on SUPPRESSED c3",
                ec.validate(Property.GENERATED_KEY, k1));
        check("SKS a: SPECCED_KEY set", ec.validate(Property.SPECCED_KEY, k1));
        // (b) invalid algorithm (oracle has NO algorithm constraint -> extra-oracle FP)
        resetAll();
        byte[] km2 = new byte[8];
        ec.setProperty(Property.RANDOMIZED, km2);
        SecretKeySpec k2 = new SecretKeySpec(km2, "DES");
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c1Event(km2, "DES", k2);
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c3Event(km2, "DES", k2);
        check("SKS b: 1 UnsatisfiedConstraint for algorithm outside the .mop whitelist",
                errCount() == 1 && errTypes().contains("UnsatisfiedConstraint"));
        check("SKS b: no GENERATED_KEY", !ec.validate(Property.GENERATED_KEY, k2));
        // (c) 4-arg ctor drops the REQUIRES check: NON-randomized material accepted
        resetAll();
        byte[] km3 = new byte[32]; // NOT marked RANDOMIZED
        SecretKeySpec k3 = new SecretKeySpec(km3, 0, 16, "AES");
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c2Event(km3, 0, 16, "AES", k3);
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c4Event(km3, 0, 16, "AES", k3);
        check("SKS c: 4-arg NON-randomized material -> GENERATED_KEY GRANTED, 0 errors "
                + "(REQUIRES dropped on this overload)",
                errCount() == 0 && ec.validate(Property.GENERATED_KEY, k3));
        // (d) real-ctor behavior for the length constraint (is c4's length branch live?)
        String[] outcome = new String[2];
        try { new SecretKeySpec(new byte[8], 0, 16, "AES"); outcome[0] = "RETURNED"; }
        catch (Throwable t) { outcome[0] = t.getClass().getSimpleName(); }
        try { new SecretKeySpec(new byte[8], 4, 8, "AES");  outcome[1] = "RETURNED"; }
        catch (Throwable t) { outcome[1] = t.getClass().getSimpleName(); }
        System.out.println("      SKS d outcomes (JDK impl): len>material -> " + outcome[0]
                + "; off+len>material -> " + outcome[1]);
        // (e) lowercase algorithm accepted through toUpperCase folding
        resetAll();
        byte[] km4 = new byte[32];
        ec.setProperty(Property.RANDOMIZED, km4);
        SecretKeySpec k4 = new SecretKeySpec(km4, "aes");
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c1Event(km4, "aes", k4);
        SecretKeySpecSpecRuntimeMonitor.SecretKeySpecSpec_c3Event(km4, "aes", k4);
        check("SKS e: lowercase \"aes\" accepted via folding (0 errors, GENERATED_KEY)",
                errCount() == 0 && ec.validate(Property.GENERATED_KEY, k4));
    }
}
