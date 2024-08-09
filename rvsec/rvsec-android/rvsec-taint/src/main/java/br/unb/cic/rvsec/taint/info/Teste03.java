package br.unb.cic.rvsec.taint.info;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ActivityInfo;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.model.SootActivity;
import br.unb.cic.rvsec.taint.model.ViewInfo;
import javamop.util.MOPException;
import soot.Body;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.VirtualInvokeExpr;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;
import soot.jimple.internal.JCastExpr;
import soot.jimple.internal.JInstanceFieldRef;
import soot.tagkit.Tag;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.UnitGraph;
import soot.util.Chain;

public class Teste03 {

	private String apkPath;

	private SootClass rIdClass;
	private SootClass rLayoutClass;
	private SootClass rStringClass;
	private SootClass rArrayClass;

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile)
			throws MOPException, IOException, XmlPullParserException {
//		listFiles(apkPath);
		this.apkPath = apkPath;

		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);
//
		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);
//

		recuperarClassesR(apkInfo);

		List<SootActivity> activities = processActivities(apkInfo);

		System.out.println("************************************");
		activities.forEach(System.out::println);

	}

	private void recuperarClassesR(ApkInfo apkInfo) {
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			String name = clazz.getName();

			if (name.equals(apkInfo.getManifestPackage() + ".R$id")) {
				rIdClass = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage() + ".R$layout")) {
				rLayoutClass = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage() + ".R$string")) {
				rStringClass = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage() + ".R$array")) {
				rArrayClass = clazz;
			}
		}
	}

	public void initializeMaps() {

	}

	public void listFiles(String apkPath) throws IOException {

		ZipFile zip = new ZipFile(apkPath);

		// search for file with given filename
		Enumeration<?> entries = zip.entries();
		while (entries.hasMoreElements()) {
			ZipEntry entry = (ZipEntry) entries.nextElement();
			String entryName = entry.getName();
			if (entryName.startsWith("res/")) {
				System.out.println(entryName);
			}
		}

	}

	private List<SootActivity> processActivities(ApkInfo apkInfo) {
		System.out.println("Processing activities ...");
		List<SootActivity> activities = new ArrayList<>();
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			for (ActivityInfo actInfo : apkInfo.getActivities()) {
				if (actInfo.getName().equals(clazz.getName())) {
					SootActivity activity = processActivity(actInfo, clazz);
					activities.add(activity);
				}
			}
		}
		return activities;
	}

	private SootActivity processActivity(ActivityInfo actInfo, SootClass clazz) {
		System.out.println("Processing Activity: " + clazz.getName() + "::" + clazz.getPackageName() + ":::" + clazz.getJavaStyleName());

		SootActivity sootActivity = new SootActivity(actInfo, clazz);
		// TODO Auto-generated method stub
//		System.out.println("..." + getActLayout(c));
		String layoutFileName = getActivityLayoutFilename(clazz);

		List<ViewInfo> views = parseActivityLayout(layoutFileName);
		actInfo.setViews(views);

		processViews(views, clazz);

		return sootActivity;
	}

	private void processViews(List<ViewInfo> views, SootClass activity) {
		processViewAssignements(views, activity);
		processCallbacks(views, activity);
	}


	private void processCallbacks(List<ViewInfo> views, SootClass activity) {
		for (ViewInfo view : views) {
			if(view.getCallback() != null) {
				Optional<SootMethod> methodOpt = getMethodByName(view.getCallback(), activity);
				if(methodOpt.isPresent()) {
					SootMethod method = methodOpt.get();
					view.setCallbackMethod(method);
				}
			}
		}
	}

	private void processViewAssignements(List<ViewInfo> views, SootClass activity) {
		Optional<SootMethod> methodOpt = getMethodByName("onCreate", activity);
		if (methodOpt.isPresent()) {
			SootMethod method = methodOpt.get();
			Map<String, SootField> mapa = getAllAssignStmtContainingInvokeExprByMethodName(method);

			for (ViewInfo view : views) {
				SootField field = mapa.get(view.getName());
				if(field != null) {
					view.setField(field);
				}
			}
		}
	}



	private Map<String, SootField> getAllAssignStmtContainingInvokeExprByMethodName(SootMethod method) {
		System.out.println("\ngetAllAssignStmtContainingInvokeExprByMethodName");

		Map<String, SootField> mapa = new HashMap<>();

		Body body = method.retrieveActiveBody();
		UnitGraph cfg = new BriefUnitGraph(body);

		for (Unit unit : cfg) {
			Stmt stmt = (Stmt) unit;

			if (stmt instanceof AssignStmt && stmt.containsInvokeExpr()) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				Value right = assignStmt.getRightOp();
				if (right instanceof VirtualInvokeExpr) {
					VirtualInvokeExpr expr = (VirtualInvokeExpr) right;
					SootMethod rmethod = expr.getMethod();
					String rname = rmethod.getName();
					if (rname.equals("findViewById")) {
						Value arg0 = expr.getArg(0);
						String name = getIdName(arg0.toString());
						Value left = assignStmt.getLeftOp();

						SootField field = findField(left, unit, cfg);
						System.out.println("arg0: " + arg0 + "::name=" + name + ":::left=" + left);
						mapa.put(name, field);
					}
				}
			}
		}

		return mapa;
	}

	private SootField findField(Value value, Unit u, UnitGraph cfg) {
		//TODO .........................ver condicao de parada
		System.out.println("findField .......... value="+value);
		List<Unit> succsOf = cfg.getSuccsOf(u);
		for (Unit unit : succsOf) {
			Stmt stmt = (Stmt) unit;
			if (stmt instanceof AssignStmt) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				Value left = assignStmt.getLeftOp();
				Value right = assignStmt.getRightOp();
				System.out.println("AAA="+assignStmt);

				if(right instanceof JCastExpr) {
					JCastExpr cast = (JCastExpr) right;
					if(cast.getOp().equals(value)) {
						System.out.println("xcvb="+cast.getOp());
						return findField(left, unit, cfg);
					}
				}
				//TODO identificar quais os outros casos do "right" e tratar ....

				if(left instanceof JInstanceFieldRef) {
					JInstanceFieldRef fieldRef = (JInstanceFieldRef) left;
					System.out.println("fieldRef="+fieldRef+"::right="+right+":::value="+value);
					if(right.equals(value)) {
						System.out.println("FIELD="+fieldRef.getField());
						return fieldRef.getField();
					}
				}
			}
		}

		return null;
	}

	private List<InvokeExpr> getAllAssignStmtContainingInvokeExprByMethodNameOld(String methodName, SootMethod method) {
		System.out.println("\ngetAllAssignStmtContainingInvokeExprByMethodName");
		List<InvokeExpr> expressions = new ArrayList<>();
		UnitPatchingChain units = method.retrieveActiveBody().getUnits();
		for (Unit u : units) {
			Stmt stmt = (Stmt) u;

			System.out.println(stmt);
//			System.out.println("aaa=" + (stmt instanceof Stmt));
//			System.out.println("bbb=" + (stmt instanceof AssignStmt));
//			System.out.println("ccc=" + (stmt.containsInvokeExpr()));
//			System.out.println("ddd=" + (stmt.containsFieldRef()));

			if (stmt instanceof AssignStmt && stmt.containsInvokeExpr()) {
				System.out.println("entrou................");
				AssignStmt assignStmt = (AssignStmt) stmt;
				Value right = assignStmt.getRightOp();
				if (right instanceof VirtualInvokeExpr) {
					VirtualInvokeExpr expr = (VirtualInvokeExpr) right;
					SootMethod rmethod = expr.getMethod();
					String rname = rmethod.getName();
					if (rname.equals("findViewById")) {
						Value arg0 = expr.getArg(0);
						String name = getIdName(arg0.toString());
						Value left = assignStmt.getLeftOp();
						System.out.println("arg0: " + arg0 + "::name=" + name + ":::left=" + left);

						Chain<SootField> fields = method.getDeclaringClass().getFields();
						for (SootField field : fields) {
							System.out.println("\tfield=" + field);
						}

//						Widget fviWidget = new Widget();// widget from findViewById
//						fviWidget.setId(++curWidgetId);
//						fviWidget.setWidgetId(getIdName(arg0.toString()));
//						fviWidget.setWidgetType(base.getType().toString());
//						fviWidget.setEvent(event);
//						fviWidget.setEventMethod(eventCallBack);
//						fviWidget.setListenerName(listener.toString());
//						widgets.add(fviWidget);
//						break;
					}
				}
			}

//			if(stmt.containsFieldRef())
//
//			if (stmt.containsInvokeExpr()) {
//				InvokeExpr invokeExpr = stmt.getInvokeExpr();
//				SootMethod invokeMethod = invokeExpr.getMethod();
//				if (invokeMethod.getName().equals(methodName)) {
//					expressions.add(invokeExpr);
//				}
//			}
		}
		return expressions;
	}

	public List<ViewInfo> parseActivityLayout(String filename) {
		List<ViewInfo> views = new ArrayList<>();
		String layoutPath = "res/layout/" + filename + ".xml";
		try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
			InputStream layoutStream = apkHandler.getInputStream(layoutPath);
			if (layoutStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);

				List<ViewInfo> buttons = parseButtons(aXmlHandler);
				views.addAll(buttons);

				List<ViewInfo> editTexts = parseEditTexts(aXmlHandler);
				views.addAll(editTexts);

				List<ViewInfo> spinnerTexts = parseSpinners(aXmlHandler);
				views.addAll(spinnerTexts);

			}
		} catch (IOException e) {
			// TODO
			e.printStackTrace();
		}
		return views;
	}

	private List<ViewInfo> parseButtons(AXmlHandler aXmlHandler) {
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Button");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String callback = getAttributeValue("onClick", node);
			System.out.println("\tcallback=" + callback);
			String name = getIdName(id.toString());
			System.out.println("\tbuttonName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("Button");
			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}

	private List<ViewInfo> parseEditTexts(AXmlHandler aXmlHandler) {
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("EditText");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = getIdName(id.toString());
			System.out.println("\teditTextName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("EditText");
//			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}

	private List<ViewInfo> parseSpinners(AXmlHandler aXmlHandler) {
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Spinner");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = getIdName(id.toString());
			System.out.println("\tspinnerName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("Spinner");
//			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}

	private <T> T getAttributeValue(String name, AXmlNode bNode) {
		AXmlAttribute<T> attribute = (AXmlAttribute<T>) bNode.getAttribute(name);
		if (attribute != null) {
			return attribute.getValue();
		}
		return null;
	}

	public String getIdName(String idValue) {
		if (idValue == null) {
			return null;
		}
		for (SootField idField : rIdClass.getFields()) {
			if (idField.isFinal() && idField.isStatic()) {
				String fieldName = idField.getName();
				Tag fieldTag = idField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					String fieldValue = tagString.split(" ")[1];
					if (fieldValue.equals(idValue)) {
						return fieldName;
					}
				}
			}
		}
		return null;
	}

	public String getActivityLayoutFilename(SootClass activity) {
		Optional<SootMethod> methodOpt = getMethodByName("onCreate", activity);
		if (methodOpt.isPresent()) {
			SootMethod method = methodOpt.get();
			Optional<InvokeExpr> invokeExprOpt = getInvokeExprByMethodName("setContentView", method);
			if (invokeExprOpt.isPresent()) {
				InvokeExpr invokeExpr = invokeExprOpt.get();
				String layoutId = invokeExpr.getArg(0).toString();
				System.out.println("layoutId=" + layoutId);
				return getLayoutFieldNameById(layoutId);
			}
		}
		return null;
	}

	private Optional<SootMethod> getMethodByName(String methodName, SootClass clazz) {
		return clazz.getMethods().stream().filter(m -> m.getName().equals(methodName)).findFirst();
	}

	private List<SootMethod> getMethodsByName(String methodName, SootClass clazz) {
		return clazz.getMethods().stream().filter(m -> m.getName().equals(methodName)).collect(Collectors.toList());
	}

	private Optional<InvokeExpr> getInvokeExprByMethodName(String methodName, SootMethod method) {
		UnitPatchingChain units = method.retrieveActiveBody().getUnits();
		for (Unit u : units) {
			Stmt stmt = (Stmt) u;
			if (stmt.containsInvokeExpr()) {
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				SootMethod invokeMethod = invokeExpr.getMethod();
				if (invokeMethod.getName().equals(methodName)) {
					return Optional.of(invokeExpr);
				}
			}
		}
		return Optional.empty();
	}

	public String getLayoutFieldNameById(String layoutId) {
		for (SootField layoutField : rLayoutClass.getFields()) {
			if (layoutField.isFinal() && layoutField.isStatic()) {
				String fieldName = layoutField.getName();
				System.out.println("fieldName=" + fieldName);
				Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					System.out.println("tagString=" + tagString);
					String fieldValue = tagString.split(" ")[1];
					if (layoutId.equals(fieldValue)) {
						return fieldName;
					}
				}
			}
		}
		return null;
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

		Teste03 t = new Teste03();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
