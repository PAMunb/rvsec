package br.unb.cic.rvsec.reach;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xmlpull.v1.XmlPullParserException;

import com.fdu.se.sootanalyze.SootAnalyze;
import com.fdu.se.sootanalyze.model.WindowNode;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import br.unb.cic.rvsec.reach.analysis.ReachabilityAnalysis;
import br.unb.cic.rvsec.reach.analysis.ReachabilityStrategy;
import br.unb.cic.rvsec.reach.analysis.SootReachabilityStrategy;
import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;
import br.unb.cic.rvsec.reach.mop.MopFacade;
import br.unb.cic.rvsec.reach.writer.CsvWriter;
import br.unb.cic.rvsec.reach.writer.Writer;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;

public class Main {
	private static final Logger log = LoggerFactory.getLogger(Main.class);

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String resultsFile) throws Exception {
		log.info("Executing ...");

		// get some application info
		AppInfo appInfo = AppReader.readApk(apkPath);
		log.info("App info: " + appInfo);

		// initialize soot (infoflow)
		SetupApplication infoflow = SootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		// methods used in MOP specifications
		Set<SootMethod> mopMethods = getMopMethods(mopSpecsDir, appInfo);

		// the list of all activities (with inner classes)
		List<SootClass> activities = getActivitiesWithInnerClasses(appInfo);

		// Entrypoints: methods (public or protected) of each activity
		Set<SootMethod> entryPoints = getEntrypoints(activities, appInfo);

		log.info("Constructing call graph ...");
		infoflow.constructCallgraph();

		ReachabilityStrategy<SootMethod, Path> analysisStrategy = new SootReachabilityStrategy(); //TODO vir como parametro (CLI)
		// ReachabilityStrategy<SootMethod, Path> analysisStrategy = new JGraphReachabilityAnalysis();
		Set<RvsecClass> result = reachabilityAnalysis(appInfo, infoflow, mopMethods, entryPoints, analysisStrategy);
		
		Writer writer = new CsvWriter(); //TODO vir como parametro (CLI)
		writeResults(result, resultsFile, writer);
	}

	private Set<RvsecClass> reachabilityAnalysis(AppInfo appInfo, SetupApplication infoflow, Set<SootMethod> mopMethods, Set<SootMethod> entryPoints, ReachabilityStrategy<SootMethod, Path> analysisStrategy) throws IOException, XmlPullParserException {
		ReachabilityAnalysis analysis = new ReachabilityAnalysis(appInfo, mopMethods, entryPoints);

		Set<RvsecClass> result = analysis.reachabilityAnalysis(analysisStrategy);

		SootAnalyze gesda = new SootAnalyze();
		gesda.init(appInfo, infoflow);
		List<WindowNode> windows = gesda.analyze();
		
		analysis.complementReachabilityAnalysis(result, windows);
		
		return result;
	}
	
	private void writeResults(Set<RvsecClass> result, String resultsFile, Writer writer) {
		writer.write(result, new File(resultsFile));
		log.info("Results saved in: "+resultsFile);

		log.info("Results: "+result.size());
		for (RvsecClass clazz : result) {
			log.info("CLASS: "+clazz.getClassName()+", isActivity="+clazz.isActivity());
			for (RvsecMethod method : clazz.getMethods()) {
				log.info("   - "+method);
			}
		}
	}

	private Set<SootMethod> getEntrypoints(List<SootClass> activities, AppInfo appInfo) {
		Set<SootMethod> entryPoints = new HashSet<>();
		for (SootClass clazz : activities) {
			for (SootMethod method : clazz.getMethods()) {
				if (isValidEntrypoint(method, appInfo)) {
					entryPoints.add(method);
				}
			}
		}
		log.info("EntryPoints: " + entryPoints.size());
		entryPoints.forEach(m -> log.debug(" - " + m.getSignature()));
		return entryPoints;
	}

	private boolean isValidEntrypoint(SootMethod sootMethod, AppInfo appInfo) {
		if(sootMethod.isConstructor() || sootMethod.isPrivate()) {
			return false;
		}
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

	
	public static void main(String[] args) {
		execute(args);
	}

	private static void execute(String[] args) {
		// TODO Auto-generated method stub
		executeTest();
//		executeCLI();
	}

	private static void executeTest() {
		String mopSpecsDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

//		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
////		String sinksFile = "";
//		String callbacksFile = "";

		String outFile = "/home/pedro/tmp/teste.csv";
		
		Main main = new Main();
		try {
			main.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, outFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
	
}
