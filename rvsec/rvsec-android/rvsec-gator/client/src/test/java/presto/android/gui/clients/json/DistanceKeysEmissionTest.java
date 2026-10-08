package presto.android.gui.clients.json;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.io.StringWriter;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import presto.android.gui.clients.reach.ReachabilityEnricher;
import presto.android.gui.clients.reach.ReachabilityIndex;
import presto.android.gui.clients.reach.TargetDistances;
import soot.G;
import soot.Modifier;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Type;
import soot.VoidType;
import soot.options.Options;

/**
 * When the two distance keys appear in the artefact (INV-ANA-73).
 *
 * <ul>
 *   <li>{@code distanceTargets} is written whenever the distance pass ran, as an empty
 *       list when it found no target; it is missing only when the pass failed.</li>
 *   <li>{@code targetDistances} is present on a method with at least one pair and
 *       absent otherwise.</li>
 * </ul>
 *
 * <p>The top-level key goes through {@link JsonReportWriter#writeDistanceTargets}. The
 * per-method key is checked on {@link ReachabilityEnricher#enrichMethod}: the
 * reachability writer emits it exactly when that map carries it, and the writer itself
 * needs the manifest parser, which a unit test does not have.
 *
 * <p>Call graph of the fixture: {@code u -> t}, {@code t} directly reaches a target,
 * {@code v} calls nothing.
 */
public class DistanceKeysEmissionTest {

	private SootMethod t;
	private SootMethod u;
	private SootMethod v;

	@Before
	public void buildScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		Scene.v().addBasicClass("java.lang.Object", SootClass.SIGNATURES);
		Scene.v().loadNecessaryClasses();

		SootClass app = new SootClass("p.App", Modifier.PUBLIC);
		app.setSuperclass(Scene.v().getSootClass("java.lang.Object"));
		Scene.v().addClass(app);
		t = method(app, "t");
		u = method(app, "u");
		v = method(app, "v");
	}

	@After
	public void tearDown() {
		G.reset();
	}

	private static SootMethod method(SootClass owner, String name) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC);
		owner.addMethod(m);
		return m;
	}

	private TargetDistances<SootMethod> distances(Set<SootMethod> direct) {
		Map<SootMethod, Set<SootMethod>> callers = new HashMap<>();
		callers.put(t, new HashSet<>(Collections.singleton(u)));
		return TargetDistances.compute(callers, new HashSet<>(Arrays.asList(t, u, v)), direct,
				Collections.<SootMethod>emptySet(), SootMethod::getSignature);
	}

	private static ReachabilityEnricher enricher(TargetDistances<SootMethod> d) {
		ReachabilityIndex index = new ReachabilityIndex(Collections.<SootMethod>emptySet(),
				Collections.<SootMethod>emptySet(), Collections.<SootMethod>emptySet());
		return new ReachabilityEnricher(index, "p", "p", "p.App", "manifest", 1, d);
	}

	private static JsonObject writeTopLevel(List<Map<String, String>> targets) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		JsonReportWriter.writeDistanceTargets(w, targets);
		w.endObject();
		w.close();
		return JsonParser.parseString(sw.toString()).getAsJsonObject();
	}

	@Test
	public void distanceTargetsListsEachTargetWithSignatureAndKind() throws IOException {
		JsonObject out = writeTopLevel(
				enricher(distances(Collections.singleton(t))).distanceTargets());

		JsonArray targets = out.getAsJsonArray(JsonSchema.Keys.DISTANCE_TARGETS);
		assertEquals(1, targets.size());
		JsonObject first = targets.get(0).getAsJsonObject();
		assertEquals("<p.App: void t()>", first.get(JsonSchema.Keys.SIGNATURE).getAsString());
		assertEquals(TargetDistances.KIND_DIRECT, first.get(JsonSchema.Keys.KIND).getAsString());
	}

	@Test
	public void distanceTargetsIsAnEmptyListWhenThePassFoundNoTarget() throws IOException {
		JsonObject out = writeTopLevel(
				enricher(distances(Collections.<SootMethod>emptySet())).distanceTargets());

		assertTrue(out.has(JsonSchema.Keys.DISTANCE_TARGETS));
		assertEquals(0, out.getAsJsonArray(JsonSchema.Keys.DISTANCE_TARGETS).size());
	}

	@Test
	public void distanceTargetsIsMissingOnlyWhenThePassFailed() throws IOException {
		// computeDistances returns null on failure; the enricher is built with that null.
		JsonObject out = writeTopLevel(enricher(null).distanceTargets());

		assertFalse(out.has(JsonSchema.Keys.DISTANCE_TARGETS));
	}

	@Test
	public void targetDistancesOnAMethodWithinReachOfATarget() {
		ReachabilityEnricher e = enricher(distances(Collections.singleton(t)));

		int[][] uPairs = (int[][]) e.enrichMethod(u).get(JsonSchema.Keys.TARGET_DISTANCES);
		assertEquals(1, uPairs.length);
		assertArrayEquals(new int[] { 0, 1 }, uPairs[0]);
		int[][] tPairs = (int[][]) e.enrichMethod(t).get(JsonSchema.Keys.TARGET_DISTANCES);
		assertArrayEquals(new int[] { 0, 0 }, tPairs[0]);
	}

	@Test
	public void targetDistancesAbsentOnAMethodWithNoPair() {
		ReachabilityEnricher e = enricher(distances(Collections.singleton(t)));

		assertFalse(e.enrichMethod(v).containsKey(JsonSchema.Keys.TARGET_DISTANCES));
	}

	@Test
	public void targetDistancesAbsentEverywhereWhenThePassFailed() {
		ReachabilityEnricher e = enricher(null);

		for (SootMethod m : Arrays.asList(t, u, v)) {
			assertFalse(m.getName(), e.enrichMethod(m).containsKey(JsonSchema.Keys.TARGET_DISTANCES));
		}
	}
}
