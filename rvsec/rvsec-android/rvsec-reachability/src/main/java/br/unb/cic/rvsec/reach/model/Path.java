package br.unb.cic.rvsec.reach.model;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

import soot.SootMethod;

public class Path {

	private final List<String> path;

	public Path(List<SootMethod> path) {
		this.path = path.stream().map(SootMethod::getSignature).collect(Collectors.toList());
	}

//	private boolean isValid(List<SootMethod> pathToCheck) {
//		return pathToCheck != null && pathToCheck.size() > 1;
//	}

	public List<String> getPath() {
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
		return String.join(", ", path);
	}
}
