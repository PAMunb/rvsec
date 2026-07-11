package br.unb.cic.rvsec.reach.cli;

import java.io.File;

import com.beust.jcommander.Parameter;

import br.unb.cic.rvsec.reach.writer.WriterType;

public class CommandLineArgs {

	@Parameter(names = { "--android-dir", "-d" }, description = "Android platforms path (~/Android/sdk/platforms). Default: $ANDROID_HOME")
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
	
	@Parameter(names = { "--timeout", "-t" }, description = "Data flow analysis timeout (in seconds). Default: 300", required = false)
	private int timeout = 300;

	@Parameter(names = { "--writer", "-w" }, description = "Output file type: csv or json. Default: csv")
	private WriterType writerType = WriterType.csv;

	@Parameter(names = { "--full", "-f" },
			description = "Performs analysis on all methods contained in the apk. The default analysis only analyzes the methods of classes contained in the package declared in the manifest. Default: false",
			required = false)
	private boolean full = false;

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
	
	public int getTimeout() {
		return timeout;
	}

	public String getApk() {
		return apk;
	}

	public boolean isFull() {
		return full;
	}

	public boolean isDebug() {
		return debug;
	}

	public WriterType getWriterType() {
		return writerType;
	}

}
