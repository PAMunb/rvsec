package mop;

// JUDGE discriminating test, batch A (2026-08-09).
// J3: independent re-execution of Beta's HMC global-monitor counterexample
//     (BETA-HMC-03), on the ROUND-INPUT artifact (sha adebef51...), host JDK
//     javax.xml.crypto.dsig.spec.HMACParameterSpec (class absent from android-30;
//     realizable wherever the class exists).

import javax.xml.crypto.dsig.spec.HMACParameterSpec;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

public class JuizHmc {
    public static void main(String[] args) {
        ExecutionContext.instance().reset();
        ErrorCollector.instance().reset();
        HMACParameterSpec h1 = new HMACParameterSpec(256); // CrySL-legal
        HMACParameterSpec h2 = new HMACParameterSpec(160); // CrySL-legal, distinct object
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h1);
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h2);
        System.out.println("errors=" + ErrorCollector.instance().getErrors().size());
        for (ErrorDescription e : ErrorCollector.instance().getErrors())
            System.out.println("  [" + e.getType() + " spec=" + e.getSpec() + " expecting=" + e.getExpecting() + "]");
        System.out.println("h1 PREPARED_HMAC=" + ExecutionContext.instance().validate(Property.PREPARED_HMAC, h1));
        System.out.println("h2 PREPARED_HMAC=" + ExecutionContext.instance().validate(Property.PREPARED_HMAC, h2));
        boolean fp = ErrorCollector.instance().getErrors().size() == 1
                && !ExecutionContext.instance().validate(Property.PREPARED_HMAC, h2);
        System.out.println(fp
                ? "J3 RESULT: GLOBAL-MONITOR FALSE POSITIVE REPRODUCED (2 legal constructions -> 1 InvalidSequenceOfMethodCalls; 2nd object denied PREPARED_HMAC)"
                : "J3 RESULT: not reproduced");
    }
}
