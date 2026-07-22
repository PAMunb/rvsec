package presto.android.gui.clients.target;

import java.util.HashSet;
import java.util.Set;

import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

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
 *       are excluded; the bytecode scanner remains LENIENT by
 *       construction (see design.md §D7).</li>
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
	 */
	public static Set<SootMethod> resolveInScene(Set<TargetMethod> targets) {
		Set<SootMethod> resolved = new HashSet<>();
		for (SootClass cls : Scene.v().getClasses()) {
			String fqn = cls.getName();
			for (SootMethod method : cls.getMethods()) {
				String name = method.getName();
				for (TargetMethod t : targets) {
					if (!t.getClassName().equals(fqn) || !t.getMethodName().equals(name)) {
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
