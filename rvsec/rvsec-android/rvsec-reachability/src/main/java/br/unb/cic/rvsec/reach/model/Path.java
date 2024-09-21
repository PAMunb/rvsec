package br.unb.cic.rvsec.reach.model;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

import soot.SootMethod;

public class Path {

	private List<SootMethod> path;

	public Path(List<SootMethod> path) {
//		if (!isValid(path)) {
//			throw new RuntimeException("Invalid path: " + path);
//		}
		this.path = path;
	}

//	private boolean isValid(List<SootMethod> pathToCheck) {
//		return pathToCheck != null && pathToCheck.size() > 1;
//	}

	public List<SootMethod> getPath() {
		return path;
	}

	@Override
	public int hashCode() {
		return Objects.hash(path);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Path other = (Path) obj;
		return Objects.equals(path, other.path);
	}

	@Override
	public String toString() {
		return path.stream().map(SootMethod::getSignature).collect(Collectors.joining(", "));
	}
}
