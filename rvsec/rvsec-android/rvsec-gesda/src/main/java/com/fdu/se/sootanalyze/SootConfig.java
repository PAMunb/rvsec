package com.fdu.se.sootanalyze;

import java.io.File;
import java.util.Collections;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import soot.G;
import soot.Scene;
import soot.jimple.infoflow.InfoflowConfiguration;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.options.Options;

public class SootConfig {
	private static Logger log = LoggerFactory.getLogger(SootAnalyze.class);
	
	private static InfoflowAndroidConfiguration config;

	public static SetupApplication initialize(String apk, String androiPlatformsDir, String rtJarPath) {
		initializeSoot(apk, androiPlatformsDir, rtJarPath);

		config = new InfoflowAndroidConfiguration();
		config.getAnalysisFileConfig().setTargetAPKFile(apk);
//		config.getAnalysisFileConfig().setAdditionalClasspath(rtJarPath);
		config.getAnalysisFileConfig().setAndroidPlatformDir(androiPlatformsDir);
//		config.getCallbackConfig().setEnableCallbacks(false);
		config.setCodeEliminationMode(InfoflowConfiguration.CodeEliminationMode.NoCodeElimination);
		config.setCallgraphAlgorithm(InfoflowConfiguration.CallgraphAlgorithm.SPARK);
		config.setMergeDexFiles(true);
		config.setEnableReflection(true);
		config.setEnableOriginalNames(true);
		config.setSootIntegrationMode(InfoflowAndroidConfiguration.SootIntegrationMode.UseExistingInstance);

		log.debug("Creating soot.jimple.infoflow.android.SetupApplication");
		return new SetupApplication(config);
	}

	public static InfoflowAndroidConfiguration getConfig() {
		return config;
	}
	
	private static void initializeSoot(String apk, String androidPlatformsDir, String rtJarPath) {
		log.debug("Initializing Soot ...");
		log.trace("APK: "+apk);
		log.trace("Android platforms dir: "+androidPlatformsDir);
		log.trace("RT jar: "+rtJarPath);
		G.reset();
		Options.v().set_full_resolver(true);
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_prepend_classpath(true);
		Options.v().set_validate(true);
//		Options.v().set_output_format(Options.output_format_none);
		
		Options.v().set_output_format(Options.output_format_jimple);
//		Options.v().set_output_dir("/home/pedro/tmp/cryptoapp_jimple");
		
		Options.v().set_process_dir(Collections.singletonList(apk));
		Options.v().set_android_jars(androidPlatformsDir);
		Options.v().set_src_prec(Options.src_prec_apk);
		Options.v().set_process_multiple_dex(true);
		Options.v().set_soot_classpath(androidPlatformsDir + File.pathSeparatorChar + rtJarPath);

//		Options.v().parse(new String[]{"-keep-line-number", "-p", "jb", "use-original-names:true"});
//		Options.v().parse(new String[]{"-keep-line-number"});
		Options.v().keep_line_number();
		Options.v().parse(new String[]{"-p", "jb", "use-original-names:true"});
		Options.v().setPhaseOption("jb", "use-original-names:true");
		

//		soot.options.Options.v().set_whole_program(true);
//		soot.options.Options.v().set_force_android_jar(androidJAR);
//		soot.options.Options.v().force_overwrite();
//		Scene.v().addBasicClass("java.io.PrintStream",SootClass.SIGNATURES);
		Options.v().setPhaseOption("cg", "all-reachable");
		Options.v().setPhaseOption("cg.spark", "on");
		Options.v().setPhaseOption("cg.spark", "verbose:false");

		Scene.v().loadNecessaryClasses();
		
//		PackManager.v().runPacks();
//		PackManager.v().writeOutput();
	}
}
