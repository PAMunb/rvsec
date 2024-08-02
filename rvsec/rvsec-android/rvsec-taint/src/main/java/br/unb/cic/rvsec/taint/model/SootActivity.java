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

	@Override
	public String toString() {
		return activityInfo.toString();
	}

}
