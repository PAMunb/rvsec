import com.google.gson.*;
import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.mopspec.*;
import javamop.parser.ast.aspectj.*;
import java.io.File; import java.nio.file.*; import java.util.*;

/** Leitor do lado MOP: .mop -> modelo canonico em JSON. Roda com o classpath do javamop. */
public class LiftMop {
  public static void main(String[] a) throws Exception {
    String dir = a[0], out = a[1];
    File[] fs = new File(dir).listFiles((d,n)->n.endsWith(".mop")); Arrays.sort(fs);
    JsonArray todos = new JsonArray();
    for (File f : fs) {
      JsonObject o = new JsonObject();
      o.addProperty("kind", "mop"); o.addProperty("source", f.getName());
      MOPSpecFile m;
      try { m = SpecExtractor.parse(f); }
      catch (Throwable t) { o.addProperty("error", String.valueOf(t.getMessage())); todos.add(o); continue; }
      for (JavaMOPSpec s : m.getSpecs()) {
        JsonObject so = o.deepCopy();
        so.addProperty("spec", s.getName());
        JsonArray ps = new JsonArray();
        for (MOPParameter p : s.getParameters()) {
          JsonObject j = new JsonObject(); j.addProperty("type", p.getType().getOp()); j.addProperty("name", p.getName()); ps.add(j);
        }
        so.add("params", ps);
        JsonArray evs = new JsonArray();
        for (EventDefinition e : s.getEvents()) {
          JsonObject j = new JsonObject();
          j.addProperty("id", e.getId());
          j.addProperty("pos", e.getPos());
          j.addProperty("creation", e.isCreationEvent());
          j.addProperty("pointcut", String.valueOf(e.getPointCutString()));
          j.addProperty("purePointcut", String.valueOf(e.getPurePointCutString()));
          j.addProperty("condition", String.valueOf(e.getCondition()));
          j.addProperty("hasReturning", e.hasReturning());
          j.addProperty("body", e.getAction()==null ? "" : e.getAction().toString());
          JsonArray sigs = new JsonArray();
          collect(e.getPointCut(), sigs);
          j.add("callSignatures", sigs);
          evs.add(j);
        }
        so.add("events", evs);
        JsonArray props = new JsonArray();
        for (PropertyAndHandlers p : s.getPropertiesAndHandlers()) {
          JsonObject j = new JsonObject();
          Property pr = p.getProperty();
          j.addProperty("formalism", pr.getType());
          j.addProperty("text", pr instanceof Formula ? ((Formula) pr).getFormula() : pr.toString());
          JsonObject hs = new JsonObject();
          for (Map.Entry<String, javamop.parser.ast.stmt.BlockStmt> h : p.getHandlers().entrySet())
            hs.addProperty(h.getKey(), h.getValue()==null ? "" : h.getValue().toString());
          j.add("handlers", hs);
          props.add(j);
        }
        so.add("properties", props);
        JsonArray decls = new JsonArray();
        if (s.getDeclarations()!=null) for (Object d : s.getDeclarations()) decls.add(String.valueOf(d));
        so.add("declarations", decls);
        todos.add(so);
      }
    }
    Files.writeString(Paths.get(out), new GsonBuilder().setPrettyPrinting().create().toJson(todos));
    System.err.println("# LiftMop: " + todos.size() + " specs -> " + out);
  }

  /** Anda o pointcut e recolhe as assinaturas de call(...). */
  static void collect(PointCut pc, JsonArray out) {
    if (pc == null) return;
    if (pc instanceof CombinedPointCut c) { for (PointCut p : c.getPointcuts()) collect(p, out); return; }
    if (pc instanceof NotPointCut c) { collect(c.getPointCut(), out); return; }
    if (pc instanceof MethodPointCut c) { out.add(c.getType() + " " + c.getSignature().toString()); return; }
  }
}
