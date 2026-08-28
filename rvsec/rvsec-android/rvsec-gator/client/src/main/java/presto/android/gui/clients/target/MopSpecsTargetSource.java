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
}
