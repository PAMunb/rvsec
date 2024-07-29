package br.unb.cic.rvsec.taint;

import java.util.Collections;

import soot.MethodOrMethodContext;
import soot.Scene;
import soot.jimple.infoflow.InfoflowConfiguration;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.ReachableMethods;
import soot.options.Options;
import soot.util.queue.QueueReader;

public class Teste03 {
//	private static final String ANDROID_PLATFORMS_DIR = "/home/pedro/desenvolvimento/aplicativos/android/platforms";
	private static final String ANDROID_PLATFORMS_DIR = "/home/pedro/desenvolvimento/aplicativos/android/platforms-sable";
	private static final String OUTPUT_DIR = "/home/pedro/tmp/soot";

	public void execute(String apk) {
		initializeSoot(OUTPUT_DIR, apk, ANDROID_PLATFORMS_DIR);

		final InfoflowAndroidConfiguration config = new InfoflowAndroidConfiguration();
		config.getAnalysisFileConfig().setTargetAPKFile(apk);
		config.getAnalysisFileConfig().setAndroidPlatformDir(ANDROID_PLATFORMS_DIR);
		config.setCodeEliminationMode(InfoflowConfiguration.CodeEliminationMode.NoCodeElimination);
		config.setCallgraphAlgorithm(InfoflowConfiguration.CallgraphAlgorithm.SPARK); // CHA or SPARK
		config.setMergeDexFiles(true);
        config.setEnableReflection(true);
		config.setSootIntegrationMode(InfoflowAndroidConfiguration.SootIntegrationMode.UseExistingInstance);

		SetupApplication app = new SetupApplication(config);

		app.constructCallgraph();

		CallGraph callGraph = Scene.v().getCallGraph();

		ReachableMethods reachableMethods = Scene.v().getReachableMethods();
		QueueReader<MethodOrMethodContext> methods = reachableMethods.listener();
		System.out.println("ReachableMethods");
		while (methods.hasNext()) {
			String tmp = methods.next().method().getSignature().toString();
			if (tmp.contains("MessageDigest")) {
				System.out.println("*** " + tmp);
			}
		}

		System.out.println("FIM DE FESTA!!!");

	}

	private void initializeSoot(String output, String apk, String androidJAR) {
		Options.v().set_full_resolver(true);
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_prepend_classpath(true);
		Options.v().set_validate(true);
//        Options.v().set_output_format(Options.output_format_jimple);
		Options.v().set_output_format(Options.output_format_none);
		Options.v().set_output_dir(output);
		Options.v().set_process_dir(Collections.singletonList(apk));
		Options.v().set_android_jars(androidJAR);
		Options.v().set_src_prec(Options.src_prec_apk);
		Options.v().set_process_multiple_dex(true);
		Options.v().set_soot_classpath(androidJAR);
//		Options.v().set_soot_classpath(androidJAR+":/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar");

//		soot.options.Options.v().set_whole_program(true);
//		soot.options.Options.v().set_force_android_jar(androidJAR);
//		soot.options.Options.v().force_overwrite();
//		Scene.v().addBasicClass("java.io.PrintStream",SootClass.SIGNATURES);
		Options.v().setPhaseOption("cg", "all-reachable");
		Options.v().setPhaseOption("cg.spark", "on");
		Options.v().setPhaseOption("cg.spark", "verbose:false");

		Scene.v().loadNecessaryClasses();
	}

	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
		String apk = baseDir + "cryptoapp.apk";

//		String apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-android/cryptoapp/app/build/intermediates/apk/debug/app-debug.apk";

		new Teste03().execute(apk);
	}
}
