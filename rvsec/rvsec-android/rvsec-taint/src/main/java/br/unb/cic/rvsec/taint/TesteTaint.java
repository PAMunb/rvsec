package br.unb.cic.rvsec.taint;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.infoflow.android.data.parsers.PermissionMethodParser;
import soot.jimple.infoflow.results.InfoflowResults;

public class TesteTaint {
//https://github.com/secure-software-engineering/FlowDroid/issues/138
	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile)
			throws MOPException, IOException, XmlPullParserException {
		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);

		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
//		app.constructCallgraph();

		List<String> sinks = getSinks(mopSpecsDir, apkInfo, sourcesAndSinksFile);
//		for (String sourceSinkItem : sinks) {
//			System.out.println(sourceSinkItem);
//		}

		System.out.println("INICIANDO ANALISE .....................");
		InfoflowResults results = app.runInfoflow(PermissionMethodParser.fromStringList(sinks));

		System.out.println("FIM DA ANALISE .....................");
		results.printResults();

//		app.getCollectedSinks().forEach(System.out::println);

		System.out.println("FIM DE FESTA !!!");
	}

	private List<String> readSourcesAndSinksFile(String sourcesAndSinksFile) throws IOException {
		List<String> data = new ArrayList<>();
		try (FileReader fileReader = new FileReader(sourcesAndSinksFile)) {
			String line;
			BufferedReader br = new BufferedReader(fileReader);
			try (br) {
				while ((line = br.readLine()) != null) {
					data.add(line);
				}
			}
		}
		return data;
	}

	private List<String> getSinks(String mopSpecsDir, ApkInfo apkInfo, String sourcesAndSinksFile) throws MOPException, IOException {
		List<String> sinksAsString = readSourcesAndSinksFile(sourcesAndSinksFile);
		Set<SootMethod> sinks = new HashSet<>();
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
							// && doesInvokeMethod(stmt, "byte[] digest()", "MessageDigest")) {

							InvokeExpr invokeExpr = stmt.getInvokeExpr();
							// System.out.println("-----------
							// "+invokeExpr.getMethod().getDeclaringClass().getName()+" ::
							// "+invokeExpr.getMethod().getSubSignature());

							if (isMop(invokeExpr, mopMethods)) {
								System.out.println(
										"********************* " + invokeExpr.getMethod().getDeclaringClass().getName() + " :: " + invokeExpr.getMethod().getSubSignature());
								// sinks.add(new SourceSinkItem(invokeExpr.getMethod(),
								// SourceSinkCategory.SINK));
								sinks.add(invokeExpr.getMethod());
							}
//						if(invokeExpr.getMethod().getDeclaringClass().getName().equals("java.security.MessageDigest")) {
//							System.out.println("********************* "+invokeExpr.getMethod().getDeclaringClass().getName()+" :: "+invokeExpr.getMethod().getSubSignature());
//						}
						}
					}
				}
			}
		}

		sinksAsString.addAll(sinks.stream().map(m -> m.getSignature() + " -> _SINK_").collect(Collectors.toList()));
		return sinksAsString;
//		return sinks;
	}

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

		TesteTaint t = new TesteTaint();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
