package com.fdu.se.sootanalyze;

import java.io.File;
import java.io.IOException;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xmlpull.v1.XmlPullParserException;

import com.beust.jcommander.JCommander;
import com.fdu.se.sootanalyze.cli.CommandLineArgs;
import com.fdu.se.sootanalyze.model.WindowNode;
import com.fdu.se.sootanalyze.model.out.ApkInfoOut;
import com.fdu.se.sootanalyze.writer.OutputFactory;
import com.fdu.se.sootanalyze.writer.OutputWriter;

import br.unb.cic.rvsec.apk.model.AppInfo;

public class Main {
	private static final Logger log = LoggerFactory.getLogger(Main.class);

	private static void runCLI(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		JCommander jc = JCommander.newBuilder().addObject(jArgs).build();

		if (args.length == 0) {
			jc.usage();
			return;
		}

		jc.parse(args);

		executeAnalysis(jArgs.getAndroidDir(), jArgs.getRtJar(), jArgs.getApk(), jArgs.getOutputFile(), jArgs.isDebug());
	}

	private static void runLocal() {
		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";
		String apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk";
		String outputFile = "/home/pedro/tmp/rvsec-gesda.json";
		boolean debug = false;

		executeAnalysis(androidPlatformsDir, rtJarPath, apk, outputFile, debug);
	}

	private static void executeAnalysis(String androidPlatformsDir, String rtJarPath, String apk, String outputFile, boolean debug) {
		if (debug) {
			ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
			root.setLevel(ch.qos.logback.classic.Level.DEBUG);
		}

		log.info("Starting analysis ...");
		SootAnalyze sootAnalyze = new SootAnalyze(androidPlatformsDir, rtJarPath);
		try {
			AppInfo info = sootAnalyze.init(apk);
			List<WindowNode> nodes = sootAnalyze.analyze();
			sootAnalyze.analyseDependencies(nodes);
//			TransitionGraph graph = sootAnalyze.generateTransitionGraph(nodes);
			ApkInfoOut infoOut = OutputFactory.createApkInfoOut(info, nodes);
			OutputWriter.write(infoOut, new File(outputFile));
		} catch (IOException | XmlPullParserException e) {
			e.printStackTrace();
		}
		log.info("Analysis completed");
	}

	public static void main(String[] args) {
		runCLI(args);

//		runLocal();
	}
	
}
