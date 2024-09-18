package com.fdu.se.sootanalyze.tmp;

import java.io.IOException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.xmlpull.v1.XmlPullParserException;

import com.fdu.se.sootanalyze.SootConfig;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import soot.Body;
import soot.Scene;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.ClassConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.internal.JimpleLocal;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.UnitGraph;
import soot.util.queue.QueueReader;

public class TesteIntent01 {
	private static final String INTENT_NEW = "<android.content.Intent: void <init>(android.content.Context,java.lang.Class)>";

	private String androiPlatformsDir;
	private String rtJarPath;

	public TesteIntent01(String androiPlatformsDir, String rtJarPath) {
		this.androiPlatformsDir = androiPlatformsDir;
		this.rtJarPath = rtJarPath;
	}

	public void teste01(String apkPath) throws IOException, XmlPullParserException {
		SetupApplication app = SootConfig.initialize(apkPath, androiPlatformsDir, rtJarPath);
		
		app.constructCallgraph();

		AppInfo appInfo = AppReader.readApk(apkPath);
		Set<Edge> startActivityEdges = findStartActivityEdges(appInfo.getPackage());

		for (Edge edge : startActivityEdges) {
			processStartActivity(edge);
		}
	}

	private void processStartActivity(Edge edge) {
		System.out.println("processStartActivity: " + edge);
		System.out.println("processStartActivity ::: " + edge.getSrc().method().getSignature() + " ==> " + edge.getTgt().method().getSignature());
		SootMethod src = edge.src();
		System.out.println("processStartActivity ::: src=" + src.getSignature());
		System.out.println("processStartActivity ::: kind=" + edge.kind());
		System.out.println("processStartActivity ::: unit=" + edge.srcUnit());
		System.out.println("processStartActivity ::: stmt=" + edge.srcStmt());
		System.out.println("processStartActivity ::: passesParameters=" + edge.passesParameters());

//		CallGraph callGraph = Scene.v().getCallGraph();

		Value currentValue = getStartActivityParameter(edge.srcStmt());

		Body body = src.retrieveActiveBody();
		UnitGraph cfg = new BriefUnitGraph(body);
		Stmt curStmt = edge.srcStmt();

		//TODO rever ........
		List<Unit> predsOf = cfg.getPredsOf(curStmt);
		if (!predsOf.isEmpty()) {
			Unit unit = predsOf.remove(0);
			Stmt stmt = (Stmt) unit;
			System.out.println("stmt=" + stmt + "..." + stmt.getClass());
			Value parameter = findNewIntentParameter(curStmt, currentValue);
			System.out.println("processStartActivity ::: parameter=" + parameter);
			if (parameter != null) {
				if (parameter instanceof ClassConstant) {
					System.out.println("******** processStartActivity(ClassConstant)=" + parameter);
//					return parameter;
				}
				if (parameter instanceof JimpleLocal) {
					Value xxx = findIntentDeclarationIntraprocedural(parameter, stmt, cfg);
					System.out.println("******** processStartActivity(JimpleLocal)=" + xxx);

					if (xxx == null) {
						// TODO interprocedural
					}
				}
			}
		}

	}

	private Value findIntentDeclarationIntraprocedural(Value parameter, Stmt currentStmt, UnitGraph cfg) {
		System.out.println("findIntentDeclarationIntraprocedural=" + parameter);
		List<Unit> predsOf = cfg.getPredsOf(currentStmt);
		for (Unit unit : predsOf) {
			Stmt stmt = (Stmt) unit;
			System.out.println("findIntentDeclarationIntraprocedural ::: stmt=" + stmt);

			if (stmt instanceof AssignStmt) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				System.out.println("findIntentDeclarationIntraprocedural ::: assignStmt=" + assignStmt);
				if (assignStmt.getLeftOp().equals(parameter)) {
					System.out.println("findIntentDeclarationIntraprocedural ::: assignStmt ****** right=" + assignStmt.getRightOp());
					return assignStmt.getRightOp();
				}
				if (assignStmt.getRightOp().equals(parameter)) {
					System.out.println("findIntentDeclarationIntraprocedural ::: assignStmt ****** left=" + assignStmt.getLeftOp());
					return findIntentDeclarationIntraprocedural(assignStmt.getLeftOp(), stmt, cfg);
				}
			}

			return findIntentDeclarationIntraprocedural(parameter, stmt, cfg);
		}

		return null;
	}

	private Value findNewIntentParameter(Stmt stmt, Value currentValue) {
		System.out.println("findNewIntentParameter: value=" + currentValue + ", stmt=" + stmt);
		if (stmt instanceof InvokeStmt) {
			InvokeStmt invokeStmt = (InvokeStmt) stmt;
			InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();

			if (invokeExpr instanceof SpecialInvokeExpr) {
				SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
				System.out.println("findNewIntentParameter ::: specialInvokeExpr=" + specialInvokeExpr);
				SootMethod invokeMethod = specialInvokeExpr.getMethod();
				String signature = invokeMethod.getSignature();
				if (signature.equals(INTENT_NEW)) {
					Value invokeObj = specialInvokeExpr.getBase();
					System.out.println("findNewIntentParameter ::: specialInvokeExpr::invokeObj=" + invokeObj + " ::: tmp=" + specialInvokeExpr.getArg(1) + " ::: invokeObj.class=" + invokeObj.getClass());
					System.out.println("findNewIntentParameter ::: specialInvokeExpr::invokeObj.equivTo(returnValue)=" + invokeObj.equivTo(currentValue));
					if (invokeObj.equivTo(currentValue)) {
						return specialInvokeExpr.getArg(1);
					}
				}
			}

		}
		return null;
	}

	private Value getStartActivityParameter(Stmt stmt) {
		System.out.println("getStartActivityParameter = " + stmt);
		if (stmt.containsInvokeExpr()) {
			InvokeExpr invokeExpr = stmt.getInvokeExpr();
			System.out.println("getStartActivityParameter ::: invokeExpr=" + invokeExpr + " ::: getArgCount=" + invokeExpr.getArgCount());
			return invokeExpr.getArg(0);
		}
		return null;
	}

	private Set<Edge> findStartActivityEdges(String appPackage) {
		Set<Edge> edges = new HashSet<>();
		CallGraph cg = Scene.v().getCallGraph();
		QueueReader<Edge> listener = cg.listener();
		while (listener.hasNext()) {
			Edge edge = listener.next();
			if (isStartActivity(edge, appPackage)) {
				edges.add(edge);
			}
		}
		return edges;
	}

	private boolean isStartActivity(Edge edge, String appPackage) {
		SootMethod source = edge.src();
		SootMethod target = edge.tgt();
		String methodSignature = target.getSignature();
		if (source.getDeclaringClass().getName().startsWith(appPackage) && Constants.startActivitySignatures.contains(methodSignature)) {
			return true;
		}
		return false;
	}

//	private List<SootClass> findMainActivityWithInnerClasses(AppInfo appInfo) {
//		List<SootClass> activities = new ArrayList<>();// all activities'window node
//		for (SootClass clazz : Scene.v().getApplicationClasses()) {
//			for (ActivityInfo actInfo : appInfo.getActivities()) {
//				if (clazz.getName().startsWith(actInfo.getName())) { // include inner classes
//					activities.add(clazz);
//				}
//			}
//		}
//		return activities;
//	}

	public static void main(String[] args) {
		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
		String apk = baseDir + "cryptoapp.apk";

//		String outputFile = "/home/pedro/tmp/rvsec-gesda.json";

		TesteIntent01 teste = new TesteIntent01(androidPlatformsDir, rtJarPath);
		try {
			teste.teste01(apk);
		} catch (IOException | XmlPullParserException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
