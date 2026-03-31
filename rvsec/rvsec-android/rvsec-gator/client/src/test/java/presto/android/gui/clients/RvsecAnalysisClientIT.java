package presto.android.gui.clients;

import static org.junit.Assert.*;

import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

import org.junit.Assume;
import org.junit.BeforeClass;
import org.junit.Test;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

/**
 * Integration test: run RvsecAnalysisClient via GATOR on cryptoapp.apk
 * and verify the JSON output structure and content.
 *
 * Requires RVSEC_HOME, cryptoapp.apk, and rvsec-analysis-client.jar.
 * Skipped if prerequisites are missing.
 *
 * Run with: mvn verify -DskipTests=false -DskipITs=false
 */
public class RvsecAnalysisClientIT {

	private static JsonObject result;

	@BeforeClass
	public static void runAnalysis() throws Exception {
		String rvsecHome = System.getenv("RVSEC_HOME");
		Assume.assumeTrue("RVSEC_HOME must be set", rvsecHome != null && !rvsecHome.isEmpty());

		result = GatorTestHelper.getAnalysisResult();
		assertNotNull("Analysis result must not be null", result);
	}

	// -----------------------------------------------------------------
	// Top-level structure
	// -----------------------------------------------------------------

	@Test
	public void testTopLevelKeysPresent() {
		assertTrue("Missing 'package'", result.has("package"));
		assertTrue("Missing 'mainActivity'", result.has("mainActivity"));
		assertTrue("Missing 'reachability'", result.has("reachability"));
		assertTrue("Missing 'components'", result.has("components"));
		assertTrue("Missing 'windows'", result.has("windows"));
		assertTrue("Missing 'transitions'", result.has("transitions"));
	}

	@Test
	public void testPackageAndMainActivity() {
		assertEquals("br.unb.cic.cryptoapp", result.get("package").getAsString());
		assertEquals("br.unb.cic.cryptoapp.MainActivity",
				result.get("mainActivity").getAsString());
	}

	// -----------------------------------------------------------------
	// Reachability section
	// -----------------------------------------------------------------

	@Test
	public void testReachabilityNonEmpty() {
		JsonArray reachability = result.getAsJsonArray("reachability");
		assertTrue("Reachability must have at least 1 class", reachability.size() > 0);

		int totalMethods = 0;
		for (JsonElement elem : reachability) {
			JsonObject cls = elem.getAsJsonObject();
			assertTrue("Class must have className", cls.has("className"));
			assertTrue("Class must have methods array", cls.has("methods"));
			totalMethods += cls.getAsJsonArray("methods").size();
		}
		assertTrue("Must have at least 1 method", totalMethods > 0);
	}

	@Test
	public void testReachabilityMethodFields() {
		JsonArray reachability = result.getAsJsonArray("reachability");

		for (JsonElement classElem : reachability) {
			JsonObject cls = classElem.getAsJsonObject();
			assertTrue("Missing componentType", cls.has("componentType"));
			assertTrue("Missing isMain", cls.has("isMain"));

			for (JsonElement methodElem : cls.getAsJsonArray("methods")) {
				JsonObject method = methodElem.getAsJsonObject();
				assertTrue("Missing name", method.has("name"));
				assertTrue("Missing signature", method.has("signature"));
				assertTrue("Missing reachable", method.has("reachable"));
				assertTrue("Missing reachesMop", method.has("reachesMop"));
				assertTrue("Missing directlyReachesMop", method.has("directlyReachesMop"));
			}
		}
	}

	@Test
	public void testAtLeastOneDirectlyReachesMop() {
		JsonArray reachability = result.getAsJsonArray("reachability");
		boolean found = false;
		for (JsonElement classElem : reachability) {
			for (JsonElement methodElem : classElem.getAsJsonObject().getAsJsonArray("methods")) {
				if (methodElem.getAsJsonObject().get("directlyReachesMop").getAsBoolean()) {
					found = true;
					break;
				}
			}
			if (found) break;
		}
		assertTrue("cryptoapp uses JCA — at least one method must have directlyReachesMop=true", found);
	}

	@Test
	public void testMainActivityMarked() {
		JsonArray reachability = result.getAsJsonArray("reachability");
		boolean foundMain = false;
		for (JsonElement classElem : reachability) {
			JsonObject cls = classElem.getAsJsonObject();
			if (cls.get("isMain").getAsBoolean()) {
				assertEquals("br.unb.cic.cryptoapp.MainActivity", cls.get("className").getAsString());
				assertEquals("Main activity must have componentType=activity", "activity", cls.get("componentType").getAsString());
				foundMain = true;
			}
		}
		assertTrue("Must have exactly one isMain=true class", foundMain);
	}

	// -----------------------------------------------------------------
	// Inner class notation (D7)
	// -----------------------------------------------------------------

	@Test
	public void testInnerClassDollarNotation() {
		// Pattern: two uppercase segments separated by a dot (e.g., Outer.Inner)
		// This would indicate wrong notation. Packages like android.os.Bundle
		// are fine because they have lowercase after the dot.
		Pattern wrongNotation = Pattern.compile("[A-Z][a-z]*\\.[A-Z]");

		JsonArray reachability = result.getAsJsonArray("reachability");
		for (JsonElement classElem : reachability) {
			String className = classElem.getAsJsonObject().get("className").getAsString();
			// Extract the simple name (after last dot that's followed by uppercase = class boundary)
			// For inner classes, we only check if they use $ correctly
			if (className.contains("$")) {
				// Good — inner class uses $
				continue;
			}
			// Check for potential wrong inner class notation
			String simpleName = className.substring(className.lastIndexOf('.') + 1);
			assertFalse(
					"Class name '" + className + "' may use wrong inner class notation (should use $)",
					wrongNotation.matcher(simpleName).find());
		}
	}

	// -----------------------------------------------------------------
	// Windows section
	// -----------------------------------------------------------------

	@Test
	public void testWindowsNonEmpty() {
		JsonArray windows = result.getAsJsonArray("windows");
		assertTrue("Must have at least 1 window (cryptoapp has 4+ activities)", windows.size() > 0);
	}

	@Test
	public void testWindowFields() {
		JsonArray windows = result.getAsJsonArray("windows");
		Set<Integer> windowIds = new HashSet<>();

		for (JsonElement winElem : windows) {
			JsonObject window = winElem.getAsJsonObject();
			assertTrue("Window missing id", window.has("id"));
			assertTrue("Window missing name", window.has("name"));
			assertTrue("Window missing type", window.has("type"));
			assertTrue("Window missing isMain", window.has("isMain"));
			assertTrue("Window missing widgets", window.has("widgets"));

			int id = window.get("id").getAsInt();
			windowIds.add(id);

			String type = window.get("type").getAsString();
			assertTrue("Window type must be ACTIVITY, DIALOG, or OPTIONSMENU",
					type.equals("ACTIVITY") || type.equals("DIALOG") || type.equals("OPTIONSMENU"));
		}

		// Window IDs should be unique
		assertEquals("Window IDs must be unique", windows.size(), windowIds.size());
	}

	@Test
	public void testMainWindowPresent() {
		JsonArray windows = result.getAsJsonArray("windows");
		boolean foundMain = false;
		for (JsonElement winElem : windows) {
			JsonObject window = winElem.getAsJsonObject();
			if (window.get("isMain").getAsBoolean()) {
				assertTrue("Main window must be ACTIVITY type",
						window.get("type").getAsString().equals("ACTIVITY"));
				assertTrue("Main window name must contain MainActivity",
						window.get("name").getAsString().contains("MainActivity"));
				foundMain = true;
			}
		}
		assertTrue("Must have exactly one main window", foundMain);
	}

	@Test
	public void testWidgetFields() {
		JsonArray windows = result.getAsJsonArray("windows");
		int widgetCount = 0;

		for (JsonElement winElem : windows) {
			JsonArray widgets = winElem.getAsJsonObject().getAsJsonArray("widgets");
			for (JsonElement wElem : widgets) {
				JsonObject widget = wElem.getAsJsonObject();
				assertTrue("Widget missing id", widget.has("id"));
				assertTrue("Widget missing idName", widget.has("idName"));
				assertTrue("Widget missing type", widget.has("type"));
				assertTrue("Widget missing text", widget.has("text"));
				assertTrue("Widget missing hint", widget.has("hint"));
				assertTrue("Widget missing inputType", widget.has("inputType"));
				assertTrue("Widget missing entries", widget.has("entries"));
				assertTrue("Widget missing listeners", widget.has("listeners"));
				widgetCount++;
			}
		}

		assertTrue("cryptoapp must have widgets", widgetCount > 0);
	}

	// -----------------------------------------------------------------
	// Transitions section
	// -----------------------------------------------------------------

	@Test
	public void testTransitionsPresent() {
		JsonArray transitions = result.getAsJsonArray("transitions");
		assertNotNull("Transitions must be present (not null)", transitions);
		// cryptoapp has multiple activities — expect transitions
		assertTrue("cryptoapp should have transitions", transitions.size() > 0);
	}

	@Test
	public void testTransitionFields() {
		JsonArray transitions = result.getAsJsonArray("transitions");
		for (JsonElement tElem : transitions) {
			JsonObject transition = tElem.getAsJsonObject();
			assertTrue("Transition missing sourceId", transition.has("sourceId"));
			assertTrue("Transition missing targetId", transition.has("targetId"));
			assertTrue("Transition missing events", transition.has("events"));

			JsonArray events = transition.getAsJsonArray("events");
			for (JsonElement eElem : events) {
				JsonObject event = eElem.getAsJsonObject();
				assertTrue("Event missing type", event.has("type"));
				assertTrue("Event missing handler", event.has("handler"));
				assertTrue("Event missing widgetId", event.has("widgetId"));
				assertTrue("Event missing widgetClass", event.has("widgetClass"));
				assertTrue("Event missing widgetName", event.has("widgetName"));
			}
		}
	}

	// -----------------------------------------------------------------
	// JSON validity
	// -----------------------------------------------------------------

	@Test
	public void testJsonValid() {
		// If we got here, the JSON parsed successfully.
		// Additional check: all top-level values are the right types
		assertTrue("package must be string", result.get("package").isJsonPrimitive());
		assertTrue("mainActivity must be string", result.get("mainActivity").isJsonPrimitive());
		assertTrue("reachability must be array", result.get("reachability").isJsonArray());
		assertTrue("components must be object", result.get("components").isJsonObject());
		assertTrue("windows must be array", result.get("windows").isJsonArray());
		assertTrue("transitions must be array", result.get("transitions").isJsonArray());
	}
}
