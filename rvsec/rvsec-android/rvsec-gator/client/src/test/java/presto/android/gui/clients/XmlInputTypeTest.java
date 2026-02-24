package presto.android.gui.clients;

import org.junit.*;
import org.junit.rules.TemporaryFolder;
import static org.junit.Assert.*;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

/**
 * Unit tests for the XML parsing helpers in RvsecAnalysisClient:
 * parseArraysXml(), resolveStringReference(), and enrichWidgetsFromLayout().
 *
 * Uses TemporaryFolder to create fixture XML files, exercising the
 * package-private methods without Soot or GATOR dependencies.
 */
public class XmlInputTypeTest {

	@Rule
	public TemporaryFolder tempDir = new TemporaryFolder();

	private RvsecAnalysisClient client;

	@Before
	public void setUp() {
		client = new RvsecAnalysisClient();
	}

	// ── helpers ──────────────────────────────────────────────────────────

	private void writeFile(File file, String content) throws IOException {
		try (FileWriter fw = new FileWriter(file)) {
			fw.write(content);
		}
	}

	/**
	 * Build a widget map entry with the standard keys used by collectWidgets().
	 */
	private Map<String, Object> makeWidget(int id, String idName, String type,
										   String text, String hint, String inputType,
										   List<String> entries) {
		Map<String, Object> widget = new LinkedHashMap<>();
		widget.put("id", id);
		widget.put("idName", idName);
		widget.put("type", type);
		widget.put("text", text);
		widget.put("hint", hint);
		widget.put("inputType", inputType);
		widget.put("entries", entries);
		return widget;
	}

	// ── parseArraysXml tests ────────────────────────────────────────────

	@Test
	public void testParseArraysXmlPlainItems() throws IOException {
		File valuesDir = tempDir.newFolder("values");
		File arraysXml = new File(valuesDir, "arrays.xml");
		writeFile(arraysXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string-array name=\"algos\">\n" +
				"    <item>AES</item>\n" +
				"    <item>DES</item>\n" +
				"  </string-array>\n" +
				"</resources>");

		Map<String, List<String>> result = client.parseArraysXml(tempDir.getRoot().getAbsolutePath());

		assertEquals(1, result.size());
		assertTrue(result.containsKey("algos"));
		assertEquals(Arrays.asList("AES", "DES"), result.get("algos"));
	}

	@Test
	public void testParseArraysXmlWithStringRefs() throws IOException {
		File valuesDir = tempDir.newFolder("values");

		File arraysXml = new File(valuesDir, "arrays.xml");
		writeFile(arraysXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string-array name=\"items\">\n" +
				"    <item>Plain</item>\n" +
				"    <item>@string/ref1</item>\n" +
				"  </string-array>\n" +
				"</resources>");

		File stringsXml = new File(valuesDir, "strings.xml");
		writeFile(stringsXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string name=\"ref1\">Resolved Value</string>\n" +
				"</resources>");

		Map<String, List<String>> result = client.parseArraysXml(tempDir.getRoot().getAbsolutePath());

		assertEquals(1, result.size());
		assertEquals(Arrays.asList("Plain", "Resolved Value"), result.get("items"));
	}

	@Test
	public void testParseArraysXmlMissingFile() {
		// tempDir exists but has no values/arrays.xml
		Map<String, List<String>> result = client.parseArraysXml(tempDir.getRoot().getAbsolutePath());

		assertTrue(result.isEmpty());
	}

	@Test
	public void testParseArraysXmlEmpty() throws IOException {
		File valuesDir = tempDir.newFolder("values");
		File arraysXml = new File(valuesDir, "arrays.xml");
		writeFile(arraysXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources></resources>");

		Map<String, List<String>> result = client.parseArraysXml(tempDir.getRoot().getAbsolutePath());

		assertTrue(result.isEmpty());
	}

	// ── resolveStringReference tests ────────────────────────────────────

	@Test
	public void testResolveStringFound() throws IOException {
		File valuesDir = tempDir.newFolder("values");
		File stringsXml = new File(valuesDir, "strings.xml");
		writeFile(stringsXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string name=\"hello\">World</string>\n" +
				"</resources>");

		String result = client.resolveStringReference(tempDir.getRoot().getAbsolutePath(), "hello");

		assertEquals("World", result);
	}

	@Test
	public void testResolveStringNotFound() throws IOException {
		File valuesDir = tempDir.newFolder("values");
		File stringsXml = new File(valuesDir, "strings.xml");
		writeFile(stringsXml,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string name=\"other\">Something</string>\n" +
				"</resources>");

		String result = client.resolveStringReference(tempDir.getRoot().getAbsolutePath(), "missing");

		assertNull(result);
	}

	@Test
	public void testResolveStringMissingFile() {
		// tempDir exists but has no values/strings.xml
		String result = client.resolveStringReference(tempDir.getRoot().getAbsolutePath(), "anything");

		assertNull(result);
	}

	// ── enrichWidgetsFromLayout tests ───────────────────────────────────

	@Test
	public void testEnrichInputType() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@id/edit1\" android:inputType=\"textPersonName\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("edit1", makeWidget(1, "edit1", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);

		assertEquals("textPersonName", widgetByIdName.get("edit1").get("inputType"));
	}

	@Test
	public void testEnrichInputTypePipeSeparated() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@id/edit1\" android:inputType=\"textPassword|textVisiblePassword\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("edit1", makeWidget(1, "edit1", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);

		assertEquals("textPassword", widgetByIdName.get("edit1").get("inputType"));
	}

	@Test
	public void testEnrichEntries() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <Spinner android:id=\"@id/spinner1\" android:entries=\"@array/algos\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("spinner1", makeWidget(2, "spinner1", "Spinner", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();
		arrays.put("algos", Arrays.asList("AES", "DES"));

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);

		assertEquals(Arrays.asList("AES", "DES"), widgetByIdName.get("spinner1").get("entries"));
	}

	@Test
	public void testEnrichNoMatch() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@id/otherWidget\" android:inputType=\"number\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("edit1", makeWidget(1, "edit1", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);

		// Widget map should be unchanged — inputType remains empty
		assertEquals("", widgetByIdName.get("edit1").get("inputType"));
	}

	@Test
	public void testEnrichMalformedXml() throws IOException {
		File layoutFile = tempDir.newFile("broken.xml");
		writeFile(layoutFile, "this is not valid xml <<<<>>>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("edit1", makeWidget(1, "edit1", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		// Should not throw — graceful degradation
		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);

		// Widget map should be unchanged
		assertEquals("", widgetByIdName.get("edit1").get("inputType"));
	}
}
