package br.unb.cic.rvsec.taint.reach;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.jgrapht.GraphPath;
import org.jgrapht.alg.shortestpath.DijkstraShortestPath;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.MopFacade;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import javamop.util.MOPException;
import soot.MethodOrMethodContext;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.jimple.toolkits.callgraph.Filter;
import soot.jimple.toolkits.callgraph.ReachableMethods;
import soot.util.queue.QueueReader;

public class TesteCallgraph01 {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);				
		
		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
		
		app.constructCallgraph();
		CallGraph callGraph = Scene.v().getCallGraph();
		
		MopFacade mopFacade = new MopFacade();
		Set<SootMethod> mopMethods = mopFacade.getMopMethods(mopSpecsDir, apkInfo);
		
		AndroidCallGraphFilter callGraphFilter = new AndroidCallGraphFilter(apkInfo, mopMethods);
		
		Collection<SootMethod> entryPoints = getEntryPoints(callGraphFilter);
				
		ReachableMethods reachableMethods = new ReachableMethods(callGraph, entryPoints.iterator(), new Filter(callGraphFilter::isValidEdge));		
		QueueReader<MethodOrMethodContext> methods = reachableMethods.listener();
		System.out.println("ReachableMethods....");
		while (methods.hasNext()) {
			SootMethod mopReachableMethod = methods.next().method();
			if(mopMethods.contains(mopReachableMethod)) {
				System.out.println("MOP="+mopReachableMethod.getSignature());
			}
//			
//			String tmp = methods.next().method().getSignature().toString();
//			if (tmp.contains("MessageDigest") || tmp.contains("cryptoapp")) {
//				System.out.println("*** " + tmp);
//			}
		}

//		//TODO mudar a estrutura de dados pra pegar todos os caminhos?
//		Map<SootMethod,SootMethod> reachableMethods = getAllReachableMethods(entryPoints);
		DefaultDirectedGraph<SootMethod,DefaultEdge> graph = getAllReachableMethodsGraph(entryPoints, callGraphFilter);
		DijkstraShortestPath<SootMethod, DefaultEdge> dijkstra = new DijkstraShortestPath<>(graph);
		for(SootMethod entryPoint: entryPoints) {
			for(SootMethod mopMethod: mopMethods) {
				System.out.println("hasPath??? "+entryPoint.getSignature()+" :::: "+mopMethod.getSignature());
				GraphPath<SootMethod,DefaultEdge> path = dijkstra.getPath(entryPoint, mopMethod);
				if(path != null) {
					System.out.println("%%%%% "+entryPoint.getSignature()+" >>> "+entryPoint.getSignature());
					String pathString = path.getVertexList().stream().map((Function<? super SootMethod, ? extends String>) SootMethod::getSignature).collect(Collectors.joining(" >>> "));
					System.out.println(pathString);
				}
			}
		}
		
		
		
		
//		System.out.println("Entry Points: ");
//		app.getEntrypointClasses().forEach(System.out::println);		
//		for (SootClass clazz : app.getEntrypointClasses()) {
////			for (SootMethod method : clazz.getMethods()) {				
////				
////			}
//			System.out.println(clazz);
//		}
				
//		show(callGraph);
//
//		teste01(apkPath, callGraph);
//
//		teste02();

	}


private Collection<SootMethod> getEntryPoints(AndroidCallGraphFilter filter) {
	Collection<SootMethod> entryPoints = new HashSet<>();
	System.out.println("get entrypoints ...");
	for (SootClass clazz : filter.getValidClasses()) {
		System.out.println("clazz="+clazz.getName());
		for (SootMethod method : clazz.getMethods()) {
			if(filter.isValidMethod(method)) {
				System.out.println("entrypoint: "+method.getSignature());
				entryPoints.add(method);
			}
		}
	}
	return entryPoints;
}


	private void show(CallGraph cg) {
		for (Edge edge : cg) {
			MethodOrMethodContext src = edge.getSrc();
			MethodOrMethodContext tgt = edge.getTgt();
			
			
		}
	}


	// A Breadth-First Search algorithm to get all reachable methods from the entryPoints list in the callgraph
    // The output is a map from reachable methods to their parents
    public Map<SootMethod, SootMethod> getAllReachableMethods(Collection<SootMethod> entryPoints){
        CallGraph callgraph = Scene.v().getCallGraph();
        List<SootMethod> queue = new ArrayList<>(entryPoints);
        Map<SootMethod, SootMethod> parentMap = initializeParentMap(entryPoints);
        for(int i=0; i< queue.size(); i++){
            SootMethod method = queue.get(i);
            for (Iterator<Edge> it = callgraph.edgesOutOf(method); it.hasNext(); ) {
                Edge edge = it.next();
                SootMethod childMethod = edge.tgt();
                if(parentMap.containsKey(childMethod))
                    continue;
                parentMap.put(childMethod, method);
                queue.add(childMethod);
            }
        }
        return parentMap;
    }
    
    public DefaultDirectedGraph<SootMethod, DefaultEdge> getAllReachableMethodsGraph(Collection<SootMethod> entryPoints, AndroidCallGraphFilter filter){
    	DefaultDirectedGraph<SootMethod, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);
        CallGraph callgraph = Scene.v().getCallGraph();
        List<SootMethod> queue = new ArrayList<>(entryPoints);
        for(int i=0; i< queue.size(); i++){
            SootMethod method = queue.get(i);
            if(filter.isValidMethod(method)) {
            for (Iterator<Edge> it = callgraph.edgesOutOf(method); it.hasNext(); ) {
                Edge edge = it.next();
                SootMethod childMethod = edge.tgt();
                if(filter.isValidMethod(childMethod) && !g.containsEdge(method, childMethod)) {
                	g.addVertex(method);
    				g.addVertex(childMethod);
    				g.addEdge(method, childMethod);
//    				System.out.println("edge(" + method.getSubSignature() + " >>> " + childMethod.getSubSignature());
    				
    				queue.add(childMethod);
                }
            }
            }
        }
        return g;
    }
    
    private Map<SootMethod, SootMethod> initializeParentMap(Collection<SootMethod> entryPoints) {
    	Map<SootMethod, SootMethod> parentMap = new HashMap<>();
    	for (SootMethod method : entryPoints) {
    		parentMap.put(method, null);
		}
    	return parentMap;
    }


//	private void teste01(String apkPath, CallGraph callGraph) {
//		int classIndex = 0;
//		AndroidCallGraphFilter androidCallGraphFilter = new AndroidCallGraphFilter(AndroidUtil.getPackageName(apkPath));
//		for (SootClass sootClass : androidCallGraphFilter.getValidClasses()) {
//			System.out.println(String.format("Class %d: %s", ++classIndex, sootClass.getName()));
//			for (SootMethod sootMethod : sootClass.getMethods()) {
//				int incomingEdge = 0;
//				for (Iterator<Edge> it = callGraph.edgesInto(sootMethod); it.hasNext(); incomingEdge++, it.next())
//					;
//				int outgoingEdge = 0;
//				for (Iterator<Edge> it = callGraph.edgesOutOf(sootMethod); it.hasNext(); outgoingEdge++, it.next())
//					;
//				System.out.println(String.format("\tMethod %s, #IncomeEdges: %d, #OutgoingEdges: %d", sootMethod.getName(), incomingEdge, outgoingEdge));
//			}
//		}
//	}
	
	private void teste02() {
		ReachableMethods reachableMethods = Scene.v().getReachableMethods();
		QueueReader<MethodOrMethodContext> methods = reachableMethods.listener();

		System.out.println("ReachableMethods");
		while (methods.hasNext()) {
			String tmp = methods.next().method().getSignature().toString();
			if (tmp.contains("MessageDigest")) {// || tmp.contains("digest")) {
				System.out.println("*** " + tmp);
			}
		}
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

		TesteCallgraph01 t = new TesteCallgraph01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
