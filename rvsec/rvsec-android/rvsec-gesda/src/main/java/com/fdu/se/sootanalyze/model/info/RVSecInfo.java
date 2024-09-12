package com.fdu.se.sootanalyze.model.info;

import java.util.Objects;

@Deprecated
//vai para modulo especifico para reachability
public class RVSecInfo {

	// reachable from any entrypoint
	private boolean reachable;

	// reaches any methods defined in MOP specs
	private boolean reachesMop;

	// directly reaches any methods defined in MOP specs. EX: A method directly
	// calls a MOP method, inside its body
	private boolean directlyReachesMop;

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

	@Override
	public int hashCode() {
		return Objects.hash(directlyReachesMop, reachable, reachesMop);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		RVSecInfo other = (RVSecInfo) obj;
		return directlyReachesMop == other.directlyReachesMop && reachable == other.reachable && reachesMop == other.reachesMop;
	}

	@Override
	public String toString() {
		return String.format("RVSecInfo [reachable=%s, reachesMop=%s, directlyReachesMop=%s]", reachable, reachesMop, directlyReachesMop);
	}

}
