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

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

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

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

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

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

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

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

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
		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

		// Widget map should be unchanged
		assertEquals("", widgetByIdName.get("edit1").get("inputType"));
	}

	// ── codex fix #5: @+id/ prefix (declaration form) ───────────────────
	//
	// Previously enrichFromElement only matched "@id/foo" (reference
	// form). Real-world layouts overwhelmingly use "@+id/foo" — the
	// declaration form for newly-introduced widget ids — so most
	// XML-declared widgets were silently skipped by the enrichment pass.
	// The fix accepts either prefix; these tests pin the new contract.

	@Test
	public void testEnrichAtPlusIdInputType() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@+id/password\" android:inputType=\"textPassword\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("password", makeWidget(1, "password", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

		assertEquals("textPassword", widgetByIdName.get("password").get("inputType"));
	}

	@Test
	public void testEnrichAtPlusIdEntries() throws IOException {
		// Spinner declared inline with @+id/ + entries pointing at @array/.
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <Spinner android:id=\"@+id/country_picker\" android:entries=\"@array/countries\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("country_picker",
				makeWidget(2, "country_picker", "Spinner", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();
		arrays.put("countries", Arrays.asList("BR", "US", "PT"));

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

		assertEquals(Arrays.asList("BR", "US", "PT"),
				widgetByIdName.get("country_picker").get("entries"));
	}

	@Test
	public void testEnrichMixedAtIdAndAtPlusId() throws IOException {
		// Layout mixing both prefix forms — both MUST be matched.
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@+id/email\" android:inputType=\"textEmailAddress\"/>\n" +
				"  <EditText android:id=\"@id/legacy\" android:inputType=\"phone\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("email", makeWidget(1, "email", "EditText", "", "", "", new ArrayList<>()));
		widgetByIdName.put("legacy", makeWidget(2, "legacy", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

		assertEquals("textEmailAddress", widgetByIdName.get("email").get("inputType"));
		assertEquals("phone", widgetByIdName.get("legacy").get("inputType"));
	}

	// ── gh60-fix: hint/text inline-literal coverage ────────────────────
	//
	// Pre-fix: enrichFromElement covered inputType/entries/prompt/
	// spinnerMode/contentDescription/tooltipText but NOT hint/text.
	// Path-A (collectWidgets via PropertyManager) only sees CG-tracked
	// / @string-resolved values, so inline literals like
	// `android:hint="Enter password"` were silently dropped — 0/51
	// widgets populated on cryptoapp despite 4 hint + 17 text source
	// declarations. Fix wires both fields through `putStringAttr`,
	// which short-circuits on null/empty raw so the path-A seed
	// survives when the layout XML carries no attribute. See
	// `openspec/changes/gh60-targets-core/design.md` D11.

	@Test
	public void testEnrichHintLiteral() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@+id/password\" android:hint=\"Enter password\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("password",
				makeWidget(1, "password", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays,
				layoutFile.getParentFile().getParent());

		assertEquals("Enter password", widgetByIdName.get("password").get("hint"));
	}

	@Test
	public void testEnrichTextLiteral() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <Button android:id=\"@+id/submit\" android:text=\"Submit\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("submit",
				makeWidget(1, "submit", "Button", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays,
				layoutFile.getParentFile().getParent());

		assertEquals("Submit", widgetByIdName.get("submit").get("text"));
	}

	@Test
	public void testEnrichHintStringRef() throws IOException {
		File layoutDir = tempDir.newFolder("layout");
		File layoutFile = new File(layoutDir, "activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@+id/email\" android:hint=\"@string/hint_email\"/>\n" +
				"</LinearLayout>");

		File valuesDir = tempDir.newFolder("values");
		writeFile(new File(valuesDir, "strings.xml"),
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<resources>\n" +
				"  <string name=\"hint_email\">your.email@example.com</string>\n" +
				"</resources>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		widgetByIdName.put("email",
				makeWidget(1, "email", "EditText", "", "", "", new ArrayList<>()));

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays,
				tempDir.getRoot().getAbsolutePath());

		assertEquals("your.email@example.com", widgetByIdName.get("email").get("hint"));
	}

	@Test
	public void testEnrichHintAbsentPreservesSeed() throws IOException {
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <EditText android:id=\"@+id/foo\" android:inputType=\"text\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		Map<String, Object> seed = makeWidget(1, "foo", "EditText",
				"seeded-text", "seeded-hint", "", new ArrayList<>());
		widgetByIdName.put("foo", seed);

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays,
				layoutFile.getParentFile().getParent());

		assertEquals("text", seed.get("inputType"));
		assertEquals("seeded-hint", seed.get("hint"));
		assertEquals("seeded-text", seed.get("text"));
	}

	@Test
	public void testEnrichEmptyIdAttributeIgnored() throws IOException {
		// android:id present but empty — must NOT match any widget.
		File layoutFile = tempDir.newFile("activity_main.xml");
		writeFile(layoutFile,
				"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
				"<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
				"  <TextView android:id=\"\" android:contentDescription=\"x\"/>\n" +
				"</LinearLayout>");

		Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
		// Use empty-string idName widget to make sure an empty id attr
		// does NOT match it via a degenerate path.
		Map<String, Object> w = makeWidget(1, "", "TextView", "", "", "", new ArrayList<>());
		widgetByIdName.put("", w);

		Map<String, List<String>> arrays = new HashMap<>();

		client.enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, layoutFile.getParentFile().getParent());

		// contentDescription should not be set because no prefix matched.
		assertFalse("contentDescription must NOT be enriched when id has no prefix",
				w.containsKey("contentDescription") && w.get("contentDescription") != null);
	}
}
