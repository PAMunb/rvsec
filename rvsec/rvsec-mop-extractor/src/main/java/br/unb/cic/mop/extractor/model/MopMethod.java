package br.unb.cic.mop.extractor.model;

import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.StringJoiner;

public class MopMethod {

	private String className;
	private String name;
	private List<String> parameters;
	private String signature;
	/** Owner declared with the AspectJ '+' subtype operator (e.g. {@code Collection+}). */
	private boolean includeSubtypes;
	/** Method name declared with a trailing '*' (e.g. {@code add*}), or the bare '*'. */
	private boolean nameIsPattern;
	/**
	 * Owner resolved only through the implicit {@code java.lang} package — neither an explicit
	 * import nor a wildcard-import package answered for it. Recorded because it decides the
	 * match policy: such a target is emitted STRICT, so the implicit resolution cannot widen
	 * what the spec accuses. It is a property of the *route*, not of the package: an owner in
	 * {@code java.lang} that its own spec imports resolves at the first step and is unaffected.
	 */
	private boolean ownerFromImplicitSeed;

	public MopMethod(String className, String name, List<String> parameters, String signature,
			boolean includeSubtypes, boolean nameIsPattern, boolean ownerFromImplicitSeed) {
		this.className = className;
		this.name = name;
		this.parameters = parameters;
		this.signature = signature;
		this.includeSubtypes = includeSubtypes;
		this.nameIsPattern = nameIsPattern;
		this.ownerFromImplicitSeed = ownerFromImplicitSeed;
	}

	public String getClassName() {
		return className;
	}

	public String getName() {
		return name;
	}

	public List<String> getParameters() {
		return Collections.unmodifiableList(parameters);
	}

	public String getParametersAsString() {
		StringJoiner joiner = new StringJoiner(",", "(", ")");
		parameters.forEach(joiner::add);
		return joiner.toString();
	}

	public String getSignature() {
		return signature;
	}

	public boolean isIncludeSubtypes() {
		return includeSubtypes;
	}

	public boolean isNameIsPattern() {
		return nameIsPattern;
	}

	public boolean isOwnerFromImplicitSeed() {
		return ownerFromImplicitSeed;
	}

	// All three flags participate in identity, but they do not all earn it, and the difference
	// is worth stating rather than leaving as folklore.
	//
	// `includeSubtypes` and `nameIsPattern` are derivable from fields already here: `signature`
	// is the printed MethodPattern, which carries the owner's '+' and the name's '*' verbatim —
	// measured, `Iterator+.next` prints "* Iterator+.next()" against "* Iterator.next(..)", so
	// those two could never have collapsed. Including them is harmless and keeps identity
	// aligned with the accessors; it is not what prevents the collapse.
	//
	// `ownerFromImplicitSeed` is the one that earns its place: it is NOT derivable. Two specs in
	// one directory writing the same pointcut, one importing the owner's package and one not,
	// produce identical className/name/parameters/signature and differ only in the route the
	// owner resolved by — which decides the match policy downstream. Without the flag one of the
	// two would be dropped by the HashSet and the surviving policy would be whichever won the
	// insertion race.
	@Override
	public int hashCode() {
		return Objects.hash(className, name, parameters, signature, includeSubtypes, nameIsPattern,
				ownerFromImplicitSeed);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		MopMethod other = (MopMethod) obj;
		return Objects.equals(className, other.className) && Objects.equals(name, other.name) && Objects.equals(parameters, other.parameters)
				&& Objects.equals(signature, other.signature) && includeSubtypes == other.includeSubtypes
				&& nameIsPattern == other.nameIsPattern && ownerFromImplicitSeed == other.ownerFromImplicitSeed;
	}

	@Override
	public String toString() {
		return String.format(
				"MopMethod [className=%s, name=%s, parameters=%s, signature=%s, includeSubtypes=%s, nameIsPattern=%s, ownerFromImplicitSeed=%s]",
				className, name, parameters, signature, includeSubtypes, nameIsPattern, ownerFromImplicitSeed);
	}

}
