package mop;

// JUDGE discriminating test, batch A (2026-08-09).
// J2: end-to-end DHG suppression -> KeyPairGeneratorSpec false positive, on real JDK
//     classes, driving the generated monitors exactly as the generated advices do.
// Monitors: DHGenParameterSpecSpecRuntimeMonitor (round input, sha 90aaf45b...),
//           KeyPairGeneratorSpecRuntimeMonitor (generated in juiz scratch from the
//           frozen jca_android KeyPairGeneratorSpec.mop).

import javax.crypto.spec.DHGenParameterSpec;
import java.security.KeyPairGenerator;
import java.security.spec.AlgorithmParameterSpec;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

public class JuizDrive {

    static void dump(String label) {
        System.out.print(label + " errors=" + ErrorCollector.instance().getErrors().size());
        for (ErrorDescription e : ErrorCollector.instance().getErrors()) {
            System.out.print(" [" + e.getType() + " spec=" + e.getSpec()
                    + " expecting=" + e.getExpecting() + "]");
        }
        System.out.println();
    }

    public static void main(String[] args) throws Exception {
        // ---- Scenario A (control): construction the .mop condition ACCEPTS ----
        ExecutionContext.instance().reset();
        ErrorCollector.instance().reset();
        DHGenParameterSpec okSpec = new DHGenParameterSpec(1024, 512); // exp < prime
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(1024, 512, okSpec);
        boolean prepA = ExecutionContext.instance().validate(Property.PREPARED_DH, okSpec);
        KeyPairGenerator k1 = KeyPairGenerator.getInstance("DH");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("DH", k1);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init3Event(okSpec, k1);
        System.out.println("A: PREPARED_DH(okSpec)=" + prepA);
        dump("A:");

        // ---- Scenario B (FP): oracle-legal construction the .mop SUPPRESSES ----
        ExecutionContext.instance().reset();
        ErrorCollector.instance().reset();
        DHGenParameterSpec fpSpec = new DHGenParameterSpec(1024, 1024); // legal under api30 rule (no CONSTRAINTS)
        DHGenParameterSpecSpecRuntimeMonitor.DHGenParameterSpecSpec_c1Event(1024, 1024, fpSpec);
        boolean prepB = ExecutionContext.instance().validate(Property.PREPARED_DH, fpSpec);
        KeyPairGenerator k2 = KeyPairGenerator.getInstance("DH");
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event("DH", k2);
        KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init3Event(fpSpec, k2);
        System.out.println("B: PREPARED_DH(fpSpec)=" + prepB
                + "  (construction is LEGAL under the raw api30 oracle)");
        dump("B:");
        System.out.println(ErrorCollector.instance().getErrors().size() == 1
                ? "J2 RESULT: END-TO-END FALSE POSITIVE CONFIRMED (accusation at KeyPairGeneratorSpec for an oracle-legal DHGenParameterSpec)"
                : "J2 RESULT: no FP observed");
    }
}
