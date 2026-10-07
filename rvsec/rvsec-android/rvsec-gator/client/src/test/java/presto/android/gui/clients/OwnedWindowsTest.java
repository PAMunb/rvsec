package presto.android.gui.clients;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.*;
import static org.junit.Assert.*;

/**
 * Unit tests for the window bookkeeping of the {@code FRAGMENT} and {@code HOSTED}
 * windows: one window per host for each distinct widget list, and ids past every
 * existing window id (INV-ANA-76).
 */
public class OwnedWindowsTest {

	private static Map<String, Object> window(int id, String name, String type, String... ids) {
		Map<String, Object> w = new LinkedHashMap<>();
		w.put("id", id);
		w.put("name", name);
		w.put("type", type);
		List<Map<String, Object>> widgets = new ArrayList<>();
		for (String idName : ids) {
			Map<String, Object> x = new LinkedHashMap<>();
			x.put("idName", idName);
			widgets.add(x);
		}
		w.put("widgets", widgets);
		return w;
	}

	@Test
	public void repeatedTreeUnderOneHostIsKeptOnce() {
		List<Map<String, Object>> windows = new ArrayList<>(Arrays.asList(
				window(1, "a.Main", "ACTIVITY", "x"),
				window(900000, "a.Main#a.FragOne", "FRAGMENT", "ok", "cancel"),
				window(900001, "a.Main#a.FragTwo", "FRAGMENT", "ok", "cancel"),
				window(900002, "a.Main#a.Adapter", "HOSTED", "ok", "cancel")));
		RvsecAnalysisClient.dropRepeatedOwnedWindows(windows);
		assertEquals(2, windows.size());
		assertEquals("a.Main#a.FragOne", windows.get(1).get("name"));
	}

	@Test
	public void sameTreeUnderTwoHostsIsKeptTwice() {
		List<Map<String, Object>> windows = new ArrayList<>(Arrays.asList(
				window(900000, "a.Main#a.Frag", "FRAGMENT", "ok"),
				window(900001, "a.Other#a.Frag", "FRAGMENT", "ok")));
		RvsecAnalysisClient.dropRepeatedOwnedWindows(windows);
		assertEquals(2, windows.size());
	}

	@Test
	public void activityWindowsAreNeverDropped() {
		List<Map<String, Object>> windows = new ArrayList<>(Arrays.asList(
				window(1, "a.Main", "ACTIVITY", "ok"),
				window(2, "a.Main", "ACTIVITY", "ok")));
		RvsecAnalysisClient.dropRepeatedOwnedWindows(windows);
		assertEquals(2, windows.size());
	}

	@Test
	public void equalWidgetRecordsAreKeptOnce() {
		Map<String, Object> w = window(900000, "a.Main#a.Dialogs", "HOSTED", "edit", "edit", "ok", "edit");
		Map<String, Object> other = window(1, "a.Main", "ACTIVITY", "x", "x");
		RvsecAnalysisClient.dropRepeatedWidgets(new ArrayList<>(Arrays.asList(w, other)));
		assertEquals(2, ((List<?>) w.get("widgets")).size());
		assertEquals("edit", ((Map<?, ?>) ((List<?>) w.get("widgets")).get(0)).get("idName"));
		assertEquals(1, ((List<?>) other.get("widgets")).size());
	}

	@Test
	public void recordsOfOneIdThatDifferAreBothKept() {
		Map<String, Object> w = window(900000, "a.Main#a.Dialogs", "HOSTED", "edit", "edit");
		@SuppressWarnings("unchecked")
		List<Map<String, Object>> widgets = (List<Map<String, Object>>) w.get("widgets");
		widgets.get(1).put("text", "other");
		RvsecAnalysisClient.dropRepeatedWidgets(new ArrayList<>(Arrays.asList(w)));
		assertEquals(2, widgets.size());
	}

	@Test
	public void ownedIdsStartPastEveryExistingId() {
		List<Map<String, Object>> windows = new ArrayList<>(Arrays.asList(
				window(12, "a.Main", "ACTIVITY"),
				window(900004, "a.Main#a.Frag", "FRAGMENT")));
		assertEquals(900005, RvsecAnalysisClient.nextOwnedWindowId(windows));
		assertEquals(900000, RvsecAnalysisClient.nextOwnedWindowId(new ArrayList<>()));
	}
}
