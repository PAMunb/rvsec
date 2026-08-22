import org.objectweb.asm.*;
import java.io.*;
import java.util.*;
import java.util.zip.*;

/** Indexa o android.jar e confere cada assinatura resolvida pelo CrySLParser. */
public class ApiCheck {
  // classe -> conjunto de "nome(tipo,tipo)" e "nome/aridade"
  static Map<String, Set<String>> byName = new HashMap<>();
  static Map<String, Set<String>> byNameArity = new HashMap<>();
  static Map<String, Boolean> isStatic = new HashMap<>();
  static Set<String> classes = new HashSet<>();

  static String desc2java(Type t) { return t.getClassName(); }

  public static void main(String[] a) throws Exception {
    try (ZipFile z = new ZipFile(a[0])) {
      Enumeration<? extends ZipEntry> en = z.entries();
      while (en.hasMoreElements()) {
        ZipEntry e = en.nextElement();
        if (!e.getName().endsWith(".class")) continue;
        try (InputStream in = z.getInputStream(e)) {
          ClassReader cr = new ClassReader(in);
          String cn = cr.getClassName().replace('/', '.');
          classes.add(cn);
          cr.accept(new ClassVisitor(Opcodes.ASM9) {
            public MethodVisitor visitMethod(int acc, String name, String desc, String sig, String[] ex) {
              Type[] ps = Type.getArgumentTypes(desc);
              StringBuilder sb = new StringBuilder(cn).append("#").append(name).append("(");
              for (int i = 0; i < ps.length; i++) { if (i>0) sb.append(","); sb.append(desc2java(ps[i])); }
              sb.append(")");
              byName.computeIfAbsent(cn, k -> new HashSet<>()).add(sb.toString());
              byNameArity.computeIfAbsent(cn, k -> new HashSet<>()).add(cn + "#" + name + "/" + ps.length);
              isStatic.put(sb.toString(), (acc & Opcodes.ACC_STATIC) != 0);
              return null;
            }
          }, ClassReader.SKIP_CODE | ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
        } catch (Exception ignored) {}
      }
    }
    System.err.println("# android.jar indexado: " + classes.size() + " classes");

    BufferedReader br = new BufferedReader(new FileReader(a[1]));
    String line; int tot=0, exato=0, aridade=0, semClasse=0, ausente=0;
    while ((line = br.readLine()) != null) {
      if (!line.startsWith("EVENT")) continue;
      String[] f = line.split("\t");
      String sig = f[2];                                // fqn.metodo(nome:Tipo,...)->ret
      String head = sig.substring(0, sig.indexOf("->"));
      int par = head.indexOf('(');
      String fq = head.substring(0, par);
      String argsRaw = head.substring(par+1, head.length()-1);
      String cls, mth;
      if (classes.contains(fq)) { cls = fq; mth = "<init>"; }
      else { int dot = fq.lastIndexOf('.'); cls = fq.substring(0, dot); mth = fq.substring(dot+1); }
      List<String> types = new ArrayList<>();
      boolean anyType = false;
      if (!argsRaw.isBlank()) for (String p : argsRaw.split(",")) {
        String t = p.substring(p.indexOf(':')+1);
        if (t.equals("AnyType")) anyType = true;
        types.add(t);
      }
      tot++;
      if (!classes.contains(cls)) { semClasse++; System.out.println("CLASSE-AUSENTE\t"+f[1]+"\t"+sig); continue; }
      // construtor: o nome curto == nome da classe
      String m = mth;
      String key = cls + "#" + m + "(" + String.join(",", types) + ")";
      if (!anyType && byName.getOrDefault(cls, Set.of()).contains(key)) { exato++; continue; }
      if (byNameArity.getOrDefault(cls, Set.of()).contains(cls + "#" + m + "/" + types.size())) {
        aridade++;
        if (!anyType) System.out.println("SO-ARIDADE\t"+f[1]+"\t"+sig);
        continue;
      }
      ausente++;
      System.out.println("METODO-AUSENTE\t"+f[1]+"\t"+sig);
    }
    System.err.println("# eventos=" + tot + " assinatura-exata=" + exato + " so-aridade=" + aridade
        + " classe-ausente=" + semClasse + " metodo-ausente=" + ausente);
  }
}
