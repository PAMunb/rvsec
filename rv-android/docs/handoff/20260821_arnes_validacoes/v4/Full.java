import crysl.parsing.CrySLModelReader;
import crysl.rule.*;
import java.io.File; import java.util.*; import java.util.stream.Collectors;
public class Full {
  public static void main(String[] a) throws Exception {
    CrySLModelReader r = new CrySLModelReader();
    File[] fs = new File(a[0]).listFiles((d,n)->n.endsWith(".crysl")); Arrays.sort(fs);
    Map<String,CrySLRule> rs = new LinkedHashMap<>();
    for (File f : fs) { try { rs.put(f.getName().replace(".crysl",""), r.readRule(f)); } catch (Throwable t) {} }
    for (int i=1;i<a.length;i++) {
      CrySLRule rule = rs.get(a[i]); System.out.println("===== "+a[i]+" =====");
      for (TransitionEdge e : rule.getUsagePattern().getEdges()) {
        System.out.println("  "+e.getLeft().getName()+" -> "+e.getRight().getName());
        for (CrySLMethod m : e.getLabel()) System.out.println("      "+m.getSignature());
      }
    }
  }
}
