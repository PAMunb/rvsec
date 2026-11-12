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
import presto.android.gui.clients.reach.DistancePaths;
import presto.android.gui.clients.reach.ReachabilityEnricher;
import presto.android.gui.clients.reach.TargetDistances;
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
 *
 * <p>Output mode (INV-ANA-85, INV-ANA-86). Both modes are written with no
 * whitespace between tokens: no indent is set on the {@link JsonWriter}.
 * Full output carries every distance pair the searches recorded. Compact
 * output, the client's default, carries the {@code distancePairs} marker
 * and writes each method's pairs reduced by
 * {@link TargetDistances#compact}. A writer has one mode, so the pre-WTG
 * write and the final write of a run always agree.
 *
 * <p>Distance horizon (INV-ANA-99). A writer given the run's
 * {@code distMax} writes it as the {@code distMax} member right after
 * {@code class_defs_under_key}, in every write and in both modes. A writer
 * given none writes no such member.
 *
 * <p>Distance paths (INV-ANA-90). A writer given a {@link DistancePaths}
 * writes {@code pathMethods} and {@code distancePaths} right after
 * {@code reachability}, in every write. A writer given none writes
 * neither, and its document is otherwise the same.
 */
public final class JsonReportWriter {

	private final ReachabilityEnricher enricher;
	private final boolean compact;
	private final DistancePaths paths;
	private final Integer distMax;

	/**
	 * @param enricher the only source of per-node reachability (INV-ANA-30)
	 * @param compact {@code true} for compact output, {@code false} for full output
	 * @param paths the distance paths to write, or {@code null} to write none
	 * @param distMax the run's {@code distMax} client parameter, written as the
	 *     {@code distMax} member (INV-ANA-99), or {@code null} when the run was
	 *     given none, to write no member
	 */
	public JsonReportWriter(ReachabilityEnricher enricher, boolean compact, DistancePaths paths,
			Integer distMax) {
		if (enricher == null) {
			throw new NullPointerException("enricher");
		}
		this.enricher = enricher;
		this.compact = compact;
		this.paths = paths;
		this.distMax = distMax;
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

			w.beginObject();

			// The scope metadata is read through the enricher rather than from new
			// writer arguments — the same routing that keeps this class free of a
			// ReachabilityIndex reference (INV-ANA-30).
			writeHeader(w, appPackage, mainActivity != null ? mainActivity.getName() : null,
					enricher.topLevelMetadata(), compact, distMax);

			// Distance targets (INV-ANA-73): the index space of every method's
			// targetDistances pairs, so it precedes the reachability section. Read
			// through the enricher; absent when the distance pass failed.
			writeDistanceTargets(w, enricher.distanceTargets());

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
			RvsecAnalysisClient.writeReachabilitySection(w, appClasses, guiOutput, enricher,
					compact);
			w.flush();

			// Distance paths (INV-ANA-90): nothing when the writer has none.
			writeDistancePaths(w, paths);
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
	 * Emit the members {@link #write} writes before {@code distanceTargets}, in this order:
	 * {@code package}, {@code mainActivity}, the three scope members, {@code distMax} when it
	 * is not null, and the {@code distancePairs} marker in compact output.
	 *
	 * <p>It takes no Soot type, so a unit test can drive it ({@link #write} needs a Soot Scene),
	 * and no distance-pass result, so none of these members depends on whether the distance
	 * pass produced {@code distanceTargets}.
	 *
	 * @param appPackage the manifest package; {@code null} is written as an empty string
	 * @param mainActivityName the main activity's class name; {@code null} is written as an
	 *     empty string
	 * @param metadata the enricher's {@link ReachabilityEnricher#topLevelMetadata()}
	 * @param compact {@code true} for compact output, which carries the marker
	 * @param distMax the run's horizon to record, or {@code null} to write no member
	 */
	static void writeHeader(JsonWriter w, String appPackage, String mainActivityName,
			Map<String, Object> metadata, boolean compact, Integer distMax) throws IOException {
		w.name(JsonSchema.Keys.PACKAGE).value(appPackage != null ? appPackage : "");
		w.name(JsonSchema.Keys.MAIN_ACTIVITY).value(
				mainActivityName != null ? mainActivityName : "");

		// Scope provenance (INV-ANA-66). PACKAGE above is the manifest package; these
		// three are what the run actually filtered by.
		w.name(JsonSchema.Keys.CODE_PACKAGE).value(
				String.valueOf(metadata.get("codePackage")));
		w.name(JsonSchema.Keys.CODE_PACKAGE_SOURCE).value(
				String.valueOf(metadata.get("codePackageSource")));
		w.name(JsonSchema.Keys.CLASS_DEFS_UNDER_KEY).value(
				((Number) metadata.get("class_defs_under_key")).intValue());

		// Distance horizon (INV-ANA-99): only when the run was given distMax, so a
		// document without the member was computed with TargetDistances.DEFAULT_DIST_MAX.
		// Before the marker, so the converter, which inserts the marker before
		// distanceTargets, keeps GATOR's member order (INV-ANA-87).
		if (distMax != null) {
			w.name(JsonSchema.Keys.DIST_MAX).value(distMax.intValue());
		}

		// Output-mode marker (INV-ANA-86): only in compact output, before the
		// first pair so a streaming reader learns the document's kind early, and
		// after the scope members and distMax so the member order is otherwise the
		// full one. Written even when distanceTargets is absent: it describes how the
		// document was written, not what the distance pass found.
		if (compact) {
			writeDistancePairs(w);
		}
	}

	/**
	 * Emit the compact-output marker {@code "distancePairs":{"weighedMax":3,"k":3}}: the
	 * values of {@link TargetDistances#COMPACT_WEIGHED_MAX} and
	 * {@link TargetDistances#COMPACT_K}, so each compact document records the reduction its
	 * {@code targetDistances} lists went through.
	 */
	static void writeDistancePairs(JsonWriter w) throws IOException {
		w.name(JsonSchema.Keys.DISTANCE_PAIRS);
		w.beginObject();
		w.name(JsonSchema.Keys.WEIGHED_MAX).value(TargetDistances.COMPACT_WEIGHED_MAX);
		w.name(JsonSchema.Keys.K).value(TargetDistances.COMPACT_K);
		w.endObject();
	}

	/** Emit {@code distanceTargets} as a list of {@code {signature, kind}}; nothing when null. */
	static void writeDistanceTargets(JsonWriter w, List<Map<String, String>> targets)
			throws IOException {
		if (targets == null) {
			return;
		}
		w.name(JsonSchema.Keys.DISTANCE_TARGETS);
		w.beginArray();
		for (Map<String, String> t : targets) {
			w.beginObject();
			w.name(JsonSchema.Keys.SIGNATURE).value(t.get(JsonSchema.Keys.SIGNATURE));
			w.name(JsonSchema.Keys.KIND).value(t.get(JsonSchema.Keys.KIND));
			w.endObject();
		}
		w.endArray();
	}

	/**
	 * Emit {@code pathMethods} and then {@code distancePaths} (INV-ANA-91); nothing when
	 * {@code paths} is null, so the document is the one written without paths (INV-ANA-90).
	 */
	static void writeDistancePaths(JsonWriter w, DistancePaths paths) throws IOException {
		if (paths == null) {
			return;
		}
		w.name(JsonSchema.Keys.PATH_METHODS);
		w.beginArray();
		for (String signature : paths.methods()) {
			w.value(signature);
		}
		w.endArray();
		w.name(JsonSchema.Keys.DISTANCE_PATHS);
		w.beginArray();
		for (int[] step : paths.steps()) {
			w.beginArray().value(step[0]).value(step[1]).value(step[2]).endArray();
		}
		w.endArray();
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
