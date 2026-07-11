package br.unb.cic.rvsec.reach.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

import soot.SootMethod;
import soot.Type;

public class RvsecMethod {
	private final String methodName;
	private final List<String> methodParams;
	private final String methodSignature;
	private final int modifiers;

	// is reachable from an entrypoint (methods from activities)
	private boolean reachable = false;

	// reaches an method declared in MOP specs
	private boolean reachesTarget = false;

	// true if directly calls a MOP method
	// false if the MOP method is reached by a library/system
	private boolean directlyReachesTarget = false;

	private Set<String> targetMethodsReached = new HashSet<>();

	// one of the possible paths (from an endpoint and this method)
	private Path possiblePath;

	// all paths (from this method to a mop method)
	//TODO renomear
	private final List<Path> possiblePathToMop = new ArrayList<>();

	public RvsecMethod(SootMethod method) {
		this.methodName = method.getName();
		this.methodParams = method.getParameterTypes().stream()
				.map(Type::toString)
				.collect(Collectors.toList());
		this.methodSignature = method.getSignature();
		this.modifiers = method.getModifiers();
	}

	public String getMethodName() {
		return methodName;
	}

	public List<String> getMethodParams() {
		return methodParams;
	}

	public String getMethodSignature() {
		return methodSignature;
	}

	public int getModifiers() {
		return modifiers;
	}

	public boolean isReachable() {
		return reachable;
	}

	public boolean isReachesMop() {
		return reachesTarget;
	}

	public boolean reachesTarget() {
		return reachesTarget;
	}

	public boolean isDirectlyReachesMop() {
		return directlyReachesTarget;
	}

	public boolean directlyReachesTarget() {
		return directlyReachesTarget;
	}

	public Set<String> getMopMethodsReached() {
		return targetMethodsReached;
	}

	public void setReachable(boolean reachable) {
		this.reachable = reachable;
	}

	public void setReachesMop(boolean reachesTarget) {
		this.reachesTarget = reachesTarget;
	}

	public void setDirectlyReachesMop(boolean directlyReachesTarget) {
		this.directlyReachesTarget = directlyReachesTarget;
	}

	public void setPossiblePath(Path path) {
		this.possiblePath = path;
	}

	public Path getPossiblePath() {
		return possiblePath;
	}

	public List<Path> getPossiblePathToMop() {
		return possiblePathToMop;
	}

	public void addPathToMop(Path path) {
		possiblePathToMop.add(path);
	}

	private String allPathsToMop() {
		return possiblePathToMop.stream()
			.map(p -> "path=["+p+"]")
			.collect(Collectors.joining(", "));
	}

	public void addMopMethodReached(String mopMethod) {
		targetMethodsReached.add(mopMethod);
	}

	@Override
	public int hashCode() {
		return Objects.hash(directlyReachesTarget, methodName, methodParams, methodSignature, modifiers, possiblePath, possiblePathToMop, reachable, reachesTarget);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		RvsecMethod other = (RvsecMethod) obj;
		return directlyReachesTarget == other.directlyReachesTarget && Objects.equals(methodName, other.methodName) && Objects.equals(methodParams, other.methodParams) && Objects.equals(methodSignature, other.methodSignature) && modifiers == other.modifiers
				&& Objects.equals(possiblePath, other.possiblePath) && Objects.equals(possiblePathToMop, other.possiblePathToMop) && reachable == other.reachable && reachesTarget == other.reachesTarget;
	}

	@Override
	public String toString() {
		return String.format("RvsecMethod [methodName=%s, methodSignature=%s, modifiers=%s, reachable=%s, reachesTarget=%s, directlyReachesTarget=%s, possiblePath=%s, possiblePathToMop=%s]", methodName, methodSignature, modifiers, reachable, reachesTarget,
				directlyReachesTarget, possiblePath, allPathsToMop());
	}

}
