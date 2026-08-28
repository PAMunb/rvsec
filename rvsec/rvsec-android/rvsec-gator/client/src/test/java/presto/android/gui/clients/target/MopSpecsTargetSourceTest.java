package presto.android.gui.clients.target;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.net.URL;
import java.nio.file.Files;
import java.util.Set;
import java.util.TreeSet;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * INV-ANA-41 — the {@code MopMethod → TargetMethod} propagation boundary.
 *
 * <p>The extractor's own tests stop at {@code MopMethod}; the matcher's tests start at
 * {@code TargetMethod}. This is the seam between them, and it is a seam where a flag can be
 * dropped without anything else going red: a target that loses {@code includeSubtypes} still
 * loads, still counts, and still matches — just never against a subtype, which is the entire
 * behaviour being added.
 */
public class MopSpecsTargetSourceTest {

	@Rule
	public TemporaryFolder tempDir = new TemporaryFolder();

	@Test
	public void hierarchyDeclaredSpecsCarryTheirFlagsAcrossTheBoundary() throws Exception {
		File dir = specDir("generic", "Collection_UnsynchronizedAddAll.mop");
		Set<TargetMethod> targets = new MopSpecsTargetSource(dir.getAbsolutePath()).load();
		assertFalse("the fixture must yield targets at all", targets.isEmpty());

		TargetMethod addAll = find(targets, "java.util.Collection", "addAll");
		assertTrue("Collection+ must arrive as includeSubtypes", addAll.isIncludeSubtypes());
		assertFalse("addAll is a literal name", addAll.isNameIsPattern());

		TargetMethod add = find(targets, "java.util.Collection", "add*");
		assertTrue("add* must arrive as a name pattern", add.isNameIsPattern());
		assertTrue("...on a subtype owner", add.isIncludeSubtypes());

		for (TargetMethod t : targets) {
			assertEquals("the policy axis is untouched by this capability",
					TargetMethod.MatchPolicy.LENIENT, t.getPolicy());
		}
	}

	@Test
	public void jcaSpecsCarryBothFlagsFalse() throws Exception {
		File dir = specDir("jca", "CipherSpec.mop", "MessageDigestSpec.mop");
		Set<TargetMethod> targets = new MopSpecsTargetSource(dir.getAbsolutePath()).load();
		assertFalse(targets.isEmpty());
		for (TargetMethod t : targets) {
			assertFalse("no JCA pointcut declares a `+` owner: " + t, t.isIncludeSubtypes());
			assertFalse("no JCA pointcut declares a wildcard name: " + t, t.isNameIsPattern());
		}
	}

	@Test
	public void targetsDifferingOnlyBySubtypeFlagBothSurvive() throws Exception {
		// Map_UnsafeIterator writes `Iterator.next` (exact) while ListIterator_Set writes
		// `Iterator+.next`. If the flag were dropped at this boundary — or left out of
		// TargetMethod's identity — the two would collapse into one entry in the Set and the
		// subtype target would silently vanish.
		File dir = specDir("mixed", "Collection_UnsynchronizedAddAll.mop", "Map_UnsafeIterator.mop");
		Set<TargetMethod> targets = new MopSpecsTargetSource(dir.getAbsolutePath()).load();

		Set<String> iteratorNext = new TreeSet<>();
		for (TargetMethod t : targets) {
			if ("java.util.Iterator".equals(t.getClassName()) && "next".equals(t.getMethodName())) {
				iteratorNext.add(t.isIncludeSubtypes() ? "subtype" : "exact");
			}
		}
		assertTrue("the exact Iterator.next target must be present",
				iteratorNext.contains("exact"));
	}

	@Test
	public void seededOwnerArrivesStrictAndCarriesFqnParameters() throws Exception {
		// The policy half of INV-ANA-40 boundary (c). `RandomStringPassword.mop` names the owner
		// `String` and imports neither java.lang explicitly nor by wildcard, so its owner
		// resolves only at the third and last step — and a target that took that route MUST
		// arrive STRICT. The two halves are one decision: resolving the owner while leaving the
		// target LENIENT is the forbidden middle state, because `String#valueOf` would then
		// match every overload (measured: 74 call sites over 3 corpus APKs, 17 of them woven).
		File dir = specDir("seeded", "RandomStringPassword.mop");
		Set<TargetMethod> targets = new MopSpecsTargetSource(dir.getAbsolutePath()).load();
		assertEquals("the spec declares exactly two call() pointcuts", 2, targets.size());

		TargetMethod valueOf = find(targets, "java.lang.String", "valueOf");
		assertEquals("a seeded owner must arrive STRICT", TargetMethod.MatchPolicy.STRICT,
				valueOf.getPolicy());
		// Without the FQN resolution the STRICT policy is inexpressible rather than merely
		// imprecise: TargetResolver compares against the Soot signature, which reads
		// java.lang.Object where the pointcut wrote Object, so the target would match nothing.
		assertEquals("its parameters must be FQN, or STRICT can never match",
				java.util.Collections.singletonList("java.lang.Object"), valueOf.getParams());

		TargetMethod toCharArray = find(targets, "java.lang.String", "toCharArray");
		assertEquals(TargetMethod.MatchPolicy.STRICT, toCharArray.getPolicy());
		assertTrue("toCharArray takes no parameters", toCharArray.getParams().isEmpty());

		for (TargetMethod t : targets) {
			assertFalse("neither pointcut declares a `+` owner: " + t, t.isIncludeSubtypes());
			assertFalse("neither declares a wildcard name: " + t, t.isNameIsPattern());
		}
	}

	@Test
	public void anOwnerResolvedByItsOwnImportStaysLenient() throws Exception {
		// The criterion is the ROUTE, not the package — asserted here because getting it wrong
		// is silent. `Collection_UnsynchronizedAddAll` and `Map_UnsafeIterator` declare owners
		// that their own imports resolve, including java.lang ones, so none of them may become
		// STRICT: they write `(..)` parameters, which STRICT could never match.
		File dir = specDir("imported", "Collection_UnsynchronizedAddAll.mop", "Map_UnsafeIterator.mop");
		for (TargetMethod t : new MopSpecsTargetSource(dir.getAbsolutePath()).load()) {
			assertEquals("an owner its spec imports must stay LENIENT: " + t,
					TargetMethod.MatchPolicy.LENIENT, t.getPolicy());
		}
	}

	private File specDir(String name, String... specs) throws Exception {
		File dir = tempDir.newFolder(name + "-specs");
		for (String spec : specs) {
			copyResource(dir, spec);
		}
		return dir;
	}

	private void copyResource(File dir, String name) throws URISyntaxException, IOException {
		URL res = getClass().getClassLoader().getResource("test-specs/" + name);
		assertNotNull("Missing test resource: test-specs/" + name, res);
		Files.copy(new File(res.toURI()).toPath(), new File(dir, name).toPath());
	}

	private static TargetMethod find(Set<TargetMethod> targets, String className, String methodName) {
		for (TargetMethod t : targets) {
			if (t.getClassName().equals(className) && t.getMethodName().equals(methodName)) {
				return t;
			}
		}
		throw new AssertionError("no target " + className + "#" + methodName + " was loaded");
	}
}
