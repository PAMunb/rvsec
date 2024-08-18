package br.unb.cic.rvsec.taint.reach;

import java.io.IOException;
import java.util.List;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.ValueBox;
import soot.jimple.AbstractStmtSwitch;
import soot.jimple.AssignStmt;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.Stmt;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.internal.JAssignStmt.LinkedVariableBox;
import soot.jimple.toolkits.ide.icfg.JimpleBasedInterproceduralCFG;

public class TesteInterProced01 {
	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
//		listFiles(apkPath);

		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);
//
		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
//
		// String methodSigStr = "<br.unb.cic.cryptoapp.MainActivity: void
		// showScreenMessageDigest(android.view.View)>";
		String methodSigStr = "<br.unb.cic.cryptoapp.MainActivity: void showScreen(java.lang.Class)>";

		// By constructing call graph, PointsTo analysis implicitly will be executed
//		app.constructCallgraph();

//		teste01(methodSigStr);
		teste02(methodSigStr);
	}

	private void teste02(String methodSigStr) {
//		JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(false, false);
		for (SootClass clazz : Scene.v().getClasses()) {
			if (clazz.getName().startsWith("br.unb.cic.cryptoapp.MainActivity")) {// && !clazz.getName().startsWith("br.unb.cic.cryptoapp.R$")) {
				for (SootMethod method : clazz.getMethods()) {
					System.out.println("\nMETHOD: " + method.getSignature());
					for (Unit unit : method.retrieveActiveBody().getUnits()) {
//						MyVisitor visitor = new MyVisitor();
//						unit.apply(visitor);						
						Stmt currentStmt = (Stmt) unit;
						
						if(currentStmt instanceof InvokeStmt) {
							InvokeStmt invokeStmt = (InvokeStmt) currentStmt;
							
							if("startActivity".equals(invokeStmt.getInvokeExpr().getMethod().getName())){
								System.out.println("InvokeStmt=" + invokeStmt);
								InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
								Value intentValueParam = invokeExpr.getArgs().get(0);
								System.out.println("intentValueParam="+intentValueParam);
								
								findIntentTarget(invokeStmt, method);//, icfg);
							}
						}
					}
				}
			}
		}
	}

	private void findIntentTarget(Unit unit, SootMethod method) {//, JimpleBasedInterproceduralCFG icfg) {
		InvokeStmt invokeStmt = (InvokeStmt) unit;
		InvokeExpr startActExpr = invokeStmt.getInvokeExpr();
        
		Value intentValue = startActExpr.getArg(0);
		
		List<ValueBox> defBoxes = method.retrieveActiveBody().getDefBoxes();
		for (ValueBox valueBox : defBoxes) {
			System.out.println("valueBox="+valueBox);
			Value value = valueBox.getValue();
			if(value.equivTo(intentValue)) {
				LinkedVariableBox b = (LinkedVariableBox) valueBox;
				System.out.println("ACHOU: "+b);
			}
		}
        
//        System.out.println(" - methodOf: " + icfg.getMethodOf(unit));
//		System.out.println(" - getCalleesOfCallAt:");
//		icfg.getCalleesOfCallAt(unit).forEach(System.out::println);		
////		icfg.getSuccsOf(unit)
//		System.out.println(" - PredsOf: ");
//		icfg.getPredsOf(unit).forEach(System.out::println);
//		System.out.println(" - PredsOfCallAt: ");
//		icfg.getPredsOfCallAt(unit).forEach(System.out::println);
//		System.out.println(" - getBoxesPointingToThis: ");
//		unit.getBoxesPointingToThis().forEach(System.out::println);
	}

	class MyVisitor extends AbstractStmtSwitch<String> {
		private String intentClazzName = null;

		@Override
		public void caseInvokeStmt(InvokeStmt stmt) {
			if("startActivity".equals(stmt.getInvokeExpr().getMethod().getName())){
				System.out.println("InvokeStmt=" + stmt);
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				Value intentValueParam = invokeExpr.getArgs().get(0);
//				intentValueParam.
			}
		}

		@Override
		public void caseAssignStmt(AssignStmt stmt) {
//			System.out.println("AssignStmt=" + stmt);
//
//			Value rightOp = stmt.getRightOp();
//			if (rightOp instanceof InvokeStmt) {
//				System.out.println("****************");
//			}
//
//			if (stmt.containsInvokeExpr()) {
//				System.out.println(" - containsInvokeExpr: " + stmt.getInvokeExpr());
//				InvokeExpr invokeExpr = stmt.getInvokeExpr();
//				if (invokeExpr instanceof SpecialInvokeExpr) {
//					System.out.println(" - SpecialInvokeExpr");
//					SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
//					SootMethod invokeMethod = specialInvokeExpr.getMethod();
//					String signature = invokeMethod.getSignature();
//					System.out.println(" - signature=" + signature);
//					if (signature.equals("<android.content.Intent: void <init>(android.content.Context,java.lang.Class)>")) {
//						System.out.println("invokeExpr=" + invokeExpr);
//						System.out.println("invokeMethod=" + invokeMethod);
//						Value invokeObj = specialInvokeExpr.getBase();
//						System.out.println("invokeObj=" + invokeObj);
//						System.out.println("args=" + specialInvokeExpr.getArgs());
//					}
//				}
//			}
		}

		@Override
		public String getResult() {
			return intentClazzName;
		}
	}

	private void teste01(String methodSigStr) {
		for (SootClass clazz : Scene.v().getClasses()) {
			if (clazz.getName().startsWith("br.unb.cic.cryptoapp") && !clazz.getName().startsWith("br.unb.cic.cryptoapp.R$")) {
				for (SootMethod method : clazz.getMethods()) {
					if (methodSigStr.equals(method.getSignature())) {
						System.out.println("\nENTROU ............");
						System.out.println("METHOD: " + method);

						JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(false, false);
						for (Unit unit : method.retrieveActiveBody().getUnits()) {
							System.out.println("*** unit=" + unit);
							Stmt stmt = (Stmt) unit;
							System.out.println(" - methodOf: " + icfg.getMethodOf(unit));
							System.out.println(" - getCalleesOfCallAt:");
							icfg.getCalleesOfCallAt(unit).forEach(System.out::println);
//							icfg.getSuccsOf(unit)
							System.out.println(" - PredsOf: ");
							icfg.getPredsOf(unit).forEach(System.out::println);
						}

						System.out.println("CALLERS :::::");
						icfg.getCallersOf(method).forEach(System.out::println);
						System.out.println("\nCALLS_FROM_WITHIN :::::");
						icfg.getCallsFromWithin(method).forEach(System.out::println);
						System.out.println("PARAMS_REFS :::::");
						icfg.getParameterRefs(method).forEach(System.out::println);
						System.out.println("ENDPOINTS :::::");
						icfg.getEndPointsOf(method).forEach(System.out::println);
					}
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

		TesteInterProced01 t = new TesteInterProced01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
