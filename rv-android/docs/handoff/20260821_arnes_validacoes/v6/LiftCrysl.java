import com.google.gson.*;
import crysl.parsing.CrySLModelReader;
import crysl.rule.*;
import java.io.File; import java.nio.file.*; import java.util.*;
import com.google.inject.Injector;
import de.darmstadt.tu.crossing.CrySLStandaloneSetup;
import de.darmstadt.tu.crossing.crySL.Domainmodel;
import de.darmstadt.tu.crossing.crySL.Aggregate;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.xtext.common.types.access.impl.ClasspathTypeProvider;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.XtextResourceSet;
import java.net.URL; import java.net.URLClassLoader;

/** Leitor do lado CrySL: regra -> modelo canonico em JSON. Roda com o classpath do CrySLParser. */
public class LiftCrysl {
  public static void main(String[] a) throws java.lang.Exception {
    String dir = a[0], out = a[1];
    CrySLModelReader r = new CrySLModelReader();
    // Segunda leitura, pela AST EMF: e de la que saem os nomes de evento e de agregado
    // (que a fachada descarta) e a procedencia arquivo:linha. Sao ~10 linhas, e o
    // recurso carrega mesmo para as regras que a fachada rejeita por erro de validacao.
    Injector inj = new CrySLStandaloneSetup().createInjectorAndDoEMFRegistration();
    XtextResourceSet rs = inj.getInstance(XtextResourceSet.class);
    URL[] vcp = crysl.parsing.CrySLModelReaderClassPath.JAVA_CLASS_PATH.getClassPath();
    rs.setClasspathURIContext(new URLClassLoader(vcp));
    new ClasspathTypeProvider(new URLClassLoader(vcp), rs, null, null);
    File[] fs = new File(dir).listFiles((d,n)->n.endsWith(".crysl")); Arrays.sort(fs);
    JsonArray todos = new JsonArray();
    for (File f : fs) {
      JsonObject o = new JsonObject();
      o.addProperty("kind", "crysl");
      o.addProperty("source", f.getName());
      o.add("ast", ast(rs, f));
      CrySLRule rule;
      try { rule = r.readRule(f); }
      catch (Throwable t) { o.addProperty("error", t.getMessage()); todos.add(o); continue; }
      o.addProperty("type", rule.getClassName());
      JsonArray objs = new JsonArray();
      for (Map.Entry<String,String> e : rule.getObjects()) {
        JsonObject j = new JsonObject(); j.addProperty("name", e.getKey()); j.addProperty("type", e.getValue()); objs.add(j);
      }
      o.add("objects", objs);
      JsonArray evs = new JsonArray();
      for (CrySLMethod m : rule.getEvents()) {
        JsonObject j = new JsonObject();
        j.addProperty("signature", m.getSignature());
        j.addProperty("methodName", m.getMethodName());
        j.addProperty("shortName", m.getShortMethodName());
        j.addProperty("declaringClass", m.getDeclaringClassName());
        JsonArray pr = new JsonArray();
        for (Map.Entry<String,String> pe : m.getParameters()) {
          JsonObject pj = new JsonObject(); pj.addProperty("name", pe.getKey()); pj.addProperty("type", pe.getValue()); pr.add(pj);
        }
        j.add("params", pr);
        if (m.getRetObject() != null) {
          JsonObject rj = new JsonObject();
          rj.addProperty("name", m.getRetObject().getKey()); rj.addProperty("type", m.getRetObject().getValue());
          j.add("ret", rj);
        }
        evs.add(j);
      }
      o.add("events", evs);
      JsonArray fb = new JsonArray();
      for (CrySLForbiddenMethod m : rule.getForbiddenMethods()) fb.add(m.toString());
      o.add("forbidden", fb);

      StateMachineGraph g = rule.getUsagePattern();
      g.wrapUpCreation();
      JsonObject ord = new JsonObject();
      ord.addProperty("start", g.getStartNode().getName());
      JsonArray acc = new JsonArray();
      for (StateNode n : g.getAcceptingStates()) acc.add(n.getName());
      ord.add("accepting", acc);
      JsonArray eds = new JsonArray();
      for (TransitionEdge e : g.getEdges()) {
        JsonObject j = new JsonObject();
        j.addProperty("from", e.getLeft().getName()); j.addProperty("to", e.getRight().getName());
        JsonArray sy = new JsonArray();
        for (CrySLMethod m : e.getLabel()) sy.add(m.getSignature());
        j.add("symbols", sy); eds.add(j);
      }
      ord.add("edges", eds);
      // determinismo do que o parser entrega
      Map<String,Set<String>> det = new LinkedHashMap<>();
      for (TransitionEdge e : g.getEdges())
        for (CrySLMethod m : e.getLabel())
          det.computeIfAbsent(e.getLeft().getName()+"#"+m.getSignature(), k->new LinkedHashSet<>()).add(e.getRight().getName());
      ord.addProperty("deterministic", det.values().stream().allMatch(s -> s.size()==1));
      o.add("order", ord);

      o.add("ensures", preds(rule.getPredicates()));
      o.add("negates", preds(rule.getNegatedPredicates()));
      JsonArray req = new JsonArray();
      for (ISLConstraint c : rule.getRequiredPredicates()) req.add(c.toString());
      o.add("requires", req);
      JsonArray cons = new JsonArray();
      for (ISLConstraint c : rule.getConstraints()) cons.add(constraint(c));
      o.add("constraints", cons);
      todos.add(o);
    }
    Files.writeString(Paths.get(out), new GsonBuilder().setPrettyPrinting().create().toJson(todos));
    System.err.println("# LiftCrysl: " + todos.size() + " regras -> " + out);
  }
  /** Serializa a arvore de constraints; o que nao se reconhece vira Unknown com texto cru. */
  static JsonObject constraint(ISLConstraint c) {
    JsonObject j = new JsonObject();
    j.addProperty("class", c.getClass().getSimpleName());
    j.addProperty("text", c.toString());
    j.addProperty("vars", String.join(",", c.getInvolvedVarNames()));
    if (c instanceof CrySLValueConstraint v) {
      j.addProperty("form", "in-set");
      j.addProperty("var", v.getVarName());
      j.addProperty("varType", v.getVar().getJavaType());
      JsonArray vs = new JsonArray(); for (String s : v.getValueRange()) vs.add(s);
      j.add("values", vs);
    } else if (c instanceof CrySLComparisonConstraint cc) {
      j.addProperty("form", "comparison");
      j.addProperty("op", cc.getOperator().toString());
      j.addProperty("left", cc.getLeft().toString());
      j.addProperty("right", cc.getRight().toString());
    } else if (c instanceof CrySLConstraint bc) {
      j.addProperty("form", "logical");
      j.addProperty("op", bc.getOperator().toString());
      j.add("leftC", constraint(bc.getLeft()));
      j.add("rightC", constraint(bc.getRight()));
    } else {
      j.addProperty("form", "Unknown");
    }
    return j;
  }

  /** Nomes de evento, agregados e ORDER cru, com linha -- direto da AST EMF. */
  static JsonObject ast(XtextResourceSet rs, File f) {
    JsonObject j = new JsonObject();
    try {
      Resource res = rs.getResource(org.eclipse.emf.common.util.URI.createFileURI(f.getAbsolutePath()), true);
      if (res.getContents().isEmpty()) { j.addProperty("astError", "recurso vazio"); return j; }
      Domainmodel dm = (Domainmodel) res.getContents().get(0);
      JsonArray evs = new JsonArray(), aggs = new JsonArray();
      if (dm.getEvents() != null)
        for (de.darmstadt.tu.crossing.crySL.Event e : dm.getEvents().getEvents()) {
          int line = NodeModelUtils.getNode(e) == null ? -1 : NodeModelUtils.getNode(e).getStartLine();
          if (e instanceof Aggregate ag) {
            JsonObject x = new JsonObject();
            x.addProperty("name", ag.getName()); x.addProperty("line", line);
            JsonArray ms = new JsonArray();
            for (de.darmstadt.tu.crossing.crySL.Event m : ag.getEvents()) ms.add(m.getName());
            x.add("members", ms); aggs.add(x);
          } else {
            JsonObject x = new JsonObject();
            x.addProperty("name", e.getName()); x.addProperty("line", line);
            x.addProperty("text", txt(e)); evs.add(x);
          }
        }
      j.add("eventNames", evs); j.add("aggregates", aggs);
      if (dm.getOrder() != null) {
        j.addProperty("orderText", txt(dm.getOrder()).replaceAll("\\s+", " ").strip());
        j.addProperty("orderLine", NodeModelUtils.getNode(dm.getOrder()).getStartLine());
      }
    } catch (Throwable t) { j.addProperty("astError", String.valueOf(t.getMessage())); }
    return j;
  }
  static String txt(org.eclipse.emf.ecore.EObject e) {
    var n = NodeModelUtils.getNode(e);
    return n == null ? "" : NodeModelUtils.getTokenText(n).replaceAll("\\s+", " ").strip();
  }

  static JsonArray preds(Collection<CrySLPredicate> ps) {
    JsonArray a = new JsonArray();
    for (CrySLPredicate p : ps) {
      JsonObject j = new JsonObject();
      j.addProperty("name", p.getPredName());
      j.addProperty("negated", p.isNegated());
      j.addProperty("text", p.toString());
      JsonArray par = new JsonArray();
      for (ICrySLPredicateParameter q : p.getParameters()) par.add(q.getName());
      j.add("params", par);
      j.addProperty("arity", p.getParameters().size());
      a.add(j);
    }
    return a;
  }
}
