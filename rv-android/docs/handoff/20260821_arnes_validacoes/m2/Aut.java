import java.util.*;
import java.util.stream.Collectors;

/** NFA/DFA sobre alfabeto de String, com determinizacao e equivalencia por busca no produto. */
public class Aut {

  // ---------- NFA ----------
  public static class Nfa {
    List<Map<String, Set<Integer>>> t = new ArrayList<>();
    int start; Set<Integer> accept = new LinkedHashSet<>();
    int add() { t.add(new LinkedHashMap<>()); return t.size() - 1; }
    void edge(int a, String s, int b) { t.get(a).computeIfAbsent(s, k -> new LinkedHashSet<>()).add(b); }
    static final String EPS = "";
    Set<Integer> close(Set<Integer> in) {
      Deque<Integer> st = new ArrayDeque<>(in); Set<Integer> out = new LinkedHashSet<>(in);
      while (!st.isEmpty()) for (int n : t.get(st.pop()).getOrDefault(EPS, Set.of())) if (out.add(n)) st.push(n);
      return out;
    }
    Set<String> alphabet() {
      Set<String> a = new TreeSet<>();
      for (var m : t) for (String k : m.keySet()) if (!k.equals(EPS)) a.add(k);
      return a;
    }
    Dfa determinize() {
      Set<String> alpha = alphabet();
      Map<Set<Integer>, Integer> idx = new LinkedHashMap<>();
      List<Set<Integer>> lst = new ArrayList<>();
      Deque<Set<Integer>> q = new ArrayDeque<>();
      Set<Integer> s0 = close(Set.of(start));
      idx.put(s0, 0); lst.add(s0); q.add(s0);
      List<Map<String, Integer>> d = new ArrayList<>(); d.add(new LinkedHashMap<>());
      while (!q.isEmpty()) {
        Set<Integer> cur = q.poll(); int ci = idx.get(cur);
        for (String s : alpha) {
          Set<Integer> nx = new LinkedHashSet<>();
          for (int n : cur) nx.addAll(t.get(n).getOrDefault(s, Set.of()));
          if (nx.isEmpty()) continue;
          nx = close(nx);
          Integer ni = idx.get(nx);
          if (ni == null) { ni = lst.size(); idx.put(nx, ni); lst.add(nx); d.add(new LinkedHashMap<>()); q.add(nx); }
          d.get(ci).put(s, ni);
        }
      }
      Dfa r = new Dfa(); r.delta = d; r.alpha = alpha;
      for (int i = 0; i < lst.size(); i++) if (!Collections.disjoint(lst.get(i), accept)) r.accept.add(i);
      return r;
    }
  }

  // ---------- DFA ----------
  public static class Dfa {
    List<Map<String, Integer>> delta = new ArrayList<>();
    Set<Integer> accept = new LinkedHashSet<>();
    Set<String> alpha = new TreeSet<>();
    int size() { return delta.size(); }
  }

  /** Resultado da comparacao: testemunhas mais curtas nas duas direcoes. */
  public static class Verdict {
    public List<String> aMinusB, bMinusA;
    public String label() {
      if (aMinusB == null && bMinusA == null) return "EQUIVALENTES";
      if (bMinusA == null) return "A MAIS PERMISSIVA";
      if (aMinusB == null) return "B MAIS PERMISSIVA";
      return "INCOMPARAVEIS";
    }
  }

  /** Busca no produto sobre os dois DFAs completados com sumidouro implicito (-1). */
  public static Verdict compare(Dfa a, Dfa b) {
    Set<String> alpha = new TreeSet<>(a.alpha); alpha.addAll(b.alpha);
    Verdict v = new Verdict();
    v.aMinusB = witness(a, b, alpha, true);
    v.bMinusA = witness(a, b, alpha, false);
    return v;
  }

  private static List<String> witness(Dfa a, Dfa b, Set<String> alpha, boolean aNotB) {
    record P(int x, int y) {}
    Map<P, List<String>> seen = new LinkedHashMap<>();
    Deque<P> q = new ArrayDeque<>();
    P s = new P(0, 0); seen.put(s, List.of()); q.add(s);
    while (!q.isEmpty()) {
      P p = q.poll(); List<String> w = seen.get(p);
      boolean ax = p.x() >= 0 && a.accept.contains(p.x());
      boolean by = p.y() >= 0 && b.accept.contains(p.y());
      if (aNotB ? (ax && !by) : (by && !ax)) return w;
      for (String c : alpha) {
        int nx = p.x() < 0 ? -1 : a.delta.get(p.x()).getOrDefault(c, -1);
        int ny = p.y() < 0 ? -1 : b.delta.get(p.y()).getOrDefault(c, -1);
        P np = new P(nx, ny);
        if (nx < 0 && ny < 0) continue;
        if (seen.containsKey(np)) continue;
        List<String> nw = new ArrayList<>(w); nw.add(c);
        seen.put(np, nw); q.add(np);
      }
    }
    return null;
  }

  // ---------- parser de ERE ----------
  public static Nfa ere(String src) { return new EreParser(src).parse(); }

  static class EreParser {
    final String s; int i = 0; Nfa n = new Nfa();
    EreParser(String s) { this.s = s; }
    void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
    boolean at(char c) { ws(); return i < s.length() && s.charAt(i) == c; }
    Nfa parse() {
      int[] f = alt(); ws();
      if (i < s.length()) throw new IllegalStateException("lixo em " + i + ": " + s.substring(i));
      n.start = f[0]; n.accept.add(f[1]); return n;
    }
    int[] alt() {
      List<int[]> br = new ArrayList<>(); br.add(cat());
      while (at('|')) { i++; br.add(cat()); }
      if (br.size() == 1) return br.get(0);
      int a = n.add(), b = n.add();
      for (int[] f : br) { n.edge(a, Nfa.EPS, f[0]); n.edge(f[1], Nfa.EPS, b); }
      return new int[]{a, b};
    }
    int[] cat() {
      List<int[]> ps = new ArrayList<>();
      while (true) { ws(); if (i >= s.length() || s.charAt(i)=='|' || s.charAt(i)==')') break; ps.add(rep()); }
      if (ps.isEmpty()) { int a = n.add(); return new int[]{a, a}; }
      for (int k = 0; k + 1 < ps.size(); k++) n.edge(ps.get(k)[1], Nfa.EPS, ps.get(k+1)[0]);
      return new int[]{ps.get(0)[0], ps.get(ps.size()-1)[1]};
    }
    int[] rep() {
      int[] f = atom();
      while (true) {
        ws(); if (i >= s.length()) break;
        char c = s.charAt(i);
        if (c == '*') { i++; int a = n.add(), b = n.add();
          n.edge(a, Nfa.EPS, f[0]); n.edge(a, Nfa.EPS, b); n.edge(f[1], Nfa.EPS, f[0]); n.edge(f[1], Nfa.EPS, b); f = new int[]{a,b}; }
        else if (c == '+') { i++; int a = n.add(), b = n.add();
          n.edge(a, Nfa.EPS, f[0]); n.edge(f[1], Nfa.EPS, f[0]); n.edge(f[1], Nfa.EPS, b); f = new int[]{a,b}; }
        else if (c == '?') { i++; int a = n.add(), b = n.add();
          n.edge(a, Nfa.EPS, f[0]); n.edge(a, Nfa.EPS, b); n.edge(f[1], Nfa.EPS, b); f = new int[]{a,b}; }
        else break;
      }
      return f;
    }
    int[] atom() {
      ws();
      if (at('(')) { i++; int[] f = alt(); ws(); if (!at(')')) throw new IllegalStateException("faltou ) em " + i); i++; return f; }
      int st = i;
      while (i < s.length() && (Character.isLetterOrDigit(s.charAt(i)) || s.charAt(i)=='_')) i++;
      if (st == i) throw new IllegalStateException("simbolo esperado em " + i + ": " + s.substring(Math.min(i, s.length())));
      int a = n.add(), b = n.add(); n.edge(a, s.substring(st, i), b); return new int[]{a, b};
    }
  }

  /** Reetiqueta um NFA: simbolo -> conjunto de simbolos canonicos, ou vazio = epsilon. */
  public static Nfa relabel(Nfa in, Map<String, Set<String>> map) {
    Nfa out = new Nfa();
    for (int k = 0; k < in.t.size(); k++) out.add();
    out.start = in.start; out.accept.addAll(in.accept);
    for (int k = 0; k < in.t.size(); k++)
      for (var e : in.t.get(k).entrySet())
        for (int d : e.getValue()) {
          if (e.getKey().equals(Nfa.EPS)) { out.edge(k, Nfa.EPS, d); continue; }
          Set<String> to = map.get(e.getKey());
          if (to == null) throw new IllegalStateException("evento sem mapeamento: " + e.getKey());
          if (to.isEmpty()) out.edge(k, Nfa.EPS, d);
          else for (String c : to) out.edge(k, c, d);
        }
    return out;
  }

  /** Intersecao com "no maximo uma ocorrencia de simbolo de `criadores`" (normalizacao N1). */
  public static Dfa atMostOneCreation(Dfa d, Set<String> criadores) {
    // produto com automato de 2 estados (0 = nenhum criador visto, 1 = um visto)
    Dfa r = new Dfa(); r.alpha = d.alpha;
    Map<String, Integer> idx = new LinkedHashMap<>();
    List<int[]> lst = new ArrayList<>(); Deque<int[]> q = new ArrayDeque<>();
    int[] s0 = {0, 0}; idx.put("0,0", 0); lst.add(s0); q.add(s0); r.delta.add(new LinkedHashMap<>());
    while (!q.isEmpty()) {
      int[] cur = q.poll(); int ci = idx.get(cur[0] + "," + cur[1]);
      for (var e : d.delta.get(cur[0]).entrySet()) {
        int c2 = criadores.contains(e.getKey()) ? cur[1] + 1 : cur[1];
        if (c2 > 1) continue;
        int[] np = {e.getValue(), c2}; String key = np[0] + "," + np[1];
        Integer ni = idx.get(key);
        if (ni == null) { ni = lst.size(); idx.put(key, ni); lst.add(np); q.add(np); r.delta.add(new LinkedHashMap<>()); }
        r.delta.get(ci).put(e.getKey(), ni);
      }
    }
    for (int k = 0; k < lst.size(); k++) if (d.accept.contains(lst.get(k)[0])) r.accept.add(k);
    return r;
  }
}
