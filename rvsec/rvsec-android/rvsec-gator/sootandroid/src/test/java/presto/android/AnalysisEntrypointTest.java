/*
 * AnalysisEntrypointTest — pins the four resolution cases of the scope key the
 * app/library guard reads (INV-ANA-65).
 *
 * No Soot, no Scene, no APK: resolveScopeKey is a pure string function, which is
 * exactly why it was extracted. The mistake it guards against — forgetting that
 * Configs.getClientParamCode returns the WHOLE parameter string, prefix included —
 * compiles clean and fails silently, promoting nothing and collapsing the
 * denominator to whatever libPackages.txt happens not to match.
 */
package presto.android;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class AnalysisEntrypointTest {

  private static final String MANIFEST = "com.example.app";

  @Test
  public void parameterPresentStripsThePrefix() {
    assertEquals(
        "com.github.cvzi",
        AnalysisEntrypoint.resolveScopeKey("codePackage=com.github.cvzi", MANIFEST));
  }

  @Test
  public void nullParameterFallsBackToTheManifest() {
    assertEquals(MANIFEST, AnalysisEntrypoint.resolveScopeKey(null, MANIFEST));
  }

  @Test
  public void emptyKeyFallsBackToTheManifest() {
    // "" would make startsWith("") true for every class in the Scene, promoting
    // the whole universe — libraries included — into the denominator.
    assertEquals(MANIFEST, AnalysisEntrypoint.resolveScopeKey("codePackage=", MANIFEST));
  }

  @Test
  public void blankKeyFallsBackToTheManifest() {
    assertEquals(MANIFEST, AnalysisEntrypoint.resolveScopeKey("codePackage=   ", MANIFEST));
  }

  @Test
  public void nonPrefixParameterFallsBackToTheManifest() {
    assertEquals(
        MANIFEST, AnalysisEntrypoint.resolveScopeKey("targetsFile=/tmp/targets.txt", MANIFEST));
  }

  @Test
  public void theWholeParameterIsNeverUsedAsTheKey() {
    // The regression this suite exists for: returning the raw parameter would make
    // the guard test startsWith("codePackage=..."), which no class name satisfies.
    String resolved = AnalysisEntrypoint.resolveScopeKey("codePackage=app.pachli", MANIFEST);
    assertEquals("app.pachli", resolved);
  }
}
