package presto.android.gui.clients.target;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import javamop.util.MOPException;

/**
 * Loads target methods from a JavaMOP specs directory by delegating to
 * {@link JavamopFacade#listUsedMethods(String, boolean)}. Every emitted
 * {@link TargetMethod} carries {@link TargetMethod.MatchPolicy#LENIENT}
 * because the historical MOP→Soot resolution matched on
 * (className, methodName) only — preserving that contract byte-for-byte
 * is INV-ANA-35.
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
				targets.add(new TargetMethod(
						m.getClassName(),
						m.getName(),
						m.getParameters(),
						m.getSignature(),
						TargetMethod.MatchPolicy.LENIENT));
			}
			System.out.println("[MopSpecsTargetSource] Loaded " + targets.size()
					+ " MOP signatures from " + mopDir);
			return targets;
		} catch (MOPException e) {
			System.err.println("[MopSpecsTargetSource] ERROR loading MOP specs: " + e.getMessage());
			return Collections.emptySet();
		}
	}
}
