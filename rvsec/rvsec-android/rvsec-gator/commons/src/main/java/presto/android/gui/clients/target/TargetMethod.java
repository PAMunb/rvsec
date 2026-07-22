package presto.android.gui.clients.target;

import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Canonical, source-agnostic representation of a method that GATOR's
 * reachability analysis treats as a target. Replaces the MOP-specific
 * coupling that used to live in {@code RvsecAnalysisClient}: a target can
 * originate from JavaMOP specs (LENIENT class+name match) or from an
 * external signature file (STRICT full-signature match).
 *
 * <p>Immutable by construction (all fields {@code final}, no setters).
 * The match policy is per-instance: a {@code SignatureFileTargetSource}
 * may emit some STRICT entries and some LENIENT ones (e.g., wildcard
 * parameter lists), so the policy travels with the target, not with the
 * source.
 */
public final class TargetMethod {

	public enum MatchPolicy {
		/** Match on (className, methodName) only — original MOP behavior. */
		LENIENT,
		/** Match on the full Soot signature. */
		STRICT
	}

	private final String className;
	private final String methodName;
	private final List<String> params;
	private final String signature;
	private final MatchPolicy policy;

	public TargetMethod(String className, String methodName, List<String> params,
			String signature, MatchPolicy policy) {
		this.className = Objects.requireNonNull(className, "className");
		this.methodName = Objects.requireNonNull(methodName, "methodName");
		this.params = Collections.unmodifiableList(Objects.requireNonNull(params, "params"));
		this.signature = signature;
		this.policy = Objects.requireNonNull(policy, "policy");
	}

	public String getClassName() {
		return className;
	}

	public String getMethodName() {
		return methodName;
	}

	public List<String> getParams() {
		return params;
	}

	public String getSignature() {
		return signature;
	}

	public MatchPolicy getPolicy() {
		return policy;
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) return true;
		if (!(o instanceof TargetMethod)) return false;
		TargetMethod that = (TargetMethod) o;
		return Objects.equals(className, that.className)
				&& Objects.equals(methodName, that.methodName)
				&& Objects.equals(params, that.params)
				&& Objects.equals(signature, that.signature)
				&& policy == that.policy;
	}

	@Override
	public int hashCode() {
		return Objects.hash(className, methodName, params, signature, policy);
	}

	@Override
	public String toString() {
		return "TargetMethod[" + className + "." + methodName + params + " policy=" + policy + "]";
	}
}
