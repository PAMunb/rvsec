package presto.android.gui.clients.json;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import org.junit.Test;

/**
 * The members written before {@code distanceTargets} (INV-ANA-66, INV-ANA-86, INV-ANA-99).
 * {@link JsonReportWriter#write} cannot be driven from a unit test (its section writers need a
 * Soot Scene and GATOR's manifest parser), so the members go through
 * {@link JsonReportWriter#writeHeader}, the call {@code write} makes right after it opens the
 * document. Each fixture opens and closes the object around the call, on a {@link JsonWriter}
 * with no indent set, as {@code write} does in both output modes.
 */
public class JsonReportWriterHeaderTest {

	private static final String SCOPE = "\"package\":\"com.example\","
			+ "\"mainActivity\":\"com.example.Main\","
			+ "\"codePackage\":\"com.example.app\","
			+ "\"codePackageSource\":\"detector\","
			+ "\"class_defs_under_key\":42";
	private static final String MARKER = "\"distancePairs\":{\"weighedMax\":3,\"k\":3}";
	private static final List<String> SCOPE_KEYS = Arrays.asList(JsonSchema.Keys.PACKAGE,
			JsonSchema.Keys.MAIN_ACTIVITY, JsonSchema.Keys.CODE_PACKAGE,
			JsonSchema.Keys.CODE_PACKAGE_SOURCE, JsonSchema.Keys.CLASS_DEFS_UNDER_KEY);
	private static final Pattern WHITESPACE = Pattern.compile("\\s");

	/**
	 * The shape of {@code ReachabilityEnricher.topLevelMetadata()}, which also carries two
	 * members the header does not write.
	 */
	private static Map<String, Object> metadata() {
		Map<String, Object> m = new LinkedHashMap<>();
		m.put("manifestPackage", "com.example");
		m.put("codePackage", "com.example.app");
		m.put("mainActivity", "com.example.Main");
		m.put("codePackageSource", "detector");
		m.put("class_defs_under_key", Integer.valueOf(42));
		return m;
	}

	private static String header(boolean compact, Integer distMax) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		JsonReportWriter.writeHeader(w, "com.example", "com.example.Main", metadata(), compact,
				distMax);
		w.endObject();
		w.close();
		return sw.toString();
	}

	private static List<String> keys(String document) {
		return new ArrayList<>(JsonParser.parseString(document).getAsJsonObject().keySet());
	}

	private static List<String> scopeKeysAnd(String... more) {
		List<String> out = new ArrayList<>(SCOPE_KEYS);
		out.addAll(Arrays.asList(more));
		return out;
	}

	@Test
	public void fullModeWithoutDistMaxWritesTheScopeMembersOnly() throws IOException {
		String doc = header(false, null);

		assertEquals("{" + SCOPE + "}", doc);
		assertEquals(SCOPE_KEYS, keys(doc));
	}

	@Test
	public void fullModeWritesDistMaxRightAfterClassDefsUnderKey() throws IOException {
		String doc = header(false, 15);

		assertEquals("{" + SCOPE + ",\"distMax\":15}", doc);
		assertEquals(scopeKeysAnd(JsonSchema.Keys.DIST_MAX), keys(doc));
	}

	@Test
	public void compactModeWithoutDistMaxWritesTheMarkerAfterTheScopeMembers()
			throws IOException {
		String doc = header(true, null);

		assertEquals("{" + SCOPE + "," + MARKER + "}", doc);
		assertEquals(scopeKeysAnd(JsonSchema.Keys.DISTANCE_PAIRS), keys(doc));
	}

	@Test
	public void compactModeWritesDistMaxBetweenClassDefsUnderKeyAndTheMarker()
			throws IOException {
		String doc = header(true, 15);

		assertEquals("{" + SCOPE + ",\"distMax\":15," + MARKER + "}", doc);
		assertEquals(scopeKeysAnd(JsonSchema.Keys.DIST_MAX, JsonSchema.Keys.DISTANCE_PAIRS),
				keys(doc));
	}

	@Test
	public void noModeWritesWhitespace() throws IOException {
		for (boolean compact : new boolean[] { false, true }) {
			for (Integer distMax : new Integer[] { null, 15 }) {
				String doc = header(compact, distMax);

				assertFalse("compact=" + compact + " distMax=" + distMax + ": " + doc,
						WHITESPACE.matcher(doc).find());
			}
		}
	}

	@Test
	public void anAbsentPackageOrMainActivityIsWrittenAsAnEmptyString() throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		JsonReportWriter.writeHeader(w, null, null, metadata(), false, null);
		w.endObject();
		w.close();

		String doc = sw.toString();
		assertTrue(doc, doc.startsWith("{\"package\":\"\",\"mainActivity\":\"\","));
	}

	@Test
	public void theHorizonSurvivesAFailedDistancePass() throws IOException {
		// write passes distanceTargets as null when the distance pass failed; the header
		// members, distMax among them, do not depend on it.
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		JsonReportWriter.writeHeader(w, "com.example", "com.example.Main", metadata(), true, 15);
		JsonReportWriter.writeDistanceTargets(w, null);
		w.name(JsonSchema.Keys.COMPONENTS).beginObject().endObject();
		w.endObject();
		w.close();

		assertEquals(scopeKeysAnd(JsonSchema.Keys.DIST_MAX, JsonSchema.Keys.DISTANCE_PAIRS,
				JsonSchema.Keys.COMPONENTS), keys(sw.toString()));
	}
}
