package br.unb.cic.rvsec.reach;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import org.jgrapht.Graph;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import br.unb.cic.rvsec.reach.analysis.ReachabilityAnalysis;
import br.unb.cic.rvsec.reach.analysis.SootReachabilityAnalysis;
import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;
import br.unb.cic.rvsec.reach.mop.MopFacade;
import br.unb.cic.rvsec.reach.util.AndroidUtil;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class Teste01 {
	private static Logger log = LoggerFactory.getLogger(Teste01.class);

	private ReachabilityAnalysis<SootMethod, Path> analysis;

	private AppInfo appInfo;

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String resultsFile) throws Exception {
		log.info("Executing ...");

		// get some application info
		appInfo = AppReader.readApk(apkPath);
		log.info("App info: " + appInfo);

		// initialize soot (infoflow)
		SetupApplication app = SootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		// methods used in MOP specifications
		Set<SootMethod> mopMethods = getMopMethods(mopSpecsDir, appInfo);

		// the list of all activities (with inner classes)
		List<SootClass> activities = getActivitiesWithInnerClasses(appInfo);

		// Entrypoints: methods (public or protected) of each activity
		Set<SootMethod> entryPoints = getEntrypoints(activities, appInfo);

		log.info("Constructing call graph ...");
		app.constructCallgraph();

		//
		Set<RvsecClass> result = reachabilityAnalysis(mopMethods, activities, entryPoints);

		writeResults(result, resultsFile);

		System.out.println("FIM DE FESTA !!!");
	}

	private void writeResults(Set<RvsecClass> result, String resultsFile) {
		log.info("Results: "+result.size());
		for (RvsecClass clazz : result) {
			log.info("CLASS: "+clazz.getClassName()+", isActivity="+clazz.isActivity());
			for (RvsecMethod method : clazz.getMethods()) {
				log.info("   - "+method);
			}
		}
	}

	private Set<RvsecClass> reachabilityAnalysis(Set<SootMethod> mopMethods, List<SootClass> activities, Set<SootMethod> entryPoints) {
		Set<RvsecClass> result = new HashSet<>();
		
//		analysis = new JGraphReachabilityAnalysis();
		analysis = new SootReachabilityAnalysis();	
		analysis.initialize(Scene.v().getCallGraph(), appInfo);

		//for each class (in package declared in manifest)
		for (SootClass sootClass : getApplicationClasses()) {
			RvsecClass clazz = new RvsecClass(sootClass, isMainActivity(sootClass));
			result.add(clazz);
			// for each method of the clazz
			for (SootMethod sootMethod : sootClass.getMethods()) {
				RvsecMethod method = new RvsecMethod(sootMethod);
				clazz.addMethod(method);
				
				// analyses reachability between entrypoints and the current method
				processReachabilityFromEndpoints(method, sootMethod, entryPoints);
				
				// analyses reachability between the current method and methods defined in MOP specs
				processReachabilityToMop(method, sootMethod, mopMethods);				
			}
		}
		return result;
	}

	private void processReachabilityToMop(RvsecMethod method, SootMethod sootMethod, Set<SootMethod> mopMethods) {
		for (SootMethod mopMethod : mopMethods) {
			Optional<Path> pathOpt = analysis.findPath(sootMethod, mopMethod);
			if(pathOpt.isPresent()) {
				boolean isSuccessor = analysis.isSuccessor(sootMethod, mopMethod);
				if(isSuccessor) {
					method.setDirectlyReachesMop(true);							
				}
				method.setReachesMop(true);
				method.addPathToMop(pathOpt.get());
			}
		}
	}

	private void processReachabilityFromEndpoints(RvsecMethod method, SootMethod sootMethod, Set<SootMethod> entryPoints) {
		// Visit each method/node of the callgraph and verifies if there is a path
		// between an entrypoint and the method being visited.
		// (the entrypoint reaches the method ... the method is reachable)
		Map<SootMethod, Path> reachableMethods = getReachableMethods(entryPoints);
		
		for (SootMethod reachableMethod : reachableMethods.keySet()) {
			if(reachableMethod.equals(sootMethod)) {
				method.setReachable(true);
				method.setPossiblePath(reachableMethods.get(sootMethod));
				break;
			}
		}		
	}

	private boolean isMainActivity(SootClass clazz) {
		for (ActivityInfo info : appInfo.getActivities()) {
			if (info.getName().equals(clazz.getName())) {
				return true;
			}
		}
		return false;
	}

	/**
	 * @param entryPoints
	 * @return
	 */
	private Map<SootMethod, Path> getReachableMethods(Set<SootMethod> entryPoints) {
		Map<SootMethod, Path> reachableMethods = new HashMap<>();
		for (SootClass clazz : getApplicationClasses()) {
			for (SootMethod method : clazz.getMethods()) {
				for (SootMethod entrypoint : entryPoints) {
					if (!entrypoint.equals(method)) {// && reaches(entrypoint, method)) {
						Optional<Path> path = analysis.findPath(entrypoint, method);
						if(path.isPresent()) {
							reachableMethods.put(method, path.get());
						}
					}
				}
			}
		}
		return reachableMethods;
	}

//	private boolean reaches(SootMethod source, SootMethod target) {
//		Optional<Path> path = analysis.findPath(source, target);
//		if (path.isPresent()) {
//			return true;
//		}
//		return false;
//	}

	private List<SootClass> getApplicationClasses() {
		return Scene.v().getApplicationClasses().stream()
				.filter(clazz -> AndroidUtil.isClassInApplicationPackage(clazz, appInfo))
				.collect(Collectors.toList());
	}

//	private Set<SootMethod> getReachableMethods2(Set<SootMethod> entryPoints) {
//	    Set<SootMethod> reachableMethods = new HashSet<>();
//	    Scene.v().getApplicationClasses().stream()
//	        .filter(clazz -> AndroidUtil.isClassInApplicationPackage(clazz, appInfo))
//	        .flatMap(clazz -> clazz.getMethods().stream())
//	        .forEach(method -> entryPoints.stream()
//	            .filter(entry -> analysis.findPath(entry, method).isPresent())
//	            .findFirst()
//	            .ifPresent(entry -> reachableMethods.add(method)));
//	    return reachableMethods;
//	}

	private Set<SootMethod> getEntrypoints(List<SootClass> activities, AppInfo appInfo) {
		Set<SootMethod> entryPoints = new HashSet<>();
		for (SootClass clazz : activities) {
			for (SootMethod method : clazz.getMethods()) {
				if (isValidEntrypoint(method)) {
					entryPoints.add(method);
				}
			}
		}
		log.info("Entrypoints: " + entryPoints.size());
		entryPoints.forEach(m -> log.debug(" - " + m.getSignature()));
		return entryPoints;
	}

	private boolean isValidEntrypoint(SootMethod sootMethod) {
//		System.out.println("isValidEntrypoint=" + sootMethod);
//		System.out.println("\t-" + sootMethod.getDeclaringClass().declaresMethod(sootMethod.getSubSignature()));
//		System.out.println("\t- abstract=" + sootMethod.isAbstract() + " :: concrete=" + sootMethod.isConcrete() + " :: constructor=" + sootMethod.isConstructor());
//		System.out.println("\t- declared=" + sootMethod.isDeclared() + " :: " + sootMethod.isEntryMethod() + " :: main=" + sootMethod.isMain() + " :: " + sootMethod.isPhantom());
//		System.out.println("\t- numSubSig" + sootMethod.getNumberedSubSignature());
//		System.out.println("\t- numSubSig" + sootMethod.getDeclaration());

//		if (sootMethod.toString().contains("<init>") 
//				|| sootMethod.toString().contains("<clinit>") 
//				|| sootMethod.getName().equals("dummyMainMethod"))
//			return false;
		return true;
	}

	private Set<SootMethod> getMopMethods(String mopSpecsDir, AppInfo appInfo) throws MOPException {
		MopFacade mopFacade = new MopFacade();
		Set<SootMethod> mopMethods = mopFacade.getMopMethods(mopSpecsDir, appInfo);
		log.info("MOP methods: " + mopMethods.size());
		mopMethods.forEach(m -> log.debug(" - " + m.getSignature()));
		return mopMethods;
	}


	private List<SootClass> getActivitiesWithInnerClasses(AppInfo appInfo) {
		List<SootClass> activities = new ArrayList<>();// all activities'window node
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			for (ActivityInfo activityInfo : appInfo.getActivities()) {
				if (clazz.getName().startsWith(activityInfo.getName())) { // include inner classes
//				if (actInfo.getName().equals(clazz.getName())) {
					activities.add(clazz);
				}
			}
		}
		log.info("Activities: " + activities.size());
		activities.forEach(m -> log.debug(" - " + m.getName()));
		return activities;
	}

//	private Collection<SootMethod> getEntryPoints(List<SootClass> activities) {
//		Collection<SootMethod> entryPoints = new HashSet<>();
////		System.out.println("get entrypoints ...");
//		for (SootClass clazz : activities) {
////			System.out.println("clazz=" + clazz.getName());
//			for (SootMethod method : clazz.getMethods()) {
//				if (isValidEntrypoint(method)) {
////					System.out.println("entrypoint: " + method.getSignature());
//					entryPoints.add(method);
//				}
//			}
//		}
//		return entryPoints;
//	}

	private Graph<SootMethod, DefaultEdge> toJGraph(CallGraph callGraph, AppInfo appInfo) {
		Graph<SootMethod, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);
		System.out.println("CallGraph (soot) = " + callGraph.size());
		for (Edge edge : callGraph) {
			if (isValid(edge, appInfo)) {
				g.addVertex(edge.src());
				g.addVertex(edge.tgt());
				if (g.containsEdge(edge.src(), edge.tgt())) {
					System.out.println("******************* JA CONTEM");
				}
				g.addEdge(edge.src(), edge.tgt());
			}
		}
		return g;
	}

	//TODO colocar no util pq o analysis tbm usa (duplicou codigo la)
	private boolean isValid(Edge edge, AppInfo appInfo) {
//		SootClass sourceClass = edge.getSrc().method().getDeclaringClass();
//		return AndroidUtil.isAppClass(sourceClass, appInfo);
		return true;
	}

//	public static Map<SootMethod, List<SootMethod>> analisarAlcancabilidade(CallGraph callGraph, Collection<SootMethod> collection, Set<SootMethod> mopMethods) {
//		Map<SootMethod, List<SootMethod>> alcancabilidade = new HashMap<>();
//
//		for (SootMethod origem : collection) {
//			alcancabilidade.put(origem, new ArrayList<>());
//			Set<SootMethod> visitados = new HashSet<>();
//
//			Queue<SootMethod> fila = new LinkedList<>();
//			fila.add(origem);
//
//			while (!fila.isEmpty()) {
//				SootMethod metodoAtual = fila.poll();
//				visitados.add(metodoAtual);
//
//				Iterator<Edge> it = callGraph.edgesOutOf(metodoAtual);
//				while (it.hasNext()) {
//					Edge e = it.next();
//					SootMethod metodoDestino = e.tgt();
//
//					if (!visitados.contains(metodoDestino)) {
//						fila.add(metodoDestino);
//					}
//
//					if (mopMethods.contains(metodoDestino)) {
//						alcancabilidade.get(origem).add(metodoDestino);
//					}
//				}
//			}
//		}
//
//		return alcancabilidade;
//	}
//
//	public static Map<SootMethod, List<List<SootMethod>>> analisarAlcancabilidade2(CallGraph callGraph, Collection<SootMethod> collection, Set<SootMethod> mopMethods) {
//		Map<SootMethod, List<List<SootMethod>>> resultado = new HashMap<>();
//
//		for (SootMethod origem : collection) {
//			System.out.println("origem=" + origem.getSignature());
//			List<List<SootMethod>> caminhos = new ArrayList<>();
//			Set<SootMethod> visitados = new HashSet<>();
//
//			dfs(callGraph, origem, mopMethods, new ArrayList<>(), caminhos, visitados);
//
//			System.out.println("origem >>>> " + caminhos);
//			resultado.put(origem, caminhos);
//		}
//
//		return resultado;
//	}
//
//	private static void dfs(CallGraph callGraph, SootMethod metodoAtual, Set<SootMethod> mopMethods, List<SootMethod> caminhoAtual, List<List<SootMethod>> caminhos, Set<SootMethod> visitados) {
////        System.out.println("dfs........");
//		visitados.add(metodoAtual);
//		caminhoAtual.add(metodoAtual);
//
//		if (mopMethods.contains(metodoAtual)) {
//			caminhos.add(new ArrayList<>(caminhoAtual));
//		}
//
//		Iterator<Edge> it = callGraph.edgesOutOf(metodoAtual);
//		while (it.hasNext()) {
//			Edge e = it.next();
//			SootMethod proximoMetodo = e.tgt();
//
//			if (!visitados.contains(proximoMetodo)) {
//				dfs(callGraph, proximoMetodo, mopMethods, caminhoAtual, caminhos, visitados);
//			}
//		}
//
//		caminhoAtual.remove(caminhoAtual.size() - 1);
//		visitados.remove(metodoAtual);
//	}

	public static void main(String[] args) {
		String mopSpecsDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

//		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
////		String sinksFile = "";
//		String callbacksFile = "";

		String outFile = "/home/pedro/tmp/teste.csv";

		Teste01 t = new Teste01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, outFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
