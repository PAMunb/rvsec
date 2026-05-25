package presto.android.gui.clients.reach;

import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

import soot.SootMethod;

/**
 * Immutable, O(1)-lookup reachability ADT.
 *
 * <p>Encapsulates the three sets that {@link ReachabilityEngine#run} produces:
 * <ul>
 *   <li>{@code reachableSet} — methods reachable from the application entry
 *       points (forward BFS on the SPARK call graph + lifecycle/listener
 *       complement).</li>
 *   <li>{@code reachesTargetSet} — methods whose transitive call closure
 *       contains at least one target method (reverse BFS seeded from the
 *       resolved targets, with the same callback complement).</li>
 *   <li>{@code directTargetSet} — methods that directly invoke a target,
 *       union of CG-edge detection and bytecode-scan detection
 *       (BUG-INV-ANA-19).</li>
 * </ul>
 *
 * <p>Built once after the engine's pipeline completes; consumers (the JSON
 * writer + enricher in C1d/C1e) only read. Field names temporarily mirror
 * the gh57 MOP nomenclature on the inside ({@code reachesTargetSet} carries
 * the same content as the historical {@code reachesMopSet}); Group 6 (C1f)
 * propagates the rename through the JSON schema as well, with no semantic
 * change.
 */
public final class ReachabilityIndex {

	private final Set<SootMethod> reachableSet;
	private final Set<SootMethod> reachesTargetSet;
	private final Set<SootMethod> directTargetSet;
	private final Set<String> reachesTargetSignatures;
	private final Set<String> directTargetSignatures;

	public ReachabilityIndex(
			Set<SootMethod> reachableSet,
			Set<SootMethod> reachesTargetSet,
			Set<SootMethod> directTargetSet) {
		Objects.requireNonNull(reachableSet, "reachableSet");
		Objects.requireNonNull(reachesTargetSet, "reachesTargetSet");
		Objects.requireNonNull(directTargetSet, "directTargetSet");

		// Defensive copies — the engine hands its working sets in by reference,
		// but downstream consumers (writer + enricher) MUST NOT see mutations
		// after the index is published.
		this.reachableSet = Collections.unmodifiableSet(new HashSet<>(reachableSet));
		this.reachesTargetSet = Collections.unmodifiableSet(new HashSet<>(reachesTargetSet));
		this.directTargetSet = Collections.unmodifiableSet(new HashSet<>(directTargetSet));

		this.reachesTargetSignatures = signaturesOf(this.reachesTargetSet);
		this.directTargetSignatures = signaturesOf(this.directTargetSet);
	}

	private static Set<String> signaturesOf(Set<SootMethod> methods) {
		Set<String> out = new HashSet<>(methods.size());
		for (SootMethod m : methods) {
			out.add(m.getSignature());
		}
		return Collections.unmodifiableSet(out);
	}

	public boolean isReachable(SootMethod m) {
		return reachableSet.contains(m);
	}

	public boolean reachesTarget(SootMethod m) {
		return reachesTargetSet.contains(m);
	}

	public boolean directlyReachesTarget(SootMethod m) {
		return directTargetSet.contains(m);
	}

	public Set<SootMethod> reachableMethods() {
		return reachableSet;
	}

	public Set<SootMethod> reachesTargetMethods() {
		return reachesTargetSet;
	}

	public Set<SootMethod> directlyReachesTargetMethods() {
		return directTargetSet;
	}

	public Set<String> reachesTargetSignatures() {
		return reachesTargetSignatures;
	}

	public Set<String> directlyReachesTargetSignatures() {
		return directTargetSignatures;
	}
}
