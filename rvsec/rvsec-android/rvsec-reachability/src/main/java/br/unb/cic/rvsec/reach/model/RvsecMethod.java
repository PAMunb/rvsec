package br.unb.cic.rvsec.reach.model;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

import soot.SootMethod;

public class RvsecMethod {
	private final String methodName;
	private final String methodSignature;
	private int modifiers;

	// is reachable from an entrypoint (methods from activities)
	private boolean reachable = false;

	// reaches an method declared in MOP specs
	private boolean reachesMop = false;

	// true if directly calls a MOP method
	// false if the MOP method is reached by a library
	private boolean directlyReachesMop = false;

	// one of the possible paths (from an endpoint and this method)
	private Path possiblePath;

	// all paths (from this method to a mop method)
	private List<Path> possiblePathToMop = new ArrayList<>();

	public RvsecMethod(SootMethod method) {
		this.methodName = method.getName();
		this.methodSignature = method.getSignature();
		this.modifiers = method.getModifiers();
	}

	public String getMethodName() {
		return methodName;
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
		return reachesMop;
	}

	public boolean reachesMop() {
		return reachesMop;
	}

	public boolean isDirectlyReachesMop() {
		return directlyReachesMop;
	}

	public boolean directlyReachesMop() {
		return directlyReachesMop;
	}

	public void setReachable(boolean reachable) {
		this.reachable = reachable;
	}

	public void setReachesMop(boolean reachesMop) {
		this.reachesMop = reachesMop;
	}

	public void setDirectlyReachesMop(boolean directlyReachesMop) {
		this.directlyReachesMop = directlyReachesMop;
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

//	public void setPossiblePathToMop(List<Path> possiblePathToMop) {
//		this.possiblePathToMop = possiblePathToMop;
//	}
	public void addPathToMop(Path path) {
		possiblePathToMop.add(path);
	}

	@Override
	public int hashCode() {
		return Objects.hash(directlyReachesMop, methodName, methodSignature, modifiers, possiblePath, possiblePathToMop, reachable, reachesMop);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		RvsecMethod other = (RvsecMethod) obj;
		return directlyReachesMop == other.directlyReachesMop && Objects.equals(methodName, other.methodName) && Objects.equals(methodSignature, other.methodSignature) && modifiers == other.modifiers
				&& Objects.equals(possiblePath, other.possiblePath) && Objects.equals(possiblePathToMop, other.possiblePathToMop) && reachable == other.reachable && reachesMop == other.reachesMop;
	}

	

}
