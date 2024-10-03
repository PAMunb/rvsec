package br.unb.cic.rvsec.reach.cli;

import java.io.File;

import com.beust.jcommander.Parameter;

import br.unb.cic.rvsec.reach.writer.WriterType;

public class CommandLineArgs {

	@Parameter(names = { "--android-dir", "-d" }, description = "Android platforms path (~/Android/sdk/platforms). Default: $ANDROID_HOME") // , required = true)
	private String androidDir;

	@Parameter(names = { "--mop-dir", "-m" }, description = "MOP specifications path", required = true)
	private String mopSpecsDir;

	@Parameter(names = { "--rt-jar", "-r" }, description = "rt.jar path", required = true)
	private String rtJar;

	@Parameter(names = { "--apk", "-a" }, description = "APK to be analyzed", required = true)
	private String apk;

	@Parameter(names = { "--output", "-o" }, description = "Output file containing the results", required = true)
	private String outputFile;

	@Parameter(names = { "--gesda", "-g" }, description = "Gesda output file containing APK info", required = false)
	private String gesdaFile;

	@Parameter(names = { "--writer", "-w" }, description = "Output file type: csv or json. Default: csv")
	private WriterType writerType = WriterType.csv;

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

	public String getMopSpecsDir() {
		return mopSpecsDir;
	}

	public String getRtJar() {
		return rtJar;
	}

	public String getOutputFile() {
		return outputFile;
	}

	public String getGesdaFile() {
		return gesdaFile;
	}

	public String getApk() {
		return apk;
	}

	public boolean isDebug() {
		return debug;
	}

	public WriterType getWriterType() {
		return writerType;
	}

}
