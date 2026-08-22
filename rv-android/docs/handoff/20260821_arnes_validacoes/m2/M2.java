import com.google.gson.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/** Nucleo M2: compara L(A_mop) com L(A_crysl) sobre o alfabeto canonico de assinaturas.
 *  Zero dependencia de javamop ou CrySLParser -- le so os JSON dos dois leitores. */
public class M2 {

  public static void main(String[] args) throws Exception {
    JsonArray crysl = JsonParser.parseString(Files.readString(Paths.get(args[0]))).getAsJsonArray();
    JsonArray mop   = JsonParser.parseString(Files.readString(Paths.get(args[1]))).getAsJsonArray();
    for (int i = 2; i < args.length; i++) run(crysl, mop, Paths.get(args[i]));
  }

  static void run(JsonArray crysl, JsonArray mop, Path mapFile) throws Exception {
    Map<String, String> meta = new LinkedHashMap<>();
    Map<String, Set<String>> alpha = new LinkedHashMap<>();
    for (String raw : Files.readAllLines(mapFile)) {
      String l = raw.strip();
      if (l.isEmpty() || l.startsWith("#")) continue;
      if (l.contains("->")) {
        String[] p = l.split("->", 2);
        String ev = p[0].strip();
        String rhs = p[1].strip();
        Set<String> to = new LinkedHashSet<>();
        if (!rhs.equals("EPSILON"))
          for (String s : rhs.split("\\|")) if (!s.isBlank()) to.add(s.strip());
        alpha.put(ev, to);
      } else {
        String[] p = l.split(":", 2);
        meta.put(p[0].strip(), p[1].strip());
      }
    }
    String specName = meta.get("spec"), ruleName = meta.get("rule");
    JsonObject cr = find(crysl, "source", ruleName);
    JsonObject mo = find(mop, "spec", specName);

    Aut.Dfa dc = cryslDfa(cr, meta.getOrDefault("crysl-erase", ""));
    Aut.Nfa nm = mopNfa(mo, meta);
    Aut.Nfa rl = Aut.relabel(nm, alpha);
    Aut.Dfa dm = rl.determinize();

    System.out.println("========== " + specName + "  x  " + ruleName + " ==========");
    System.out.println("  CrySL: estados=" + dc.size() + " aceitantes=" + dc.accept
        + " deterministico-na-origem=" + cr.getAsJsonObject("order").get("deterministic").getAsBoolean());
    System.out.println("  MOP  : formalismo=" + meta.getOrDefault("formalismo","?")
        + " estados(DFA)=" + dm.size() + " aceitantes=" + dm.accept);

    report("  SEM N1", Aut.compare(dm, dc));
    if (meta.containsKey("creation")) {
      Set<String> cri = new LinkedHashSet<>();
      for (String ev : meta.get("creation").split("\\s+"))
        if (alpha.containsKey(ev)) cri.addAll(alpha.get(ev));
      Aut.Dfa dn1 = Aut.atMostOneCreation(dm, cri);
      report("  COM N1", Aut.compare(dn1, dc));
    }
    System.out.println();
  }

  static void report(String tag, Aut.Verdict v) {
    System.out.println(tag + ": " + v.label());
    if (v.aMinusB != null) System.out.println("      MOP \\ regra : " + shorten(v.aMinusB));
    if (v.bMinusA != null) System.out.println("      regra \\ MOP : " + shorten(v.bMinusA));
  }
  static String shorten(List<String> w) {
    return w.stream().map(s -> { int i = s.lastIndexOf('.', s.indexOf('(') < 0 ? s.length()-1 : s.indexOf('(')); 
      return i < 0 ? s : s.substring(i+1); }).collect(Collectors.joining(" "));
  }

  static JsonObject find(JsonArray a, String key, String val) {
    for (JsonElement e : a) {
      JsonObject o = e.getAsJsonObject();
      if (o.has(key) && o.get(key).getAsString().equals(val)) return o;
    }
    throw new IllegalStateException("nao achei " + key + "=" + val);
  }

  static Aut.Dfa cryslDfa(JsonObject cr, String erase) {
    Set<String> era = new LinkedHashSet<>();
    for (String e : erase.split("\\s*;\\s*")) if (!e.isBlank()) era.add(e.strip());
    JsonObject ord = cr.getAsJsonObject("order");
    Map<String, Integer> idx = new LinkedHashMap<>();
    Aut.Nfa n = new Aut.Nfa();
    java.util.function.Function<String, Integer> st = name -> {
      Integer k = idx.get(name); if (k == null) { k = n.add(); idx.put(name, k); } return k; };
    st.apply(ord.get("start").getAsString());
    for (JsonElement e : ord.getAsJsonArray("edges")) {
      JsonObject j = e.getAsJsonObject();
      int a = st.apply(j.get("from").getAsString()), b = st.apply(j.get("to").getAsString());
      for (JsonElement s : j.getAsJsonArray("symbols"))
        n.edge(a, era.contains(s.getAsString()) ? Aut.Nfa.EPS : s.getAsString(), b);
    }
    n.start = idx.get(ord.get("start").getAsString());
    for (JsonElement s : ord.getAsJsonArray("accepting")) n.accept.add(st.apply(s.getAsString()));
    return n.determinize();
  }

  static Aut.Nfa mopNfa(JsonObject mo, Map<String, String> meta) {
    JsonObject prop = mo.getAsJsonArray("properties").get(0).getAsJsonObject();
    String form = prop.get("formalism").getAsString();
    meta.put("formalismo", form);
    String text = prop.get("text").getAsString();
    if (form.equals("ere")) return Aut.ere(text.replaceAll("\\s+", " ").strip());
    if (form.equals("fsm")) return fsm(text, meta);
    throw new IllegalStateException("formalismo nao suportado: " + form);
  }

  /** Parser do bloco `fsm:` -- `estado [ ev -> destino ... ]` mais `alias matchN = estado`. */
  static Aut.Nfa fsm(String text, Map<String, String> meta) {
    Map<String, Integer> idx = new LinkedHashMap<>();
    Aut.Nfa n = new Aut.Nfa();
    java.util.function.Function<String, Integer> st = name -> {
      Integer k = idx.get(name); if (k == null) { k = n.add(); idx.put(name, k); } return k; };
    List<String> aliases = new ArrayList<>();
    String cur = null; String first = null;
    for (String raw : text.split("\n")) {
      String l = raw.strip();
      if (l.isEmpty() || l.startsWith("//")) continue;
      if (l.startsWith("alias")) { aliases.add(l.split("=")[1].strip()); continue; }
      if (l.endsWith("[")) { cur = l.substring(0, l.length()-1).strip(); if (first==null) first = cur; st.apply(cur); continue; }
      if (l.equals("]")) { cur = null; continue; }
      if (l.contains("->")) {
        String[] p = l.split("->", 2);
        n.edge(st.apply(cur), p[0].strip(), st.apply(p[1].strip()));
      }
    }
    n.start = idx.get(first);
    String acc = meta.get("accepting");
    List<String> nomes = acc != null ? List.of(acc.split("\\s+")) : aliases;
    for (String a : nomes) {
      Integer k = idx.get(a);
      if (k == null) throw new IllegalStateException("estado aceitante inexistente: " + a);
      n.accept.add(k);
    }
    meta.put("aceitantes-usados", String.join(",", nomes));
    return n;
  }
}
