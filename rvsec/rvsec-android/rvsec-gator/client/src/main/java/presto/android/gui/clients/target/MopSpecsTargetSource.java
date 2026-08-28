package presto.android.gui.clients.target;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import javamop.util.MOPException;

/**
 * Loads target methods from a JavaMOP specs directory by delegating to
 * {@link JavamopFacade#listUsedMethods(String, boolean)}.
 *
 * <p>Almost every emitted {@link TargetMethod} carries
 * {@link TargetMethod.MatchPolicy#LENIENT}, because the historical MOP→Soot
 * resolution matched on (className, methodName) only — preserving that
 * contract byte-for-byte is INV-ANA-35.
 *
 * <p>The one exception is a target whose owner the extractor could resolve
 * <em>only</em> through the implicit {@code java.lang} package. Those are
 * emitted {@link TargetMethod.MatchPolicy#STRICT}, and the two rules are one
 * decision rather than two: resolving such an owner leniently would make
 * {@code String#valueOf} match every overload — 74 call sites over 3 corpus
 * APKs of which 17 are the woven signatures — so the implicit resolution is
 * admissible only because the strictness bounds it. Note what the rule is
 * keyed on: the <em>route</em> the owner resolved by, not the package it
 * lives in. An owner in {@code java.lang} that its own spec imports resolves
 * earlier and stays LENIENT, which matters because such pointcuts routinely
 * declare {@code (..)} parameters that STRICT could never match.
 */
public final class MopSpecsTargetSource implements TargetMethodSource {

	private final String mopDir;

	public MopSpecsTargetSource(String mopDir) {
		this.mopDir = mopDir;
	}

	@Override
	public Set<TargetMethod> load() {
		try {
			JavamopFacade facade = new JavamopFacade();
			Set<MopMethod> mopMethods = facade.listUsedMethods(mopDir, false);
			Set<TargetMethod> targets = new HashSet<>(mopMethods.size());
			for (MopMethod m : mopMethods) {
				// The two flags MUST cross this boundary. They are the only record that the
				// pointcut declared its owner by hierarchy (`Collection+`) or its method name
				// by pattern (`add*`); dropping them here would silently put every such target
				// back on the exact-FQN path that never matched anything (INV-ANA-41).
				TargetMethod.MatchPolicy policy = m.isOwnerFromImplicitSeed()
						? TargetMethod.MatchPolicy.STRICT
						: TargetMethod.MatchPolicy.LENIENT;
				if (policy == TargetMethod.MatchPolicy.STRICT) {
					warnIfParametersCannotMatch(m.getClassName(), m.getName(), m.getParameters());
				}
				targets.add(new TargetMethod(
						m.getClassName(),
						m.getName(),
						m.getParameters(),
						m.getSignature(),
						policy,
						m.isIncludeSubtypes(),
						m.isNameIsPattern()));
			}
			long strict = targets.stream()
					.filter(t -> t.getPolicy() == TargetMethod.MatchPolicy.STRICT)
					.count();
			System.out.println("[MopSpecsTargetSource] Loaded " + targets.size()
					+ " MOP signatures from " + mopDir + " (" + strict
					+ " STRICT — owner resolved through the implicit java.lang package)");
			return targets;
		} catch (MOPException e) {
			System.err.println("[MopSpecsTargetSource] ERROR loading MOP specs: " + e.getMessage());
			return Collections.emptySet();
		}
	}

	/**
	 * A STRICT target is compared against the full Soot signature, so every parameter must be a
	 * type name Soot will report. A pointcut that wrote {@code ..}, a bare {@code *}, a subtype
	 * operator, or a name nothing resolved yields a target that matches nothing at all — the same
	 * silent-zero shape (INV-ANA-40, RISK-013) this component exists to end, arriving through the
	 * parameter list instead of the owner. It is reported rather than repaired here: the target
	 * still loads, and the fix belongs in the spec or the extractor.
	 */
	private static final java.util.Set<String> PRIMITIVE_TYPES = java.util.Set.of(
			"boolean", "byte", "char", "short", "int", "long", "float", "double", "void");

	private static void warnIfParametersCannotMatch(String className, String methodName,
			java.util.List<String> params) {
		for (String p : params) {
			// A primitive is a complete Soot type name with no package, so it is expressible;
			// everything else without a dot is a simple name nothing resolved.
			String base = p.endsWith("]") ? p.substring(0, p.indexOf('[')) : p;
			if (PRIMITIVE_TYPES.contains(base)) {
				continue;
			}
			if ("..".equals(p) || "*".equals(p) || p.indexOf('+') >= 0 || p.indexOf('<') >= 0
					|| p.indexOf('*') >= 0 || p.indexOf('.') < 0) {
				System.out.println("[MopSpecsTargetSource] WARN STRICT target " + className + "#"
						+ methodName + params + " declares the parameter '" + p + "', which is not"
						+ " a resolvable Soot type name; this target will match no call site");
				return;
			}
		}
	}
}
