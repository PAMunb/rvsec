package presto.android.gui.clients.reach;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import soot.SootClass;
import soot.SootMethod;

/**
 * Stateless visitor that annotates per-node reachability for the JSON
 * writer. Each {@code enrich*} method consults the immutable
 * {@link ReachabilityIndex} and returns the key/value pairs the writer
 * should emit for that node, with no side effects on either the index
 * or the enricher itself (INV-ANA-30 preserves writer purity).
 *
 * <p>For gh60 (C1d) only {@link #enrichMethod} carries content; the
 * widget / transition / component overloads are placeholders that
 * return empty maps. C3 ({@code gh<N+2>-agent-enrichment}) fills them
 * in with per-widget {@code handlerReachesTarget} etc. without touching
 * the writer.
 *
 * <p>Keys still use the legacy gh57 names ("reachable", "reachesTarget",
 * "directlyReachesTarget") because Group 6 (C1f) renames the JSON schema
 * atomically across producer + consumers. The enricher's job in C1d/C1e
 * is to land the visitor contract; the rename is its own commit.
 */
public final class ReachabilityEnricher {

	private static final Map<String, Object> EMPTY = Collections.emptyMap();

	private final ReachabilityIndex index;
	private final String manifestPackage;
	private final String codePackage;
	private final String mainActivity;
	private final String codePackageSource;
	private final int classDefsUnderKey;

	/**
	 * Four-argument form kept for callers that carry no provenance — the tests that
	 * exercise the per-method enrichment only. Production goes through the six-argument
	 * constructor: an artefact written without the provenance is one whose denominator
	 * cannot be audited afterwards (INV-ANA-66).
	 */
	public ReachabilityEnricher(
			ReachabilityIndex index,
			String manifestPackage,
			String codePackage,
			String mainActivity) {
		this(index, manifestPackage, codePackage, mainActivity, null, -1);
	}

	public ReachabilityEnricher(
			ReachabilityIndex index,
			String manifestPackage,
			String codePackage,
			String mainActivity,
			String codePackageSource,
			int classDefsUnderKey) {
		if (index == null) {
			throw new NullPointerException("index");
		}
		this.index = index;
		this.manifestPackage = manifestPackage != null ? manifestPackage : "";
		this.codePackage = codePackage != null ? codePackage : "";
		this.mainActivity = mainActivity != null ? mainActivity : "";
		this.codePackageSource = codePackageSource != null ? codePackageSource : "";
		this.classDefsUnderKey = classDefsUnderKey;
	}

	/**
	 * Per-method reachability annotations. Used by {@code writeReachability}
	 * to populate each method object inside a class's {@code methods[]}.
	 */
	public Map<String, Object> enrichMethod(SootMethod method) {
		// LinkedHashMap preserves insertion order so the writer emits keys
		// in a stable sequence — important for diff-friendly snapshots.
		Map<String, Object> out = new LinkedHashMap<>(3);
		out.put("reachable", index.isReachable(method));
		out.put("reachesTarget", index.reachesTarget(method));
		out.put("directlyReachesTarget", index.directlyReachesTarget(method));
		return out;
	}

	/**
	 * Per-widget annotations. Empty in C1d; C3 introduces
	 * {@code handlerReachesTarget}/{@code handlerDirectlyReachesTarget}
	 * here without modifying the writer.
	 */
	public Map<String, Object> enrichWidget(Map<String, Object> widget) {
		return EMPTY;
	}

	/**
	 * Per-transition annotations. Empty in C1d; C3 introduces
	 * {@code handlerReachesTarget}/{@code externalExit}/{@code exitKind}
	 * per WTG edge here.
	 */
	public Map<String, Object> enrichTransition(Object transitionDescriptor) {
		return EMPTY;
	}

	/**
	 * Per-component annotations. Empty in C1d; C3 may emit
	 * {@code componentReachesTarget} aggregates here.
	 */
	public Map<String, Object> enrichComponent(SootClass component) {
		return EMPTY;
	}

	/**
	 * App-level metadata: the two packages, the main activity, the origin of the
	 * effective key and the compiled class universe under it.
	 *
	 * <p>The last two exist so that a stored artefact answers, on its own, the two
	 * questions a coverage denominator raises after the fact — which key filtered it,
	 * and how many compiled classes that key covered (INV-ANA-66). Neither is
	 * recoverable from the file otherwise: the {@code package} member is the manifest
	 * package whatever key filtered the contents, and no consumer holds the APK.
	 *
	 * <p>{@code class_defs_under_key} is the NET count — the compiled classes under the
	 * key that survive {@code RvsecAnalysisClient.isAppClass}, the same predicate that
	 * filtered the parsed side. That is what lets the denominator gate merely divide.
	 * It is {@code -1} when this enricher was built without provenance.
	 */
	public Map<String, Object> topLevelMetadata() {
		Map<String, Object> out = new LinkedHashMap<>(5);
		out.put("manifestPackage", manifestPackage);
		out.put("codePackage", codePackage);
		out.put("mainActivity", mainActivity);
		out.put("codePackageSource", codePackageSource);
		out.put("class_defs_under_key", Integer.valueOf(classDefsUnderKey));
		return out;
	}

	/**
	 * Set of Soot signatures for methods that reach a target. The writer
	 * emits this as the {@code targetMethods}/{@code targetMethods} top-level
	 * key (name changes in Group 6 — payload identical).
	 */
	public Set<String> targetSignatures() {
		return index.reachesTargetSignatures();
	}

	/**
	 * Set of Soot signatures for methods that DIRECTLY reach a target
	 * (CG-edge ∪ bytecode-scan).
	 */
	public Set<String> directTargetSignatures() {
		return index.directlyReachesTargetSignatures();
	}

	public ReachabilityIndex index() {
		return index;
	}
}
