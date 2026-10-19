package presto.android.gui.clients.reach;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiPredicate;
import java.util.function.Function;

import soot.SootClass;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * Call-graph distance from each app method to each distance target (INV-ANA-73).
 *
 * <p>The targets are two kinds of app methods:
 * <ul>
 *   <li>{@value #KIND_DIRECT}: C, the app methods in the {@code directlyReachesTarget} set;</li>
 *   <li>{@value #KIND_BOUNDARY}: B \ C, where B holds the app methods with a call-graph edge to
 *       a library method from which a target is reachable through library methods only. A target
 *       itself is not such a library method: an edge to a target makes the caller a member of
 *       C.</li>
 * </ul>
 * The list is C sorted by signature followed by B \ C sorted by signature, so the index of a
 * target is stable for a given artefact. Library methods are never targets: a distance to a
 * library direct caller gives the explorer nothing to act on in the app.
 *
 * <p>One reverse breadth-first search per target over the call graph with self-loops dropped —
 * the graph the reachability search walks, lambda edges included — records the level at which
 * it first visits each method, up to {@value #DIST_MAX}; {@code d(t, t) = 0}. The search walks
 * library methods too (D2: app callbacks invoked from library code are real paths), but only
 * app methods carry pairs. Every method with a pair is in {@code reachesTarget}, because the
 * reachability search runs on the same graph from a superset of these seeds (INV-ANA-74).
 *
 * <p>Each search visits a method's callers in signature order with a first-in first-out queue.
 * The order changes no distance, since a breadth-first level does not depend on it; it fixes
 * which of several equally short paths a search reaches first, which {@link #paths} records
 * (INV-ANA-92).
 *
 * <p>The algorithm works on a callee → callers map, so it is exercised in tests on string
 * vertices without a Soot Scene; {@link #compute(CallGraph, ReachabilityIndex, Map, Set)} builds
 * that map from the Soot call graph.
 *
 * @param <V> vertex type ({@link SootMethod} in production)
 */
public final class TargetDistances<V> {

	public static final int DIST_MAX = 10;
	/** Largest distance a compact document keeps for every target (see {@link #compact}). */
	public static final int COMPACT_WEIGHED_MAX = 3;
	/** Number of nearest targets a compact document keeps per method (see {@link #compact}). */
	public static final int COMPACT_K = 3;
	public static final String KIND_DIRECT = "direct";
	public static final String KIND_BOUNDARY = "boundary";

	private static final Comparator<int[]> BY_INDEX = Comparator.comparingInt(p -> p[0]);
	private static final Comparator<int[]> BY_DISTANCE_THEN_INDEX =
			Comparator.<int[]>comparingInt(p -> p[1]).thenComparingInt(p -> p[0]);

	private final List<V> targets;
	private final List<String> kinds;
	private final Map<V, int[][]> pairs;
	/**
	 * Callee → callers in signature order, kept so {@link #paths} repeats the same searches;
	 * {@code null} after {@link #releaseCallers}.
	 */
	private Map<V, List<V>> callers;
	private final Function<V, String> signature;

	private TargetDistances(List<V> targets, List<String> kinds, Map<V, int[][]> pairs,
			Map<V, List<V>> callers, Function<V, String> signature) {
		this.targets = Collections.unmodifiableList(targets);
		this.kinds = Collections.unmodifiableList(kinds);
		this.pairs = Collections.unmodifiableMap(pairs);
		this.callers = callers;
		this.signature = signature;
	}

	/**
	 * Drops the callers map, a copy of the call graph's reverse edges that only {@link #paths}
	 * reads, so it is not held through the WTG. The distances and pairs stay readable.
	 */
	public void releaseCallers() {
		callers = null;
	}

	/** Targets in index order. */
	public List<V> targets() {
		return targets;
	}

	/** Kind of the target at each index ({@value #KIND_DIRECT} or {@value #KIND_BOUNDARY}). */
	public List<String> kinds() {
		return kinds;
	}

	/** Pairs {@code [i, d]} of {@code m}, sorted by {@code i}; empty when none is within reach. */
	public int[][] pairs(V m) {
		int[][] p = pairs.get(m);
		return p != null ? p : new int[0][];
	}

	/** Number of methods that carry at least one pair. */
	public int methodsWithPairs() {
		return pairs.size();
	}

	/**
	 * One method's pairs as a compact document writes them (INV-ANA-85): the pairs
	 * {@code [i, d]} with {@code d <= }{@value #COMPACT_WEIGHED_MAX}, plus the pairs whose rank
	 * in the order {@code (d, i)} is below {@value #COMPACT_K}, sorted by {@code i}.
	 *
	 * <p>The two values are the MOP derive's ({@code aperv} D15/D18): the APE-RV jar weighs a
	 * pair only up to {@code d = 3}, and {@code activityDist} keeps the 3 nearest targets. The
	 * reduction is exact for that consumer. A dropped pair has {@value #COMPACT_K} targets ahead
	 * of it in its own method, and those targets stay ahead of it after any merge by the
	 * minimum distance, so it can never be among the nearest ones the derive keeps.
	 *
	 * <p>No merge step is needed: each target's reverse search records one depth per method,
	 * so a method's array holds at most one pair per target. Since the nearest pair always
	 * survives, a non-empty input gives a non-empty output, and a method carries
	 * {@code targetDistances} in compact output exactly when it does in full output.
	 *
	 * @param pairs pairs {@code [i, d]} of one method; not modified
	 * @return the kept pairs sorted by {@code i}; never null, empty for an empty input
	 */
	public static int[][] compact(int[][] pairs) {
		int[][] byDistance = pairs.clone();
		Arrays.sort(byDistance, BY_DISTANCE_THEN_INDEX);
		List<int[]> kept = new ArrayList<>(byDistance.length);
		for (int rank = 0; rank < byDistance.length; rank++) {
			int[] pair = byDistance[rank];
			if (rank < COMPACT_K || pair[1] <= COMPACT_WEIGHED_MAX) {
				kept.add(pair);
			}
		}
		kept.sort(BY_INDEX);
		return kept.toArray(new int[0][]);
	}

	/**
	 * Distances over the Soot call graph. {@code targets} are the resolved target methods the
	 * reachability search was seeded with.
	 */
	public static TargetDistances<SootMethod> compute(CallGraph cg, ReachabilityIndex index,
			Map<SootClass, List<SootMethod>> appClasses, Set<SootMethod> targets) {
		Set<SootMethod> appMethods = new HashSet<>();
		for (List<SootMethod> ms : appClasses.values()) {
			appMethods.addAll(ms);
		}
		Map<SootMethod, Set<SootMethod>> callers = new HashMap<>();
		Iterator<Edge> it = cg.iterator();
		while (it.hasNext()) {
			Edge e = it.next();
			SootMethod src = e.src();
			SootMethod tgt = e.tgt();
			if (src == null || tgt == null || src.equals(tgt)) {
				continue;
			}
			callers.computeIfAbsent(tgt, k -> new HashSet<>()).add(src);
		}
		return compute(callers, appMethods, index.directlyReachesTargetMethods(), targets,
				SootMethod::getSignature);
	}

	/**
	 * Distances over a callee → callers map (self-loops already dropped).
	 *
	 * @param direct the {@code directlyReachesTarget} set; only its app members become targets
	 * @param targets the resolved target methods; the library ones seed the boundary search
	 */
	public static <V> TargetDistances<V> compute(Map<V, Set<V>> callerSets, Set<V> appMethods,
			Set<V> direct, Set<V> targets, Function<V, String> signature) {
		Comparator<V> bySignature = Comparator.comparing(signature);
		// Sorted once here; both passes walk these lists (INV-ANA-92).
		Map<V, List<V>> callers = new HashMap<>(callerSets.size() * 2);
		for (Map.Entry<V, Set<V>> e : callerSets.entrySet()) {
			List<V> sorted = new ArrayList<>(e.getValue());
			sorted.sort(bySignature);
			callers.put(e.getKey(), sorted);
		}
		List<V> c = new ArrayList<>();
		for (V m : direct) {
			if (appMethods.contains(m)) {
				c.add(m);
			}
		}
		c.sort(bySignature);

		Set<V> libReach = libraryReachesTarget(callers, appMethods, targets);
		Set<V> cSet = new HashSet<>(c);
		Set<V> bNotC = new HashSet<>();
		for (V lib : libReach) {
			if (targets.contains(lib)) {
				continue;
			}
			for (V p : callers.getOrDefault(lib, Collections.emptyList())) {
				if (appMethods.contains(p) && !cSet.contains(p)) {
					bNotC.add(p);
				}
			}
		}
		List<V> b = new ArrayList<>(bNotC);
		b.sort(bySignature);

		List<V> all = new ArrayList<>(c);
		all.addAll(b);
		List<String> kinds = new ArrayList<>(all.size());
		for (int i = 0; i < all.size(); i++) {
			kinds.add(i < c.size() ? KIND_DIRECT : KIND_BOUNDARY);
		}

		// Targets are visited in index order, so each method's pairs come out sorted by index.
		Map<V, List<int[]>> collected = new HashMap<>();
		for (int i = 0; i < all.size(); i++) {
			for (Map.Entry<V, Integer> e : reverseBfs(callers, all.get(i), null).entrySet()) {
				if (appMethods.contains(e.getKey())) {
					collected.computeIfAbsent(e.getKey(), k -> new ArrayList<>())
							.add(new int[] { i, e.getValue() });
				}
			}
		}
		Map<V, int[][]> pairs = new HashMap<>(collected.size() * 2);
		for (Map.Entry<V, List<int[]>> e : collected.entrySet()) {
			pairs.put(e.getKey(), e.getValue().toArray(new int[0][]));
		}
		return new TargetDistances<>(all, kinds, pairs, callers, signature);
	}

	/**
	 * The written-pair predicate of compact output, for {@link #paths}: true for the pairs
	 * {@link #compact} keeps of {@code pairs(m)}. It reduces a method's pairs once and reuses the
	 * result while it is asked about the same method, as {@link #paths} asks about one method's
	 * pairs in a row. Not thread-safe.
	 */
	public BiPredicate<V, int[]> keptByCompact() {
		return new BiPredicate<V, int[]>() {
			private V method;
			private Set<Integer> keptTargets;

			@Override
			public boolean test(V m, int[] pair) {
				if (keptTargets == null || !m.equals(method)) {
					method = m;
					keptTargets = new HashSet<>();
					for (int[] kept : compact(pairs(m))) {
						keptTargets.add(kept[0]);
					}
				}
				// A method holds at most one pair per target, so the index identifies the pair.
				return keptTargets.contains(pair[0]);
			}
		};
	}

	/**
	 * Distance paths of the written pairs (INV-ANA-91, -92, -93), in a second pass.
	 *
	 * <p>For each target named by a written pair, the target's reverse search runs again, the
	 * same one {@code compute} ran, and records for each method the callee from which the search
	 * first visited it. From the method of each written pair {@code [i, d]} the recorded callees
	 * lead to the target in {@code d} steps; each step {@code [i, v, n]} on those chains is kept
	 * once. One target's search is held at a time, so the memory is that search plus the steps.
	 *
	 * @param written true exactly for the pairs the output mode writes on a method: every pair
	 *     in full output, {@link #keptByCompact()} in compact output
	 * @return the steps over the table of the methods that occur in them
	 * @throws IllegalStateException when the repeated search does not find a written pair's
	 *     method at the pair's distance, which would mean the two passes walked different graphs
	 */
	public DistancePaths paths(BiPredicate<V, int[]> written) {
		if (callers == null) {
			throw new IllegalStateException("callers released before the path pass");
		}
		// The written pairs grouped by target: method → distance, one map per named target.
		List<Map<V, Integer>> byTarget = new ArrayList<>(
				Collections.<Map<V, Integer>>nCopies(targets.size(), null));
		for (Map.Entry<V, int[][]> e : pairs.entrySet()) {
			for (int[] pair : e.getValue()) {
				if (written.test(e.getKey(), pair)) {
					Map<V, Integer> methods = byTarget.get(pair[0]);
					if (methods == null) {
						methods = new HashMap<>();
						byTarget.set(pair[0], methods);
					}
					methods.put(e.getKey(), pair[1]);
				}
			}
		}

		List<Step<V>> steps = new ArrayList<>();
		Set<V> vertices = new HashSet<>();
		for (int i = 0; i < byTarget.size(); i++) {
			Map<V, Integer> chainStarts = byTarget.get(i);
			if (chainStarts == null) {
				continue;
			}
			byTarget.set(i, null);
			Map<V, V> callee = new HashMap<>();
			Map<V, Integer> dist = reverseBfs(callers, targets.get(i), callee);
			// A method's chain is fixed by its recorded callee, so a chain that reaches a method
			// already walked for this target continues with steps already kept.
			Set<V> walked = new HashSet<>();
			for (Map.Entry<V, Integer> start : chainStarts.entrySet()) {
				V v = start.getKey();
				int d = start.getValue();
				Integer found = dist.get(v);
				if (found == null || found != d) {
					throw new IllegalStateException("distance path: " + signature.apply(v)
							+ " carries [" + i + ", " + d + "] but the repeated search found "
							+ found);
				}
				for (int k = d; k > 0 && walked.add(v); k--) {
					V n = callee.get(v);
					steps.add(new Step<>(i, v, n));
					vertices.add(v);
					vertices.add(n);
					v = n;
				}
			}
		}

		List<V> ordered = new ArrayList<>(vertices);
		ordered.sort(Comparator.comparing(signature));
		Map<V, Integer> position = new HashMap<>(ordered.size() * 2);
		List<String> methods = new ArrayList<>(ordered.size());
		for (V v : ordered) {
			position.put(v, methods.size());
			methods.add(signature.apply(v));
		}
		int[][] out = new int[steps.size()][];
		for (int s = 0; s < out.length; s++) {
			Step<V> step = steps.get(s);
			out[s] = new int[] { step.target, position.get(step.caller),
					position.get(step.callee) };
		}
		// At most one step per (i, v), so this order is total.
		Arrays.sort(out, Comparator.<int[]>comparingInt(p -> p[0]).thenComparingInt(p -> p[1]));
		return new DistancePaths(methods, out);
	}

	/**
	 * On the way to target {@code target}, {@code caller} calls {@code callee}, one call closer.
	 * A class, not a record: the build's ClassIndex annotation processor rejects records.
	 */
	private static final class Step<V> {
		final int target;
		final V caller;
		final V callee;

		Step(int target, V caller, V callee) {
			this.target = target;
			this.caller = caller;
			this.callee = callee;
		}
	}

	/**
	 * Reverse BFS from {@code seed}, levels up to {@link #DIST_MAX}; returns vertex → distance.
	 * When {@code callee} is not null, it receives, for each visited vertex other than the seed,
	 * the vertex from which the search first visited it.
	 */
	private static <V> Map<V, Integer> reverseBfs(Map<V, List<V>> callers, V seed,
			Map<V, V> callee) {
		Map<V, Integer> dist = new HashMap<>();
		ArrayDeque<V> queue = new ArrayDeque<>();
		dist.put(seed, 0);
		queue.add(seed);
		while (!queue.isEmpty()) {
			V cur = queue.poll();
			int d = dist.get(cur);
			if (d == DIST_MAX) {
				continue;
			}
			for (V p : callers.getOrDefault(cur, Collections.emptyList())) {
				if (!dist.containsKey(p)) {
					dist.put(p, d + 1);
					if (callee != null) {
						callee.put(p, cur);
					}
					queue.add(p);
				}
			}
		}
		return dist;
	}

	/**
	 * Library methods from which a library target is reachable along call-graph paths through
	 * library methods only; the library targets themselves are included.
	 */
	private static <V> Set<V> libraryReachesTarget(Map<V, List<V>> callers, Set<V> appMethods,
			Set<V> targets) {
		Set<V> seen = new HashSet<>();
		ArrayDeque<V> queue = new ArrayDeque<>();
		for (V t : targets) {
			if (!appMethods.contains(t) && seen.add(t)) {
				queue.add(t);
			}
		}
		while (!queue.isEmpty()) {
			for (V p : callers.getOrDefault(queue.poll(), Collections.emptyList())) {
				if (!appMethods.contains(p) && seen.add(p)) {
					queue.add(p);
				}
			}
		}
		return seen;
	}
}
