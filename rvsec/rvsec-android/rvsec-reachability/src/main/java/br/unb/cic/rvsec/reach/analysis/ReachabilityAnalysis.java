package br.unb.cic.rvsec.reach.analysis;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import com.esotericsoftware.minlog.Log;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;
import br.unb.cic.rvsec.reach.util.AndroidUtil;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

public class ReachabilityAnalysis {
	
	private AppInfo appInfo;	
	private Set<SootMethod> mopMethods;
	private Set<SootMethod> entryPoints;
	private ReachabilityStrategy<SootMethod, Path> analysisStrategy;
	
	public ReachabilityAnalysis(AppInfo appInfo, Set<SootMethod> mopMethods, Set<SootMethod> entryPoints) {
		this.appInfo = appInfo;
		this.mopMethods = mopMethods;
		this.entryPoints = entryPoints;
	}

	public Set<RvsecClass> reachabilityAnalysis(ReachabilityStrategy<SootMethod, Path> strategy) {
		Set<RvsecClass> result = new HashSet<>();
		
		this.analysisStrategy = strategy;
		analysisStrategy.initialize(Scene.v().getCallGraph(), appInfo);

		//for each class (in package declared in manifest)
		for (SootClass sootClass : getApplicationClasses()) {
			RvsecClass clazz = createRvsecClass(sootClass);
			result.add(clazz);
			Log.debug("Processing class: "+clazz.getClassName());
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

	private RvsecClass createRvsecClass(SootClass sootClass) {
		boolean isActivity = false;
		boolean isMainActivity = false;
		ActivityInfo info = getActivityInfo(sootClass);
		if(info != null) {
			isActivity = true;
			isMainActivity = info.isMain();
		}
		return new RvsecClass(sootClass, isActivity, isMainActivity);
	}

	private void processReachabilityToMop(RvsecMethod method, SootMethod sootMethod, Set<SootMethod> mopMethods) {
		for (SootMethod mopMethod : mopMethods) {
			Optional<Path> pathOpt = analysisStrategy.findPath(sootMethod, mopMethod);
			if(pathOpt.isPresent()) {
				boolean isSuccessor = analysisStrategy.isSuccessor(sootMethod, mopMethod);
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
	
	private Map<SootMethod, Path> getReachableMethods(Set<SootMethod> entryPoints) {
		Map<SootMethod, Path> reachableMethods = new HashMap<>();
		for (SootClass clazz : getApplicationClasses()) {
			for (SootMethod method : clazz.getMethods()) {
				for (SootMethod entrypoint : entryPoints) {
					if (!entrypoint.equals(method)) {
						Optional<Path> path = analysisStrategy.findPath(entrypoint, method);
						if(path.isPresent()) {
							reachableMethods.put(method, path.get());
						}
					}
				}
			}
		}
		return reachableMethods;
	}
	
	private ActivityInfo getActivityInfo(SootClass clazz) {
		for (ActivityInfo info : appInfo.getActivities()) {
			if (info.getName().equals(clazz.getName())) {
				return info;
			}
		}
		return null;
	}
	
	private List<SootClass> getApplicationClasses() {
		return Scene.v().getApplicationClasses().stream()
				.filter(clazz -> AndroidUtil.isClassInApplicationPackage(clazz, appInfo))
				.collect(Collectors.toList());
	}
	
}
