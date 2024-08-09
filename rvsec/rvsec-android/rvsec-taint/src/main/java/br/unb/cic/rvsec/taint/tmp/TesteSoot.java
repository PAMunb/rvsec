package br.unb.cic.rvsec.taint.tmp;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import br.unb.cic.rvsec.taint.SootConfig;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.jimple.AbstractStmtSwitch;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.Stmt;
import soot.jimple.StmtSwitch;
import soot.jimple.infoflow.android.SetupApplication;

public class TesteSoot {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) {
		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		teste01();
	}

	private void teste01() {
		Scene.v().getApplicationClasses().forEach(c -> {
			if (c.getName().startsWith("br.unb.cic.cryptoapp") && !c.getName().startsWith("br.unb.cic.cryptoapp.R")) {
				System.out.println("CLASSE: " + c.getName());
				c.getMethods().forEach(m -> {
					System.out.println("METODO: " + m.getSignature());
					m.retrieveActiveBody().getUnits().forEach(u -> {
						Stmt stmt = (Stmt) u;
						if (stmt.containsInvokeExpr()) {
							InvokeExpr invokeExpr = stmt.getInvokeExpr();
							if (invokeExpr.getMethod().getDeclaringClass().getName().equals("java.security.MessageDigest")) {
								System.out.println("********************* " + invokeExpr.getMethod().getDeclaringClass().getName() + " :: " + invokeExpr.getMethod().getSubSignature());
							}
						}
					});
				});
			}
		});
	}

	private void teste02() {
		AtomicBoolean result = new AtomicBoolean(false);
		
		List<StmtSwitch> visitors = new ArrayList<>();
		visitors.add(invokeMessageDigest(result));
		
		
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			if (clazz.getName().startsWith("br.unb.cic.cryptoapp") && !clazz.getName().startsWith("br.unb.cic.cryptoapp.R")) {
				System.out.println("CLASSE: " + clazz.getName());
				for (SootMethod method : clazz.getMethods()) {
					System.out.println("METODO: " + method.getSignature());
					for (Unit unit : method.retrieveActiveBody().getUnits()) {
						visitors.forEach(unit::apply);
//						unit.apply(invokeMessageDigest(result));
					}
				}
			}
		}
		System.out.println(result.get());
	}

	private AbstractStmtSwitch<Object> invokeMessageDigest(AtomicBoolean result) {
		return new AbstractStmtSwitch<>() {
			@Override
			public void caseInvokeStmt(InvokeStmt invokeStmt) {
				InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
				if (invokeExpr.getMethod().getDeclaringClass().getName().equals("java.security.MessageDigest")) {
					System.out.println("********************* " + invokeExpr.getMethod().getDeclaringClass().getName() + " :: " + invokeExpr.getMethod().getSubSignature());
					result.set(true);
				}
			}
		};
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

		TesteSoot t = new TesteSoot();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
