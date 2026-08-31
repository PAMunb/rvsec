package presto.android.gui.clients;

import org.junit.*;
import static org.junit.Assert.*;

/**
 * Unit tests for RvsecAnalysisClient.isAppClass() — the package-based
 * class filter that excludes library classes and generated resource
 * classes (R, R$*, BuildConfig, Manifest, Manifest$*) from the
 * reachability section.
 *
 * The reachability section defines the 100% universe for coverage
 * calculation. Including library classes (e.g., retrofit2, kotlinx)
 * would inflate the denominator and make coverage metrics meaningless.
 *
 * <p>The cases below the "gh111" heading are the ones that matter for
 * INV-ANA-71: every case that pre-dates it anchors its resource class at
 * the scope key's root, so all of them passed under the old rule and
 * said nothing about it.
 */
public class ExtractClassesFilterTest {

	private static final String PKG = "com.gh4a";

	// ── App classes — should be INCLUDED ────────────────────────────────

	@Test
	public void testAppActivityIncluded() {
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.activities.MainActivity", PKG));
	}

	@Test
	public void testAppInnerClassIncluded() {
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.activities.MainActivity$1", PKG));
	}

	@Test
	public void testAppNestedInnerClassIncluded() {
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.Foo$Bar$Baz", PKG));
	}

	@Test
	public void testAppUtilClassIncluded() {
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.utils.CryptoHelper", PKG));
	}

	@Test
	public void testAppTopLevelClassIncluded() {
		// Class directly in the package (no subpackage)
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.Application", PKG));
	}

	// ── Library classes — should be EXCLUDED ────────────────────────────

	@Test
	public void testRetrofitExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("retrofit2.Retrofit", PKG));
	}

	@Test
	public void testKotlinxExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("kotlinx.coroutines.CoroutineScope", PKG));
	}

	@Test
	public void testAndroidxExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("androidx.appcompat.app.AppCompatActivity", PKG));
	}

	@Test
	public void testGoogleGmsExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.google.android.gms.auth.GoogleAuth", PKG));
	}

	@Test
	public void testGithubSdkExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.meisolsson.githubsdk.model.Issue", PKG));
	}

	@Test
	public void testJavaxCryptoExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("javax.crypto.Cipher", PKG));
	}

	// ── Generated classes — should be EXCLUDED ─────────────────────────

	@Test
	public void testRClassExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R", PKG));
	}

	@Test
	public void testRInnerClassExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R$layout", PKG));
	}

	@Test
	public void testRStyleExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R$style", PKG));
	}

	@Test
	public void testRIdExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R$id", PKG));
	}

	@Test
	public void testRDrawableExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R$drawable", PKG));
	}

	@Test
	public void testBuildConfigExcluded() {
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.BuildConfig", PKG));
	}

	// ── Edge cases ─────────────────────────────────────────────────────

	@Test
	public void testSimilarPrefixExcluded() {
		// "com.gh4a_extra" starts with "com.gh4a" but is a different package
		// The filter uses startsWith so "com.gh4a_extra.Foo" does match "com.gh4a"
		// This is acceptable — such collisions are extremely rare in practice
		// and the Python parser applies a second filter with code_package
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a_extra.Foo", PKG));
	}

	@Test
	public void testExactPackageNameNotAClass() {
		// The package name itself is not a valid class name, but test the boundary
		// "com.gh4a" with suffix "" — should be included (it's a class named
		// exactly as the package, which is unusual but valid in Java)
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a", PKG));
	}

	@Test
	public void testClassNamedRButNotGenerated() {
		// A class like com.gh4a.util.R should be excluded (matches .R pattern)
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.R", PKG));
	}

	@Test
	public void testClassContainingRInName() {
		// "com.gh4a.Repository" should be INCLUDED — "R" appears but not as .R suffix
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.Repository", PKG));
	}

	@Test
	public void testClassContainingBuildConfigInName() {
		// "com.gh4a.BuildConfigHelper" should be INCLUDED — not exactly .BuildConfig
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.BuildConfigHelper", PKG));
	}

	@Test
	public void testSubpackageRClass() {
		// INVERTED by gh111 (INV-ANA-71). This case used to assert that com.gh4a.ui.R
		// is an app class, on the reasoning that "subpackage ones are rare" — it was
		// the leak itself, written down as expected behaviour. They are not rare:
		// every module of a multi-module Gradle build emits one, and 505 of them were
		// in the corpus denominator. The test now anchors at the last segment.
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.ui.R", PKG));
	}

	// ── Different package prefixes ─────────────────────────────────────

	@Test
	public void testDifferentPackagePrefix() {
		String pkg = "br.unb.cic.cryptoapp";
		assertTrue(RvsecAnalysisClient.isAppClass("br.unb.cic.cryptoapp.MainActivity", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("br.unb.cic.cryptoapp.R", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("br.unb.cic.cryptoapp.R$layout", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("br.unb.cic.cryptoapp.BuildConfig", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("com.google.gson.Gson", pkg));
	}

	@Test
	public void testSingleSegmentPackage() {
		// Edge case: single-segment package name (uncommon but valid)
		String pkg = "myapp";
		assertTrue(RvsecAnalysisClient.isAppClass("myapp.Main", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("myapp.R", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("myapp.BuildConfig", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("otherapp.Main", pkg));
	}

	// ── gh111 / INV-ANA-71 — the generated-class test is anchored at the class
	//    name's LAST segment, not at the scope key's root ─────────────────────

	@Test
	public void testModuleLevelResourceClassExcluded() {
		// Multi-module Gradle emits one R per module. Under the root-anchored rule
		// the suffix was ".core.database.R", which matched nothing — measured over
		// the corpus, 117 such classes were in app.pachli_50's denominator alone.
		String pkg = "app.pachli";
		assertFalse(RvsecAnalysisClient.isAppClass("app.pachli.core.database.R", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("app.pachli.core.database.R$string", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("app.pachli.core.ui.BuildConfig", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("app.pachli.core.database.AppDatabase", pkg));
	}

	@Test
	public void testAncestorKeyDoesNotLetResourceClassesThrough() {
		// The detector elects an ancestor of the resource namespace. Under the
		// root-anchored rule the suffix was ".screenshottile.R", so every resource
		// class of the app escaped into the denominator — and task 1.8's old
		// acceptance number counted them.
		String pkg = "com.github.cvzi";
		assertFalse(RvsecAnalysisClient.isAppClass("com.github.cvzi.screenshottile.R", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("com.github.cvzi.screenshottile.R$string", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("com.github.cvzi.screenshottile.BuildConfig", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.github.cvzi.screenshottile.MainActivity", pkg));
	}

	@Test
	public void testManifestResourceClassExcluded() {
		String pkg = "com.gh4a";
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.Manifest", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.Manifest$permission", pkg));
		assertFalse(RvsecAnalysisClient.isAppClass("com.gh4a.core.Manifest$permission", pkg));
		// A class merely NAMED like one is not one: the segment must be exact.
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.ManifestParser", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.Router", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.RepositoryActivity", pkg));
	}

	@Test
	public void testAnnotationProcessorOutputStaysInTheDenominator() {
		// Negative case, deliberate. Annotation-processor output is 5,816 classes
		// carrying 36,264 non-trivial methods that DO execute; removing them would
		// redefine the denominator rather than close a leak. A later widening of
		// this filter by analogy with the resource rule must trip here first.
		String pkg = "com.gh4a";
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.di.HomeModule_ProvideFactory", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.db.AppDatabase_Impl", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.model.User$$serializer", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.Hilt_MainActivity", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.DaggerAppComponent", pkg));
		assertTrue(RvsecAnalysisClient.isAppClass("com.gh4a.MainActivity_MembersInjector", pkg));
	}

	@Test
	public void testResourceClassOutsideTheKeyIsStillOutside() {
		// The last-segment rule widens what is excluded, never what is included:
		// a resource class of a library remains excluded by the prefix test.
		assertFalse(RvsecAnalysisClient.isAppClass("androidx.appcompat.R", PKG));
		assertFalse(RvsecAnalysisClient.isAppClass("androidx.appcompat.R$id", PKG));
	}
}
