import java.security.MessageDigest;
public class Prog3 {
  public static void main(String[] a) throws Exception {
    System.out.println("=== 1) algoritmo seguro ===");
    MessageDigest m1 = MessageDigest.getInstance("SHA-256");
    m1.digest();
    System.out.println("=== 2) algoritmo inseguro ===");
    MessageDigest m2 = MessageDigest.getInstance("MD5");
    m2.digest();
    System.out.println("=== fim ===");
  }
}
