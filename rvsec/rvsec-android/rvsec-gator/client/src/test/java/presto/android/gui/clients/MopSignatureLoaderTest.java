package presto.android.gui.clients;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import javamop.util.MOPException;

import org.junit.*;
import org.junit.rules.TemporaryFolder;
import static org.junit.Assert.*;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.net.URL;
import java.nio.file.Files;
import java.util.AbstractMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Tests MOP signature loading by calling JavamopFacade.listUsedMethods()
 * with real .mop spec files from test resources (test-specs/).
 *
 * RvsecAnalysisClient.loadMopSignatures() is private but delegates to
 * JavamopFacade, so we test the same facade directly.
 */
public class MopSignatureLoaderTest {

	@Rule
	public TemporaryFolder tempDir = new TemporaryFolder();

	private JavamopFacade facade;

	@Before
	public void setUp() {
		facade = new JavamopFacade();
	}

	// ── helpers ──────────────────────────────────────────────────────────

	/**
	 * Copy a test resource file into the given target directory.
	 */
	private void copyResourceToDir(String resourceName, File targetDir)
			throws URISyntaxException, IOException {
		URL resource = getClass().getClassLoader().getResource("test-specs/" + resourceName);
		assertNotNull("Test resource not found: test-specs/" + resourceName, resource);
		File src = new File(resource.toURI());
		Files.copy(src.toPath(), new File(targetDir, resourceName).toPath());
	}

	/**
	 * Extract (className, methodName) pairs from a set of MopMethod.
	 */
	private Set<Map.Entry<String, String>> classMethodPairs(Set<MopMethod> methods) {
		return methods.stream()
				.map(m -> new AbstractMap.SimpleEntry<>(m.getClassName(), m.getName()))
				.collect(Collectors.toSet());
	}

	/**
	 * Check that the set of MopMethod contains at least one entry matching
	 * the given className and methodName.
	 */
	private void assertContainsMethod(Set<MopMethod> methods, String className, String methodName) {
		boolean found = methods.stream()
				.anyMatch(m -> className.equals(m.getClassName()) && methodName.equals(m.getName()));
		assertTrue(
				String.format("Expected method %s.%s not found in: %s", className, methodName, methods),
				found);
	}

	// ── test cases ──────────────────────────────────────────────────────

	@Test
	public void testLoadMessageDigestSpec() throws Exception {
		File specDir = tempDir.newFolder("md-specs");
		copyResourceToDir("MessageDigestSpec.mop", specDir);

		Set<MopMethod> methods = facade.listUsedMethods(specDir.getAbsolutePath(), false);

		assertFalse("Should return at least one method", methods.isEmpty());

		assertContainsMethod(methods, "java.security.MessageDigest", "getInstance");
		assertContainsMethod(methods, "java.security.MessageDigest", "digest");
		assertContainsMethod(methods, "java.security.MessageDigest", "update");
		assertContainsMethod(methods, "java.security.MessageDigest", "reset");
	}

	@Test
	public void testLoadCipherSpec() throws Exception {
		File specDir = tempDir.newFolder("cipher-specs");
		copyResourceToDir("CipherSpec.mop", specDir);

		Set<MopMethod> methods = facade.listUsedMethods(specDir.getAbsolutePath(), false);

		assertFalse("Should return at least one method", methods.isEmpty());

		assertContainsMethod(methods, "javax.crypto.Cipher", "getInstance");
		assertContainsMethod(methods, "javax.crypto.Cipher", "init");
		assertContainsMethod(methods, "javax.crypto.Cipher", "doFinal");
		assertContainsMethod(methods, "javax.crypto.Cipher", "update");
	}

	@Test
	public void testLoadMultipleSpecs() throws Exception {
		File specDir = tempDir.newFolder("multi-specs");
		copyResourceToDir("MessageDigestSpec.mop", specDir);
		copyResourceToDir("CipherSpec.mop", specDir);

		Set<MopMethod> methods = facade.listUsedMethods(specDir.getAbsolutePath(), false);

		assertFalse("Should return methods from both specs", methods.isEmpty());

		// Methods from MessageDigestSpec
		assertContainsMethod(methods, "java.security.MessageDigest", "getInstance");
		assertContainsMethod(methods, "java.security.MessageDigest", "digest");

		// Methods from CipherSpec
		assertContainsMethod(methods, "javax.crypto.Cipher", "getInstance");
		assertContainsMethod(methods, "javax.crypto.Cipher", "init");

		// Verify both class names are present
		Set<String> classNames = methods.stream()
				.map(MopMethod::getClassName)
				.collect(Collectors.toSet());
		assertTrue("Should contain MessageDigest class",
				classNames.contains("java.security.MessageDigest"));
		assertTrue("Should contain Cipher class",
				classNames.contains("javax.crypto.Cipher"));
	}

	@Test
	public void testLoadEmptyDirectory() throws Exception {
		File emptyDir = tempDir.newFolder("empty-specs");

		Set<MopMethod> methods = facade.listUsedMethods(emptyDir.getAbsolutePath(), false);

		assertNotNull("Should return a non-null set", methods);
		assertTrue("Should return empty set for empty directory", methods.isEmpty());
	}

	@Test
	public void testLoadDirectoryWithNonMopFiles() throws Exception {
		File nonMopDir = tempDir.newFolder("non-mop-specs");
		File txtFile = new File(nonMopDir, "not-a-spec.txt");
		Files.write(txtFile.toPath(), "This is not a MOP file.".getBytes());

		Set<MopMethod> methods = facade.listUsedMethods(nonMopDir.getAbsolutePath(), false);

		assertNotNull("Should return a non-null set", methods);
		assertTrue("Should return empty set when no .mop files present", methods.isEmpty());
	}
}
