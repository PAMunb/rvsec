package br.unb.cic.rvsec.reach.writer.json;

import java.util.ArrayList;
import java.util.List;

import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecMethod;

public class RvsecMethodJson {
	private String methodName;
	private String methodSignature;
	private int modifiers;

	// is reachable from an entrypoint (methods from activities)
	private boolean reachable = false;

	// reaches an method declared in MOP specs
	private boolean reachesMop = false;

	// true if directly calls a MOP method
	// false if the MOP method is reached by a library/system
	private boolean directlyReachesMop = false;

	// one of the possible paths (from an endpoint and this method)
	private List<String> possiblePath;

	// all paths (from this method to a mop method)
	private List<List<String>> allPathsToMop;

	public RvsecMethodJson(RvsecMethod method) {
		this.methodName = method.getMethodName();
		this.methodSignature = method.getMethodSignature();
		this.modifiers = method.getModifiers();
		this.reachable = method.isReachable();
		this.reachesMop = method.reachesMop();
		this.directlyReachesMop = method.directlyReachesMop();

		if (method.getPossiblePath() != null) {
			this.possiblePath = method.getPossiblePath().getPath();
		}

		if (method.getPossiblePathToMop() != null) {
			allPathsToMop = new ArrayList<>();
			for (Path path : method.getPossiblePathToMop()) {
				allPathsToMop.add(path.getPath());
			}
		}
	}

	public String getMethodName() {
		return methodName;
	}

	public void setMethodName(String methodName) {
		this.methodName = methodName;
	}

	public String getMethodSignature() {
		return methodSignature;
	}

	public void setMethodSignature(String methodSignature) {
		this.methodSignature = methodSignature;
	}

	public int getModifiers() {
		return modifiers;
	}

	public void setModifiers(int modifiers) {
		this.modifiers = modifiers;
	}

	public boolean isReachable() {
		return reachable;
	}

	public void setReachable(boolean reachable) {
		this.reachable = reachable;
	}

	public boolean isReachesMop() {
		return reachesMop;
	}

	public void setReachesMop(boolean reachesMop) {
		this.reachesMop = reachesMop;
	}

	public boolean isDirectlyReachesMop() {
		return directlyReachesMop;
	}

	public void setDirectlyReachesMop(boolean directlyReachesMop) {
		this.directlyReachesMop = directlyReachesMop;
	}

	public List<String> getPossiblePath() {
		return possiblePath;
	}

	public void setPossiblePath(List<String> possiblePath) {
		this.possiblePath = possiblePath;
	}

	public List<List<String>> getAllPathsToMop() {
		return allPathsToMop;
	}

	public void setAllPathsToMop(List<List<String>> possiblePathToMop) {
		this.allPathsToMop = possiblePathToMop;
	}

}
