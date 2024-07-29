package br.unb.cic.rvsec.taint.model;

import java.util.Objects;

public class Activity {
	private String name, shortName, packageName;
	private boolean isMain = false;

	private boolean reachesMop = false;

	public Activity(String name, boolean isMain) {
		setName(name);
		this.isMain = isMain;
	}

	public String getName() {
		return name;
	}

	private void setName(String name) {
		this.name = name;
		this.packageName = name.substring(0, name.lastIndexOf('.'));
		this.shortName = name.substring(name.lastIndexOf('.') + 1);
	}

	public boolean isReachesMop() {
		return reachesMop;
	}

	public void setReachesMop(boolean reachesMop) {
		this.reachesMop = reachesMop;
	}

	public String getShortName() {
		return shortName;
	}

	public String getPackageName() {
		return packageName;
	}

	public boolean isMain() {
		return isMain;
	}

	@Override
	public int hashCode() {
		return Objects.hash(isMain, name, packageName, reachesMop, shortName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Activity other = (Activity) obj;
		return isMain == other.isMain && Objects.equals(name, other.name) && Objects.equals(packageName, other.packageName) && reachesMop == other.reachesMop
				&& Objects.equals(shortName, other.shortName);
	}

	@Override
	public String toString() {
		return String.format("Activity [name=%s, shortName=%s, packageName=%s, isMain=%s, reachesMop=%s]", name, shortName, packageName, isMain, reachesMop);
	}

}
