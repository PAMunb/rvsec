package br.unb.cic.rvsec.taint;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.InfoflowConfiguration;
import soot.jimple.infoflow.InfoflowConfiguration.ImplicitFlowMode;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.options.Options;
import soot.util.queue.QueueReader;

public class Teste01 {
//	private static final String ANDROID_PLATFORMS_DIR = "/home/pedro/desenvolvimento/aplicativos/android/platforms";
	private static final String ANDROID_PLATFORMS_DIR = "/home/pedro/desenvolvimento/aplicativos/android/platforms-sable";
	private static final String OUTPUT_DIR = "/home/pedro/tmp/soot";

	public void execute(String apk) {
		initializeSoot(OUTPUT_DIR, apk, ANDROID_PLATFORMS_DIR);

		final InfoflowAndroidConfiguration config = new InfoflowAndroidConfiguration();
		config.getAnalysisFileConfig().setTargetAPKFile(apk);
		config.getAnalysisFileConfig().setAndroidPlatformDir(ANDROID_PLATFORMS_DIR);
		config.setCodeEliminationMode(InfoflowConfiguration.CodeEliminationMode.NoCodeElimination);
		config.setCallgraphAlgorithm(InfoflowConfiguration.CallgraphAlgorithm.SPARK);
//		config.getCallbackConfig().setEnableCallbacks(false);
		config.setMergeDexFiles(true);
//config.setExcludeSootLibraryClasses(false);
//config.setIgnoreFlowsInSystemPackages(true);
//config.setCreateActivityEntryMethods(true);
//		config.setAliasingAlgorithm(AliasingAlgorithm.FlowSensitive);
		config.setEnableExceptionTracking(true);
		config.setEnableLineNumbers(true);
		config.setEnableOriginalNames(true);
//		config.setEnableReflection(true);
//		config.setEnableTypeChecking(true);
		config.setImplicitFlowMode(ImplicitFlowMode.AllImplicitFlows);
		config.setSootIntegrationMode(InfoflowAndroidConfiguration.SootIntegrationMode.UseExistingInstance);
//		config.setSootIntegrationMode(InfoflowAndroidConfiguration.SootIntegrationMode.CreateNewInstance);

		SetupApplication app = new SetupApplication(config);


//		Scene.v().getApplicationClasses().forEach(c -> {
//			if(c.getName().startsWith("br.unb.cic.cryptoapp")
//					&& !c.getName().startsWith("br.unb.cic.cryptoapp.R")) {
//				System.out.println("CLASSE: "+c.getName());
//				c.getMethods().forEach(m -> {
//					System.out.println("METODO: "+m.getSignature());
//					m.retrieveActiveBody().getUnits().forEach(u -> {
//						Stmt stmt = (Stmt) u;
//						if(stmt.containsInvokeExpr()) {
//							InvokeExpr invokeExpr = stmt.getInvokeExpr();
//							if(invokeExpr.getMethod().getDeclaringClass().getName().equals("java.security.MessageDigest")) {
//								System.out.println("********************* "+invokeExpr.getMethod().getDeclaringClass().getName()+" :: "+invokeExpr.getMethod().getSubSignature());
//							}
//						}
//					});
//				});
//			}
//		});

//		List<SootMethod> entryPoints = new ArrayList<>();
//		Scene.v().getApplicationClasses().forEach(c -> {
//			if(c.getName().equals("br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity")) {
//				System.out.println("CLASSE: "+c.getName());
//				c.getMethods().forEach(m -> {
//					System.out.println("METODO: "+m.getSignature());
//					if(m.isPublic() || m.isProtected()) {
//						entryPoints.add(m);
//					}
//				});
//			}
//		});
//		Scene.v().setEntryPoints(entryPoints);
//		for (SootMethod sootMethod : entryPoints) {
//			System.out.println(sootMethod);
//		}
//
////		Scene.v().setEntryPoints(Collections.singletonList(entryMethod));
//		PackManager.v().runPacks();

		app.constructCallgraph();
		CallGraph callGraph = Scene.v().getCallGraph();

		QueueReader<Edge> listener = callGraph.listener();
		while(listener.hasNext()) {
			Edge edge = listener.next();
			if(edge.toString().contains("java.security.MessageDigest") && edge.toString().contains("cryptoapp")) {
				System.out.println("EDGE: "+edge);
			}
		}

//		// Perform BFS from the main entrypoint to see if "unreachableMehthod" is reachable at all or not
//        Map<SootMethod, SootMethod> reachableParentMapFromEntryPoint = getAllReachableMethods(app.getDummyMainMethod());
//
//
//		ReachableMethods reachableMethods = Scene.v().getReachableMethods();
//        QueueReader<MethodOrMethodContext> methods = reachableMethods.listener();
//
//        System.out.println("ReachableMethods");
//        while(methods.hasNext()){
//        	String tmp = methods.next().method().getSignature().toString();
//        	if(tmp.contains("MessageDigest")) {// || tmp.contains("digest")) {
//        		System.out.println("*** "+tmp);
//        	}
//        }

		System.out.println("FIM DE FESTA!!!");
	}

	// A Breadth-First Search algorithm to get all reachable methods from initialMethod in the callgraph
    // The output is a map from reachable methods to their parents
    public static Map<SootMethod, SootMethod> getAllReachableMethods(SootMethod initialMethod){
        CallGraph callgraph = Scene.v().getCallGraph();
        List<SootMethod> queue = new ArrayList<>();
        queue.add(initialMethod);
        Map<SootMethod, SootMethod> parentMap = new HashMap<>();
        parentMap.put(initialMethod, null);
        for(int i=0; i< queue.size(); i++){
            SootMethod method = queue.get(i);

            //if(method.getName().equals("hash")) {
            if(method.getSignature().contains("br.unb.cic.cryptoapp.messagedigest")) {
            	System.out.println("METODO: "+method.getSubSignature());
            	Iterator<Edge> it = callgraph.edgesOutOf(method);
            	while(it.hasNext()) {
            		Edge e = it.next();
            		System.out.println("\t - out: "+e.getTgt());
            	}
            }

            for (Iterator<Edge> it = callgraph.edgesOutOf(method); it.hasNext(); ) {
                Edge edge = it.next();
                SootMethod childMethod = edge.tgt();

//                if(childMethod.getSignature().contains("security") || method.getSignature().contains("security")) {
//               	 System.out.println(">>> "+childMethod + " >>>>>>> "+method);
//               }

                if(parentMap.containsKey(childMethod))
                    continue;



                parentMap.put(childMethod, method);
                queue.add(childMethod);
            }
        }
        return parentMap;
    }

	private void initializeSoot(String output, String apk, String androidJAR) {
		Options.v().set_full_resolver(true);

		Options.v().set_include_all(true);
		Options.v().set_include(Arrays.asList("javax.*","java.*"));

		Options.v().set_allow_phantom_refs(true);
		Options.v().set_prepend_classpath(true);
		Options.v().set_validate(true);
//        Options.v().set_output_format(Options.output_format_jimple);
		Options.v().set_output_format(Options.output_format_none);
		Options.v().set_output_dir(output);
		Options.v().set_process_dir(Collections.singletonList(apk));
		Options.v().set_android_jars(androidJAR);
		Options.v().set_src_prec(Options.src_prec_apk);
//		Options.v().set_src_prec(Options.src_prec_apk_class_jimple);
		Options.v().set_process_multiple_dex(true);

		Options.v().set_soot_classpath(androidJAR+":/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar");
		System.out.println("Options.v().soot_classpath()="+Options.v().soot_classpath());

//		Options.v().set_derive_java_version(true);
//		Options.v().set_permissive_resolving(true);
//		Options.v().set_app(true);

		Options.v().set_whole_program(true);

//		soot.options.Options.v().set_whole_program(true);
		Scene.v().loadBasicClasses();
		Scene.v().loadDynamicClasses();
		Options.v().parse(new String[]{"-keep-line-number", "-p", "jb", "use-original-names:true"});
		soot.options.Options.v().set_throw_analysis(soot.options.Options.throw_analysis_dalvik);
//		soot.options.Options.v().set_force_android_jar(androidJAR);
//		soot.options.Options.v().force_overwrite();
		Scene.v().addBasicClass("java.io.PrintStream",SootClass.SIGNATURES);
//		soot.options.Options.v().setPhaseOption("cg.spark", "on");



		Scene.v().loadNecessaryClasses();
	}

	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

//		String apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-android/cryptoapp/app/build/intermediates/apk/debug/app-debug.apk";
		new Teste01().execute(apk);
	}
}
