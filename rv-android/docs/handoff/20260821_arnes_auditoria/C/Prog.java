import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.security.Key;
public class Prog {
  public static void main(String[] a) throws Exception {
    Key k = new SecretKeySpec(new byte[16], "AES");

    System.out.println("=== A testemunha do documento: getInstance; init; doFinal() ===");
    Cipher c1 = Cipher.getInstance("AES/CBC/PKCS5Padding");
    c1.init(Cipher.ENCRYPT_MODE, k);
    c1.doFinal();

    System.out.println();
    System.out.println("=== Controle: getInstance; init; update; doFinal(pt) ===");
    Cipher c2 = Cipher.getInstance("AES/CBC/PKCS5Padding");
    c2.init(Cipher.ENCRYPT_MODE, k);
    c2.update(new byte[16]);
    c2.doFinal(new byte[16]);
  }
}
