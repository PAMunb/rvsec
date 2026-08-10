// EXEC-SET dedupe probe: does the SSL init RANDOMIZED read exist and error when it
// is the ONLY failing constraint (X1), and do two distinct failing constraints at
// the SAME call site collapse into one record (X2)? ErrorDescription identity is
// the ErrorSummary (spec, type, clazz, method, loc) -- `expecting` excluded
// (ErrorDescription.java:109-139). Merged monitors; real JDK objects; 3 reps.
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;
import mop.MultiSpec_1RuntimeMonitor;

import javax.net.ssl.*;
import java.security.SecureRandom;
import java.util.*;
import java.util.stream.Collectors;

public class SetExecDedupeProbe {
    static Set<ErrorDescription> seen = new HashSet<>();
    static void delta(String step) {
        Set<ErrorDescription> now = new HashSet<>(ErrorCollector.instance().getErrors());
        List<String> fresh = now.stream().filter(e -> !seen.contains(e))
                .map(e -> e.getType() + "/" + e.getSpec() + " expecting=" + e.getExpecting())
                .sorted().collect(Collectors.toList());
        seen = now;
        System.out.println("  DELTA " + step + " (" + fresh.size() + "): " + fresh);
    }

    public static void main(String[] args) throws Exception {
        ExecutionContext ctx = ExecutionContext.instance();
        KeyManager[] kms = new KeyManager[0];
        TrustManager[] tms = new TrustManager[0];
        ctx.setProperty(Property.GENERATED_KEY_MANAGERS, kms);   // synthetic marks: isolate the
        ctx.setProperty(Property.GENERATED_TRUST_MANAGERS, tms); // random read in X1
        SecureRandom rFresh = new SecureRandom(); // unmonitored on purpose

        System.out.println("== X1: only the SecureRandom constraint fails at this site ==");
        SSLContext c1 = SSLContext.getInstance("TLSv1.3");
        MultiSpec_1RuntimeMonitor.SSLContextSpec_g1Event("TLSv1.3", c1);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLSv1.3", c1);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(c1, kms, tms, rFresh);
        delta("X1");

        System.out.println("== X2: km AND random constraints both fail at ONE call site ==");
        KeyManager[] kmsBad = new KeyManager[0]; // unmarked
        SSLContext c2 = SSLContext.getInstance("TLSv1.3");
        MultiSpec_1RuntimeMonitor.SSLContextSpec_g1Event("TLSv1.3", c2);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_unsafe_protocolEvent("TLSv1.3", c2);
        MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(c2, kmsBad, tms, rFresh);
        delta("X2 (two distinct constraint failures, one site)");
        System.out.println("== done ==");
    }
}
