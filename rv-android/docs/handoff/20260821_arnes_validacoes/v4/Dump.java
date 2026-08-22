import crysl.parsing.CrySLModelReader;
import crysl.rule.*;
import java.io.File;
import java.util.*;
import java.util.stream.Collectors;

public class Dump {
  static String lbl(TransitionEdge e) {
    return e.getLabel().stream().map(CrySLMethod::getShortMethodName).sorted()
        .collect(Collectors.joining("|"));
  }
  public static void main(String[] a) throws Exception {
    CrySLModelReader r = new CrySLModelReader();
    // le o diretorio inteiro em ordem alfabetica antes: o escopo de OBJECTS vaza entre regras
    File[] todos = new File(a[0]).listFiles((d,n) -> n.endsWith(".crysl"));
    java.util.Arrays.sort(todos);
    Map<String, CrySLRule> regras = new LinkedHashMap<>();
    for (File f0 : todos) { try { regras.put(f0.getName().replace(".crysl",""), r.readRule(f0)); } catch (Throwable t) {} }
    System.out.println("# lidas: " + regras.size() + "/" + todos.length);
    for (int i = 1; i < a.length; i++) {
      CrySLRule rule = regras.get(a[i]);
      if (rule == null) { System.out.println("===== " + a[i] + " ===== NAO CARREGOU"); continue; }
      StateMachineGraph g = rule.getUsagePattern();
      System.out.println("===== " + a[i] + " =====");
      System.out.println("nodes: " + g.getNodes().stream().map(n -> n.getName()
          + (n.getInit()?"[init]":"") + (n.getAccepting()?"[acc]":"")).collect(Collectors.joining(", ")));
      System.out.println("start: " + g.getStartNode());
      System.out.println("accepting: " + g.getAcceptingStates());
      System.out.println("edges:");
      Map<String, Set<String>> det = new LinkedHashMap<>();
      for (TransitionEdge e : g.getEdges()) {
        System.out.println("  " + e.getLeft().getName() + " --[" + lbl(e) + "]--> " + e.getRight().getName());
        for (CrySLMethod m : e.getLabel())
          det.computeIfAbsent(e.getLeft().getName() + "#" + m.getSignature(), k -> new LinkedHashSet<>())
             .add(e.getRight().getName());
      }
      List<String> nd = det.entrySet().stream().filter(x -> x.getValue().size() > 1)
          .map(x -> x.getKey() + " -> " + x.getValue()).toList();
      System.out.println("NAO-DETERMINISMO: " + (nd.isEmpty() ? "nenhum" : nd));
      System.out.println("hopsToAccepting(start) antes de wrapUpCreation: " + g.getStartNode().getHopsToAccepting());
      g.wrapUpCreation();
      System.out.println("hopsToAccepting(start) depois: " + g.getStartNode().getHopsToAccepting());
      System.out.println();
    }
  }
}
