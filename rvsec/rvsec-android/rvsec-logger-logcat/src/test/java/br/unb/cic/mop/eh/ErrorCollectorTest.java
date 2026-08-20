package br.unb.cic.mop.eh;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * Covers the line text of a violation report and nothing else.
 *
 * <p>
 * {@code addError} is deliberately never called here. Its only observable effect is a call into
 * {@code android.util.Log}, and the {@code android} artifact this module compiles against is the
 * stub jar (scope {@code provided}) whose every method body is {@code throw new
 * RuntimeException("Stub!")} — so any test that reached {@code Log.v} would measure the stub, not
 * the collector. {@code buildLine} and {@code escape} are package-private for exactly this reason.
 */
public class ErrorCollectorTest {

	private final ErrorCollector collector = ErrorCollector.instance();

	private ErrorDescription description(String expecting) {
		return new ErrorDescription(
				ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "com.example.Hash.digest(Hash.java:40)", expecting);
	}

	@Test
	public void escapeTurnsANewlineIntoTheTwoCharacterSequence() {
		assertEquals("first\\nsecond", collector.escape("first\nsecond"));
	}

	@Test
	public void escapeHandlesEveryLineTerminatorLogcatWouldSplitOn() {
		assertEquals("a\\nb\\nc", collector.escape("a\r\nb\rc"));
	}

	@Test
	public void escapeLeavesCommasAlone() {
		String expecting = "expecting one of MD5,SHA-256 but found MD2";
		assertEquals(expecting, collector.escape(expecting));
	}

	@Test
	public void escapeLeavesQuotesAlone() {
		String envelope = "v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' exp='MD5' msg=''";
		assertEquals(envelope, collector.escape(envelope));
	}

	@Test
	public void buildLineJoinsTheSummaryAndTheEscapedExpectingWithOneComma() {
		String line = collector.buildLine(description("  expecting one of MD5,SHA-256 but found MD2  "));

		assertEquals(
				"MessageDigestSpec,com.example.Hash,Hash,digest,Hash.java:40,UnsafeAlgorithm,"
						+ "expecting one of MD5,SHA-256 but found MD2",
				line);
	}

	@Test
	public void buildLineEmitsOneLineForAMessageCarryingANewline() {
		String line = collector.buildLine(description("expecting one of MD5\nbut found MD2"));

		assertFalse(line.contains("\n"));
		assertTrue(line.endsWith(",expecting one of MD5\\nbut found MD2"));
	}

	@Test
	public void buildLineSubstitutesTheSentinelEnvelopeForANullExpecting() {
		String line = collector.buildLine(description(null));

		assertEquals(
				"MessageDigestSpec,com.example.Hash,Hash,digest,Hash.java:40,UnsafeAlgorithm,"
						+ "v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''",
				line);
	}

	@Test
	public void buildLineKeepsTheSixSummaryFieldsAheadOfTheSeventh() {
		String line = collector.buildLine(description("unknown"));

		assertEquals(7, line.split(",").length);
	}

	@Test
	public void buildLineReproducesTheRecordedFixtureLineByteForByte() {
		// The Python side of gh104 checks the transport chain against a recorded transcript of
		// this method, `rv-android/data/gh104/evidence/collector_lines.logcat`. A transcript can
		// go stale silently — the fixture would keep passing while the collector had moved on,
		// and the end-to-end test would then be measuring a format nothing emits any more. This
		// test is the other half of that pin: the two enveloped lines of the transcript are
		// asserted here verbatim, so a change to the line text fails in the module that owns it.
		String site = "com.example.vault.Hash.digest(Hash.java:40)";
		String prefix = "MessageDigestSpec,com.example.vault.Hash,Hash,digest,Hash.java:40,"
				+ "InvalidSequenceOfMethodCalls,";
		String envelope = "v=1 code=MESSAGEDIGEST-ORDER-00 ev=%s obj=MessageDigest val='' exp='' "
				+ "msg='the observed call sequence is not one MessageDigestSpec accepts'";

		for (String event : new String[] {"update", "reset"}) {
			String expecting = String.format(envelope, event);
			ErrorDescription err = new ErrorDescription(
					ErrorType.InvalidSequenceOfMethodCalls, "MessageDigestSpec", site, expecting);

			assertEquals(prefix + expecting, collector.buildLine(err));
		}
	}
}
