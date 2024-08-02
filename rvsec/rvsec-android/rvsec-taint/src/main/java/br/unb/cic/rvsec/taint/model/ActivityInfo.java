package br.unb.cic.rvsec.taint.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

public class ActivityInfo {
	private String name, shortName, packageName;
	private boolean isMain = false;

	private String layoutFileName;
	private List<ViewInfo> views = new ArrayList<>();

//	private boolean reachesMop = false;
//	private SootClass sootClass;

	public ActivityInfo(String name, boolean isMain) {
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

//	public boolean isReachesMop() {
//		return reachesMop;
//	}
//
//	public void setReachesMop(boolean reachesMop) {
//		this.reachesMop = reachesMop;
//	}

	public String getShortName() {
		return shortName;
	}

	public String getPackageName() {
		return packageName;
	}

	public boolean isMain() {
		return isMain;
	}

	public String getLayoutFileName() {
		return layoutFileName;
	}

	public void setLayoutFileName(String layoutFileName) {
		this.layoutFileName = layoutFileName;
	}

	public List<ViewInfo> getViews() {
		return Collections.unmodifiableList(views);
	}

	public void setViews(List<ViewInfo> views) {
		this.views = views;
	}

	public void addView(ViewInfo view) {
		if (!views.contains(view)) {
			views.add(view);
		}
	}

//	public SootClass getSootClass() {
//		return sootClass;
//	}
//
//	public void setSootClass(SootClass sootClass) {
//		this.sootClass = sootClass;
//	}

	@Override
	public int hashCode() {
		return Objects.hash(isMain, name, packageName, shortName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		ActivityInfo other = (ActivityInfo) obj;
		return isMain == other.isMain && Objects.equals(name, other.name) && Objects.equals(packageName, other.packageName) && Objects.equals(shortName, other.shortName);
	}

	@Override
	public String toString() {
		return String.format("ActivityInfo [name=%s, isMain=%s, layoutFileName=%s, views=%s]", name, isMain, layoutFileName, views);
	}



}
