package br.unb.cic.rvsec.reach;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xmlpull.v1.XmlPullParserException;

import com.beust.jcommander.JCommander;
import com.fdu.se.sootanalyze.model.out.ApkInfoOut;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import br.unb.cic.rvsec.reach.analysis.ReachabilityAnalysis;
import br.unb.cic.rvsec.reach.analysis.ReachabilityStrategy;
import br.unb.cic.rvsec.reach.analysis.SootReachabilityStrategy;
import br.unb.cic.rvsec.reach.cli.CommandLineArgs;
import br.unb.cic.rvsec.reach.gesda.GesdaReader;
import br.unb.cic.rvsec.reach.model.Path;
import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.mop.MopFacade;
import br.unb.cic.rvsec.reach.writer.CsvWriter;
import br.unb.cic.rvsec.reach.writer.Writer;
import br.unb.cic.rvsec.reach.writer.WriterFactory;
import br.unb.cic.rvsec.reach.writer.WriterType;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;

public class Main {
	private static final Logger log = LoggerFactory.getLogger(Main.class);

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String resultsFile, String gesdaFile, Writer writer, boolean checkOnlyInAppPackage, int timeout) throws Exception {
		log.info("Executing ...");

		// get application info
		AppInfo appInfo = AppReader.readApk(apkPath);
		log.info("App info: " + appInfo);

		// initialize soot (infoflow)
		SetupApplication infoflow = SootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath, timeout);

		// methods used in MOP specifications that are called in apk/package
		Set<SootMethod> targetMethods = getMopMethods(mopSpecsDir, appInfo, checkOnlyInAppPackage);

		// the list of all activities (with inner classes)
		List<SootClass> activities = getActivitiesWithInnerClasses(appInfo);

		// Entrypoints: set of methods (public or protected) of each activity
		Set<SootMethod> entryPoints = getEntrypoints(activities, appInfo);

		log.info("Constructing callgraph ...");
		infoflow.constructCallgraph();

		ReachabilityStrategy<SootMethod, Path> analysisStrategy = new SootReachabilityStrategy(); // TODO vir como parametro (CLI)
//		ReachabilityStrategy<SootMethod, Path> analysisStrategy = new JGraphReachabilityStrategy();
		Set<RvsecClass> result = reachabilityAnalysis(appInfo, targetMethods, entryPoints, analysisStrategy, gesdaFile);

		writeResults(result, resultsFile, writer);
	}

	private Set<RvsecClass> reachabilityAnalysis(AppInfo appInfo, Set<SootMethod> targetMethods, Set<SootMethod> entryPoints, ReachabilityStrategy<SootMethod, Path> analysisStrategy,
			String gesdaFile) throws IOException, XmlPullParserException {

//		System.out.println("*************************************");
//		ReachableMethods reachableMethods = Scene.v().getReachableMethods();
//		QueueReader<MethodOrMethodContext> listener = reachableMethods.listener();
//		while (listener.hasNext()) {
//			MethodOrMethodContext next = listener.next();
//			SootMethod method = next.method();
//			if (method.getDeclaringClass().getPackageName().contains(appInfo.getPackage())
//					|| method.getDeclaringClass().getPackageName().contains("java.security")) {
//				System.out.println(next.method().getSignature());
//			}
//		}
//		System.out.println("************************************* FIM");

		ReachabilityAnalysis analysis = new ReachabilityAnalysis(appInfo, targetMethods, entryPoints);
		Set<RvsecClass> result = analysis.reachabilityAnalysis(analysisStrategy);

		if (gesdaFile == null) {
			return result;
		}
		ApkInfoOut apkInfo = GesdaReader.read(gesdaFile);

		analysis.complementReachabilityAnalysis(result, apkInfo);

		return result;
	}

	private void writeResults(Set<RvsecClass> result, String resultsFile, Writer writer) {
		writer.write(result, new File(resultsFile));
		log.info("Results saved in: " + resultsFile);
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
		return sootMethod.isConcrete() && !sootMethod.isConstructor() && !sootMethod.isPrivate();
	}

	private Set<SootMethod> getMopMethods(String mopSpecsDir, AppInfo appInfo, boolean checkOnlyInAppPackage) throws MOPException {
		MopFacade mopFacade = new MopFacade();
		Set<SootMethod> targetMethods = mopFacade.getMopMethodsUsed(mopSpecsDir, appInfo, checkOnlyInAppPackage);
		log.info("MOP methods: " + targetMethods.size());
		targetMethods.forEach(m -> log.debug(" - " + m.getSignature()));
		return targetMethods;
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
		long start = System.currentTimeMillis();

		executeCLI(args);
//		executeTest();

		long time = System.currentTimeMillis() - start;
		log.info("Executed in " + (time / 1000) + " seconds.");
	}

	private static void executeCLI(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		JCommander jc = JCommander.newBuilder().addObject(jArgs).build();

		if (args.length == 0) {
			jc.usage();
			return;
		}

		jc.parse(args);

		String androidPlatformsDir = jArgs.getAndroidDir();
		String mopSpecsDir = jArgs.getMopSpecsDir();
		String rtJarPath = jArgs.getRtJar();
		String apk = jArgs.getApk();
		String outputFile = jArgs.getOutputFile();
		String gesdaFile = jArgs.getGesdaFile();
		int timeout = jArgs.getTimeout();
		boolean checkOnlyInAppPackage = !jArgs.isFull();
		boolean debug = jArgs.isDebug();
		WriterType writerType = jArgs.getWriterType();
		Writer writer = WriterFactory.fromType(writerType);

		if (debug) {
			ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
			root.setLevel(ch.qos.logback.classic.Level.DEBUG);
		}

		log.info("Starting analysis ...");
		Main main = new Main();
		try {
			main.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, outputFile, gesdaFile, writer, checkOnlyInAppPackage, timeout);
			log.info("Analysis completed");
		} catch (Exception e) {
			e.printStackTrace();
		}

	}

	private static void executeTest() {
		String rvsecDir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec";
		String mopSpecsDir = rvsecDir + "/rvsec/rvsec-mop/src/main/resources/jca";
//		String apksDir = rvsecDir + "/rv-android/apks_exp02/";
		String apksDir = "/home/pedro/desenvolvimento/RV_ANDROID/ALL_APKS";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
//		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/platforms-sable";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

//		String apk = apksDir + "cryptoapp.apk";
//		String apk = apksDir + "com.blogspot.e_kanivets.moneytracker_38.apk";
//		String apk = apksDir + "com.gianlu.dnshero_40.apk";
//		String apk = apksDir + "com.github.axet.hourlyreminder_476.apk";
//		String apk = apksDir + "com.pindroid_69.apk";
//		String apk = apksDir + "com.rafapps.simplenotes_7.apk";
//		String apk = apksDir + "com.thibaudperso.sonycamera_24.apk";
//		String apk = apksDir + "li.klass.fhem_141.apk";
//		String apk = apksDir + "org.pulpdust.lesserpad_42.apk";
//		String apk = apksDir + "org.secuso.privacyfriendlydicer_8.apk";
//		String apk = apksDir + "org.secuso.privacyfriendlyludo_5.apk";

		String gesdaFile = null;
		boolean checkOnlyInAppPackage = false;
		int timeout = 300;

		Writer writer = new CsvWriter();
		String outFile = "/home/pedro/tmp/teste.csv";
//		Writer writer = new JsonWriter();
//		String outFile = "/home/pedro/tmp/teste.json";

//		Main main = new Main();
//		try {
//			main.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, outFile, gesdaFile, writer, checkOnlyInAppPackage, timeout);
//		} catch (Exception e) {
//			e.printStackTrace();
//		}
		
		try (Stream<java.nio.file.Path> paths = Files.walk(java.nio.file.Path.of(apksDir))) {
			long total_time = 0;
			Map<String, Long> map = new HashMap<>();
			Map<String, String> errors = new HashMap<>();
			Main main = new Main();			
            List<java.nio.file.Path> apks = paths.filter(path -> path.toString().endsWith(".apk")).collect(Collectors.toList());
            int total_apks = apks.size();
            int cont = 0;
			for (java.nio.file.Path path : apks) {
				if(map.containsKey(path.getFileName().toString())) {
					continue;
				}
				String apk = path.toAbsolutePath().toString();
				System.out.println(String.format("\n ************************************* APK(%d/%d): %s", ++cont, total_apks, apk));
				long start = System.currentTimeMillis();
				outFile = String.format("/home/pedro/tmp/RV/reach/%s.csv", path.getFileName().toString());
				try {
					main.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, outFile, gesdaFile, writer, checkOnlyInAppPackage, timeout);
					long end = System.currentTimeMillis();
					long exec_time = end - start;
					total_time += exec_time;
					map.put(path.getFileName().toString(), exec_time);
					System.out.println("exec_time="+(exec_time/1000)+" sec.");
				} catch (Exception e) {
					e.printStackTrace();
					errors.put(path.getFileName().toString(), e.getMessage());
				}				
			}
			System.out.println("\n\nRESULT: ");
			map.forEach((k,v) -> System.out.println(k+"="+(v/1000)));
			System.out.println("TOTAL: "+(total_time/1000)+" sec.");
			System.out.println("APKS analisados: "+map.size());
			System.out.println(".............................................");
			System.out.println("\nERROS: "+errors.size());
			errors.forEach((k,v) -> System.out.println(k+"="+v));
        } catch (Exception e) {
            e.printStackTrace();
        }



	}

//	com.blogspot.e_kanivets.moneytracker_38.apk
//	com.gianlu.dnshero_40.apk
//	com.github.axet.hourlyreminder_476.apk
//	com.pindroid_69.apk
//	com.rafapps.simplenotes_7.apk
//	com.thibaudperso.sonycamera_24.apk
//	li.klass.fhem_141.apk
//	org.pulpdust.lesserpad_42.apk
//	org.secuso.privacyfriendlydicer_8.apk
//	org.secuso.privacyfriendlyludo_5.apk

}
