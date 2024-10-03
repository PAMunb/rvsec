package br.unb.cic.rvsec.reach.analysis;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fdu.se.sootanalyze.model.out.ApkInfoOut;
import com.fdu.se.sootanalyze.model.out.ListenerInfoOut;
import com.fdu.se.sootanalyze.model.out.MethodInfoOut;
import com.fdu.se.sootanalyze.model.out.WidgetInfoOut;
import com.fdu.se.sootanalyze.model.out.WindowInfoOut;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.util.AndroidUtil;
import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

public class ReachabilityAnalysis {
	private static final Logger log = LoggerFactory.getLogger(ReachabilityAnalysis.class);

	private final AppInfo appInfo;
	private final Set<SootMethod> mopMethods;
	private final Set<SootMethod> entryPoints;
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
		
		// All reachable methods (from an entrypoint)
		Map<SootMethod, Path> reachableMethods = getReachableMethods(entryPoints);

		// for each class (in package declared in manifest)
		for (SootClass sootClass : getApplicationClasses()) {
			RvsecClass clazz = createRvsecClass(sootClass);
			result.add(clazz);
			log.debug("Processing class: " + clazz.getClassName());
			// for each method of the clazz
			for (SootMethod sootMethod : sootClass.getMethods()) {
				RvsecMethod method = new RvsecMethod(sootMethod);
				clazz.addMethod(method);

				// check if the method is reachable
				if(reachableMethods.containsKey(sootMethod)) {
					method.setReachable(true);
					method.setPossiblePath(reachableMethods.get(sootMethod));
				}

				// analyses reachability between the current method and methods defined in MOP specs
				processReachabilityToMop(method, sootMethod, mopMethods);
			}
		}

		return result;
	}

	public void complementReachabilityAnalysis(Set<RvsecClass> result, ApkInfoOut apkInfo) {
		// complement reachability analysis with gesda results (listener/callbacks)
		processGesdaResults(result, apkInfo);

		processActivityLifecycleCallbacks(result);
	}

	private void processGesdaResults(Set<RvsecClass> result, ApkInfoOut apkInfo) {		
		if (apkInfo == null) {
			return;
		}
		log.debug("Process GESDA info ...");
		for (WindowInfoOut window : apkInfo.getWindows()) {
			processGesdaWindow(result, window);
			if(window.getOptionsMenu() != null) {
				WindowInfoOut optionsMenu = window.getOptionsMenu();
				processGesdaWindow(result, optionsMenu);
			}
		}
	}

	private void processGesdaWindow(Set<RvsecClass> result, WindowInfoOut window) {
		for (WidgetInfoOut widget : window.getWidgets()) {
			for (ListenerInfoOut listener : widget.getListeners()) {
				if (listener.getCallbackMethod() != null) {
					MethodInfoOut callbackMethod = listener.getCallbackMethod();
					RvsecMethod method = getMethodInResults(callbackMethod.getSignature(), result);
					if (method != null) {
						method.setReachable(true);
						log.debug("reachable: " + method.getMethodSignature());
					} 
				}
			}
		}
	}

	private void processActivityLifecycleCallbacks(Set<RvsecClass> result) {
		List<String> activityLifecycleMethods = List.of("onCreate", "onStart", "onResume", 
				"onPause", "onStop", "onDestroy", "onSaveInstanceState", "onRestoreInstanceState");
		for (RvsecClass clazz : result) {
			for (RvsecMethod method : clazz.getMethods()) {
				for (String callBack : activityLifecycleMethods) {
					if (method.getMethodName().equals(callBack)) {
						method.setReachable(true);
					}
				}
			}
		}
	}

	private RvsecMethod getMethodInResults(String signature, Set<RvsecClass> result) {
		for (RvsecClass clazz : result) {
			for (RvsecMethod method : clazz.getMethods()) {
				if (method.getMethodSignature().equals(signature)) {
					return method;
				}
			}
		}
		return null;
	}

	private RvsecClass createRvsecClass(SootClass sootClass) {
		boolean isActivity = false;
		boolean isMainActivity = false;
		ActivityInfo info = getActivityInfo(sootClass);
		if (info != null) {
			isActivity = true;
			isMainActivity = info.isMain();
		}
		return new RvsecClass(sootClass, isActivity, isMainActivity);
	}

	private void processReachabilityToMop(RvsecMethod method, SootMethod sootMethod, Set<SootMethod> mopMethods) {
		for (SootMethod mopMethod : mopMethods) {
			Optional<Path> pathOpt = analysisStrategy.findPath(sootMethod, mopMethod);
			if (pathOpt.isPresent()) {
				boolean isSuccessor = analysisStrategy.isSuccessor(sootMethod, mopMethod);
				if (isSuccessor) {
					method.setDirectlyReachesMop(true);
				}
				method.setReachesMop(true);
				method.addPathToMop(pathOpt.get());
			}
		}
	}

	private Map<SootMethod, Path> getReachableMethods(Set<SootMethod> entryPoints) {
		// Visit each method/node of the callgraph and verifies if there is a path
		// between an entrypoint and the method being visited.
		// (the entrypoint reaches the method ... the method is reachable)
		log.debug("Finding reachable methods ...");
		Map<SootMethod, Path> reachableMethods = new HashMap<>();
		for (SootClass clazz : getApplicationClasses()) {
			for (SootMethod method : clazz.getMethods()) {
				if(reachableMethods.containsKey(method)) {
					continue;
				}
				for (SootMethod entrypoint : entryPoints) {
					if (!entrypoint.equals(method)) {
						Optional<Path> pathOpt = analysisStrategy.findPath(entrypoint, method);
						if (pathOpt.isPresent()) {
							Path path = pathOpt.get();
							reachableMethods.put(method, path);
						}
					}
				}
			}
		}
		return reachableMethods;
	}

	private ActivityInfo getActivityInfo(SootClass clazz) {
		return appInfo.getActivities().stream()
				.filter(info -> info.getName().equals(clazz.getName()))
				.findFirst()
				.orElse(null);
	}

	private List<SootClass> getApplicationClasses() {
		return Scene.v().getApplicationClasses().stream()
				.filter(clazz -> AndroidUtil.isClassInApplicationPackage(clazz, appInfo))
				.collect(Collectors.toList());
	}

}
