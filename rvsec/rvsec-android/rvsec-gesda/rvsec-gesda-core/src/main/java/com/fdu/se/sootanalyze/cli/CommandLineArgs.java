package com.fdu.se.sootanalyze.cli;

import java.io.File;

import com.beust.jcommander.Parameter;

public class CommandLineArgs {

	@Parameter(names = { "--android-dir", "-d" }, description = "Android platforms path (~/Android/sdk/platforms)") // , required = true)
	private String androidDir;

	// TODO ver como "embutir" o jar
	@Parameter(names = { "--rt-jar", "-r" }, description = "rt.jar path", required = true)
	private String rtJar;

	@Parameter(names = { "--apk", "-a" }, description = "APK to be analyzed", required = true)
	private String apk;

	@Parameter(names = { "--output", "-o" }, description = "Output file containing the results", required = true)
	private String outputFile;

	@Parameter(names = "-debug", description = "Debug mode")
	private boolean debug = false;

	public CommandLineArgs() {
		String androidHome = System.getenv("ANDROID_HOME");
		if (androidHome != null) {
			androidDir = androidHome + File.separatorChar + "platforms";
		}
	}

	public String getAndroidDir() {
		return androidDir;
	}

	public String getRtJar() {
		return rtJar;
	}

	public String getOutputFile() {
		return outputFile;
	}

	public String getApk() {
		return apk;
	}

	public boolean isDebug() {
		return debug;
	}

}
