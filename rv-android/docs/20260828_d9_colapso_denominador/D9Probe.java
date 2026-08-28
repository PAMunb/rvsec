import soot.*;
import soot.options.Options;
import java.util.*;
import java.io.*;
import javax.xml.parsers.*;
import org.w3c.dom.*;

/**
 * Sonda do D9: carrega a Scene com as MESMAS opcoes do GATOR em modo apk
 * (sem grafo de chamadas, que e o custo dominante) e reproduz o laco de
 * rebaixamento de AnalysisEntrypoint.run() com as duas guardas possiveis.
 *
 * argv: <apk> <manifest.xml> <android.jar> <libPackages.txt> <codePackage>
 */
public class D9Probe {

  static List<String> libPatterns = new ArrayList<>();

  static boolean isLibraryClass(String name) {
    for (String p : libPatterns) {
      if (p.equals(name)
          || ((p.endsWith(".*") || p.endsWith("$*")) && name.startsWith(p.substring(0, p.length() - 1)))) {
        return true;
      }
    }
    return false;
  }

  public static void main(String[] args) throws Exception {
    String apk = args[0], manifest = args[1], androidJar = args[2], libFile = args[3], codePkg = args[4];

    for (String l : new ArrayList<>(java.nio.file.Files.readAllLines(new File(libFile).toPath()))) {
      if (!l.trim().isEmpty()) libPatterns.add(l.trim());
    }

    Options.v().set_force_android_jar(androidJar);
    Options.v().set_src_prec(Options.src_prec_apk);
    Options.v().set_process_dir(Collections.singletonList(apk));
    Options.v().set_allow_phantom_refs(true);
    Options.v().set_no_bodies_for_excluded(true);
    Options.v().set_search_dex_in_archives(true);
    Options.v().set_keep_line_number(true);
    Options.v().set_output_format(Options.output_format_none);
    Options.v().set_ignore_resolution_errors(true);
    Options.v().set_throw_analysis(Options.throw_analysis_dalvik);
    Options.v().set_exclude(Arrays.asList("kotlin.", "kotlinx.", "androidx.compose."));

    long t0 = System.currentTimeMillis();
    Scene.v().loadNecessaryClasses();
    long t1 = System.currentTimeMillis();

    int total = Scene.v().getClasses().size();
    int app0 = Scene.v().getApplicationClasses().size();
    int lib0 = Scene.v().getLibraryClasses().size();
    int ph0 = Scene.v().getPhantomClasses().size();
    System.out.printf("[carga] %.1fs | Scene=%d app=%d lib=%d phantom=%d%n",
        (t1 - t0) / 1000.0, total, app0, lib0, ph0);

    // De quais DEX vieram? Conta por prefixo do app.
    int underCode = 0;
    for (SootClass c : Scene.v().getApplicationClasses()) {
      if (c.getName().startsWith(codePkg)) underCode++;
    }
    System.out.printf("[carga] app classes sob '%s' ANTES do rebaixamento: %d%n", codePkg, underCode);

    // Atividades declaradas no manifesto (o mesmo parse de AnalysisEntrypoint).
    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
    dbf.setNamespaceAware(true);
    Document doc = dbf.newDocumentBuilder().parse(new File(manifest));
    Node root = doc.getElementsByTagName("manifest").item(0);
    String appPkg = root.getAttributes().getNamedItem("package").getTextContent().trim();
    Set<String> activityNames = new HashSet<>();
    Node application = ((Element) root).getElementsByTagName("application").item(0);
    NodeList acts = ((Element) application).getElementsByTagName("activity");
    for (int i = 0; i < acts.getLength(); i++) {
      String n = ((Element) acts.item(i)).getAttribute("android:name");
      if (n.isEmpty()) continue;
      if (n.startsWith(".")) n = appPkg + n;
      activityNames.add(n);
    }
    System.out.printf("[manifesto] package=%s | %d activities%n", appPkg, activityNames.size());

    // Simula o laco de AnalysisEntrypoint.java:111-126 com as duas guardas, sem mutar a Scene.
    for (String guard : new String[] { appPkg, codePkg }) {
      int demoted = 0, app = 0, appUnderCode = 0;
      for (SootClass c : Scene.v().getClasses()) {
        String n = c.getName();
        boolean isApp;
        if (activityNames.contains(n)) {
          isApp = true;                               // :112-118 resgate das activities
        } else if (n.startsWith(guard)) {
          isApp = c.isApplicationClass();             // :119-120 a guarda
        } else if (!c.isPhantomClass() && c.isApplicationClass() && isLibraryClass(n)) {
          isApp = false;                              // :121-124 o rebaixamento
          demoted++;
        } else {
          isApp = c.isApplicationClass();
        }
        if (isApp) {
          app++;
          if (n.startsWith(codePkg)) appUnderCode++;
        }
      }
      System.out.printf("[guarda=%s] rebaixadas=%d  #AppClasses=%d  sob '%s'=%d%n",
          guard, demoted, app, codePkg, appUnderCode);
    }
  }
}
