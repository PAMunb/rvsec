import javax.crypto.Cipher;
public class V9c {
  public static void main(String[] a) {
    for (String s : new String[]{"AES/", "AES//", "AES///", "AES/CBC/", "/", "AES/ECB/PKCS5Padding"}) {
      try {
        Cipher c = Cipher.getInstance(s);
        System.out.println("getInstance(\"" + s + "\") OK -> getAlgorithm()=\"" + c.getAlgorithm() + "\"");
      } catch (Throwable e) {
        System.out.println("getInstance(\"" + s + "\") -> " + e.getClass().getSimpleName() + ": " + e.getMessage());
      }
    }
  }
}
