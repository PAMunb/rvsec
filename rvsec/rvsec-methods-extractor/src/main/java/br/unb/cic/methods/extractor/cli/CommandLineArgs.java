package br.unb.cic.methods.extractor.cli;

import com.beust.jcommander.Parameter;

public class CommandLineArgs {

	@Parameter(names = { "--apk", "-a" }, description = "APK to be parsed", required = true)
	private String apk;

	@Parameter(names = { "--apk-package", "-p" }, description = "APK package", required = true)
	private String appPackage;
	
	@Parameter(names = { "--android-dir", "-d" }, description = "Android platforms dir", required = true)
	private String androidPlatformsDir;
	
	@Parameter(names = { "--output", "-o" }, description = "Output CSV file", required = true)
	private String outputFile;
	
	@Parameter(names = { "--include-contructors" }, description = "Include contructors")
	private boolean includeConstructors;
	
	@Parameter(names = { "--include-static-initializers" }, description = "Include static initializers")
	private boolean includeStaticInitializers;
	
	@Parameter(names = "--help", description = "Show usage information", help = true)
	private boolean help;


	public String getApk() {
		return apk;
	}

	public String getAppPackage() {
		return appPackage;
	}

	public String getAndroidPlatformsDir() {
		return androidPlatformsDir;
	}

	public String getOutputFile() {
		return outputFile;
	}

	public boolean isIncludeConstructors() {
		return includeConstructors;
	}

	public boolean isIncludeStaticInitializers() {
		return includeStaticInitializers;
	}

	public boolean isHelp() {
		return help;
	}	

}
