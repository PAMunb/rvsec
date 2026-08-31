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
 * (components → reachability → windows → transitions), flushes after
 * each, and emits the {@code "complete": true} sentinel (ADR-6) as the
 * last top-level field when the caller asks for it — followed by an
 * explicit {@code fsync} so a post-close write-back loss on networked
 * storage cannot strip the sentinel from disk. A caller that writes an
 * intermediate report passes {@code emitSentinel=false}: the file is
 * valid JSON, but it does not claim the analysis finished.
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
	 * Write the report to {@code outputPath}. The sentinel is emitted
	 * only when {@code emitSentinel} is true; on any exception path it is
	 * not written at all (the parser detects the partial file via the
	 * sentinel's absence).
	 *
	 * <p>The flag exists because the client writes this file twice: once
	 * before WTG construction, to save reachability from a WTG timeout,
	 * and once after. A successful write is not the same event as a
	 * finished analysis — the caller is the only one that knows whether
	 * the write it is asking for is the run's last. Emitting the sentinel
	 * unconditionally made a report killed inside WTG construction
	 * indistinguishable on disk from a complete one (INV-ANA-31).
	 */
	public void write(
			String outputPath,
			boolean emitSentinel,
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

			// Scope provenance (INV-ANA-66), read through the enricher rather than
			// from new writer arguments — the same routing that keeps this class free
			// of a ReachabilityIndex reference (INV-ANA-30). PACKAGE above is the
			// manifest package; these three are what the run actually filtered by.
			Map<String, Object> metadata = enricher.topLevelMetadata();
			w.name(JsonSchema.Keys.CODE_PACKAGE).value(
					String.valueOf(metadata.get("codePackage")));
			w.name(JsonSchema.Keys.CODE_PACKAGE_SOURCE).value(
					String.valueOf(metadata.get("codePackageSource")));
			w.name(JsonSchema.Keys.CLASS_DEFS_UNDER_KEY).value(
					((Number) metadata.get("class_defs_under_key")).intValue());

			// Section 1: components — manifest-derived, trivial cost
			// (D14 2026-05-29). Promoted before the heavy analysis
			// sections so a transitions-timeout cannot drop the
			// windows->activity-class lookup downstream consumers depend
			// on. enricher + guiOutput are already in scope at writer
			// entry; no new data dependency.
			w.name(JsonSchema.Keys.COMPONENTS);
			RvsecAnalysisClient.writeComponentsSection(w,
					enricher, guiOutput.getActivities(), mainActivity);
			w.flush();

			// Section 2: reachability — coverage denominator
			w.name(JsonSchema.Keys.REACHABILITY);
			RvsecAnalysisClient.writeReachabilitySection(w, appClasses, guiOutput, enricher);
			w.flush();

			// Section 3: windows
			w.name(JsonSchema.Keys.WINDOWS);
			RvsecAnalysisClient.writeWindowsSection(w, windows);
			w.flush();

			// Section 4: transitions — heaviest, fragile under timeout
			w.name(JsonSchema.Keys.TRANSITIONS);
			if (wtg != null) {
				RvsecAnalysisClient.writeTransitionsSection(w, wtg);
			} else {
				w.beginArray().endArray();
			}
			w.flush();

			// Sentinel (ADR-6) — last top-level field. Its absence on a
			// recovered partial file is what consumers read to mark the
			// sample as incomplete and exclude it from gates requiring
			// completeness.
			writeCompletionSentinel(w, emitSentinel);

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

	/**
	 * Emit the completion sentinel as the last top-level field, or nothing
	 * when the caller says this write is not the run's end.
	 *
	 * <p>It is a method rather than an inline branch so the decision can be
	 * exercised on its own: {@link #write} cannot be driven from a unit test
	 * (its section writers need a fully-initialised Soot Scene and GATOR's
	 * XMLParser factory), so this is the only production surface where the
	 * "do not claim completeness on a partial write" rule is checkable
	 * without a full GATOR run.
	 */
	static void writeCompletionSentinel(JsonWriter w, boolean emitSentinel) throws IOException {
		if (emitSentinel) {
			w.name(JsonSchema.Keys.COMPLETE).value(true);
		}
	}

	/** Exposed for {@code JsonReportWriterPurityTest} reflection (INV-ANA-30). */
	public Set<String> reachesTargetSignatures() {
		return enricher.targetSignatures();
	}
}
