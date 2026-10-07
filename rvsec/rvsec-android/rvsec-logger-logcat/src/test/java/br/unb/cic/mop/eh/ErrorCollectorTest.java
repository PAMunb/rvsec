package br.unb.cic.mop.eh;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.Before;
import org.junit.Test;

/**
 * Covers the line text of a violation report and nothing else.
 *
 * <p>
 * {@code addError} is deliberately never called here. Its only observable effect is a call into
 * {@code android.util.Log}, and the {@code android} artifact this module compiles against is the
 * stub jar (scope {@code provided}) whose every method body is {@code throw new
 * RuntimeException("Stub!")} — so any test that reached {@code Log.v} would measure the stub, not
 * the collector. {@code buildLine}, {@code escape} and {@code occurrenceLine} are package-private for
 * exactly this reason, and {@code occurrenceLine} takes the clock as an argument so the throttle is
 * driven by explicit times instead of by sleeping.
 *
 * <p>
 * The collector is a process-wide singleton, so every test starts from {@code reset()}: a count left
 * by one test would otherwise shift the {@code n} another test asserts.
 */
public class ErrorCollectorTest {

	private static final long MS = 1_000_000L;

	/** An arbitrary origin; only the differences between the times passed to the collector matter. */
	private static final long T0 = 5_000L * MS;

	private final ErrorCollector collector = ErrorCollector.instance();

	@Before
	public void resetCollector() {
		collector.reset();
	}

	private ErrorDescription cipherOrder() {
		return new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherSpec",
				"com.example.Crypto.encrypt(Crypto.java:42)",
				"v=1 code=CIPHER-ORDER-00 ev=doFinal obj='' val='' exp='' msg='x'");
	}

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

	@Test
	public void occurrenceLineWritesTheFirstOccurrence() {
		String line = collector.occurrenceLine(cipherOrder(), T0);

		assertEquals("CipherSpec,com.example.Crypto,Crypto,encrypt,Crypto.java:42,InvalidSequenceOfMethodCalls,"
				+ "CIPHER-ORDER-00,doFinal,1", line);
	}

	@Test
	public void occurrenceLineSuppressesInsideTheWindow() {
		collector.occurrenceLine(cipherOrder(), T0);

		assertNull(collector.occurrenceLine(cipherOrder(), T0 + 10 * MS));
		assertNull(collector.occurrenceLine(cipherOrder(), T0 + 20 * MS));
		assertNull(collector.occurrenceLine(cipherOrder(), T0 + 90 * MS));
	}

	@Test
	public void occurrenceLineCountsSuppressedOccurrences() {
		// The three suppressed reports still count, so the line written once the window has
		// expired carries 5, not 2: the gap between two n values is how a reader recovers the
		// dropped occurrences.
		collector.occurrenceLine(cipherOrder(), T0);
		collector.occurrenceLine(cipherOrder(), T0 + 10 * MS);
		collector.occurrenceLine(cipherOrder(), T0 + 20 * MS);
		collector.occurrenceLine(cipherOrder(), T0 + 90 * MS);

		String line = collector.occurrenceLine(cipherOrder(), T0 + 120 * MS);

		assertNotNull(line);
		assertTrue(line, line.endsWith(",CIPHER-ORDER-00,doFinal,5"));
	}

	@Test
	public void occurrenceLineWritesAgainAfterTheWindow() {
		// The window closes at exactly 100 ms, and it is measured from the last written line, not
		// from the first occurrence: the line at +100 ms opens a new window that +199 ms is inside.
		collector.occurrenceLine(cipherOrder(), T0);
		assertNotNull(collector.occurrenceLine(cipherOrder(), T0 + 100 * MS));
		assertNull(collector.occurrenceLine(cipherOrder(), T0 + 199 * MS));
		assertNotNull(collector.occurrenceLine(cipherOrder(), T0 + 200 * MS));
	}

	@Test
	public void occurrenceLineKeepsOneCounterPerIdentity() {
		ErrorDescription otherEvent = new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherSpec",
				"com.example.Crypto.encrypt(Crypto.java:42)",
				"v=1 code=CIPHER-ORDER-00 ev=update obj='' val='' exp='' msg='x'");

		collector.occurrenceLine(cipherOrder(), T0);
		String line = collector.occurrenceLine(otherEvent, T0 + 1 * MS);

		assertNotNull(line);
		assertTrue(line, line.endsWith(",CIPHER-ORDER-00,update,1"));
	}

	@Test
	public void occurrenceLineSharesTheSixKeyFieldsWithTheRvsecLine() {
		ErrorDescription err = cipherOrder();

		String[] rvsec = collector.buildLine(err).split(",", 7);
		String[] occ = collector.occurrenceLine(err, T0).split(",");

		assertEquals(9, occ.length);
		assertEquals(Arrays.asList(rvsec).subList(0, 6), Arrays.asList(occ).subList(0, 6));
	}

	@Test
	public void occurrenceLineDoesNotCarryTheEnvelope() {
		String line = collector.occurrenceLine(cipherOrder(), T0);

		assertFalse(line, line.contains("v=1"));
		assertFalse(line, line.contains("msg="));
	}

	@Test
	public void occurrenceLineCarriesTheSentinelWithoutEnvelope() {
		ErrorDescription threeArgument = new ErrorDescription(
				ErrorType.InvalidSequenceOfMethodCalls, "CipherSpec", "com.example.Crypto.encrypt(Crypto.java:42)");

		String line = collector.occurrenceLine(threeArgument, T0);

		assertEquals("CipherSpec,com.example.Crypto,Crypto,encrypt,Crypto.java:42,InvalidSequenceOfMethodCalls,"
				+ "UNSPECIFIED,UNSPECIFIED,1", line);
	}

	@Test
	public void concurrentReportsCountEveryOccurrenceAndWriteOneFirstLine() throws Exception {
		final int threads = 8;
		final int callsPerThread = 10_000;
		final ErrorDescription err = cipherOrder();
		final CyclicBarrier start = new CyclicBarrier(threads);
		final AtomicInteger written = new AtomicInteger();
		final AtomicReference<String> writtenLine = new AtomicReference<>();
		final AtomicReference<Throwable> failure = new AtomicReference<>();

		Thread[] workers = new Thread[threads];
		for (int t = 0; t < threads; t++) {
			workers[t] = new Thread(() -> {
				try {
					start.await();
					for (int i = 0; i < callsPerThread; i++) {
						String line = collector.occurrenceLine(err, T0);
						if (line != null) {
							written.incrementAndGet();
							writtenLine.set(line);
						}
					}
				} catch (Throwable e) {
					failure.compareAndSet(null, e);
				}
			});
			workers[t].start();
		}
		for (Thread worker : workers) {
			worker.join();
		}

		assertNull(failure.get());
		// Every call shares one nowNanos, so the window the first report opened never expires:
		// the only line is the first one.
		assertEquals(1, written.get());
		assertTrue(writtenLine.get(), writtenLine.get().endsWith(",doFinal,1"));
		// One report past the window reads the count back: 80 000 earlier reports plus this one.
		String next = collector.occurrenceLine(err, T0 + 200 * MS);
		assertNotNull(next);
		assertTrue(next, next.endsWith(",doFinal," + (threads * callsPerThread + 1)));
	}

	@Test
	public void resetClearsBothStates() {
		ErrorDescription err = cipherOrder();
		for (int i = 0; i < 12; i++) {
			collector.occurrenceLine(err, T0 + i * MS);
		}
		assertTrue(collector.occurrenceLine(err, T0 + 200 * MS).endsWith(",13"));

		collector.reset();

		assertTrue(collector.getErrors().isEmpty());
		String line = collector.occurrenceLine(err, T0 + 201 * MS);
		assertNotNull(line);
		assertTrue(line, line.endsWith(",doFinal,1"));
	}
}
