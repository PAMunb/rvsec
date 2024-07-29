package br.unb.cic.rvsec.taint.model;

import soot.SootClass;

public class SootActivity {

	private Activity activity;
	private SootClass clazz;

	private boolean reachesMop;
	private boolean directlyReachesMop;
	private boolean isMain;

}
