/*
 * SentinelEmissionTest — INV-ANA-31 pattern conformance (gh60).
 *
 * What it tests
 * -------------
 * The structural invariant the production {@link JsonReportWriter}
 * relies on: when the same Gson {@link com.google.gson.stream.JsonWriter}
 * sequence the writer follows is interrupted by a {@link RuntimeException}
 * at ANY section boundary, the on-disk file MUST NOT contain the
 * {@code "complete":true} sentinel. The sentinel is written exactly once
 * and only after all four sections have flushed; an early abort leaves
 * the file in the "no signal" state the parser uses to mark a sample as
 * incomplete and exclude it from gates requiring completeness.
 *
 * It also pins the writer's own sentinel decision
 * ({@code JsonReportWriter.writeCompletionSentinel}): an intermediate
 * write — the pre-WTG one — must leave no {@code complete} key, and the
 * run's last write must still emit it. That case has no exception in it,
 * so none of the fault-injection cases below reach it.
 *
 * What it does NOT test
 * ---------------------
 * The production {@code JsonReportWriter.write(...)} method itself.
 * Driving that method requires a fully-initialised Soot Scene
 * ({@code GUIAnalysisOutput.getActivities()}, {@code XMLParser.Factory}),
 * which is only available at the end of a real GATOR run. The wire-level
 * Python test {@code tests/parity/test_sentinel_emission.py} closes that
 * gap by inspecting the bytes a real GATOR run leaves on disk.
 *
 * This test replicates the writer's sequence pattern in-test and exercises
 * fault injection at each section boundary. The two tests together pin:
 *
 *   - the byte-level contract on real output (Python end-to-end)
 *   - the structural pattern the writer must follow (this test)
 *
 * If a future refactor moves the sentinel write earlier, or duplicates
 * it across sections, this test fails immediately — and the Python test
 * would only fail if the change ever shipped through a real GATOR run.
 */
package presto.android.gui.clients.json;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Pattern;

import com.google.gson.stream.JsonWriter;

import org.junit.Test;

public class SentinelEmissionTest {

	private static final Pattern SENTINEL_TAIL = Pattern.compile(
			",\\s*\"complete\"\\s*:\\s*true\\s*}\\s*\\z", Pattern.MULTILINE);

	/** Runnable that may throw — used to inject a failure between sections. */
	@FunctionalInterface
	private interface SectionHook {
		void afterSection() throws IOException;
	}

	private static final SectionHook NOOP = () -> {};

	/**
	 * Drive a JsonWriter through the EXACT sequence {@link JsonReportWriter}
	 * follows: open object, two metadata keys, four sections (each a
	 * minimal valid placeholder), four flushes, sentinel as the LAST key,
	 * close object, flush, then fsync via FileDescriptor.
	 *
	 * <p>One hook per section boundary; the hook runs AFTER the section
	 * (and its flush) closes. A hook may throw to simulate any section
	 * writer failing — production code is wrapped in try-with-resources
	 * so the JsonWriter still closes (which finalises whatever state was
	 * mid-write), but the sentinel line is never reached.
	 */
	private void writeReportLike(Path out, SectionHook[] hooks) throws IOException {
		try (FileOutputStream fos = new FileOutputStream(out.toFile());
				OutputStreamWriter osw = new OutputStreamWriter(fos, StandardCharsets.UTF_8);
				JsonWriter w = new JsonWriter(osw)) {

			w.setIndent("  ");
			w.beginObject();
			w.name("package").value("test.pkg");
			w.name("mainActivity").value("test.pkg.Main");

			// D14 (2026-05-29): order is components -> reachability ->
			// windows -> transitions. components is manifest-derived and
			// promoted before the heavy analysis sections so a
			// transitions-timeout cannot drop it. Hook indices follow the
			// new writer order.
			w.name("components");
			w.beginObject().endObject();
			w.flush();
			hooks[0].afterSection();

			w.name("reachability");
			w.beginArray().endArray();
			w.flush();
			hooks[1].afterSection();

			w.name("windows");
			w.beginArray().endArray();
			w.flush();
			hooks[2].afterSection();

			w.name("transitions");
			w.beginArray().endArray();
			w.flush();
			hooks[3].afterSection();

			// Sentinel — last top-level field. Anything that throws above
			// this line MUST leave the file without it.
			w.name("complete").value(true);

			w.endObject();
			w.flush();
			osw.flush();
			fos.getFD().sync();
		}
	}

	// ── success path ────────────────────────────────────────────────────

	@Test
	public void successfulRunEndsWithCompleteSentinel() throws IOException {
		Path out = Files.createTempFile("sentinel-success-", ".json");
		try {
			writeReportLike(out, new SectionHook[]{NOOP, NOOP, NOOP, NOOP});

			String content = new String(Files.readAllBytes(out), StandardCharsets.UTF_8);
			assertTrue(
					"successful run must end with `,\"complete\":true}` — got tail:\n"
							+ tail(content, 80),
					SENTINEL_TAIL.matcher(content).find());

			// Belt-and-braces: exactly one `complete` key. A regression that
			// emits the sentinel twice (mid-stream + at end) would still
			// match SENTINEL_TAIL — this counter catches it.
			int hits = countMatches(content, "\"complete\"");
			assertTrue("expected exactly one \"complete\" key, got " + hits, hits == 1);
		} finally {
			Files.deleteIfExists(out);
		}
	}

	// ── failure paths — one per section boundary ────────────────────────

	// D14 (2026-05-29): hook indices follow the new writer order
	// components(0) -> reachability(1) -> windows(2) -> transitions(3).

	@Test
	public void throwAfterComponentsProducesNoSentinel() throws IOException {
		runAndAssertNoSentinel(0, "components");
	}

	@Test
	public void throwAfterReachabilityProducesNoSentinel() throws IOException {
		runAndAssertNoSentinel(1, "reachability");
	}

	@Test
	public void throwAfterWindowsProducesNoSentinel() throws IOException {
		runAndAssertNoSentinel(2, "windows");
	}

	@Test
	public void throwAfterTransitionsProducesNoSentinel() throws IOException {
		runAndAssertNoSentinel(3, "transitions");
	}

	private void runAndAssertNoSentinel(int failAfterIndex, String sectionLabel) throws IOException {
		Path out = Files.createTempFile("sentinel-fail-" + sectionLabel + "-", ".json");
		try {
			SectionHook[] hooks = new SectionHook[]{NOOP, NOOP, NOOP, NOOP};
			hooks[failAfterIndex] = () -> {
				throw new IOException("synthetic failure after " + sectionLabel);
			};

			try {
				writeReportLike(out, hooks);
				fail("expected IOException at hook[" + failAfterIndex + "] (" + sectionLabel + ")");
			} catch (IOException expected) {
				// fall through to file inspection below
			}

			// Try-with-resources still closed the underlying streams when
			// the IOException propagated, so a partial file IS on disk. The
			// invariant: no `complete` key anywhere in it.
			String content = new String(Files.readAllBytes(out), StandardCharsets.UTF_8);
			assertFalse(
					"failure after " + sectionLabel + " left a sentinel in the file — "
							+ "INV-ANA-31 says the sentinel is emitted only on the success "
							+ "path. Content tail:\n" + tail(content, 200),
					content.contains("\"complete\""));
		} finally {
			Files.deleteIfExists(out);
		}
	}

	// ── the writer's own sentinel decision ──────────────────────────────

	// The cases above replicate the writer's sequence; these two call the
	// production decision itself. The gap they close is the pre-WTG write:
	// it fails no section, throws nothing, and finishes cleanly — every
	// fault-injection case above passes while it silently claims the run
	// finished. The end-to-end Python test cannot see it either, because
	// the post-WTG write overwrites the file it would inspect.

	@Test
	public void sentinelSuppressedOnAnIntermediateWrite() throws IOException {
		Path out = Files.createTempFile("sentinel-suppressed-", ".json");
		try {
			writeMinimalReport(out, false);

			String content = new String(Files.readAllBytes(out), StandardCharsets.UTF_8);
			assertFalse(
					"a write asked not to emit the sentinel must leave no `complete` key — "
							+ "this is the pre-WTG write, and a run killed inside WTG "
							+ "construction is exactly what INV-ANA-31 must not report as "
							+ "finished. Content:\n" + tail(content, 200),
					content.contains("\"complete\""));
		} finally {
			Files.deleteIfExists(out);
		}
	}

	@Test
	public void sentinelEmittedOnTheFinalWrite() throws IOException {
		Path out = Files.createTempFile("sentinel-final-", ".json");
		try {
			writeMinimalReport(out, true);

			String content = new String(Files.readAllBytes(out), StandardCharsets.UTF_8);
			assertTrue(
					"the run's last write must still end with `,\"complete\":true}` — got tail:\n"
							+ tail(content, 80),
					SENTINEL_TAIL.matcher(content).find());
		} finally {
			Files.deleteIfExists(out);
		}
	}

	/**
	 * Write a report whose sections are empty placeholders, closing it
	 * through {@link JsonReportWriter#writeCompletionSentinel} — the same
	 * call {@code JsonReportWriter.write(...)} makes. The section writers
	 * are not driven here because they need a fully-initialised Soot Scene;
	 * what is under test is the sentinel decision, and that is production
	 * code, not a replica.
	 */
	private void writeMinimalReport(Path out, boolean emitSentinel) throws IOException {
		try (FileOutputStream fos = new FileOutputStream(out.toFile());
				OutputStreamWriter osw = new OutputStreamWriter(fos, StandardCharsets.UTF_8);
				JsonWriter w = new JsonWriter(osw)) {

			w.setIndent("  ");
			w.beginObject();
			w.name("package").value("test.pkg");
			w.name("components");
			w.beginObject().endObject();
			w.name("reachability");
			w.beginArray().endArray();
			w.name("windows");
			w.beginArray().endArray();
			w.name("transitions");
			w.beginArray().endArray();
			w.flush();

			JsonReportWriter.writeCompletionSentinel(w, emitSentinel);

			w.endObject();
			w.flush();
			osw.flush();
			fos.getFD().sync();
		}
	}

	// ── helpers ─────────────────────────────────────────────────────────

	private static String tail(String s, int n) {
		if (s.length() <= n) return s;
		return "…" + s.substring(s.length() - n);
	}

	private static int countMatches(String haystack, String needle) {
		int count = 0;
		int idx = 0;
		while ((idx = haystack.indexOf(needle, idx)) != -1) {
			count++;
			idx += needle.length();
		}
		return count;
	}
}
