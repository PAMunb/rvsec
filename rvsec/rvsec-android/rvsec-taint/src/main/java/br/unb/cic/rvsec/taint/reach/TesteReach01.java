package br.unb.cic.rvsec.taint.reach;

import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.jgrapht.Graph;
import org.jgrapht.GraphPath;
import org.jgrapht.alg.connectivity.ConnectivityInspector;
import org.jgrapht.alg.shortestpath.DijkstraShortestPath;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.MopFacade;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.model.SootActivity;
import br.unb.cic.rvsec.taint.util.AndroidUtil;
import br.unb.cic.rvsec.taint.xml.XmlAnalysis;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class TesteReach01 {

	private ApkInfo apkInfo;

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws Exception {
		ApkReader apkReader = new ApkReader();
		apkInfo = apkReader.readApk(apkPath);

		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		MopFacade mopFacade = new MopFacade();
		Set<SootMethod> mopMethods = mopFacade.getMopMethods(mopSpecsDir, apkInfo);

		XmlAnalysis analysis = new XmlAnalysis();
		List<SootActivity> activities = analysis.processActivities(apkInfo);

		app.constructCallgraph();
		CallGraph callGraph = Scene.v().getCallGraph();

		Graph<SootMethod, DefaultEdge> graph = toJGraph(callGraph);
//		graph.

		teste01(graph, mopMethods, activities);

	}

	private void teste01(Graph<SootMethod, DefaultEdge> graph, Set<SootMethod> mopMethods, List<SootActivity> activities) {
		Collection<SootMethod> entryPoints = getEntryPoints(activities);

		ConnectivityInspector<SootMethod, DefaultEdge> inspector = new ConnectivityInspector<>(graph);
		DijkstraShortestPath<SootMethod, DefaultEdge> dijkstra = new DijkstraShortestPath<>(graph);

		System.out.println("REACHES ........");
		for (SootMethod entryPoint : entryPoints) {
			if (graph.containsVertex(entryPoint)) {
				for (SootMethod mop : mopMethods) {
					// TODO tem como saber se um metodo foi herdado ou sobrescrito?
//					System.out.println("path exists? " + entryPoint.getSignature() + "("+entryPoint.isDeclared()+") :::: " + mop.getSubSignature());
					if (inspector.pathExists(entryPoint, mop)) {
						System.out.println("************ " + entryPoint.getSignature() + " >>>>> " + mop.getSignature());
						GraphPath<SootMethod, DefaultEdge> path = dijkstra.getPath(entryPoint, mop);
						if (path != null) {
							System.out.println("CAMINHO:::");
							path.getVertexList().forEach(v -> System.out.println("\t>> " + v.getSignature()));
						} else {
							System.out.println("INCONSISTENCIA ...................................");
						}
					}
				}
			}
		}
	}

	private Collection<SootMethod> getEntryPoints(List<SootActivity> activities) {
		Collection<SootMethod> entryPoints = new HashSet<>();
		System.out.println("get entrypoints ...");
		for (SootActivity sootActivity : activities) {
			SootClass clazz = sootActivity.getClazz();
			System.out.println("clazz=" + clazz.getName());
			for (SootMethod method : clazz.getMethods()) {
				if (isValidEntrypoint(method)) {
					System.out.println("entrypoint: " + method.getSignature());
					entryPoints.add(method);
				}
			}
		}
		return entryPoints;
	}

	public boolean isValidEntrypoint(SootMethod sootMethod) {
		System.out.println("isValidEntrypoint="+sootMethod);
		System.out.println("\t-"+sootMethod.getDeclaringClass().declaresMethod(sootMethod.getSubSignature()));
		System.out.println("\t- abstract="+sootMethod.isAbstract()+" :: concrete="+sootMethod.isConcrete()+" :: constructor="+sootMethod.isConstructor());
		System.out.println("\t- declared="+sootMethod.isDeclared()+" :: "+sootMethod.isEntryMethod()+" :: main="+sootMethod.isMain()+" :: "+sootMethod.isPhantom());
		System.out.println("\t- numSubSig"+sootMethod.getNumberedSubSignature());
		System.out.println("\t- numSubSig"+sootMethod.getDeclaration());
//		if (sootMethod.toString().contains("<init>") 
//				|| sootMethod.toString().contains("<clinit>") 
//				|| sootMethod.getName().equals("dummyMainMethod"))
//			return false;
		return true;
	}

	private Graph<SootMethod, DefaultEdge> toJGraph(CallGraph callGraph) {
		Graph<SootMethod, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);
		for (Edge edge : callGraph) {
			if (isValid(edge)) {
				g.addVertex(edge.src());
				g.addVertex(edge.tgt());
				g.addEdge(edge.src(), edge.tgt());
			}
		}
		return g;
	}

	private boolean isValid(Edge edge) {
		SootClass sourceClass = edge.getSrc().method().getDeclaringClass();
		return AndroidUtil.isAppClass(sourceClass, apkInfo);
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

		TesteReach01 t = new TesteReach01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
