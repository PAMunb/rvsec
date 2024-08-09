package br.unb.cic.rvsec.taint.model;

import soot.SootClass;

public class SootActivity {

	private ActivityInfo activityInfo;
	private SootClass clazz;

	private boolean reachesMop;
	private boolean directlyReachesMop;

	public boolean isMain() {
		return activityInfo.isMain();
	}


	public SootActivity(ActivityInfo activityInfo, SootClass clazz) {
		this.activityInfo = activityInfo;
		this.clazz = clazz;
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


	public ActivityInfo getActivityInfo() {
		return activityInfo;
	}


	public SootClass getClazz() {
		return clazz;
	}


	@Override
	public String toString() {
		return activityInfo.toString();
	}

}
