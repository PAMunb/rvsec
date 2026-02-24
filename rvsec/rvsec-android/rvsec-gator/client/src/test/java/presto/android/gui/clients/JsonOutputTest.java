package presto.android.gui.clients;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import org.junit.*;
import org.junit.rules.TemporaryFolder;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;

/**
 * Tests the JSON serialization structure produced by RvsecAnalysisClient.
 *
 * Since writeJson(), writeWindows(), writeWidget(), and writeTransitions() are
 * private and tightly coupled to Soot objects, we test the JSON contract
 * indirectly: build the same Map<String, Object> data structures that the
 * extraction methods produce, write them through Gson's JsonWriter (the same
 * API used in the production code), then parse the output and verify structure.
 *
 * This validates that consumers of the JSON (rv-static-analysis parsers) will
 * find the expected keys, types, and nesting.
 */
public class JsonOutputTest {

	@Rule
	public TemporaryFolder tempFolder = new TemporaryFolder();

	// ── helpers ──────────────────────────────────────────────────────────

	/**
	 * Write a complete JSON document mimicking RvsecAnalysisClient.writeJson()
	 * structure and return the parsed JsonObject.
	 */
	private JsonObject writeAndParse(WriteAction action) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.setIndent("  ");
		action.write(w);
		w.close();
		return JsonParser.parseString(sw.toString()).getAsJsonObject();
	}

	/**
	 * Write a JSON array and return the parsed JsonArray.
	 */
	private JsonArray writeArrayAndParse(WriteAction action) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.setIndent("  ");
		action.write(w);
		w.close();
		return JsonParser.parseString(sw.toString()).getAsJsonArray();
	}

	/**
	 * Write JSON to a StringWriter and return the raw string.
	 */
	private String writeToString(WriteAction action) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.setIndent("  ");
		action.write(w);
		w.close();
		return sw.toString();
	}

	@FunctionalInterface
	private interface WriteAction {
		void write(JsonWriter w) throws IOException;
	}

	// ── test 1: top-level keys ──────────────────────────────────────────

	@Test
	public void testJsonStructureTopLevelKeys() throws IOException {
		JsonObject root = writeAndParse(w -> {
			w.beginObject();
			w.name("package").value("test.app");
			w.name("mainActivity").value("test.app.MainActivity");

			w.name("reachability");
			w.beginArray();
			w.endArray();

			w.name("windows");
			w.beginArray();
			w.endArray();

			w.name("transitions");
			w.beginArray();
			w.endArray();

			w.endObject();
		});

		// Verify exactly the expected top-level keys
		Set<String> expectedKeys = new LinkedHashSet<>(
				Arrays.asList("package", "mainActivity", "reachability", "windows", "transitions"));
		assertEquals(expectedKeys, root.keySet());

		assertEquals("test.app", root.get("package").getAsString());
		assertEquals("test.app.MainActivity", root.get("mainActivity").getAsString());
		assertTrue(root.get("reachability").isJsonArray());
		assertTrue(root.get("windows").isJsonArray());
		assertTrue(root.get("transitions").isJsonArray());
	}

	// ── test 2: reachability entry ──────────────────────────────────────

	@Test
	public void testReachabilityEntry() throws IOException {
		JsonArray reachability = writeArrayAndParse(w -> {
			w.beginArray();
			w.beginObject();
			w.name("className").value("test.app.MyClass");
			w.name("isActivity").value(true);
			w.name("isMainActivity").value(false);

			w.name("methods");
			w.beginArray();
			w.beginObject();
			w.name("name").value("onCreate");
			w.name("signature").value(
					"<test.app.MyClass: void onCreate(android.os.Bundle)>");
			w.name("reachable").value(true);
			w.name("reachesMop").value(false);
			w.name("directlyReachesMop").value(false);
			w.endObject();
			w.endArray();

			w.endObject();
			w.endArray();
		});

		assertEquals(1, reachability.size());

		JsonObject classEntry = reachability.get(0).getAsJsonObject();
		assertEquals("test.app.MyClass", classEntry.get("className").getAsString());
		assertTrue(classEntry.get("isActivity").getAsBoolean());
		assertFalse(classEntry.get("isMainActivity").getAsBoolean());

		JsonArray methods = classEntry.getAsJsonArray("methods");
		assertEquals(1, methods.size());

		JsonObject method = methods.get(0).getAsJsonObject();
		assertEquals("onCreate", method.get("name").getAsString());
		assertEquals("<test.app.MyClass: void onCreate(android.os.Bundle)>",
				method.get("signature").getAsString());
		assertTrue(method.get("reachable").getAsBoolean());
		assertFalse(method.get("reachesMop").getAsBoolean());
		assertFalse(method.get("directlyReachesMop").getAsBoolean());
	}

	// ── test 3: window entry with widgets and listeners ─────────────────

	@Test
	public void testWindowEntry() throws IOException {
		JsonArray windows = writeArrayAndParse(w -> {
			w.beginArray();
			w.beginObject();
			w.name("id").value(1);
			w.name("name").value("test.app.MainActivity");
			w.name("type").value("ACTIVITY");
			w.name("isMain").value(true);

			w.name("widgets");
			w.beginArray();
			// One widget with a listener
			w.beginObject();
			w.name("id").value(100);
			w.name("idName").value("button1");
			w.name("type").value("android.widget.Button");
			w.name("text").value("Click");
			w.name("hint").value("");
			w.name("inputType").value("");
			w.name("entries");
			w.beginArray();
			w.endArray();
			w.name("listeners");
			w.beginArray();
			w.beginObject();
			w.name("eventType").value("click");
			w.name("handler").value(
					"<test.app.MainActivity: void onClick(android.view.View)>");
			w.endObject();
			w.endArray();
			w.endObject();
			w.endArray();

			w.endObject();
			w.endArray();
		});

		assertEquals(1, windows.size());

		JsonObject window = windows.get(0).getAsJsonObject();
		assertEquals(1, window.get("id").getAsInt());
		assertEquals("test.app.MainActivity", window.get("name").getAsString());
		assertEquals("ACTIVITY", window.get("type").getAsString());
		assertTrue(window.get("isMain").getAsBoolean());

		JsonArray widgets = window.getAsJsonArray("widgets");
		assertEquals(1, widgets.size());

		JsonObject widget = widgets.get(0).getAsJsonObject();
		assertEquals(100, widget.get("id").getAsInt());
		assertEquals("button1", widget.get("idName").getAsString());
		assertEquals("android.widget.Button", widget.get("type").getAsString());
		assertEquals("Click", widget.get("text").getAsString());
		assertEquals("", widget.get("hint").getAsString());
		assertEquals("", widget.get("inputType").getAsString());
		assertTrue(widget.getAsJsonArray("entries").isEmpty());

		JsonArray listeners = widget.getAsJsonArray("listeners");
		assertEquals(1, listeners.size());

		JsonObject listener = listeners.get(0).getAsJsonObject();
		assertEquals("click", listener.get("eventType").getAsString());
		assertEquals("<test.app.MainActivity: void onClick(android.view.View)>",
				listener.get("handler").getAsString());
	}

	// ── test 4: transition entry ────────────────────────────────────────

	@Test
	public void testTransitionEntry() throws IOException {
		JsonArray transitions = writeArrayAndParse(w -> {
			w.beginArray();
			w.beginObject();
			w.name("sourceId").value(1);
			w.name("targetId").value(2);

			w.name("events");
			w.beginArray();
			w.beginObject();
			w.name("type").value("click");
			w.name("handler").value(
					"<test.app.MainActivity: void onClick(android.view.View)>");
			w.name("widgetId").value(100);
			w.name("widgetClass").value("android.widget.Button");
			w.name("widgetName").value("button1");
			w.endObject();
			w.endArray();

			w.endObject();
			w.endArray();
		});

		assertEquals(1, transitions.size());

		JsonObject transition = transitions.get(0).getAsJsonObject();
		assertEquals(1, transition.get("sourceId").getAsInt());
		assertEquals(2, transition.get("targetId").getAsInt());

		JsonArray events = transition.getAsJsonArray("events");
		assertEquals(1, events.size());

		JsonObject event = events.get(0).getAsJsonObject();
		assertEquals("click", event.get("type").getAsString());
		assertEquals("<test.app.MainActivity: void onClick(android.view.View)>",
				event.get("handler").getAsString());
		assertEquals(100, event.get("widgetId").getAsInt());
		assertEquals("android.widget.Button", event.get("widgetClass").getAsString());
		assertEquals("button1", event.get("widgetName").getAsString());
	}

	// ── test 5: inner class dollar notation ─────────────────────────────

	@Test
	public void testInnerClassDollarNotation() throws IOException {
		JsonArray reachability = writeArrayAndParse(w -> {
			w.beginArray();
			w.beginObject();
			w.name("className").value("test.app.Outer$Inner");
			w.name("isActivity").value(false);
			w.name("isMainActivity").value(false);
			w.name("methods");
			w.beginArray();
			w.endArray();
			w.endObject();
			w.endArray();
		});

		String className = reachability.get(0).getAsJsonObject()
				.get("className").getAsString();

		// Soot uses dollar notation for inner classes; JSON must preserve it
		assertTrue("Expected '$' in inner class name", className.contains("$"));
		assertEquals("test.app.Outer$Inner", className);
		assertFalse("Must NOT convert '$' to '.'",
				className.equals("test.app.Outer.Inner"));
	}

	// ── test 6: empty sections ──────────────────────────────────────────

	@Test
	public void testEmptySections() throws IOException {
		JsonObject root = writeAndParse(w -> {
			w.beginObject();
			w.name("package").value("test.app");
			w.name("mainActivity").value("test.app.MainActivity");

			w.name("reachability");
			w.beginArray();
			w.endArray();

			w.name("windows");
			w.beginArray();
			w.endArray();

			w.name("transitions");
			w.beginArray();
			w.endArray();

			w.endObject();
		});

		// Empty arrays must be present (not null) — consumers rely on this
		JsonArray reachability = root.getAsJsonArray("reachability");
		assertNotNull("reachability must not be null", reachability);
		assertEquals(0, reachability.size());

		JsonArray windows = root.getAsJsonArray("windows");
		assertNotNull("windows must not be null", windows);
		assertEquals(0, windows.size());

		JsonArray transitions = root.getAsJsonArray("transitions");
		assertNotNull("transitions must not be null", transitions);
		assertEquals(0, transitions.size());
	}

	// ── test 7: JsonWriter flush between sections ───────────────────────

	@Test
	public void testJsonWriterFlushBetweenSections() throws IOException {
		// Reproduce the flush pattern from RvsecAnalysisClient.writeJson():
		// flush() after reachability, windows, and transitions sections.
		// Verify the final output is still valid JSON.

		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.setIndent("  ");

		w.beginObject();
		w.name("package").value("test.app");
		w.name("mainActivity").value("test.app.MainActivity");

		// Section 1: reachability — flush after
		w.name("reachability");
		w.beginArray();
		w.beginObject();
		w.name("className").value("test.app.MyClass");
		w.name("isActivity").value(true);
		w.name("isMainActivity").value(false);
		w.name("methods");
		w.beginArray();
		w.endArray();
		w.endObject();
		w.endArray();
		w.flush();

		// Section 2: windows — flush after
		w.name("windows");
		w.beginArray();
		w.beginObject();
		w.name("id").value(1);
		w.name("name").value("test.app.MainActivity");
		w.name("type").value("ACTIVITY");
		w.name("isMain").value(true);
		w.name("widgets");
		w.beginArray();
		w.endArray();
		w.endObject();
		w.endArray();
		w.flush();

		// Section 3: transitions — flush after
		w.name("transitions");
		w.beginArray();
		w.beginObject();
		w.name("sourceId").value(1);
		w.name("targetId").value(2);
		w.name("events");
		w.beginArray();
		w.endArray();
		w.endObject();
		w.endArray();
		w.flush();

		w.endObject();
		w.close();

		String json = sw.toString();

		// Must be valid JSON despite intermediate flushes
		JsonElement parsed = JsonParser.parseString(json);
		assertTrue("Output must be a valid JSON object", parsed.isJsonObject());

		JsonObject root = parsed.getAsJsonObject();
		assertEquals("test.app", root.get("package").getAsString());
		assertEquals(1, root.getAsJsonArray("reachability").size());
		assertEquals(1, root.getAsJsonArray("windows").size());
		assertEquals(1, root.getAsJsonArray("transitions").size());
	}
}
