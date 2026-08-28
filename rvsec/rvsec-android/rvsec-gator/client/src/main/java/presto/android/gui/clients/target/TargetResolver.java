package presto.android.gui.clients.target;

import java.util.HashSet;
import java.util.Set;

import soot.FastHierarchy;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Type;

/**
 * Resolves a {@link TargetMethodSource}'s output into the matching set of
 * Soot {@link SootMethod} instances in the current {@link Scene}.
 *
 * <p>Two policies coexist per the {@link TargetMethod#getPolicy} field:
 * <ul>
 *   <li>{@link TargetMethod.MatchPolicy#LENIENT} — match by
 *       {@code (className, methodName)} only. Every overload becomes a
 *       seed, preserving gh57 behavior byte-for-byte (INV-ANA-35).</li>
 *   <li>{@link TargetMethod.MatchPolicy#STRICT} — match by class+name
 *       and the parameter type list. Overloads with mismatching params
 *       are excluded. The bytecode scanner honours the same policy — it
 *       used to be lenient unconditionally, which made a STRICT target
 *       strict here and lenient there (design D13).</li>
 * </ul>
 *
 * <p>Stateless; instances are cheap to construct and not reused.
 */
public final class TargetResolver {

	private final TargetMethodSource source;

	public TargetResolver(TargetMethodSource source) {
		this.source = source;
	}

	public Set<TargetMethod> targets() {
		return source.load();
	}

	/**
	 * Resolve the supplied target set to {@link SootMethod}s in {@link Scene#v()}.
	 *
	 * <p>Static so {@code RvsecAnalysisClient}'s stepping-stone code path
	 * (which still keeps {@code Set<MopMethod>} alive until Group 6) can
	 * call it without re-constructing a source.
	 *
	 * <p>The {@code matching} helper is supplied rather than created here because the direct
	 * bytecode scan is the second match point and must share the same resolved-owner cache:
	 * resolving an owner twice would re-log the degrade warnings and could invalidate a
	 * {@code FastHierarchy} the scan is already holding.
	 *
	 * <p>Owner force-resolution happens <b>before</b> the {@code FastHierarchy} is obtained,
	 * and the instance is not cached beyond this call. Note also that
	 * {@code TargetMatching.forceResolveTargets} resolves at SIGNATURES, not HIERARCHY: the
	 * {@code cls.getMethods()} call in the loop below opens with {@code checkLevel(SIGNATURES)},
	 * so introducing an owner into the Scene below that level would turn a missing target into
	 * a crash on the next pass.
	 */
	public static Set<SootMethod> resolveInScene(Set<TargetMethod> targets, TargetMatching matching) {
		Set<SootMethod> resolved = new HashSet<>();
		if (targets.isEmpty()) {
			return resolved;
		}
		matching.forceResolveTargets(targets);
		FastHierarchy hierarchy = Scene.v().getOrMakeFastHierarchy();

		for (SootClass cls : Scene.v().getClasses()) {
			Type declaringType = cls.getType();
			for (SootMethod method : cls.getMethods()) {
				String name = method.getName();
				for (TargetMethod t : targets) {
					// Name first, owner second — the widened owner predicate costs a hierarchy
					// query where the old exact-FQN check cost a string compare, and this loop
					// is Scene.getClasses() x methods x targets.
					if (!matching.matches(declaringType, name, t, hierarchy)) {
						continue;
					}
					if (t.getPolicy() == TargetMethod.MatchPolicy.LENIENT) {
						resolved.add(method);
						break;
					}
					if (paramsMatch(method, t)) {
						resolved.add(method);
						break;
					}
				}
			}
		}
		return resolved;
	}

	/** Package-private for unit testing. */
	static boolean paramsMatch(SootMethod method, TargetMethod target) {
		int expected = target.getParams().size();
		if (method.getParameterCount() != expected) {
			return false;
		}
		for (int i = 0; i < expected; i++) {
			String actual = method.getParameterType(i).toString();
			String want = target.getParams().get(i);
			if (!actual.equals(want)) {
				return false;
			}
		}
		return true;
	}
}
