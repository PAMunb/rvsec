import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

public class Prog {
  public static void main(String[] a) throws Exception {
    System.out.println("--- dois getInstance, depois dois generateKey ---");
    KeyGenerator x = KeyGenerator.getInstance("AES");
    KeyGenerator y = KeyGenerator.getInstance("AES");
    System.out.println("[PROG] x=" + System.identityHashCode(x) + " y=" + System.identityHashCode(y));
    SecretKey kx = x.generateKey();
    SecretKey ky = y.generateKey();
    System.out.println("[PROG] fim");
  }
}
