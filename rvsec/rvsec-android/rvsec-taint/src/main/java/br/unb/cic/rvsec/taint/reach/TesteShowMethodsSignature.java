package br.unb.cic.rvsec.taint.reach;

import java.io.IOException;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.SootConfig;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.SetupApplication;

public class TesteShowMethodsSignature {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		for (SootClass clazz : Scene.v().getClasses()) {			
			if(clazz.getName().startsWith("br.unb.cic.cryptoapp") && !clazz.getName().startsWith("br.unb.cic.cryptoapp.R$")) {
				System.out.println("CLAZZ: "+clazz.getName());
				for (SootMethod method : clazz.getMethods()) {
					System.out.println("\t- "+method.getSignature());
				}
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

		TesteShowMethodsSignature t = new TesteShowMethodsSignature();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
