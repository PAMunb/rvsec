package br.unb.cic.rvsec.taint;

import java.io.IOException;
import java.net.URISyntaxException;

import org.xmlpull.v1.XmlPullParserException;

import soot.Scene;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class Teste02 {

	public void execute(String apkPath, String androidJarFolder) throws URISyntaxException, IOException, XmlPullParserException {
		SetupApplication app = new SetupApplication(androidJarFolder, apkPath);
		app.constructCallgraph();
		CallGraph callGraph = Scene.v().getCallGraph();
		for (Edge edge : callGraph) {
			System.out.println(edge);
		}

//		app.setTaintWrapper(new SummaryTaintWrapper(new LazySummaryProvider("summariesManual")));
//		InfoflowResults results = app.runInfoflow();
//		// Parse arguments
//		InfoflowConfiguration.CallgraphAlgorithm cgAlgorithm = InfoflowConfiguration.CallgraphAlgorithm.SPARK;
//		// Setup FlowDroid
//		final InfoflowAndroidConfiguration config = getFlowDroidConfig(apkPath, androidJarFolder, cgAlgorithm);
////        config.setMergeDexFiles(true);
//		SetupApplication app = new SetupApplication(config);
//		// Create the Callgraph without executing taint analysis
//		app.constructCallgraph();
//		System.out.println("construiu callgraph...");
//		CallGraph callGraph = Scene.v().getCallGraph();
//
//		for (Edge edge : callGraph) {
//			System.out.println(edge);
//		}
//
//		// Perform BFS from the main entrypoint to see if "unreachableMehthod" is
//		// reachable at all or not
////		Map<SootMethod, SootMethod> reachableParentMapFromEntryPoint = getAllReachableMethods(app.getDummyMainMethod());

		System.out.println("FIM DE FESTA !!!");
	}


	public static void main(String[] args) {
//		String androidPlatformDir = "/home/pedro/desenvolvimento/aplicativos/android/platforms";
		String androidPlatformDir = "/home/pedro/desenvolvimento/aplicativos/android/platforms-sable";
		String apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk";

		Teste02 t = new Teste02();
		try {
			t.execute(apk, androidPlatformDir);
		} catch (URISyntaxException | IOException | XmlPullParserException e) {
			e.printStackTrace();
		}
	}


}
