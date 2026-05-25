package presto.android.gui.clients.json;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.HashSet;
import java.util.Set;

import org.junit.Test;

/**
 * Structural invariants on {@link JsonSchema.Keys}.
 *
 * <p>The Python-side parity test ({@code tests/parity/json_keys.py})
 * compares this class's runtime field values against the Python
 * {@code _JK} mirror via the {@link JsonSchemaKeysDump} reflection
 * helper. INV-ANA-32 says the comparison surfaces missing keys on
 * either side as a test failure. The checks below pin the producer
 * side: every constant is {@code public static final String}, values
 * are non-empty and unique, and the {@code COMPLETE} sentinel is
 * present.
 */
public class JsonSchemaKeysTest {

	@Test
	public void allFieldsArePublicStaticFinalString() {
		for (Field f : JsonSchema.Keys.class.getDeclaredFields()) {
			int mods = f.getModifiers();
			assertTrue("Field " + f.getName() + " must be public", Modifier.isPublic(mods));
			assertTrue("Field " + f.getName() + " must be static", Modifier.isStatic(mods));
			assertTrue("Field " + f.getName() + " must be final", Modifier.isFinal(mods));
			assertEquals("Field " + f.getName() + " must be String",
					String.class, f.getType());
		}
	}

	@Test
	public void allValuesAreNonEmpty() throws IllegalAccessException {
		for (Field f : JsonSchema.Keys.class.getDeclaredFields()) {
			if (!Modifier.isStatic(f.getModifiers()) || f.getType() != String.class) {
				continue;
			}
			String value = (String) f.get(null);
			assertNotNull(f.getName(), value);
			assertFalse("Field " + f.getName() + " value must be non-empty",
					value.isEmpty());
		}
	}

	@Test
	public void valuesAreUnique() throws IllegalAccessException {
		Set<String> seen = new HashSet<>();
		for (Field f : JsonSchema.Keys.class.getDeclaredFields()) {
			if (!Modifier.isStatic(f.getModifiers()) || f.getType() != String.class) {
				continue;
			}
			String value = (String) f.get(null);
			assertTrue("Duplicate JSON key value: " + value + " on " + f.getName(),
					seen.add(value));
		}
	}

	@Test
	public void completeSentinelIsPresent() {
		assertEquals("complete", JsonSchema.Keys.COMPLETE);
	}

	@Test
	public void packageAndMainActivityHaveGh57Names() {
		// Group 6 (C1f) does not rename these — they are app-metadata, not
		// reachability fields. Pinning preserves consumer compatibility.
		assertEquals("package", JsonSchema.Keys.PACKAGE);
		assertEquals("mainActivity", JsonSchema.Keys.MAIN_ACTIVITY);
	}

	@Test
	public void targetKeysStillUseGh57MopValuesPreC1f() {
		// Constant NAMES use target nomenclature (so C1f is value-only);
		// constant VALUES still emit MOP names until C1f flips them.
		assertEquals("reachesTarget", JsonSchema.Keys.REACHES_TARGET);
		assertEquals("directlyReachesTarget", JsonSchema.Keys.DIRECTLY_REACHES_TARGET);
		assertEquals("targetMethods", JsonSchema.Keys.TARGET_METHODS);
	}

	@Test
	public void keysDumpExitsCleanlyAndProducesExpectedCount() throws Exception {
		// Don't subprocess the JVM here — that's the Python parity test's
		// job. We can invoke main() directly and capture stdout to confirm
		// the dumper prints one line per key. The Python test does the same
		// via subprocess.run([java, "-cp", "...", "JsonSchemaKeysDump"]).
		java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
		java.io.PrintStream old = System.out;
		System.setOut(new java.io.PrintStream(baos));
		try {
			JsonSchemaKeysDump.main(new String[]{});
		} finally {
			System.setOut(old);
		}
		String[] lines = baos.toString().trim().split("\n");
		int expected = (int) java.util.Arrays.stream(
				JsonSchema.Keys.class.getDeclaredFields())
				.filter(f -> Modifier.isStatic(f.getModifiers())
						&& f.getType() == String.class)
				.count();
		assertEquals(expected, lines.length);
	}
}
