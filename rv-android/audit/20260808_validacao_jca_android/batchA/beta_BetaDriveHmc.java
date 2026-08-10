package mop;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import javax.xml.crypto.dsig.spec.HMACParameterSpec;

/** Discriminating test: is the HMC monitor global or per-object?
 *  CrySL lifecycle is per `this`: two independent constructions are legal.
 *  Per-object monitor => 0 errors. Global monitor => 1 InvalidSequenceOfMethodCalls (FP). */
public class BetaDriveHmc {
    public static void main(String[] a) {
        HMACParameterSpec h1 = new HMACParameterSpec(128);
        HMACParameterSpec h2 = new HMACParameterSpec(256);
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h1);
        HMACParameterSpecSpecRuntimeMonitor.HMACParameterSpecSpec_cEvent(h2);
        int n = ErrorCollector.instance().getErrors().size();
        System.out.println("errors=" + n + " " + ErrorCollector.instance().getErrors());
        System.out.println("h1 PREPARED_HMAC=" + ExecutionContext.instance().validate(Property.PREPARED_HMAC, h1));
        System.out.println("h2 PREPARED_HMAC=" + ExecutionContext.instance().validate(Property.PREPARED_HMAC, h2));
        System.out.println(n == 0 ? "PER-OBJECT (no FP)" : "GLOBAL MONITOR: FALSE POSITIVE on second legal construction");
    }
}
