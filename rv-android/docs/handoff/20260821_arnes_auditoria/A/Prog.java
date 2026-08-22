import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.security.Key;
public class Prog {
  public static void main(String[] a) throws Exception {
    Key k = new SecretKeySpec(new byte[16], "AES");
    Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
    c.init(Cipher.ENCRYPT_MODE, k);
    System.out.println("[PROG] chamando doFinal() -- UMA chamada");
    byte[] out = c.doFinal();
    System.out.println("[PROG] doFinal() devolveu " + out.length + " bytes");
  }
}
