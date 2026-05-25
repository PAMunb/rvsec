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

	public ReachabilityEnricher(
			ReachabilityIndex index,
			String manifestPackage,
			String codePackage,
			String mainActivity) {
		if (index == null) {
			throw new NullPointerException("index");
		}
		this.index = index;
		this.manifestPackage = manifestPackage != null ? manifestPackage : "";
		this.codePackage = codePackage != null ? codePackage : "";
		this.mainActivity = mainActivity != null ? mainActivity : "";
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
	 * App-level metadata. Currently the gh57 inline writer emits
	 * {@code package} and {@code mainActivity} only; {@code codePackage}
	 * is reserved for the upcoming dual-package emission (C2 — issue
	 * G11) and is exposed here so that change can add the key without
	 * touching the writer.
	 */
	public Map<String, Object> topLevelMetadata() {
		Map<String, Object> out = new LinkedHashMap<>(3);
		out.put("manifestPackage", manifestPackage);
		out.put("codePackage", codePackage);
		out.put("mainActivity", mainActivity);
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
