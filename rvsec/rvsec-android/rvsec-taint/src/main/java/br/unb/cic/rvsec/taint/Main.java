package br.unb.cic.rvsec.taint;

import java.io.IOException;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.model.Apk;
import soot.MethodOrMethodContext;
import soot.Scene;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.ReachableMethods;
import soot.util.queue.QueueReader;

public class Main {

	public void execute(String apkPath, String androidPlatformsDir, String rtJarPath) throws IOException, XmlPullParserException {
		ApkReader apkReader = new ApkReader();
		Apk apk = apkReader.readApk(apkPath);
		System.out.println(apk);

		SootConfig sootConfig = new SootConfig();
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		app.constructCallgraph();

		CallGraph callGraph = Scene.v().getCallGraph();

		ReachableMethods reachableMethods = Scene.v().getReachableMethods();
		QueueReader<MethodOrMethodContext> methods = reachableMethods.listener();
		System.out.println("ReachableMethods");
		while (methods.hasNext()) {
			String tmp = methods.next().method().getSignature().toString();
			if (tmp.contains("MessageDigest")) {
				System.out.println("*** " + tmp);
			}
		}

		System.out.println("FIM DE FESTA!!!");
	}



	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		Main main = new Main();
		try {
			main.execute(apk, androidPlatformsDir, rtJarPath);
		} catch (IOException | XmlPullParserException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
