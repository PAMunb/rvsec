package presto.android.gui.clients;

import br.unb.cic.mop.extractor.model.MopMethod;
import org.junit.Test;
import static org.junit.Assert.*;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * Unit tests for the bytecode-scan match helpers used by
 * {@code findDirectTargetCallersByBytecodeScan} (BUG-INV-ANA-19 fix).
 *
 * The full scan loop walks Soot {@code Body}/{@code InvokeExpr} structures
 * and is exercised end-to-end by integration tests on real APKs. These
 * tests cover the matching policy in isolation: keys are built from MOP
 * signatures with FQN class + method name (overload-insensitive, mirroring
 * {@link RvsecAnalysisClient#resolveMopInScene}).
 */
public class BytecodeScanMatchTest {

	private static MopMethod mop(String className, String methodName) {
		return new MopMethod(className, methodName, Collections.emptyList(),
				className + "." + methodName + "()");
	}

	private static Set<MopMethod> setOf(MopMethod... methods) {
		return new HashSet<>(Arrays.asList(methods));
	}

	@Test
	public void testBuildMopKeysEmpty() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(Collections.emptySet());
		assertTrue("Empty signatures must produce empty keys", keys.isEmpty());
	}

	@Test
	public void testBuildMopKeysSingleSignature() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(
				setOf(mop("java.security.SecureRandom", "nextInt")));
		assertEquals(Collections.singleton("java.security.SecureRandom#nextInt"), keys);
	}

	@Test
	public void testBuildMopKeysCollapsesOverloads() {
		// resolveMopInScene matches by (className, methodName) only —
		// MopMethod entries differing solely in parameter list collapse to
		// the same key. The bytecode scanner must follow the same policy.
		Set<MopMethod> sigs = new HashSet<>();
		sigs.add(new MopMethod("java.security.SecureRandom", "nextInt",
				Collections.singletonList("int"), "nextInt(int)"));
		sigs.add(new MopMethod("java.security.SecureRandom", "nextInt",
				Collections.emptyList(), "nextInt()"));
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(sigs);
		assertEquals("Both overloads must collapse to one key", 1, keys.size());
		assertTrue(keys.contains("java.security.SecureRandom#nextInt"));
	}

	@Test
	public void testBuildMopKeysMultipleSignatures() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(setOf(
				mop("java.security.MessageDigest", "getInstance"),
				mop("java.security.MessageDigest", "digest"),
				mop("javax.crypto.Cipher", "init")));
		assertEquals(3, keys.size());
		assertTrue(keys.contains("java.security.MessageDigest#getInstance"));
		assertTrue(keys.contains("java.security.MessageDigest#digest"));
		assertTrue(keys.contains("javax.crypto.Cipher#init"));
	}

	@Test
	public void testMatchesMopSignaturePositive() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(
				setOf(mop("java.security.SecureRandom", "nextInt")));
		assertTrue(RvsecAnalysisClient.matchesTargetSignature(
				"java.security.SecureRandom", "nextInt", keys));
	}

	@Test
	public void testMatchesMopSignatureRejectsDifferentClass() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(
				setOf(mop("java.security.SecureRandom", "nextInt")));
		// Same method name, different class — must not match.
		assertFalse(RvsecAnalysisClient.matchesTargetSignature(
				"java.util.Random", "nextInt", keys));
	}

	@Test
	public void testMatchesMopSignatureRejectsDifferentMethod() {
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(
				setOf(mop("java.security.SecureRandom", "nextInt")));
		// Same class, different method name — must not match.
		assertFalse(RvsecAnalysisClient.matchesTargetSignature(
				"java.security.SecureRandom", "nextLong", keys));
	}

	@Test
	public void testMatchesMopSignatureMatchesAnyOverload() {
		// One key covers any number of overloads.
		Set<String> keys = RvsecAnalysisClient.buildTargetKeys(setOf(
				mop("javax.crypto.Cipher", "init")));
		// Bytecode scanner sees a specific overload at the call site, but
		// match policy ignores parameters — both should hit.
		assertTrue(RvsecAnalysisClient.matchesTargetSignature(
				"javax.crypto.Cipher", "init", keys));
	}

	@Test
	public void testMatchesMopSignatureEmptyKeysAlwaysFalse() {
		Set<String> keys = Collections.emptySet();
		assertFalse(RvsecAnalysisClient.matchesTargetSignature(
				"java.security.SecureRandom", "nextInt", keys));
	}
}
