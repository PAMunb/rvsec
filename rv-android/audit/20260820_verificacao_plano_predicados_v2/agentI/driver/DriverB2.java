import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import mop.IvChainFsmSpecRuntimeMonitor;

/**
 * Piloto D4 - mecanismo B. Injeta os eventos diretamente nos despachantes
 * estaticos do monitor gerado (mesmo contrato do TraceRunner da gh104),
 * sem tecelagem AspectJ.
 */
public class DriverB2 {
    public static void main(String[] args) throws Exception {
        SecureRandom sr = new SecureRandom();

        // Cenario 1 - BOM: iv randomizado, cadeia completa. Esperado: MATCH, zero FAIL.
        byte[] iv1 = new byte[16];
        sr.nextBytes(iv1);
        IvParameterSpec spec1 = new IvParameterSpec(iv1);
        Cipher c1 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        System.out.println("--- cenario 1 (bom): iv1=" + System.identityHashCode(iv1)
            + " spec1=" + System.identityHashCode(spec1) + " c1=" + System.identityHashCode(c1));
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_genEvent(sr, iv1);
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_mkEvent(iv1, spec1);
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_useEvent(spec1, c1);

        // Cenario 2 - RUIM: iv estatico (nunca passou por nextBytes). Esperado: FAIL.
        byte[] iv2 = new byte[16]; // zeros, IV estatico
        IvParameterSpec spec2 = new IvParameterSpec(iv2);
        Cipher c2 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        System.out.println("--- cenario 2 (ruim, iv nao randomizado): iv2=" + System.identityHashCode(iv2)
            + " spec2=" + System.identityHashCode(spec2) + " c2=" + System.identityHashCode(c2));
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_mkEvent(iv2, spec2);
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_useEvent(spec2, c2);

        // Cenario 3 - RUIM: consumidor sem cadeia observada (spec de origem invisivel).
        // Esperado: FAIL somente se 'use' for evento criador.
        byte[] iv3 = new byte[16];
        IvParameterSpec spec3 = new IvParameterSpec(iv3);
        Cipher c3 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        System.out.println("--- cenario 3 (ruim, so o consumidor observado): spec3=" + System.identityHashCode(spec3)
            + " c3=" + System.identityHashCode(c3));
        IvChainFsmSpecRuntimeMonitor.IvChainFsmSpec_useEvent(spec3, c3);

        System.out.println("--- fim");
    }
}
