package presto.android.gui.wtg.flowgraph;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.regex.Pattern;

import org.junit.Test;

/**
 * Static guard for the gh66 container-flow memoization (design decision D4 /
 * INV-ANA-39 purity). The behavioral proof that the optimized
 * {@code buildFlowThroughContainer} produces an identical edge set is the
 * edge-set comparison on real APKs (BaselineComparisonIT on cryptoapp, and the
 * corpus diff-zero via scripts/wtg_edge_diff.py) — the analysis runs as a
 * subprocess, so the cached resolvers cannot be invoked in-process here.
 *
 * What this test CAN lock cheaply and deterministically is the one mechanically
 * checkable part of D4: the field-position caches MUST use the {@code containsKey}-
 * null pattern and MUST NOT use {@code Map.computeIfAbsent}, which does not store a
 * null result and would silently re-resolve every non-container statement on every
 * lookup — reintroducing exactly the redundancy this change removes.
 *
 * It scans the actual {@code FlowgraphRebuilder.java} source (not a copy), with
 * line comments stripped so the "(not computeIfAbsent)" doc comments do not
 * register as violations.
 */
public class FlowgraphRebuilderCacheTest {

	private String sourceWithoutLineComments() throws IOException {
		// surefire runs with user.dir = module basedir (sootandroid) most of the
		// time, but also tolerate the reactor root. Fail loudly if neither hits —
		// this is a gate, not an optional check.
		String rel = "src/main/java/presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java";
		Path base = Paths.get(System.getProperty("user.dir"));
		Path[] candidates = {
				base.resolve(rel),
				base.resolve("sootandroid").resolve(rel),
				base.getParent() == null ? base.resolve(rel) : base.getParent().resolve("sootandroid").resolve(rel),
		};
		Path found = null;
		for (Path c : candidates) {
			if (Files.isRegularFile(c)) {
				found = c;
				break;
			}
		}
		if (found == null) {
			fail("Could not locate FlowgraphRebuilder.java from user.dir=" + base
					+ " — tried " + java.util.Arrays.toString(candidates));
		}
		StringBuilder sb = new StringBuilder();
		for (String line : Files.readAllLines(found)) {
			int idx = line.indexOf("//");
			sb.append(idx >= 0 ? line.substring(0, idx) : line).append('\n');
		}
		return sb.toString();
	}

	@Test
	public void cachesUseContainsKeyNotComputeIfAbsent() throws IOException {
		String src = sourceWithoutLineComments();

		int computeIfAbsentCalls = countMatches(src, "\\.computeIfAbsent\\s*\\(");
		assertEquals("buildFlowThroughContainer caches must use the containsKey-null pattern, "
				+ "never Map.computeIfAbsent (it does not cache null results — D4/INV-ANA-39)",
				0, computeIfAbsentCalls);
	}

	@Test
	public void cachedResolversExistAndCacheNull() throws IOException {
		String src = sourceWithoutLineComments();

		assertTrue("cachedReadContainerField helper must exist",
				src.contains("cachedReadContainerField"));
		assertTrue("cachedWriteContainerField helper must exist",
				src.contains("cachedWriteContainerField"));
		// The containsKey-null pattern: a containsKey gate that returns the cached
		// value (including a cached null) before delegating to the resolver.
		assertTrue("cached resolvers must gate on Map.containsKey to cache null results",
				countMatches(src, "cache\\.containsKey\\s*\\(") >= 2);
	}

	private static int countMatches(String haystack, String regex) {
		java.util.regex.Matcher m = Pattern.compile(regex).matcher(haystack);
		int n = 0;
		while (m.find()) {
			n++;
		}
		return n;
	}
}
