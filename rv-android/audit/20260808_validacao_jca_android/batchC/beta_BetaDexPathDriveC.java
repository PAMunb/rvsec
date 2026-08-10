import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.MonitorWrappers;
import mop.MultiSpec_1RuntimeMonitor;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import java.security.KeyStore;
import java.util.*;

/**
 * Agent Beta batch C - production dexlib2 EMISSION drive. mop/MonitorWrappers.java
 * is the EXACT source WrapperEmitter.generate emitted from the merged 23-spec
 * descriptor over the frozen android-30 jar (hash-verified); calling a wrapper is
 * byte-for-byte what a rewritten call site executes on the dexlib2 path. Inline
 * BEFORE events (load/store) are invoked as MonitorInvokeBuilder emits them: one
 * static monitor call per descriptor monitorCall, in descriptor order.
 */
public class BetaDexPathDriveC {
    static int failures = 0;
    static ExecutionContext ec = ExecutionContext.instance();
    static List<ErrorDescription> snapshot = new ArrayList<>();

    static void check(String label, boolean cond, String detail) {
        System.out.println((cond ? "PASS " : "FAIL ") + label + (detail.isEmpty() ? "" : "  [" + detail + "]"));
        if (!cond) failures++;
    }
    static List<ErrorDescription> errs() { return new ArrayList<>(ErrorCollector.instance().getErrors()); }
    static List<ErrorDescription> deltaList() {
        List<ErrorDescription> now = errs(), d = new ArrayList<>(), seen = new ArrayList<>(snapshot);
        for (ErrorDescription e : now) { if (!seen.remove(e)) d.add(e); }
        return d;
    }
    static String delta() {
        StringBuilder sb = new StringBuilder();
        for (ErrorDescription e : deltaList()) sb.append(e.getType()).append('/').append(e.getSpec())
            .append('@').append(e.getLocation()).append(' ');
        return sb.toString().trim();
    }
    static int deltaCount() { return deltaList().size(); }
    static long deltaOf(String type, String spec) {
        return deltaList().stream().filter(d -> d.getType().toString().equals(type) && d.getSpec().equals(spec)).count();
    }
    static void snap() { snapshot = errs(); }

    public static void main(String[] args) throws Exception {
        System.out.println("== BetaDexPathDriveC (production dexlib2 wrappers, merged descriptor) ==");

        // DX-1: THE canonical legal call, as a dexlib2-rewritten site executes it.
        snap();
        KeyManagerFactory kmf = MonitorWrappers.javax_net_ssl_KeyManagerFactory_getInstance("PKIX");
        check("DX-1 MEASURE dexlib2 1-arg KMF.getInstance(\"PKIX\") alone -> immediate spurious fail (g1 then g2)",
              deltaOf("InvalidSequenceOfMethodCalls","KeyManagerFactorySpec") >= 1, delta());

        // DX-2: same shape for TMF.
        snap();
        TrustManagerFactory tmf = MonitorWrappers.javax_net_ssl_TrustManagerFactory_getInstance("PKIX");
        check("DX-2 MEASURE dexlib2 1-arg TMF.getInstance(\"PKIX\") alone -> immediate spurious fail",
              deltaOf("InvalidSequenceOfMethodCalls","TrustManagerFactorySpec") >= 1, delta());

        // DX-3: 2-arg route is clean (g2 wrapper only) - the defect is specific to the 1-arg site.
        snap();
        KeyManagerFactory kmf2 = MonitorWrappers.javax_net_ssl_KeyManagerFactory_getInstance_1("PKIX", "SunJSSE");
        check("DX-3 dexlib2 2-arg KMF.getInstance -> no error (g2 only fires)", deltaCount() == 0, delta());

        // DX-4: unsafe algorithm on the 1-arg wrapper: g1 suppressed, g3 fires, g2 suppressed -> no immediate error.
        snap();
        KeyManagerFactory kmf3 = MonitorWrappers.javax_net_ssl_KeyManagerFactory_getInstance("SunX509");
        check("DX-4 MEASURE unsafe alg 1-arg -> NO immediate error (conditions suppress g2); FP hits only SAFE calls",
              deltaCount() == 0, delta());

        // DX-5: KST on the dexlib2 path: getInstance wrapper + load inline; then store inline
        // (the CrySL-legal sE,Stores route) with se1 UNWOVEN (nested-type mangling).
        snap();
        KeyStore ks = MonitorWrappers.java_security_KeyStore_getInstance("PKCS12");
        ks.load(null, null);
        MultiSpec_1RuntimeMonitor.KeyStoreSpec_loadEvent(ks);   // inline BEFORE emission
        check("DX-5a getInstance+load on dexlib2 path -> no error", deltaCount() == 0, delta());
        check("DX-5b GENERATED_KEY_STORE marked", ec.validate(Property.GENERATED_KEY_STORE, ks), "");
        snap();
        // app now does ks.setEntry(...) [INVISIBLE: se1 unwoven] then ks.store(...):
        MultiSpec_1RuntimeMonitor.KeyStoreSpec_storeEvent(ks);  // store IS woven (load(..)/store(..))
        check("DX-5c MEASURE store after (invisible) setEntry -> spurious fail on the legal sE,Stores route",
              deltaOf("InvalidSequenceOfMethodCalls","KeyStoreSpec") >= 1, delta());

        // DX-6: SSL on the dexlib2 path: getInstance + init wrappers work; createSSLEngine has NO wrapper
        // (probe: UNTOUCHED). Direct event call documents what a capture repair would restore.
        snap();
        SSLContext ctx = MonitorWrappers.javax_net_ssl_SSLContext_getInstance("TLS");
        MonitorWrappers.javax_net_ssl_SSLContext_init(ctx, null, null, null);
        check("DX-6a dexlib2 SSL getInstance+init -> no seq error",
              deltaOf("InvalidSequenceOfMethodCalls","SSLContextSpec") == 0, delta());
        SSLEngine eng = ctx.createSSLEngine();
        check("DX-6b engine unobservable on dexlib2 (no wrapper exists; property never set)",
              !ec.validate(Property.GENERATE_SSL_ENGINE, eng), "");
        snap();
        MultiSpec_1RuntimeMonitor.SSLContextSpec_engineEvent(ctx, eng); // hypothetical repaired capture
        check("DX-6c direct engineEvent on initialized ctx -> accepted, GENERATE_SSL_ENGINE marked",
              deltaCount() == 0 && ec.validate(Property.GENERATE_SSL_ENGINE, eng), delta());

        System.out.println("== done; harness failures = " + failures + " ; total errors = " + errs().size());
        System.exit(failures > 0 ? 1 : 0);
    }
}
