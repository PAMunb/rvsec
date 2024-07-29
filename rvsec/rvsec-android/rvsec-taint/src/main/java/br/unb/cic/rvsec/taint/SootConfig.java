package br.unb.cic.rvsec.taint;

import java.io.File;
import java.util.Collections;

import soot.Scene;
import soot.jimple.infoflow.InfoflowConfiguration;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.options.Options;

public class SootConfig {

	public SetupApplication initialize(String apk, String androiPlatformsDir, String rtJarPath) {
		initializeSoot(null, apk, androiPlatformsDir, rtJarPath);

		final InfoflowAndroidConfiguration config = new InfoflowAndroidConfiguration();
		config.getAnalysisFileConfig().setTargetAPKFile(apk);
		config.getAnalysisFileConfig().setAndroidPlatformDir(androiPlatformsDir);
		config.setCodeEliminationMode(InfoflowConfiguration.CodeEliminationMode.NoCodeElimination);
		config.setCallgraphAlgorithm(InfoflowConfiguration.CallgraphAlgorithm.SPARK); // CHA or SPARK
		config.setMergeDexFiles(true);
		config.setEnableReflection(true);
		config.setSootIntegrationMode(InfoflowAndroidConfiguration.SootIntegrationMode.UseExistingInstance);

		return new SetupApplication(config);
	}

	private void initializeSoot(String output, String apk, String androidJAR, String rtJarPath) {
		Options.v().set_full_resolver(true);
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_prepend_classpath(true);
		Options.v().set_validate(true);
//        Options.v().set_output_format(Options.output_format_jimple);
		Options.v().set_output_format(Options.output_format_none);
//		Options.v().set_output_dir(output);
		Options.v().set_process_dir(Collections.singletonList(apk));
		Options.v().set_android_jars(androidJAR);
		Options.v().set_src_prec(Options.src_prec_apk);
		Options.v().set_process_multiple_dex(true);
		Options.v().set_soot_classpath(androidJAR + File.pathSeparatorChar + rtJarPath);

//		soot.options.Options.v().set_whole_program(true);
//		soot.options.Options.v().set_force_android_jar(androidJAR);
//		soot.options.Options.v().force_overwrite();
//		Scene.v().addBasicClass("java.io.PrintStream",SootClass.SIGNATURES);
		Options.v().setPhaseOption("cg", "all-reachable");
		Options.v().setPhaseOption("cg.spark", "on");
		Options.v().setPhaseOption("cg.spark", "verbose:false");

		Scene.v().loadNecessaryClasses();
	}
}
