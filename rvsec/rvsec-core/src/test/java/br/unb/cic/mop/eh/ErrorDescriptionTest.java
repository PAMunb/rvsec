package br.unb.cic.mop.eh;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.Test;

/**
 * Splitting a reported stack frame into a class, a method and a source position (issue #89).
 *
 * <p>
 * The values driving these tests are not invented. They are read from
 * {@code src/test/resources/frame-form-corpus.txt}, taken verbatim from the frozen 2026-07-06
 * dataset, and the same corpus drives the Python side in the sibling {@code rv-android}
 * repository ({@code modules/rv-coverage/tests/parser/log/fixtures/frame_form_corpus.py}). One
 * algorithm implemented in two languages will drift unless both are held to the same inputs.
 *
 * <p>
 * What broke before this: the class group of the old pattern accepted {@code $} while the method
 * group was {@code \w+}, which rejects {@code $}, {@code -} and space. Every Kotlin-mangled
 * internal, inline-class method, lambda, Robolectric shadow and backtick test name failed the
 * match and fell through to a fallback that left the entire frame in <em>both</em> the class and
 * the method field — putting a line number inside the key that identifies a unique misuse.
 */
public class ErrorDescriptionTest {

	private static final String CORPUS = "/frame-form-corpus.txt";

	/** One corpus line: a value and, unless it must pass through, its expected split. */
	private static final class Case {
		final String value;
		final String expectedClass;
		final String expectedMethod;
		final String expectedSource;

		Case(String value, String expectedClass, String expectedMethod, String expectedSource) {
			this.value = value;
			this.expectedClass = expectedClass;
			this.expectedMethod = expectedMethod;
			this.expectedSource = expectedSource;
		}

		boolean isFrameForm() {
			return expectedClass != null;
		}
	}

	private static List<Case> corpus() throws IOException {
		List<Case> cases = new ArrayList<>();
		try (InputStream in = ErrorDescriptionTest.class.getResourceAsStream(CORPUS)) {
			assertNotNull("corpus resource " + CORPUS + " must be on the test classpath", in);
			BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
			String line;
			while ((line = reader.readLine()) != null) {
				if (line.trim().isEmpty() || line.startsWith("#")) {
					continue;
				}
				// -1 keeps trailing empty fields, so a malformed line fails loudly here rather
				// than silently becoming a shorter case.
				String[] parts = line.split("\t", -1);
				assertEquals("corpus line must have 4 tab-separated columns: " + line, 4, parts.length);
				if ("-".equals(parts[1])) {
					cases.add(new Case(parts[0], null, null, null));
				} else {
					cases.add(new Case(parts[0], parts[1], parts[2], parts[3]));
				}
			}
		}
		assertFalse("corpus must not be empty", cases.isEmpty());
		return cases;
	}

	private static ErrorSummary summaryOf(String location) {
		return new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", location).getErrorSummary();
	}

	@Test
	public void splitsEveryFrameFormValueInTheCorpus() throws IOException {
		for (Case c : corpus()) {
			if (!c.isFrameForm()) {
				continue;
			}
			ErrorSummary summary = summaryOf(c.value);
			assertEquals(c.value, c.expectedClass, summary.getClassQualifiedName());
			assertEquals(c.value, c.expectedMethod, summary.getMethodName());
			assertEquals(c.value, c.expectedSource, summary.getLocation());
		}
	}

	@Test
	public void neverLeavesASourcePositionInTheClassOrMethodField() throws IOException {
		for (Case c : corpus()) {
			if (!c.isFrameForm()) {
				continue;
			}
			ErrorSummary summary = summaryOf(c.value);
			assertFalse(c.value, summary.getClassQualifiedName().matches(".*\\(.*:\\d+\\)$"));
			assertFalse(c.value, summary.getMethodName().matches(".*\\(.*:\\d+\\)$"));
			assertFalse(c.value, summary.getClassQualifiedName().contains("("));
		}
	}

	@Test
	public void leavesValuesThatAreNotFramesUntouched() throws IOException {
		for (Case c : corpus()) {
			if (c.isFrameForm()) {
				continue;
			}
			// Not a frame: the fallback keeps the value in all three fields, unchanged. This is
			// what guarantees the fix cannot damage input it does not understand.
			ErrorSummary summary = summaryOf(c.value);
			assertEquals(c.value, c.value, summary.getClassQualifiedName());
			assertEquals(c.value, c.value, summary.getMethodName());
			assertEquals(c.value, c.value, summary.getLocation());
		}
	}

	@Test
	public void splitIsIdempotent() throws IOException {
		for (Case c : corpus()) {
			if (!c.isFrameForm()) {
				continue;
			}
			// Re-splitting an already-split class or method must not change it, so running a
			// corrected monitor over data a corrected monitor produced is a no-op.
			assertEquals(c.expectedClass, summaryOf(c.expectedClass).getClassQualifiedName());
			assertEquals(c.expectedMethod, summaryOf(c.expectedMethod).getMethodName());
		}
	}

	@Test
	public void splitsConstructorAndStaticInitializer() {
		ErrorSummary init = summaryOf("com.example.Crypto.<init>(Crypto.java:15)");
		assertEquals("com.example.Crypto", init.getClassQualifiedName());
		assertEquals("<init>", init.getMethodName());

		ErrorSummary clinit = summaryOf("com.example.Crypto.<clinit>(Crypto.java:9)");
		assertEquals("com.example.Crypto", clinit.getClassQualifiedName());
		assertEquals("<clinit>", clinit.getMethodName());
	}

	@Test
	public void splitsBacktickTestNameContainingNestedParentheses() {
		// The reason the guard is anchored on the trailing group and constrains nothing before
		// it: this method name carries its own parenthesis pair.
		String value = "dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest."
				+ "V2-header files (3xx format) are still decryptable after reading a V1-header file"
				+ "(CryptoMigrationV2CompatibilityTest.kt:131)";
		ErrorSummary summary = summaryOf(value);

		assertEquals("dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest", summary.getClassQualifiedName());
		assertEquals("V2-header files (3xx format) are still decryptable after reading a V1-header file",
				summary.getMethodName());
		assertEquals("CryptoMigrationV2CompatibilityTest.kt:131", summary.getLocation());
	}

	@Test
	public void twoAdjacentLinesShareClassAndMethodButNotLocation() {
		ErrorSummary at83 = summaryOf("okio.ByteString.digest$okio(ByteString.kt:83)");
		ErrorSummary at84 = summaryOf("okio.ByteString.digest$okio(ByteString.kt:84)");

		assertEquals(at83.getClassQualifiedName(), at84.getClassQualifiedName());
		assertEquals(at83.getMethodName(), at84.getMethodName());
		assertFalse(at83.getLocation().equals(at84.getLocation()));
	}

	private static final String LOCATION = "okio.ByteString.digest$okio(ByteString.kt:83)";

	private static String envelope(String code, String event, String message) {
		return "v=1 code=" + code + " ev=" + event + " obj=MessageDigest val='MD5' exp='SHA-256' msg='"
				+ message + "'";
	}

	@Test
	public void hashCodeMatchesEquals() {
		// The identity is seven fields — spec, error, class, method, location, code, event — and
		// the message free text is not one of them. Two envelopes that agree on the two identity
		// keys and disagree only in their `msg` tail are therefore one record, and hashCode() must
		// agree with that or both land in different buckets and survive an in-JVM dedup.
		ErrorDescription a = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				envelope("MESSAGEDIGEST-ALG-00", "update", "MD5 is not admitted"));
		ErrorDescription b = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				envelope("MESSAGEDIGEST-ALG-00", "update", "expected one of the admitted digests"));

		assertEquals("MESSAGEDIGEST-ALG-00", a.getErrorSummary().getCode());
		assertEquals("update", a.getErrorSummary().getEvent());
		assertTrue("descriptions differing only in the message free text are equal", a.equals(b));
		assertEquals("equal descriptions must hash equally", a.hashCode(), b.hashCode());

		Set<ErrorDescription> deduped = new HashSet<>();
		deduped.add(a);
		deduped.add(b);
		assertEquals(1, deduped.size());
	}

	@Test
	public void twoEventsAtOneLocationAreTwoRecords() {
		// The reason `event` is in the identity at all. Both reports name the same specification,
		// the same error kind and the same call site, and under the five-field identity that
		// preceded this one they were a single record whose surviving cause was arrival order.
		ErrorDescription viaUpdate = new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls,
				"MessageDigestSpec", LOCATION, envelope("MESSAGEDIGEST-ORDER-00", "update", "out of order"));
		ErrorDescription viaReset = new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls,
				"MessageDigestSpec", LOCATION, envelope("MESSAGEDIGEST-ORDER-00", "reset", "out of order"));

		assertEquals("the failure code alone does not separate them",
				viaUpdate.getErrorSummary().getCode(), viaReset.getErrorSummary().getCode());
		assertFalse("two events at one location are two records", viaUpdate.equals(viaReset));

		Set<ErrorDescription> deduped = new HashSet<>();
		deduped.add(viaUpdate);
		deduped.add(viaReset);
		assertEquals(2, deduped.size());
	}

	@Test
	public void aMessageWithoutAnEnvelopeYieldsTheSentinelTwice() {
		// Every record of a specification set that emits no envelope — the frozen `jca` set, and
		// every record persisted before this change — keeps a readable identity rather than a null
		// one, and two of them still deduplicate exactly as their records allow.
		ErrorDescription a = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				"expecting one of {SHA-256, SHA-512} but found MD5.");
		ErrorDescription b = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				"expecting one of {SHA-256, SHA-512} but found SHA-1.");

		assertEquals("UNSPECIFIED", a.getErrorSummary().getCode());
		assertEquals("UNSPECIFIED", a.getErrorSummary().getEvent());
		assertTrue(a.equals(b));
		assertEquals(a.hashCode(), b.hashCode());
	}

	@Test
	public void theKeysAreReadFromTheEnvelopeAndNotFromTheFreeText() {
		// Absence of the `v=1` marker is what decides, not presence of the characters. A
		// pre-envelope sentence that happens to quote `ev=` must still yield the sentinel, or the
		// five-part and seven-part eras stop being distinguishable in the record.
		ErrorDescription prose = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				"the handler wrote ev=update and code=MESSAGEDIGEST-ALG-00 into the log");

		assertEquals("UNSPECIFIED", prose.getErrorSummary().getCode());
		assertEquals("UNSPECIFIED", prose.getErrorSummary().getEvent());

		// And inside a real envelope, the free-text tail must not supply either key: the grammar
		// puts both immediately after the marker, so the first match is always the record's own.
		ErrorDescription tail = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				envelope("MESSAGEDIGEST-ALG-00", "update", "not the value of ev=g4 nor code=WRONG-99"));

		assertEquals("MESSAGEDIGEST-ALG-00", tail.getErrorSummary().getCode());
		assertEquals("update", tail.getErrorSummary().getEvent());
	}

	@Test
	public void theReportedLineStillCarriesSixSummaryFields() {
		// `code` and `event` enter the identity and not the line: they are already on it, inside
		// the envelope the collector appends as the seventh field. Widening the positional record
		// would break every downstream parser that splits it by count, for nothing gained.
		ErrorSummary summary = new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", LOCATION,
				envelope("MESSAGEDIGEST-ALG-00", "update", "MD5 is not admitted")).getErrorSummary();

		assertEquals(6, summary.toString().split(",").length);
	}

	@Test
	public void hashCodeMatchesEqualsWhenLocationsDifferButSummariesDoNot() {
		// The split is not injective: "F:1" misses the guard and falls back into all three
		// summary fields, while "F:1.F:1(F:1)" hits it and splits to exactly the same triple.
		// Hashing the raw location would give these two equal descriptions different hashes.
		ErrorDescription viaFallback = new ErrorDescription(ErrorType.UnsafeAlgorithm, "S", "F:1");
		ErrorDescription viaSplit = new ErrorDescription(ErrorType.UnsafeAlgorithm, "S", "F:1.F:1(F:1)");

		assertEquals(viaFallback.getErrorSummary(), viaSplit.getErrorSummary());
		assertTrue(viaFallback.equals(viaSplit));
		assertEquals(viaFallback.hashCode(), viaSplit.hashCode());
	}

	@Test
	public void deduplicationStaysLineGranular() {
		// A recorded decision, not an accident: ErrorSummary keeps `location` in equals/hashCode,
		// so a method violated at two lines emits two records. The coarsening to one unique
		// misuse happens downstream.
		Set<ErrorSummary> deduped = new HashSet<>();
		deduped.add(summaryOf("okio.ByteString.digest$okio(ByteString.kt:83)"));
		deduped.add(summaryOf("okio.ByteString.digest$okio(ByteString.kt:84)"));
		deduped.add(summaryOf("okio.ByteString.digest$okio(ByteString.kt:83)"));

		assertEquals(2, deduped.size());
	}
}
