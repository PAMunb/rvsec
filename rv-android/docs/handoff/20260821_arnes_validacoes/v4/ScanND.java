import crysl.parsing.CrySLModelReader;
import crysl.rule.*;
import java.io.File;
import java.util.*;

public class ScanND {
  public static void main(String[] a) throws Exception {
    CrySLModelReader r = new CrySLModelReader();
    File[] fs = new File(a[0]).listFiles((d,n)->n.endsWith(".crysl")); Arrays.sort(fs);
    int nd=0, det=0;
    for (File f : fs) {
      CrySLRule rule; try { rule = r.readRule(f); } catch (Throwable t) { System.out.println("SKIP\t"+f.getName()); continue; }
      StateMachineGraph g = rule.getUsagePattern();
      Map<String,Set<String>> m = new LinkedHashMap<>();
      for (TransitionEdge e : g.getEdges())
        for (CrySLMethod mm : e.getLabel())
          m.computeIfAbsent(e.getLeft().getName()+"#"+mm.getSignature(), k->new LinkedHashSet<>()).add(e.getRight().getName());
      List<String> bad = m.entrySet().stream().filter(x->x.getValue().size()>1).map(x->x.getKey()+"->"+x.getValue()).toList();
      // auto-laco em todo estado? conta estados sem transicao de saida (sink implicito)
      if (bad.isEmpty()) { det++; System.out.println("DET\t"+f.getName()+"\tnodes="+g.getNodes().size()+"\tedges="+g.getEdges().size()); }
      else { nd++; System.out.println("NDET\t"+f.getName()+"\t"+bad); }
    }
    System.out.println("# deterministicos=" + det + " nao-deterministicos=" + nd);
  }
}
