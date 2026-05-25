package presto.android.gui.clients.target;

import java.util.Set;

/**
 * Polymorphic loader for the set of methods GATOR should treat as
 * reachability targets. Implementations decide how to read the targets
 * (JavaMOP specs directory, signature file, hard-coded list, ...) and
 * what {@link TargetMethod.MatchPolicy} each emitted target carries.
 *
 * <p>Returning a {@link Set} (rather than a {@link java.util.List})
 * eliminates duplicate targets at the source boundary; downstream
 * resolution treats each target once.
 */
public interface TargetMethodSource {

	Set<TargetMethod> load();
}
