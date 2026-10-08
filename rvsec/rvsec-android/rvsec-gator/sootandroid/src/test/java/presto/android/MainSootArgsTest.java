/*
 * MainSootArgsTest — pins the Soot command line GATOR builds (analysis spec, scenario
 * "Kotlin stdlib exclusion impact on reachability").
 *
 * No Soot run: Main.sootArgs is a pure function of its inputs. An -exclude that comes
 * back compiles clean and runs clean; it only shows up as app methods that stop
 * reaching a monitored API through library code, which nothing else checks.
 */
package presto.android;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.List;
import org.junit.Test;

public class MainSootArgsTest {

  private static final String[] ALGORITHMS = { "cha", "rta", "vta", "spark", "", null };

  private static List<String> args(String algo) {
    return Main.sootArgs("wjtp.gui", "/tmp/app.apk", "/sdk/android.jar", algo);
  }

  @Test
  public void noAlgorithmPassesExclude() {
    for (String algo : ALGORITHMS) {
      assertFalse("-exclude with algorithm " + algo, args(algo).contains("-exclude"));
    }
  }

  @Test
  public void noBodiesForExcludedStays() {
    // It acts on Soot's default exclusions (java.*, javax.*, sun.*); removing it moves
    // the September call graph (gh120 design, D1).
    for (String algo : ALGORITHMS) {
      assertTrue("-no-bodies-for-excluded with algorithm " + algo,
          args(algo).contains("-no-bodies-for-excluded"));
    }
  }

  @Test
  public void inputsLandAfterTheirFlags() {
    List<String> a = args("spark");
    assertEquals("/tmp/app.apk", a.get(a.indexOf("-process-dir") + 1));
    assertEquals("/sdk/android.jar", a.get(a.indexOf("-cp") + 1));
    assertEquals("enabled:true", a.get(a.indexOf("wjtp.gui") + 1));
  }

  @Test
  public void sparkEnablesSpark() {
    List<String> a = args("spark");
    int i = a.indexOf("cg.spark");
    assertTrue(i > 0);
    assertEquals("enabled:true", a.get(i + 1));
  }

  @Test
  public void withoutAlgorithmNoCallGraphPhase() {
    assertFalse(args(null).contains("cg"));
    assertFalse(args("").contains("cg"));
  }
}
