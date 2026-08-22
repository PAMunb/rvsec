import com.google.gson.*;
import javamop.parser.ast.*;
import javamop.parser.ast.aspectj.BaseTypePattern;
import javamop.parser.ast.body.BodyDeclaration;
import javamop.parser.ast.expr.NameExpr;
import javamop.parser.ast.mopspec.*;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.parser.ast.visitor.DumpVisitor;
import javamop.parser.main_parser.JavaMOPParser;
import javamop.parser.SpecExtractor;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Gerador crysl -> .mop para a familia "parameter-spec": regras cujos eventos sao todos
 * construtores do tipo da SPEC. Emite pelo writer da tecnologia (MOPSpecFile + DumpVisitor),
 * nunca por concatenacao de texto.
 *
 * Politicas declaradas (§10.3 do documento-mae):
 *  - CONSTRAINTS vao para o CORPO do evento, nunca para condition(...): uma condition
 *    compila para `if (!(guarda)) return false;` antes da transicao, e guarda falsa tira a
 *    chamada do automato. O alfabeto fica intacto e as duas camadas desacoplam.
 *  - REQUIRES tambem vao para o corpo.
 *  - ENSURES vao para @match.
 *  - O que nao se traduz vira registro Unknown tipado na saida, nao comentario no .mop.
 */
public class Gen {

  static JsonObject rule;
  static List<String> unknowns = new ArrayList<>();

  public static void main(String[] a) throws java.lang.Exception {
    JsonArray todas = JsonParser.parseString(Files.readString(Paths.get(a[0]))).getAsJsonArray();
    String alvo = a[1];
    Path out = Paths.get(a[2]);
    for (JsonElement e : todas) if (e.getAsJsonObject().get("source").getAsString().equals(alvo)) rule = e.getAsJsonObject();
    if (rule == null) throw new IllegalStateException("regra nao encontrada: " + alvo);

    String fqn = rule.get("type").getAsString();
    String simple = fqn.substring(fqn.lastIndexOf('.') + 1);
    String specName = simple + "Spec";
    String bind = "s";      // o parametro do fatiamento
    String field = "spec";  // o campo que guarda o objeto para o @match

    // ---------- imports ----------
    List<ImportDeclaration> imports = new ArrayList<>();
    imports.add(imp(fqn, false));
    // Todo tipo de parametro que o pointcut nomeia pelo nome curto precisa de import,
    // senao o .mop parseia e o aspecto gerado nao compila.
    LinkedHashSet<String> tiposUsados = new LinkedHashSet<>();
    for (JsonElement ee : rule.getAsJsonArray("events"))
      for (JsonElement pe : ee.getAsJsonObject().getAsJsonArray("params")) {
        String t = pe.getAsJsonObject().get("type").getAsString().replace("[]", "");
        if (t.contains(".") && !t.equals(fqn)) tiposUsados.add(t);
      }
    for (String t : tiposUsados) imports.add(imp(t, false));
    imports.add(imp("br.unb.cic.mop.eh", true));
    imports.add(imp("br.unb.cic.mop.ExecutionContext", false));
    imports.add(imp("br.unb.cic.mop.Property", false));
    PackageDeclaration pkg = new PackageDeclaration(0, 0, new ArrayList<>(), new NameExpr(0, 0, "mop"));

    // ---------- declaracoes ----------
    List<BodyDeclaration> decls = new ArrayList<>();
    decls.add(bodyDecl(simple + " " + field + ";"));

    // ---------- eventos ----------
    Map<String, JsonObject> porNome = new LinkedHashMap<>();
    JsonArray nomes = rule.getAsJsonObject("ast").getAsJsonArray("eventNames");
    JsonArray evsSig = rule.getAsJsonArray("events");
    // casa nome <-> assinatura pela ordem de declaracao no arquivo
    List<JsonObject> sigs = new ArrayList<>();
    for (JsonElement e : evsSig) sigs.add(e.getAsJsonObject());

    List<EventDefinition> eventos = new ArrayList<>();
    List<String> idsEmitidos = new ArrayList<>();
    for (JsonElement ne : nomes) {
      JsonObject n = ne.getAsJsonObject();
      String id = n.get("name").getAsString();
      String texto = n.get("text").getAsString();          // "c1: GCMParameterSpec(tLen, src)"
      List<String> args = argNames(texto);
      JsonObject sig = casar(sigs, args);
      if (sig == null) { unknowns.add("evento sem assinatura resolvida: " + texto); continue; }
      String mName = sig.get("methodName").getAsString();
      boolean ctor = mName.equals(fqn);
      if (!ctor) { unknowns.add("evento nao-construtor fora do escopo deste gerador: " + texto); continue; }

      List<MOPParameter> ps = new ArrayList<>();
      List<String> tipos = new ArrayList<>();
      for (JsonElement pe : sig.getAsJsonArray("params")) {
        JsonObject p = pe.getAsJsonObject();
        ps.add(param(curto(p.get("type").getAsString()), p.get("name").getAsString()));
        tipos.add(curto(p.get("type").getAsString()));
      }
      String pc = "call(public " + simple + ".new(" + String.join(", ", tipos) + "))"
                + " && args(" + ps.stream().map(MOPParameter::getName).collect(Collectors.joining(", ")) + ")";
      // O ENSURES nao pode valer para uma construcao que quebrou uma CONSTRAINTS ou um
      // REQUIRES: o campo so e ligado no ramo conforme, e o @match acha nulo nos demais.
      String checks = corpoConstraints(specName, simple, id, ps) + corpoRequires(specName, simple, id, ps);
      StringBuilder body = new StringBuilder("{\n");
      if (checks.isBlank()) body.append("  ").append(field).append(" = ").append(bind).append(";\n");
      else body.append("  boolean conforms = true;\n").append(checks)
               .append("  if (conforms) {\n    ").append(field).append(" = ").append(bind).append(";\n  }\n");
      body.append("}");
      List<MOPParameter> ret = new ArrayList<>(List.of(param(simple, bind)));
      eventos.add(new EventDefinition(0, 0, id, null, "after", ps, pc, block(body.toString()),
          true, ret, false, new ArrayList<>(), false, true, false, false));
      idsEmitidos.add(id);
    }

    // ---------- ORDER -> ere ----------
    String orderText = rule.getAsJsonObject("ast").get("orderText").getAsString();
    String ere = ordemParaEre(orderText, rule.getAsJsonObject("ast").getAsJsonArray("aggregates"));

    // ---------- handlers ----------
    LinkedHashMap<String, BlockStmt> handlers = new LinkedHashMap<>();
    handlers.put("fail", block(failBody(specName, simple)));
    handlers.put("match", block(matchBody(field)));
    List<PropertyAndHandlers> props = new ArrayList<>();
    props.add(new PropertyAndHandlers(0, 0, new Formula(0, 0, "ere", ere), handlers));

    List<MOPParameter> specParams = new ArrayList<>(List.of(param(simple, bind)));
    JavaMOPSpec spec = new JavaMOPSpec(pkg, 0, 0, 0, specName, specParams, null, decls, eventos, props);
    MOPSpecFile file = new MOPSpecFile(0, 0, pkg, imports, List.of(spec));

    DumpVisitor v = new DumpVisitor(); file.accept(v, null);
    String texto = v.getSource();
    Files.writeString(out, texto);
    System.out.println(texto);

    // portao 1: o gerado reparseia?
    MOPSpecFile again = SpecExtractor.parse(out.toFile());
    System.err.println("# reparse: OK (" + again.getSpecs().get(0).getEvents().size() + " eventos, ere="
        + ((Formula) again.getSpecs().get(0).getPropertiesAndHandlers().get(0).getProperty()).getFormula().strip() + ")");
    System.err.println("# eventos emitidos: " + idsEmitidos);
    for (String u : unknowns) System.err.println("# UNKNOWN: " + u);
  }

  // ---------- CONSTRAINTS / REQUIRES / ENSURES ----------

  static String corpoConstraints(String specName, String simple, String evId, List<MOPParameter> ps) {
    StringBuilder sb = new StringBuilder();
    Set<String> ligados = ps.stream().map(MOPParameter::getName).collect(Collectors.toCollection(LinkedHashSet::new));
    int i = 0;
    for (JsonElement ce : rule.getAsJsonArray("constraints")) {
      JsonObject c = ce.getAsJsonObject(); i++;
      String form = c.get("form").getAsString();
      String var = c.has("var") ? c.get("var").getAsString() : primeiraVar(c);
      if (var == null || !ligados.contains(var)) continue;   // a clausula nao alcanca este evento
      String cod = specName.replaceAll("Spec$", "").toUpperCase(Locale.ROOT) + "-CONSTR-" + String.format("%02d", i - 1);
      String teste, esperado;
      if (form.equals("in-set")) {
        List<String> vals = new ArrayList<>();
        for (JsonElement ve : c.getAsJsonArray("values")) vals.add(ve.getAsString());
        boolean numerico = c.get("varType").getAsString().matches("int|long|short|byte");
        String lista = vals.stream().map(x -> numerico ? x : "\"" + x + "\"").collect(Collectors.joining(", "));
        teste = "java.util.Arrays.asList(" + lista + ").contains(" + var + ")";
        esperado = "one of {" + String.join(", ", vals) + "}";
      } else if (form.equals("comparison")) {
        String l = expr(c.get("left").getAsString()), r = expr(c.get("right").getAsString());
        teste = l + " " + op(c.get("op").getAsString()) + " " + r;
        esperado = teste;
      } else { unknowns.add("constraint nao emitivel (" + form + "): " + c.get("text").getAsString()); continue; }
      sb.append("  if (!(").append(teste).append(")) {\n")
        .append("    ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, \"")
        .append(specName).append("\", \"\" + __LOC,\n")
        .append("      \"v=1 code=").append(cod).append(" ev=\" + __EVENTNAME + \" obj=").append(simple)
        .append(" val='\" + ").append(var).append(" + \"' exp='").append(esc(esperado))
        .append("' msg='expecting ").append(esc(esperado)).append(" but found \" + ").append(var).append(" + \"'\"));\n")
        .append("    conforms = false;\n")
        .append("  }\n");
    }
    return sb.toString();
  }

  static String corpoRequires(String specName, String simple, String evId, List<MOPParameter> ps) {
    StringBuilder sb = new StringBuilder();
    Set<String> ligados = ps.stream().map(MOPParameter::getName).collect(Collectors.toCollection(LinkedHashSet::new));
    for (JsonElement re : rule.getAsJsonArray("requires")) {
      String t = re.getAsString();                       // "randomized(byte[] src)"
      String nome = t.substring(0, t.indexOf('('));
      String arg = t.substring(t.lastIndexOf(' ') + 1, t.length() - 1);
      if (!ligados.contains(arg)) continue;
      String cod = specName.replaceAll("Spec$", "").toUpperCase(Locale.ROOT) + "-REQ-00";
      sb.append("  if (!ExecutionContext.instance().validate(Property.").append(prop(nome)).append(", ").append(arg).append(")) {\n")
        .append("    ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, \"")
        .append(specName).append("\", \"\" + __LOC,\n")
        .append("      \"v=1 code=").append(cod).append(" ev=\" + __EVENTNAME + \" obj=").append(simple)
        .append(" val='' exp='").append(nome).append("[").append(arg).append("]' msg='the rule requires ")
        .append(nome).append("[").append(arg).append("]'\"));\n")
        .append("    conforms = false;\n")
        .append("  }\n");
    }
    return sb.toString();
  }

  static String matchBody(String field) {
    StringBuilder sb = new StringBuilder("{\n");
    for (JsonElement ee : rule.getAsJsonArray("ensures")) {
      JsonObject e = ee.getAsJsonObject();
      int ar = e.get("arity").getAsInt();
      String p0 = e.getAsJsonArray("params").get(0).getAsString();
      if (ar > 1) { unknowns.add("ENSURES de aridade " + ar + " inexprimivel no ExecutionContext: " + e.get("text").getAsString()); continue; }
      String alvo = p0.equals("this") ? field : p0;
      sb.append("  ExecutionContext.instance().setProperty(Property.").append(prop(e.get("name").getAsString()))
        .append(", ").append(alvo).append(");\n");
    }
    sb.append("  ExecutionContext.instance().setObjectAsInAcceptingState(").append(field).append(");\n}");
    return sb.toString();
  }

  static String failBody(String specName, String simple) {
    String cod = specName.replaceAll("Spec$", "").toUpperCase(Locale.ROOT) + "-ORDER-00";
    return "{\n  ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, \""
      + specName + "\", \"\" + __LOC,\n    \"v=1 code=" + cod + " ev=\" + __EVENTNAME + \" obj=" + simple
      + " val='' exp='' msg='the observed call sequence is not one " + specName + " accepts'\"));\n  __RESET;\n}";
  }

  // ---------- ORDER -> ERE, com a precedencia da gramatica Xtext ----------
  /** Na gramatica CrySL `Sequence` e a producao mais externa e `Alternative` esta dentro:
   *  `|` liga MAIS FORTE que `,`. Em ERE a justaposicao liga mais forte que `|`, entao
   *  toda alternativa que aparece dentro de uma sequencia tem de sair parentetizada. */
  static String ordemParaEre(String order, JsonArray aggs) {
    Map<String, String> agg = new LinkedHashMap<>();
    for (JsonElement e : aggs) {
      JsonObject a = e.getAsJsonObject();
      List<String> ms = new ArrayList<>();
      for (JsonElement m : a.getAsJsonArray("members")) ms.add(m.getAsString());
      agg.put(a.get("name").getAsString(), ms.size() == 1 ? ms.get(0) : "(" + String.join(" | ", ms) + ")");
    }
    return new OrderParser(order, agg).seq(true);
  }

  static class OrderParser {
    final String s; int i = 0; final Map<String, String> agg;
    OrderParser(String s, Map<String, String> agg) { this.s = s; this.agg = agg; }
    void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
    String seq(boolean topo) {
      List<String> ps = new ArrayList<>(); ps.add(alt());
      while (true) { ws(); if (i < s.length() && s.charAt(i) == ',') { i++; ps.add(alt()); } else break; }
      return String.join(" ", ps);
    }
    String alt() {
      List<String> br = new ArrayList<>(); br.add(prim());
      while (true) { ws(); if (i < s.length() && s.charAt(i) == '|') { i++; br.add(prim()); } else break; }
      return br.size() == 1 ? br.get(0) : "(" + String.join(" | ", br) + ")";
    }
    String prim() {
      ws();
      String base;
      if (i < s.length() && s.charAt(i) == '(') { i++; base = "(" + seq(false) + ")"; ws();
        if (i >= s.length() || s.charAt(i) != ')') throw new IllegalStateException("faltou ) em " + i); i++; }
      else { int st = i; while (i < s.length() && (Character.isLetterOrDigit(s.charAt(i)) || s.charAt(i) == '_')) i++;
        String id = s.substring(st, i);
        if (id.isEmpty()) throw new IllegalStateException("simbolo esperado em " + i);
        base = agg.getOrDefault(id, id); }
      ws();
      if (i < s.length() && "*+?".indexOf(s.charAt(i)) >= 0) {
        char q = s.charAt(i++);
        boolean atomico = base.startsWith("(") || base.matches("[A-Za-z0-9_]+");
        base = (atomico ? base : "(" + base + ")") + q;
      }
      return base;
    }
  }

  // ---------- utilitarios ----------
  static List<String> argNames(String texto) {
    int p = texto.indexOf('('); if (p < 0) return List.of();
    String inner = texto.substring(p + 1, texto.lastIndexOf(')'));
    if (inner.isBlank()) return List.of();
    return Arrays.stream(inner.split(",")).map(String::strip).toList();
  }
  static JsonObject casar(List<JsonObject> sigs, List<String> args) {
    for (JsonObject s : sigs) {
      JsonArray ps = s.getAsJsonArray("params");
      if (ps.size() != args.size()) continue;
      boolean ok = true;
      for (int k = 0; k < ps.size(); k++)
        if (!ps.get(k).getAsJsonObject().get("name").getAsString().equals(args.get(k))) { ok = false; break; }
      if (ok) return s;
    }
    return null;
  }
  static String curto(String t) { int i = t.lastIndexOf('.'); return i < 0 ? t : t.substring(i + 1); }
  static String prop(String camel) {
    return camel.replaceAll("([a-z0-9])([A-Z])", "$1_$2").toUpperCase(Locale.ROOT);
  }
  static String primeiraVar(JsonObject c) {
    String v = c.has("vars") ? c.get("vars").getAsString() : "";
    return v.isBlank() ? null : v.split(",")[0];
  }
  static String expr(String s) {
    String r = s.replaceAll("\\b(int|long|short|byte|boolean|java\\.lang\\.String)\\s+", "").strip();
    r = r.replaceAll("\\s*\\+\\s*0\\b", "");
    return r;
  }
  static String op(String o) {
    return switch (o) { case "g" -> ">"; case "ge" -> ">="; case "l" -> "<"; case "le" -> "<=";
      case "eq" -> "=="; case "neq" -> "!="; default -> o; };
  }
  static String esc(String s) { return s.replace("\"", "\\\""); }
  static ImportDeclaration imp(String n, boolean star) { return new ImportDeclaration(0, 0, new NameExpr(0, 0, n), false, star); }
  static MOPParameter param(String t, String n) { return new MOPParameter(0, 0, new BaseTypePattern(0, 0, t), n); }
  static JavaMOPParser p(String src) { return new JavaMOPParser(new ByteArrayInputStream(src.getBytes(StandardCharsets.UTF_8))); }
  static BlockStmt block(String src) throws java.lang.Exception { return p(src).Block(); }
  static BodyDeclaration bodyDecl(String src) throws java.lang.Exception { return p(src).ClassOrInterfaceBodyDeclaration(false); }
}
