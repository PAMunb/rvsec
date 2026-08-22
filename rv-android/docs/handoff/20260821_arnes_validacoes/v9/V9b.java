import br.unb.cic.mop.jca.util.*;
public class V9b {
  static void t(String label, java.util.function.Supplier<Object> f) {
    try { System.out.println(label + " -> " + f.get()); }
    catch (Throwable e) { System.out.println(label + " -> LANCOU " + e.getClass().getName() + ": " + e.getMessage()); }
  }
  public static void main(String[] a) {
    for (String s : new String[]{"AES/", "AES//", "AES", "AES/CBC/PKCS5Padding", "RSA/", "/", ""}) {
      t("CipherTransformationUtil.mode(\"" + s + "\")", () -> CipherTransformationUtil.mode(s));
      t("CipherTransformationUtil.isValid(\"" + s + "\")", () -> CipherTransformationUtil.isValid(s));
      t("Api30CipherTransformationUtil.isValid(\"" + s + "\")", () -> Api30CipherTransformationUtil.isValid(s));
      System.out.println();
    }
  }
}
