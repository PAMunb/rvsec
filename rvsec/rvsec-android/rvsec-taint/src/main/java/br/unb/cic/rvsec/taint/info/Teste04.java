package br.unb.cic.rvsec.taint.info;

import java.io.IOException;
import java.util.List;

import org.jgrapht.Graph;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.model.SootActivity;
import br.unb.cic.rvsec.taint.xml.XmlAnalysis;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class Teste04 {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
//		listFiles(apkPath);

		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);
//
		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
//
		XmlAnalysis analysis = new XmlAnalysis();
		List<SootActivity> activities = analysis.processActivities(apkInfo);

		System.out.println("************************************");
		activities.forEach(System.out::println);
		
		// Create the Callgraph without executing taint analysis
        app.constructCallgraph();
        CallGraph callGraph = Scene.v().getCallGraph();
        
        Graph<SootMethod,DefaultEdge> graph = toJGraph(callGraph);
        
        teste01(graph);

	}

	private void teste01(Graph<SootMethod, DefaultEdge> graph) {
		
	}

	private Graph<SootMethod, DefaultEdge> toJGraph(CallGraph callGraph) {
		Graph<SootMethod, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);
		for (Edge edge : callGraph) {
			g.addVertex(edge.src());
			g.addVertex(edge.tgt());
			g.addEdge(edge.src(), edge.tgt());
		}
		return g;
	}

	public static void main(String[] args) {
		String mopSpecsDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
//		String sinksFile = "";
		String callbacksFile = "";

		Teste04 t = new Teste04();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
