import crysl.parsing.CrySLModelReader;
import crysl.rule.*;
import java.io.File; import java.util.*;
public class V9a {
  public static void main(String[] a) throws java.lang.Exception {
    CrySLModelReader r = new CrySLModelReader();
    File[] fs = new File(a[0]).listFiles((d,n)->n.endsWith(".crysl")); Arrays.sort(fs);
    for (File f : fs) {
      CrySLRule rule;
      try { rule = r.readRule(f); } catch (Throwable t) { System.out.println("FALHOU\t"+f.getName()+"\t"+t.getMessage()); continue; }
      System.out.println("=== " + f.getName());
      for (CrySLPredicate p : rule.getPredicates()) {
        if (p instanceof CrySLCondPredicate cp)
          System.out.println("   " + p.getPredName() + " after -> eventos=" + cp.getConditionalEvents().size()
              + " NOS=" + cp.getConditionalNodes().size() + " " + cp.getConditionalNodes());
        else System.out.println("   " + p.getPredName() + " (sem after)");
      }
    }
  }
}
