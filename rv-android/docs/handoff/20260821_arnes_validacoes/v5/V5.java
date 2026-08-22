import com.google.inject.Injector;
import de.darmstadt.tu.crossing.CrySLStandaloneSetup;
import de.darmstadt.tu.crossing.crySL.*;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.xtext.common.types.access.impl.ClasspathTypeProvider;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.XtextResourceSet;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.*;

/** V5: recupera nomes de evento e de agregado (e a posicao) andando a AST EMF,
 *  replicando a inicializacao que a fachada CrySLParser esconde. */
public class V5 {
  public static void main(String[] a) throws java.lang.Exception {
    Injector inj = new CrySLStandaloneSetup().createInjectorAndDoEMFRegistration();
    XtextResourceSet rs = inj.getInstance(XtextResourceSet.class);
    URL[] cp = crysl.parsing.CrySLModelReaderClassPath.JAVA_CLASS_PATH.getClassPath();
    rs.setClasspathURIContext(new URLClassLoader(cp));
    new ClasspathTypeProvider(new URLClassLoader(cp), rs, null, null);

    File[] fs = new File(a[0]).listFiles((d,n)->n.endsWith(".crysl")); Arrays.sort(fs);
    int ok=0, comAgg=0, totalEv=0, totalAgg=0;
    for (File f : fs) {
      Resource r = rs.getResource(URI.createFileURI(f.getAbsolutePath()), true);
      if (r.getContents().isEmpty()) { System.out.println("VAZIO\t"+f.getName()); continue; }
      Domainmodel dm = (Domainmodel) r.getContents().get(0);
      ok++;
      if (dm.getEvents() == null) { System.out.println("SEM-EVENTS\t"+f.getName()); continue; }
      List<String> evs = new ArrayList<>(), aggs = new ArrayList<>();
      for (Event e : dm.getEvents().getEvents()) {
        int line = NodeModelUtils.getNode(e) == null ? -1 : NodeModelUtils.getNode(e).getStartLine();
        if (e instanceof Aggregate ag) {
          List<String> membros = new ArrayList<>();
          for (Event m : ag.getEvents()) membros.add(m.getName());
          aggs.add(ag.getName() + ":=" + String.join("|", membros) + "@" + line);
        } else {
          evs.add(e.getName() + "@" + line);
        }
      }
      totalEv += evs.size(); totalAgg += aggs.size(); if (!aggs.isEmpty()) comAgg++;
      String ord = dm.getOrder()==null ? "-" :
          String.valueOf(NodeModelUtils.getTokenText(NodeModelUtils.getNode(dm.getOrder()))).replaceAll("\\s+"," ").strip();
      System.out.println("OK\t" + f.getName() + "\n   eventos  : " + evs
          + "\n   agregados: " + aggs + "\n   ORDER    : " + ord);
    }
    System.out.println("# arquivos com AST: " + ok + "/" + fs.length
        + "  eventos=" + totalEv + " agregados=" + totalAgg + " regras com agregado=" + comAgg);
  }
}
