package br.unb.cic.rvsec.taint.reach;

import java.io.IOException;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import javamop.util.MOPException;
import soot.Local;
import soot.PointsToSet;
import soot.Scene;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;

public class TestePointsTo01 {
	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
//		listFiles(apkPath);

		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);
//
		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
//
		String generateHashSignatureStr = "<br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity: void generateHash(android.view.View)>";

		// By constructing call graph, PointsTo analysis implicitly will be executed
		app.constructCallgraph();
		soot.PointsToAnalysis pointsToAnalysis = Scene.v().getPointsToAnalysis();
		SootMethod intermediaryMethod = Scene.v().getMethod(generateHashSignatureStr);

		System.out.println("intermediaryMethod=" + intermediaryMethod);

		for (Local local : intermediaryMethod.getActiveBody().getLocals()) {
//            if(isParentChildClassLocal(local)){
			System.out.println("local=" + local);

			PointsToSet pointsToSet = pointsToAnalysis.reachingObjects(local);
			System.out.println("possibleClassConstants:");
			if (pointsToSet.possibleClassConstants() != null) {
				pointsToSet.possibleClassConstants().forEach(System.out::println);
			}
			System.out.println("possibleStringConstants:");
			if (pointsToSet.possibleStringConstants() != null) {
				pointsToSet.possibleStringConstants().forEach(System.out::println);
			}
			System.out.println("possibleTypes:");
			if (pointsToSet.possibleTypes() != null) {
				pointsToSet.possibleTypes().forEach(System.out::println);
			}

//			((DoublePointsToSet) pointsToAnalysis.reachingObjects(local)).getOldSet().forall(new P2SetVisitor() {
//				@Override
//				public void visit(Node n) {
//					AllocNode allocNode = (AllocNode) n;
//					SootMethod allocMethod = allocNode.getMethod();
//					NewExpr allocExpr = (NewExpr) allocNode.getNewExpr();
//					System.out.println(String.format("Local %s in intermediaryMethod is allocated at method %s through expression: %s", local, allocMethod, allocExpr));
//				}
//			});
//            }
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

		TestePointsTo01 t = new TestePointsTo01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
