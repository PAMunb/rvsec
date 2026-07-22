package presto.android.gui.clients.target;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.net.URL;
import java.nio.file.Files;
import java.util.AbstractMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;

/**
 * INV-ANA-35: {@link MopSpecsTargetSource#load()} MUST produce a set
 * whose cardinality and {@code (className, methodName)} pairs equal
 * those produced by the historical {@code loadMopSignatures} path
 * (a direct call to {@link JavamopFacade#listUsedMethods(String, boolean)}).
 *
 * <p>The "exactly 16 entries on cryptoapp.mop" half of INV-ANA-35
 * is exercised by the end-to-end {@code gator} smoke in task 1.9
 * (against the real {@code cryptoapp.mop} directory on disk). This
 * unit test verifies the load-bearing parity invariant on a
 * portable subset: CipherSpec + MessageDigestSpec from test-specs/.
 */
public class MopSpecsParityTest {

	@Rule
	public TemporaryFolder tempDir = new TemporaryFolder();

	private File specDir;

	@Before
	public void setUp() throws Exception {
		specDir = tempDir.newFolder("parity-specs");
		copyResource("CipherSpec.mop");
		copyResource("MessageDigestSpec.mop");
	}

	private void copyResource(String name) throws URISyntaxException, IOException {
		URL res = getClass().getClassLoader().getResource("test-specs/" + name);
		assertNotNull("Missing test resource: test-specs/" + name, res);
		Files.copy(new File(res.toURI()).toPath(),
				new File(specDir, name).toPath());
	}

	@Test
	public void mopSpecsTargetSourceLoadMatchesJavamopFacadeByteForByte() throws Exception {
		Set<MopMethod> legacy = new JavamopFacade()
				.listUsedMethods(specDir.getAbsolutePath(), false);
		Set<TargetMethod> targets = new MopSpecsTargetSource(specDir.getAbsolutePath()).load();

		assertFalse("Legacy facade must return non-empty for CipherSpec+MessageDigestSpec",
				legacy.isEmpty());
		assertEquals("Cardinality must match the legacy loader (INV-ANA-35)",
				legacy.size(), targets.size());

		Set<Map.Entry<String, String>> legacyPairs = legacy.stream()
				.map(m -> new AbstractMap.SimpleEntry<>(m.getClassName(), m.getName()))
				.collect(Collectors.toSet());
		Set<Map.Entry<String, String>> targetPairs = targets.stream()
				.map(t -> new AbstractMap.SimpleEntry<>(t.getClassName(), t.getMethodName()))
				.collect(Collectors.toSet());

		assertEquals("(className, methodName) pairs must match (INV-ANA-35)",
				legacyPairs, targetPairs);
	}

	@Test
	public void mopSpecsTargetSourceEmitsLenientPolicy() throws Exception {
		Set<TargetMethod> targets = new MopSpecsTargetSource(specDir.getAbsolutePath()).load();
		assertFalse(targets.isEmpty());
		for (TargetMethod t : targets) {
			assertEquals("MopSpecsTargetSource must emit LENIENT — class+name match contract",
					TargetMethod.MatchPolicy.LENIENT, t.getPolicy());
		}
	}

	@Test
	public void emptyDirYieldsEmptySetWithoutThrowing() throws Exception {
		File emptyDir = tempDir.newFolder("empty-specs");
		Set<TargetMethod> targets = new MopSpecsTargetSource(emptyDir.getAbsolutePath()).load();
		assertNotNull(targets);
		assertEquals(0, targets.size());
	}
}
