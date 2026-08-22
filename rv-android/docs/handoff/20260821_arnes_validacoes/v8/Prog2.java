import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
public class Prog2 {
  public static void main(String[] a) throws Exception {
    System.out.println("--- um getInstance, um generateKey ---");
    KeyGenerator x = KeyGenerator.getInstance("AES");
    SecretKey kx = x.generateKey();
    System.out.println("[PROG] fim");
  }
}
