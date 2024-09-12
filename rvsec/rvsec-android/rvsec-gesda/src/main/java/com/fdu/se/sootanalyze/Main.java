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
import com.fdu.se.sootanalyze.model.xml.AppInfo;
import com.fdu.se.sootanalyze.output.ApkInfoOut;
import com.fdu.se.sootanalyze.output.OutputWriter;

public class Main {

	public static void main(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		JCommander jc = JCommander.newBuilder().addObject(jArgs).build();

		if (args.length == 0) {
			jc.usage();
			return;
		}

		jc.parse(args);

		String androidPlatformsDir = jArgs.getAndroidDir();
		String rtJarPath = jArgs.getRtJar();
		String apk = jArgs.getApk();
		String outputFile = jArgs.getOutputFile();
		boolean debug = jArgs.isDebug();

		if (debug) {
			// Obtém o logger root e define o nível
			ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
			root.setLevel(ch.qos.logback.classic.Level.TRACE);
		}

		SootAnalyze sootAnalyze = new SootAnalyze(androidPlatformsDir, rtJarPath);
		try {
			AppInfo info = sootAnalyze.init(apk);
			List<WindowNode> nodes = sootAnalyze.analyze();

			System.out.println("INFO: ");
			info.getActivities().forEach(System.out::println);
			System.out.println("NODES:");
			nodes.forEach(System.out::println);
			
//TODO
//			sootAnalyze.analyseDependencies(nodes);
//			TransitionGraph graph = sootAnalyze.generateTransitionGraph(nodes);
//			System.out.println("Graph: " + graph);
			
			ApkInfoOut infoOut = new ApkInfoOut(info, nodes);
			OutputWriter.write(infoOut, new File(outputFile));
		} catch (IOException | XmlPullParserException e) {
			e.printStackTrace();
		}

		System.out.println("FIM DE FESTA !!!");

	}

}
