package br.unb.cic.rvsec.taint.reach;

import java.io.IOException;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;

import org.jgrapht.GraphPath;
import org.jgrapht.alg.shortestpath.DijkstraShortestPath;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import javamop.util.MOPException;
import soot.MethodOrMethodContext;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class TesteGraph {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws IOException, XmlPullParserException, MOPException {
		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);

		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		Set<SootMethod> mopMethods = getMopMethods(mopSpecsDir, apkInfo);
//		System.out.println("MOP: ");
//		mopMethods.forEach(System.out::println);

		app.constructCallgraph();
		CallGraph callGraph = Scene.v().getCallGraph();

		DefaultDirectedGraph<String, DefaultEdge> graph = toGraph(callGraph, apkInfo);
		DijkstraShortestPath<String, DefaultEdge> dijkstra = new DijkstraShortestPath<>(graph);

		for (SootClass clazz : app.getEntrypointClasses()) {
			if (isAppClass(clazz, apkInfo)) {
				for (SootMethod method : clazz.getMethods()) {
					if (!method.isConstructor()) {// && (method.isPublic() || method.isProtected())) {
						for (SootMethod mopMethod : mopMethods) {
							System.out.println("teste=" + method.getSignature() + " >>> " + mopMethod.getSignature());
							if (graph.containsVertex(method.getSignature()) && graph.containsVertex(mopMethod.getSignature())) {
								GraphPath<String, DefaultEdge> path = dijkstra.getPath(method.getSignature(), mopMethod.getSignature());
								if (path != null) {
									System.out.println("METHOD: " + method.getSubSignature() + " >>> " + mopMethod.getSubSignature());
									System.out.println("\t - " + String.join(" >>> ", path.getVertexList()));
								}
							}
						}
					}
				}
			}
		}

	}

	private Set<SootMethod> getMopMethods(String mopSpecsDir, ApkInfo apkInfo) throws MOPException {
		Set<SootMethod> sootMopMethods = new HashSet<>();

		JavamopFacade javamopFacade = new JavamopFacade();
		Set<MopMethod> mopMethods = javamopFacade.listUsedMethods(mopSpecsDir, false);

		for (SootClass c : Scene.v().getApplicationClasses()) {
			if (isAppClass(c, apkInfo)) {
				System.out.println("CLASSE: " + c.getName());
				for (SootMethod m : c.getMethods()) {
					UnitPatchingChain units = m.retrieveActiveBody().getUnits();
					Iterator<Unit> it = units.iterator();
					while (it.hasNext()) {
						Stmt stmt = (Stmt) it.next();
						if (stmt.containsInvokeExpr()) {
							InvokeExpr invokeExpr = stmt.getInvokeExpr();
							if (isMop(invokeExpr, mopMethods)) {
								System.out.println("MOP ********************* " + invokeExpr.getMethod().getDeclaringClass().getName() + " :: " + invokeExpr.getMethod().getSubSignature());
								sootMopMethods.add(invokeExpr.getMethod());
							}
						}
					}
				}
			}
		}

		return sootMopMethods;
	}

	private DefaultDirectedGraph<String, DefaultEdge> toGraph(CallGraph callGraph, ApkInfo apkInfo) {
		DefaultDirectedGraph<String, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);

		for (Edge edge : callGraph) {
//			if (AndroidUtil.isAndroidMethod(edge.getSrc().method()) || AndroidUtil.isAndroidMethod(edge.getTgt().method())) {
//				continue;
//			}

//			if (isAppClass(edge.getSrc().method().getDeclaringClass(), apkInfo) && isAppClass(edge.getTgt().method().getDeclaringClass(), apkInfo)) {
			if (isAppClass(edge.getSrc().method().getDeclaringClass(), apkInfo)){ //&& isAppClass(edge.getTgt().method().getDeclaringClass(), apkInfo)) {
				MethodOrMethodContext src = edge.getSrc();
				MethodOrMethodContext tgt = edge.getTgt();

				g.addVertex(src.method().getSignature());
				g.addVertex(tgt.method().getSignature());
				g.addEdge(src.method().getSignature(), tgt.method().getSignature());
				System.out.println("edge(" + src.method().getSubSignature() + " >>> " + tgt.method().getSubSignature());
			}

		}

		return g;
	}

//	private boolean filter(Edge edge) {
//		edge.getSrc().method().getSignature();
//
//	}

	private boolean isMop(InvokeExpr invokeExpr, Set<MopMethod> mopMethods) {
		for (MopMethod mopMethod : mopMethods) {
			if (mopMethod.getClassName().equals(invokeExpr.getMethod().getDeclaringClass().getName()) && mopMethod.getName().equals(invokeExpr.getMethod().getName())) {
				return true;
			}
		}
		return false;
	}

	private boolean isAppClass(SootClass c, ApkInfo apkInfo) {
		return checkPackage(c, apkInfo.getManifestPackage()) || checkPackage(c, apkInfo.getAppPackage());
	}

	private boolean checkPackage(SootClass c, String appPackage) {
		return c.getName().startsWith(appPackage) && !c.getName().startsWith(appPackage + ".R");
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

		TesteGraph t = new TesteGraph();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
