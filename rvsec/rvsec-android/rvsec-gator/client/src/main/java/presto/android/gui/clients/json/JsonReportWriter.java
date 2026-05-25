package presto.android.gui.clients.json;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.google.gson.stream.JsonWriter;

import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.RvsecAnalysisClient;
import presto.android.gui.clients.reach.ReachabilityEnricher;
import presto.android.gui.wtg.ds.WTG;
import soot.SootClass;
import soot.SootMethod;

/**
 * Streaming JSON writer for the unified static-analysis report. Drives
 * the four top-level sections in priority order
 * (reachability → windows → transitions → components), flushes after
 * each, and emits the {@code "complete": true} sentinel (ADR-6) as the
 * last top-level field — followed by an explicit {@code fsync} so a
 * post-close write-back loss on networked storage cannot strip the
 * sentinel from disk.
 *
 * <p>Purity contract (INV-ANA-30): this class has zero
 * {@link presto.android.gui.clients.reach.ReachabilityIndex} reference.
 * Per-method/per-component reachability is read exclusively through
 * {@link ReachabilityEnricher} — the same visitor passed in here. The
 * section-detail helpers still live on {@code RvsecAnalysisClient} as
 * public static methods (writeReachability / writeWindows /
 * writeTransitions / writeComponents); moving them physically into
 * this class is a pure code-shuffle that is left for a follow-up
 * cleanup. The architectural boundary is the public surface of this
 * writer, which is what the spec contract pins.
 */
public final class JsonReportWriter {

	private final ReachabilityEnricher enricher;

	public JsonReportWriter(ReachabilityEnricher enricher) {
		if (enricher == null) {
			throw new NullPointerException("enricher");
		}
		this.enricher = enricher;
	}

	/**
	 * Write the report to {@code outputPath}. On success the file ends
	 * with {@code ,"complete":true}\n followed by an fsync; on any
	 * exception path the sentinel is NOT written (the parser detects
	 * the partial file via the sentinel's absence).
	 */
	public void write(
			String outputPath,
			String appPackage,
			SootClass mainActivity,
			Map<SootClass, List<SootMethod>> appClasses,
			GUIAnalysisOutput guiOutput,
			List<Map<String, Object>> windows,
			WTG wtg) throws IOException {

		try (FileOutputStream fos = new FileOutputStream(outputPath);
				OutputStreamWriter osw = new OutputStreamWriter(fos, StandardCharsets.UTF_8);
				JsonWriter w = new JsonWriter(osw)) {

			w.setIndent("  ");
			w.beginObject();

			w.name(JsonSchema.Keys.PACKAGE).value(appPackage != null ? appPackage : "");
			w.name(JsonSchema.Keys.MAIN_ACTIVITY).value(
					mainActivity != null ? mainActivity.getName() : "");

			// Section 1: reachability — coverage denominator, most critical
			w.name(JsonSchema.Keys.REACHABILITY);
			RvsecAnalysisClient.writeReachabilitySection(w, appClasses, guiOutput, enricher);
			w.flush();

			// Section 2: windows
			w.name(JsonSchema.Keys.WINDOWS);
			RvsecAnalysisClient.writeWindowsSection(w, windows);
			w.flush();

			// Section 3: transitions
			w.name(JsonSchema.Keys.TRANSITIONS);
			if (wtg != null) {
				RvsecAnalysisClient.writeTransitionsSection(w, wtg);
			} else {
				w.beginArray().endArray();
			}
			w.flush();

			// Section 4: components
			w.name(JsonSchema.Keys.COMPONENTS);
			RvsecAnalysisClient.writeComponentsSection(w,
					enricher, guiOutput.getActivities(), mainActivity);
			w.flush();

			// Sentinel (ADR-6) — last top-level field. Its absence on a
			// recovered partial file is what consumers read to mark the
			// sample as incomplete and exclude it from gates requiring
			// completeness.
			w.name(JsonSchema.Keys.COMPLETE).value(true);

			w.endObject();
			w.flush();
			osw.flush();

			// Defend against post-close write-back loss on networked FS:
			// force the kernel page cache to disk before the JVM hands the
			// file back to the operator. A crash here means the sentinel
			// did not reach disk, which is exactly what we want — the
			// consumer treats the file as incomplete.
			fos.getFD().sync();
		}
	}

	/** Exposed for {@code JsonReportWriterPurityTest} reflection (INV-ANA-30). */
	public Set<String> reachesTargetSignatures() {
		return enricher.targetSignatures();
	}
}
