package presto.android.gui.clients.json;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.Test;
import presto.android.gui.clients.reach.DistancePaths;

/**
 * When the two distance-path members appear in the artefact (INV-ANA-90, -91).
 *
 * <p>{@link JsonReportWriter#write} cannot be driven from a unit test (its section writers need
 * a Soot Scene and GATOR's manifest parser), so the members go through
 * {@link JsonReportWriter#writeDistancePaths}, the call {@code write} makes right after the
 * {@code reachability} section. Each fixture writes the members between stand-ins for
 * {@code reachability} and {@code windows}, as {@code write} does.
 */
public class DistancePathsEmissionTest {

	private static String document(DistancePaths paths) throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		w.name(JsonSchema.Keys.REACHABILITY).beginArray().endArray();
		JsonReportWriter.writeDistancePaths(w, paths);
		w.name(JsonSchema.Keys.WINDOWS).beginArray().endArray();
		w.endObject();
		w.close();
		return sw.toString();
	}

	private static DistancePaths paths() {
		return new DistancePaths(Arrays.asList("<A: void onClick()>", "<A: void save()>",
				"<Crypto: void encrypt()>"), new int[][] { { 0, 0, 1 }, { 0, 1, 2 } });
	}

	@Test
	public void membersAbsentWithoutPaths() throws IOException {
		String doc = document(null);

		JsonObject out = JsonParser.parseString(doc).getAsJsonObject();
		assertFalse(out.has(JsonSchema.Keys.PATH_METHODS));
		assertFalse(out.has(JsonSchema.Keys.DISTANCE_PATHS));
		assertEquals("the document is the one written without the call",
				"{\"reachability\":[],\"windows\":[]}", doc);
	}

	@Test
	public void membersFollowReachabilityInOrder() throws IOException {
		JsonObject out = JsonParser.parseString(document(paths())).getAsJsonObject();

		List<String> keys = new ArrayList<>(out.keySet());
		assertEquals(Arrays.asList(JsonSchema.Keys.REACHABILITY, JsonSchema.Keys.PATH_METHODS,
				JsonSchema.Keys.DISTANCE_PATHS, JsonSchema.Keys.WINDOWS), keys);
	}

	@Test
	public void valuesAreWrittenAsGiven() throws IOException {
		JsonObject out = JsonParser.parseString(document(paths())).getAsJsonObject();

		JsonArray methods = out.getAsJsonArray(JsonSchema.Keys.PATH_METHODS);
		assertEquals(3, methods.size());
		assertEquals("<A: void onClick()>", methods.get(0).getAsString());
		assertEquals("<A: void save()>", methods.get(1).getAsString());
		assertEquals("<Crypto: void encrypt()>", methods.get(2).getAsString());
		assertEquals("[[0,0,1],[0,1,2]]",
				out.getAsJsonArray(JsonSchema.Keys.DISTANCE_PATHS).toString());
	}
}
