import crysl.parsing.CrySLModelReader;
import crysl.parsing.CrySLModelReaderClassPath;
import crysl.rule.*;

import java.io.File;
import java.net.URL;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/** V3: le api30 com e sem android.jar no classpath virtual e compara os tipos resolvidos. */
public class V3 {
  public static void main(String[] args) throws Exception {
    String dir = args[0];
    String modo = args[1];              // "jdk" ou "android"
    String androidJar = args.length > 2 ? args[2] : null;

    CrySLModelReader reader;
    if ("android".equals(modo)) {
      CrySLModelReaderClassPath cp =
          CrySLModelReaderClassPath.createFromPaths(List.of(Paths.get(androidJar)));
      URL[] urls = cp.getClassPath();
      System.err.println("# classpath virtual tem " + urls.length + " entradas");
      System.err.println("# primeiras 5: " + Arrays.stream(urls).limit(5).map(URL::toString).collect(Collectors.joining(", ")));
      System.err.println("# posicao do android.jar: " +
          java.util.stream.IntStream.range(0, urls.length)
            .filter(i -> urls[i].toString().contains("android.jar")).boxed().toList());
      reader = new CrySLModelReader(cp);
    } else {
      reader = new CrySLModelReader();
    }

    File[] files = new File(dir).listFiles((d, n) -> n.endsWith(".crysl"));
    Arrays.sort(files);
    int ok = 0, fail = 0;
    for (File f : files) {
      try {
        CrySLRule r = reader.readRule(f);
        ok++;
        List<String> evs = r.getEvents().stream()
            .map(m -> m.getMethodName() + "(" + m.getParameters().stream()
                 .map(p -> p.getKey() + ":" + p.getValue()).collect(Collectors.joining(",")) + ")->" 
                 + (m.getRetObject()==null?"?":m.getRetObject().getKey()+":"+m.getRetObject().getValue()))
            .sorted().toList();
        for (String e : evs) System.out.println("EVENT\t" + f.getName() + "\t" + e);
        List<String> fbs = r.getForbiddenMethods().stream().map(Object::toString).sorted().toList();
        for (String e : fbs) System.out.println("FORBID\t" + f.getName() + "\t" + e);
      } catch (Throwable e) {
        fail++;
        System.out.println("FAIL\t" + f.getName() + "\t" + e.getClass().getSimpleName() + "\t"
            + String.valueOf(e.getMessage()).replace('\n',' '));
      }
    }
    System.err.println("# " + modo + ": ok=" + ok + " fail=" + fail + " total=" + files.length);
  }
}
