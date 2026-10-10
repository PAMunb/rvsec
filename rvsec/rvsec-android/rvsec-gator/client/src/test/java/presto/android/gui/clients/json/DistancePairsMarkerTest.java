package presto.android.gui.clients.json;

import static org.junit.Assert.assertEquals;

import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.io.StringWriter;
import org.junit.Test;

/**
 * The compact-output marker (INV-ANA-86). {@link JsonReportWriter#write} cannot be driven
 * from a unit test (its section writers need a Soot Scene and GATOR's manifest parser), so
 * the marker's bytes are pinned on {@link JsonReportWriter#writeDistancePairs}, the call
 * {@code write} makes in compact mode, through a writer without indentation as compact
 * output uses.
 */
public class DistancePairsMarkerTest {

	@Test
	public void markerBytesInCompactOutput() throws IOException {
		StringWriter sw = new StringWriter();
		JsonWriter w = new JsonWriter(sw);
		w.beginObject();
		JsonReportWriter.writeDistancePairs(w);
		w.endObject();
		w.close();

		assertEquals("{\"distancePairs\":{\"weighedMax\":3,\"k\":3}}", sw.toString());
	}
}
