package com.fdu.se.sootanalyze;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.Stack;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xmlpull.v1.XmlPullParserException;

import com.fdu.se.sootanalyze.model.ActivityWindowNode;
import com.fdu.se.sootanalyze.model.AnalysisType;
import com.fdu.se.sootanalyze.model.BaseListeners;
import com.fdu.se.sootanalyze.model.Listener;
import com.fdu.se.sootanalyze.model.ListenerType;
import com.fdu.se.sootanalyze.model.TransitionEdge;
import com.fdu.se.sootanalyze.model.TransitionGraph;
import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.Widget.WidgetBuilder;
import com.fdu.se.sootanalyze.model.WidgetBuilderFactory;
import com.fdu.se.sootanalyze.model.WidgetType;
import com.fdu.se.sootanalyze.model.WindowNode;
import com.fdu.se.sootanalyze.model.WindowType;
import com.fdu.se.sootanalyze.model.out.ApkInfoOut;
import com.fdu.se.sootanalyze.model.out.OutputWriter;
import com.fdu.se.sootanalyze.utils.NumberIncrementer;
import com.fdu.se.sootanalyze.utils.StringUtil;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import soot.Body;
import soot.MethodOrMethodContext;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Type;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.ClassConstant;
import soot.jimple.IdentityStmt;
import soot.jimple.IntConstant;
import soot.jimple.InterfaceInvokeExpr;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.ReturnStmt;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.StaticInvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.VirtualInvokeExpr;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.internal.JCastExpr;
import soot.jimple.internal.JInstanceFieldRef;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.tagkit.Tag;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.UnitGraph;

public class SootAnalyze {
	private static final String INTENT_NEW = "<android.content.Intent: void <init>(android.content.Context,java.lang.Class)>";

	private static Logger log = LoggerFactory.getLogger(SootAnalyze.class);

	private SetupApplication app;

	private static String sdkPath;
	private static String rtJarPath;

	private static String callbackPath = "AndroidCallbacks.txt";
	private static String sourceSinkFilePath = "SourcesAndSinks2.txt";

	private SootClass rIdClass;
	private SootClass rLayoutClass;
	private SootClass rMenuClass;
//	private SootClass rStringClass;
	private SootClass rArrayClass;

	private XmlParser xmlParser;

	// map ID to FIELD_NAME in R$id
	private Map<String, String> idMap = new HashMap<>();
	private Map<String, String> arrayMap = new HashMap<>();
	private Map<String, String> menuMap = new HashMap<>();

	private long curNodeId = 0;// the current id of WindowNode when constructing Transition Graph
	private NumberIncrementer curWidgetId = new NumberIncrementer();// the current id of Widget when constructing Transition Graph
	private long curEdgeId = 0;// the current id of TransitionEdge when constructing Transition Graph

//	private List<String> setListeners;
	private List<String> startActivitySignatures;
	private List<String> addMenuItemSignatures;
	private List<String> addSubMenuSignatures;
	private List<String> addSubMenuItemSignatures;
	private List<String> systemCallbacks;

	private AppInfo appInfo;

	public SootAnalyze(String androiPlatformsDir, String rtJar) {
		sdkPath = androiPlatformsDir;
		rtJarPath = rtJar;
		initStartActSignatures();
		initAddMenuItemSignatures();
		initAddSubMenuSignatures();
		initAddSubMenuItemSignatures();
		initSystemCallbacks();
	}

	public AppInfo init(String apkPath) throws IOException, XmlPullParserException {
		log.info("Initializing ...");
		app = SootConfig.initialize(apkPath, sdkPath, rtJarPath);

		// TODO tratar callback agora???
		// app.setCallbackFile(callbackPath);

		appInfo = AppReader.readApk(apkPath);
		initializeR(appInfo.getPackage());
		xmlParser = new XmlParser(appInfo, idMap);

		return appInfo;
	}

	public List<WindowNode> analyze() throws IOException, XmlPullParserException {
		if (app == null) {
			// TODO
			throw new RuntimeException("iniciar antes ....");
		}

//		testeCallBack();

		log.info("Begin to analyse app: " + StringUtil.convertToLabel(appInfo.getPath()));

		List<WindowNode> activities = new ArrayList<>();// all activities'window node
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			for (ActivityInfo actInfo : appInfo.getActivities()) {
//				if (clazz.getName().startsWith(actInfo.getName())) { // include inner classes
				if (actInfo.getName().equals(clazz.getName())) {
					WindowNode activity = processActivity(actInfo, clazz);
					activities.add(activity);
				}
			}
		}

		return activities;
	}

//	private void testeCallBack() throws IOException {
//		String callBackFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gesda/AndroidCallbacks.txt";
//		Set<SootClass> entryPoints = new HashSet<>();
//		for (SootClass clazz : Scene.v().getApplicationClasses()) {
//			for (ActivityInfo actInfo : appInfo.getActivities()) {
//				if (actInfo.getName().equals(clazz.getName())) {
//					entryPoints.add(clazz);
//				}
//			}
//		}
//
//		FastCallbackAnalyzer analyzer = new FastCallbackAnalyzer(SootConfig.getConfig(), entryPoints, callBackFile);
//
//		MultiMap<SootClass,AndroidCallbackDefinition> callbackMethods = analyzer.getCallbackMethods();
//		System.out.println("callbackMethods: "+callbackMethods.size());
//		for (SootClass sootClass : callbackMethods.keySet()) {
//			System.out.println("clazz="+sootClass.getName());
//			Set<AndroidCallbackDefinition> definitions = callbackMethods.get(sootClass);
//			for(AndroidCallbackDefinition def: definitions) {
//				System.out.println(" - "+def);
//			}
//
//		}
//	}

	private WindowNode processActivity(ActivityInfo activityInfo, SootClass activitySoot) {
		log.debug("Processing activity: " + activityInfo.getName());
		List<Widget> widgets = new ArrayList<>();// all widgets binding events of the activity

		String layoutFileName = getActivityLayoutFilename(activitySoot);
		activityInfo.setLayoutFileName(layoutFileName);
		log.debug("Activity layout file name: " + layoutFileName);

		if (layoutFileName != null) {
			List<Widget> layoutWidgets = xmlParser.parseActivityLayout(layoutFileName);
			for (Widget widget : layoutWidgets) {
				widget.setListenerName(activitySoot.getName());
				widgets.add(widget);
			}
			processWidgets(layoutWidgets, activitySoot);
		}

		ActivityWindowNode activityNode = new ActivityWindowNode(activityInfo);// window node of the activity
		activityNode.setId(++curNodeId);
		activityNode.setName(activitySoot.getName());
		activityNode.setOptionsMenuNode(getOptionsMenu(activitySoot, activityNode));
		activityNode.setWidgets(widgets);

		return activityNode;
	}

	private WindowNode getOptionsMenu(SootClass sootAct, WindowNode actNode) {
		SootMethod opt_cb = hasOptionsMenu(sootAct);// check if has onCreateOptionsMenu
		log.trace("getOptionsMenu: " + opt_cb);
		if (opt_cb != null) {
			WindowNode optMenuNode = new WindowNode();
			optMenuNode.setId(++curNodeId);
//			optMenuNode.setLabel(appInfo.getLabel());
			optMenuNode.setType(WindowType.OPTMENU);
			optMenuNode.setName(sootAct.getName());
			List<Widget> optMenuWidgets = getMenuWidgets(opt_cb);
			processDeclaredCallbacks(optMenuWidgets, sootAct);
			optMenuNode.setWidgets(optMenuWidgets);
			return optMenuNode;
		}
		return null;
	}

//	@Deprecated
//	public AppInfo getAppInfo() throws IOException, XmlPullParserException {
//		File targetAPK = new File(apkPath);
//
//		AppInfo appInfo = AppReader.readApk(apkPath);
//
//		ARSCFileParser resources = new ARSCFileParser();
//		resources.parse(targetAPK.getAbsolutePath());
//
//		try (ProcessManifest processManifest = new ProcessManifest(targetAPK, resources)) {
//			AXmlNode manifest = processManifest.getManifest();
//			String pack = getAttributeAsString("package", manifest);
//			System.out.println("package name: " + pack);
//			packageName = pack;
//			List<String> actNames = new ArrayList<>();
//			for (BinaryManifestActivity binaryManifestActivity : processManifest.getActivities()) {
//				AXmlNode act = binaryManifestActivity.getAXmlNode();
//				String actName = getAttributeAsString("name", act);
//				System.out.println(actName);
//				actNames.add(actName);
//			}
////			appInfo.setPackName(pack);
//			appInfo.setActivities(actNames);
//		}
//		return appInfo;
//	}

	private void processWidgets(List<Widget> views, SootClass activity) {
		processViewAssignements(views, activity);
		processDeclaredCallbacks(views, activity);
		processListeners(views, activity);
	}

	private void processListeners(List<Widget> views, SootClass activity) {
		log.trace("\n\n\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n");
		log.trace("+ ACTIVITY=" + activity.getName());
		for (SootMethod method : activity.getMethods()) {
			log.trace(" +++ METHOD=" + method.getSignature());
			Body body = method.retrieveActiveBody();
			UnitGraph cfg = new BriefUnitGraph(body);
			UnitPatchingChain units = body.getUnits();
			for (Unit u : units) {
				Stmt stmt = (Stmt) u;
				log.trace(" ++++++ stmt=" + stmt);
				if (stmt.containsInvokeExpr()) {
					InvokeExpr invokeExpr = stmt.getInvokeExpr();
					log.trace("invokeExpr: " + invokeExpr);
					if (invokeExpr instanceof VirtualInvokeExpr) {
						VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) invokeExpr;
						SootMethod invokeMethod = virtualInvokeExpr.getMethod();
						String invokeMethodName = invokeMethod.getName();
						ListenerType listenerType = BaseListeners.getByListenerMethod(invokeMethodName);
						log.trace("******************** listenerType=" + listenerType);
						if (listenerType != null) {
							log.debug("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& Listener: " + invokeMethodName);
							Value base = virtualInvokeExpr.getBase();// object of call method
							log.trace("base=" + base);
//									SootField field = findField(arg, u, cfg);
//									SootField field = findField(base, u, cfg);
//									log.trace("FIELD: "+field);
							SootField field = testeXXX(base, u, cfg);
							log.trace("FIELD:::" + field);
							Widget widget = findWidgetByField(field, views);
							if (widget != null) {
								log.trace(">>>>>>>>>>>>>>>>> " + widget);
								log.trace("event=" + listenerType.getEvent());
								log.trace("eventCallBack=" + listenerType.getEventCallback());
								Value arg = virtualInvokeExpr.getArg(0);
								log.trace("arg=" + arg);
								Type listenerArgType = arg.getType();// class name of the listener
								log.trace("listenerArgType=" + listenerArgType);

								Listener listener = new Listener(listenerType);
								listener.setListernerClass(listenerArgType.toString());
								SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(listenerArgType.toString());
								log.trace("sootClassUnsafe=" + sootClassUnsafe);
								if (sootClassUnsafe != null) {
									SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe(listenerType.getEventCallback());
									log.trace("methodByNameUnsafe=" + methodByNameUnsafe);
									listener.setCallbackMethod(methodByNameUnsafe);

									log.trace("======================================================%$#@");
									String targetClass = testeIntent(methodByNameUnsafe);// TODO
									log.trace("****************************************** targetClass=" + targetClass);
									widget.addTarget(targetClass);
								}
								log.trace("addListener=" + listener);
								widget.addListener(listener);
								log.trace("WIDGET=" + widget);
							}
						}
						log.trace("___________________________________________________________");
					}
				}
			}
		}
	}

	private Widget findWidgetByField(SootField field, List<Widget> widgets) {
		if (field != null) {
			for (Widget widget : widgets) {
				if (field.equals(widget.getField())) {
					return widget;
				}
			}
		}
		return null;
	}

	private void processDeclaredCallbacks(List<Widget> views, SootClass activity) {
		for (Widget view : views) {
			for (Listener listener : view.getListeners()) {
				if (listener.isEventRegisteredInLayoutFile()) {
					String listernerMethod = listener.getListernerMethod();
					log.trace("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ " + listernerMethod);
					log.trace("@@@@@@@@@@@ " + listener.getCallbackMethodName());
					log.trace("@@@@@@@@@@@ " + listener.getEventCallback());
					Optional<SootMethod> methodOpt = getMethodByName(listener.getCallbackMethodName(), activity);
					if (methodOpt.isPresent()) {
						SootMethod method = methodOpt.get();
						log.trace("@@@@@@@@@@@ " + method.getSignature());
						listener.setCallbackMethod(method);
						listener.setListernerClass(method.getDeclaringClass().getName());
					}
				}
			}
		}
	}

	private void processViewAssignements(List<Widget> views, SootClass activity) {
		Optional<SootMethod> methodOpt = getMethodByName("onCreate", activity);
		if (methodOpt.isPresent()) {
			SootMethod method = methodOpt.get();
			Map<String, SootField> mapa = getAllViewsAssignments(method);

			for (Widget view : views) {
				SootField field = mapa.get(view.getName());
				if (field != null) {
					view.setField(field);
				}
			}
		}
	}

	private Map<String, SootField> getAllViewsAssignments(SootMethod method) {
		// view_name --> soot field ::: stmt_example: soot_field =
		// findViewById(view_name)
		Map<String, SootField> views = new HashMap<>();

		Body body = method.retrieveActiveBody();
		UnitGraph cfg = new BriefUnitGraph(body);

		for (Unit unit : cfg) {
			Stmt stmt = (Stmt) unit;
			if (stmt instanceof AssignStmt && stmt.containsInvokeExpr()) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				Value right = assignStmt.getRightOp();
				if (right instanceof VirtualInvokeExpr) {
					VirtualInvokeExpr expr = (VirtualInvokeExpr) right;
					String invokedMethodName = expr.getMethod().getName();
					if (invokedMethodName.equals("findViewById")) {
						String viewName = getStringName(expr.getArg(0).toString());
						SootField field = findField(assignStmt.getLeftOp(), unit, cfg);
//						log.trace("getAllViewsAssignments() ::: arg0: " + expr.getArg(0) + "::name=" + viewName + ":::left=" + assignStmt.getLeftOp());
						views.put(viewName, field);
					}
				}
			}
		}

		return views;
	}

	private String parseAppStrings(String name) {
		return xmlParser.getStringValueByName(name);
	}

	private List<Widget> parseAppMenu(String menuName) {
		return xmlParser.parseAppMenu(menuName, curWidgetId);
	}

	public String getStringName(String stringValue) {
		return idMap.get(stringValue);
	}

	public String getMenuName(String menuValue) {
		return menuMap.get(menuValue);
	}

	/**
	 * find method in callgraph
	 *
	 * @param cg
	 * @param declClass
	 * @param method
	 * @return
	 */
	public MethodOrMethodContext findMethodContex(CallGraph cg, String declClass, String method) {
		log.trace("findMethodContex: declClass=" + declClass + ", method=" + method);
		for (Edge callEdge : cg) {
			MethodOrMethodContext src = callEdge.getSrc();
			SootMethod srcMethod = src.method();
			String dClassName = srcMethod.getDeclaringClass().getName();
			String methodName = srcMethod.getName();
			if (declClass.equals(dClassName) && method.equals(methodName)) {
				log.trace("findMethodContex ::: " + src);
				return src;
			}
		}
		return null;
	}

	public MethodOrMethodContext findMethodContex(CallGraph cg, Listener listener) {
		return findMethodContex(cg, listener.getListernerClass(), listener.getEventCallback());
	}

//	public SootMethod findMethodContexNovo(Listener listener) {
//		log.trace("findMethodContexNovo: declClass=" + listener.getListernerClass() + ", method=" + listener.getEventCallback());
//		
//		SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(listener.getListernerClass());
//		log.trace("findMethodContexNovo ::: sootClassUnsafe=" + sootClassUnsafe);
//		if (sootClassUnsafe != null) {
//			SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe(listener.getEventCallback());
//			log.trace("findMethodContexNovo ::: methodByNameUnsafe=" + methodByNameUnsafe);
//			listener.setCallbackMethod(methodByNameUnsafe);
//			return methodByNameUnsafe;
//		}
//		return null;
//	}

	@Deprecated
	public void analyseCallGraph() {
		CallGraph cg = Scene.v().getCallGraph();
		for (Edge callEdge : cg) {
			MethodOrMethodContext src = callEdge.getSrc();
			MethodOrMethodContext tgt = callEdge.getTgt();
			System.out.println(src + " --> " + tgt);
		}
	}

	/**
	 * get MenuItems and SubMenus from create menu callback(for example
	 * onCreateOptionsMenu)
	 *
	 * @param menuMethod
	 * @return
	 */
	public List<Widget> getMenuWidgets(SootMethod menuMethod) {
		log.trace("getMenuWidgets: " + menuMethod);
		List<Widget> menuWidgets = new ArrayList<>();
		boolean hasMenuWidget = false;

		Optional<InvokeExpr> invokeExprInflateOpt = getInvokeExprByMethodName("inflate", menuMethod);
		if (invokeExprInflateOpt.isPresent()) {
			InvokeExpr invokeExpr = invokeExprInflateOpt.get();
			SootMethod invokeMethod = invokeExpr.getMethod();
			String signature = invokeMethod.getSignature();
			log.trace("getMenuWidgets111 ::: **** MenuInflater: " + signature);
			Value menuIdValue = invokeExpr.getArg(0);
			log.trace("getMenuWidgets111 ::: menuIdValue=" + menuIdValue);
			String menuName = getMenuName(menuIdValue.toString());
			log.trace("getMenuWidgets111 ::: menuName=" + menuName);
			if (menuName != null) {
				menuWidgets = parseAppMenu(menuName);
			}
		}

		// TODO lista
		ListenerType listenerEnum = ListenerType.OnMenuItemClickListener;
		UnitGraph cfg = new BriefUnitGraph(menuMethod.retrieveActiveBody());
		List<Unit> allInvokeExprSetOnMenuItemClickListenerUnits = getAllInvokeExprByMethodName(listenerEnum.getListernerMethod(), menuMethod);
		for (Unit unit : allInvokeExprSetOnMenuItemClickListenerUnits) {
			Stmt stmt = (Stmt) unit;
			InvokeExpr invokeExprMenuItemClickListener = stmt.getInvokeExpr();
//			invokeExprMenuItemClickListener.getMethod()
			log.trace("getMenuWidgets ::: ####################### setOnMenuItemClickListener " + invokeExprMenuItemClickListener);
			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethod().getSignature());
			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getType());
			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethodRef());
			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getArgs());
			for (Value value : invokeExprMenuItemClickListener.getArgs()) {
				log.trace("getMenuWidgets ::: arg" + value + " ::: " + value.getType() + " ::: " + value.getClass());
			}

			Value invokeParameter = invokeExprMenuItemClickListener.getArg(0);
			SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(invokeParameter.getType().toString());
			log.trace("getMenuWidgets ::: sootClassUnsafe=" + sootClassUnsafe);
			if (sootClassUnsafe != null) {
				SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe(listenerEnum.getEventCallback());
				log.trace("getMenuWidgets ::: methodByNameUnsafe=" + methodByNameUnsafe);
				if (methodByNameUnsafe != null) {
					// TODO
//					String targetClass = testeIntent(methodByNameUnsafe);
//					log.trace("getMenuWidgets ::: ********** targetClass=" + targetClass);
					Widget widget = testeFindMenuWidget(menuWidgets, invokeParameter, cfg, unit);
					if (widget != null) {
						// TODO add targetClass (activity)

						Listener listener = new Listener(listenerEnum);
						listener.setCallbackMethod(methodByNameUnsafe);
						listener.setListernerClass(sootClassUnsafe.getName());
						widget.addListener(listener);
						log.trace("getMenuWidgets ::: ********** widget=" + widget);// + " >>>>>>>>>> " + targetClass);
					}
				}
			}
		}

//		Optional<InvokeExpr> invokeExprOpt = getInvokeExprByMethodName("setOnMenuItemClickListener", menuMethod);
//		if (invokeExprOpt.isPresent()) {
//			InvokeExpr invokeExprMenuItemClickListener = invokeExprOpt.get();
////			invokeExprMenuItemClickListener.getMethod()
//			log.trace("getMenuWidgets ::: ####################### setOnMenuItemClickListener " + invokeExprMenuItemClickListener);
//			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethod().getSignature());
//			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getType());
//			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethodRef());
//			log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getArgs());
//			for (Value value : invokeExprMenuItemClickListener.getArgs()) {
//				log.trace("getMenuWidgets ::: arg" + value + " ::: " + value.getType() + " ::: " + value.getClass());
//			}
//
//			Value invokeParameter = invokeExprMenuItemClickListener.getArg(0);
//
//			// TODO
//			// SootClass sootClassUnsafe =
//			// Scene.v().getSootClassUnsafe("br.unb.cic.cryptoapp.MainActivity$1");
//			SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(invokeParameter.getType().toString());
//			log.trace("getMenuWidgets ::: sootClassUnsafe=" + sootClassUnsafe);
//			if (sootClassUnsafe != null) {
//				SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe("onMenuItemClick");
//				log.trace("getMenuWidgets ::: methodByNameUnsafe=" + methodByNameUnsafe);
//				if (methodByNameUnsafe != null) {
//					String targetClass = testeIntent(methodByNameUnsafe);
//					log.trace("getMenuWidgets ::: ********** targetClass=" + targetClass);
//				}
//			}
//		}

//		if (menuMethod.hasActiveBody()) {
//		UnitGraph cfg = new BriefUnitGraph(menuMethod.retrieveActiveBody());
		UnitPatchingChain unitsChain = menuMethod.retrieveActiveBody().getUnits();
		for (Unit u : unitsChain) {
			Stmt stmt = (Stmt) u;
			log.trace("getMenuWidgets ::: stmt=" + stmt);
			if (stmt.containsInvokeExpr()) {
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				SootMethod invokeMethod = invokeExpr.getMethod();
				String signature = invokeMethod.getSignature();
//				if (signature.equals("<android.view.MenuInflater: void inflate(int,android.view.Menu)>")) {
//					log.trace("getMenuWidgets ::: **** MenuInflater: " + signature);
//					Value menuIdValue = invokeExpr.getArg(0);
//					log.trace("getMenuWidgets ::: menuIdValue=" + menuIdValue);
//					String menuName = getMenuName(menuIdValue.toString());
//					log.trace("getMenuWidgets ::: menuName=" + menuName);
//					if (menuName != null) {
//						return parseAppMenu(menuName);
//					}
//				}

//				getMenuItemClickListener(menu)

//				Optional<InvokeExpr> invokeExprOpt = getInvokeExprByMethodName("setOnMenuItemClickListener", menuMethod);
//				if (invokeExprOpt.isPresent()) {
//					InvokeExpr invokeExprMenuItemClickListener = invokeExprOpt.get();
////					invokeExprMenuItemClickListener.getMethod()
//					log.trace("getMenuWidgets ::: ####################### setOnMenuItemClickListener " + invokeExprMenuItemClickListener);
//					log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethod().getSignature());
//					log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getType());
//					log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getMethodRef());
//					log.trace("getMenuWidgets :::" + invokeExprMenuItemClickListener.getArgs());
//					for (Value value : invokeExprMenuItemClickListener.getArgs()) {
//						log.trace("getMenuWidgets ::: arg" + value + " ::: " + value.getType() + " ::: " + value.getClass());
//					}
//
//					Value invokeParameter = invokeExprMenuItemClickListener.getArg(0);
//
//					// TODO
//					// SootClass sootClassUnsafe =
//					// Scene.v().getSootClassUnsafe("br.unb.cic.cryptoapp.MainActivity$1");
//					SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(invokeParameter.getType().toString());
//					log.trace("getMenuWidgets ::: sootClassUnsafe=" + sootClassUnsafe);
//					if (sootClassUnsafe != null) {
//						SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe("onMenuItemClick");
//						log.trace("getMenuWidgets ::: methodByNameUnsafe=" + methodByNameUnsafe);
//						if (methodByNameUnsafe != null) {
//							String targetClass = testeIntent(methodByNameUnsafe);
//							log.trace("getMenuWidgets ::: ********** targetClass=" + targetClass);
//						}
//					}
//				}

				if (addMenuItemSignatures.contains(signature) || addSubMenuSignatures.contains(signature) || addSubMenuItemSignatures.contains(signature)) {
					hasMenuWidget = true;
					if (signature.equals("<android.view.Menu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>")) {

//						MenuItem menuItem = new MenuItem();
//						menuItem.setId(curWidgetId.inc());
						Value idValue = invokeExpr.getArg(1);
////						int id = Integer.parseInt(idValue.toString());
//						menuItem.setWidgetId(idValue.toString());
						Value textValue = invokeExpr.getArg(3);
//						String text = textValue.toString();
//						menuItem.setText(text);

						Widget menuItem = WidgetBuilderFactory.newMenuItem().widgetId(idValue.toString()).text(textValue.toString()).build();

						menuWidgets.add(menuItem);
					}
					if (signature.equals("<android.view.Menu: android.view.MenuItem add(int,int,int,int)>")) {
//						MenuItem menuItem = new MenuItem();
//						menuItem.setId(curWidgetId.inc());
						Value idValue = invokeExpr.getArg(1);
//						int id = Integer.parseInt(idValue.toString());
//						menuItem.setItemId(id);
						String textIdValue = invokeExpr.getArg(3).toString();
						String textId = getStringName(textIdValue);
						String text = null;
						if (textId != null) {
							text = parseAppStrings(textId);
//							menuItem.setText(text);
						}

						Widget menuItem = WidgetBuilderFactory.newMenuItem().widgetId(idValue.toString()).text(text).build();

						menuWidgets.add(menuItem);
					}
					if (signature.equals("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,java.lang.CharSequence)>")) {
						WidgetBuilder builder = WidgetBuilderFactory.newSubMenu();
//						subMenu.setId(curWidgetId.inc()); //TODO descomentar
						Value idValue = invokeExpr.getArg(1);
						builder.widgetId(idValue.toString());
						Value textValue = invokeExpr.getArg(3);
						String text = textValue.toString();
						builder.text(text);
						List<Widget> items = getSubItems(stmt, cfg);
//                            if(stmt instanceof AssignStmt){
//                                AssignStmt assignStmt = (AssignStmt)stmt;
//                                Value left = assignStmt.getLeftOp();
//                                if(left.getType().toString().equals("android.view.SubMenu")){
//                                    Stmt curStmt = assignStmt;
//                                    while(!cfg.getSuccsOf(curStmt).isEmpty()){
//                                        curStmt = (Stmt)cfg.getSuccsOf(curStmt).get(0);
//                                        if(curStmt.containsInvokeExpr()){
//                                            InvokeExpr curInvokeExpr = curStmt.getInvokeExpr();
//                                            if(curInvokeExpr instanceof InterfaceInvokeExpr){
//                                                InterfaceInvokeExpr interfaceInvokeExpr = (InterfaceInvokeExpr)curInvokeExpr;
//                                                Value invokeObj = interfaceInvokeExpr.getBase();
//                                                SootMethod interfaceInvokeMethod = interfaceInvokeExpr.getMethod();
//                                                String interfaceMethodSign = interfaceInvokeMethod.getSignature();
//                                                if(left.equivTo(invokeObj)){
//                                                    if(interfaceMethodSign.equals("<android.view.SubMenu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>")){
//                                                        MenuItem item = new MenuItem();
//                                                        Value subItemIdValue = interfaceInvokeExpr.getArg(1);
//                                                        int subItemId = Integer.parseInt(subItemIdValue.toString());
//                                                        item.setItemId(subItemId);
//                                                        Value subItemTextValue = interfaceInvokeExpr.getArg(3);
//                                                        String subItemText = subItemTextValue.toString();
//                                                        item.setText(subItemText);
//                                                        items.add(item);
//                                                    }
//                                                    if(interfaceMethodSign.equals("<android.view.SubMenu: android.view.MenuItem add(int,int,int,int)>")){
//                                                        MenuItem item = new MenuItem();
//                                                        Value subItemIdValue = interfaceInvokeExpr.getArg(1);
//                                                        int subItemId = Integer.parseInt(subItemIdValue.toString());
//                                                        item.setItemId(subItemId);
//                                                        Value subItemTextIdValue = interfaceInvokeExpr.getArg(3);
//                                                        String subItemTextId = getStringName(subItemTextIdValue.toString());
//                                                        if(subItemTextId != null){
//                                                            String subItemText = parseAppStrings(subItemTextId);
//                                                            item.setText(subItemText);
//                                                        }
//                                                        items.add(item);
//                                                    }
//                                                }
//                                            }
//                                        }
//                                    }
//                                }
//                            }
						builder.setMenuItems(items);
						menuWidgets.add(builder.build());
					}
					if (signature.equals("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,int)>")) {
						WidgetBuilder builder = WidgetBuilderFactory.newSubMenu();
//						subMenu.setId(curWidgetId.inc()); //TODO descomentar
						Value idValue = invokeExpr.getArg(1);
						builder.widgetId(idValue.toString());
						Value textIdValue = invokeExpr.getArg(3);
						String textId = getStringName(textIdValue.toString());
						if (textId != null) {
							String text = parseAppStrings(textId);
							builder.text(text);
						}
						List<Widget> items = getSubItems(stmt, cfg);
						builder.setMenuItems(items);
						menuWidgets.add(builder.build());
					}
				}
			}
		}
		// TODO ???????
//		if (!hasMenuWidget) {// menu creation is not directly in menuMethod
//			log.trace("getMenuWidgets ::: hasMenuWidget=" + hasMenuWidget);
//			Iterator<Unit> units = cfg.iterator();
//			while (units.hasNext()) {
//				Stmt stmt = (Stmt) units.next();
//				if (stmt.containsInvokeExpr()) {
//					InvokeExpr invokeExpr = stmt.getInvokeExpr();
//					if (invokeExpr.getArgCount() == 1) {
//						Value arg = invokeExpr.getArg(0);
//						if ("android.view.Menu".equals(arg.getType().toString())) {
//							SootMethod m = invokeExpr.getMethod();
//							return getMenuWidgets(m);
//						}
//					}
//				}
//			}
//		}
//		}
		return menuWidgets;
	}

	private Value findMenuDefinitionId(Value value, UnitGraph cfg, Unit unit) {
		log.trace("findMenuDefinitionId ::: value=" + value + " ::: unit=" + unit);
		Stmt stmt = (Stmt) unit;

		if (stmt.containsInvokeExpr()) {
			InvokeExpr invokeExpr = stmt.getInvokeExpr();
			if (invokeExpr instanceof InterfaceInvokeExpr) {
				InterfaceInvokeExpr interfaceInvokeExpr = (InterfaceInvokeExpr) invokeExpr;
				log.trace("findMenuDefinitionId ::: interfaceInvokeExpr=" + interfaceInvokeExpr + " ::: " + interfaceInvokeExpr.getArg(0));
				if (value.equivTo(interfaceInvokeExpr.getArg(0))) {
					Value base = interfaceInvokeExpr.getBase();
					for (Unit pred : cfg.getPredsOf(unit)) {
						return findMenuDefinitionId(base, cfg, pred);
					}
				}
			}
		}

		if (stmt instanceof AssignStmt) {
			AssignStmt assignStmt = (AssignStmt) stmt;
			log.trace("findMenuDefinitionId ::: assignStmt=" + assignStmt);
			if (assignStmt.getLeftOp().equivTo(value)) {
				Value rightOp = assignStmt.getRightOp();
//				TODO if(rightOp instanceof InterfaceInvokeExpr)
				log.trace("findMenuDefinitionId ::: equivTo ....." + assignStmt.getRightOp());
				log.trace("findMenuDefinitionId ::: equivTo ..ID=" + assignStmt.getInvokeExpr().getArg(0));
				return assignStmt.getInvokeExpr().getArg(0);
			}
		}

		for (Unit pred : cfg.getPredsOf(unit)) {
			return findMenuDefinitionId(value, cfg, pred);
		}

		return null;
	}

	private Widget testeFindMenuWidget(List<Widget> menuWidgets, Value arg, UnitGraph cfg, Unit unit) {
		log.trace("testeFindMenuWidget ::: arg=" + arg + " ::: unit=" + unit + " >>>>> " + cfg.getPredsOf(unit));
		Value menuId = findMenuDefinitionId(arg, cfg, unit);
		if (menuId instanceof IntConstant) {
			IntConstant cte = (IntConstant) menuId;
			int id = cte.value;
			log.trace("testeFindMenuWidget ::: testeWWW=" + menuId + " ::: " + menuId.getClass() + " ::: type=" + menuId.getType() + " ::: id=" + id);
			for (Widget widget : menuWidgets) {
				if (widget.getWidgetId().equals(id + "")) {
					log.trace("testeFindMenuWidget ::: widget=" + widget.getWidgetId());
					return widget;
				}
			}
		}
		return null;
	}

	private String testeIntent(SootMethod method) {
		return testeIntent(method, 0);
	}

	private String testeIntent(SootMethod method, int depth) {
		log.trace("testeIntent: " + method.getSignature());

		String intentTargetClass = findIntentDefinition(method);
		if (intentTargetClass != null) {
			log.trace("testeIntent ::: ****** intentTargetClass=" + intentTargetClass);
			return intentTargetClass;
		}

//		UnitGraph cfg = new BriefUnitGraph(method.retrieveActiveBody());
		int currentDepth = ++depth;
		UnitPatchingChain unitsChain = method.retrieveActiveBody().getUnits();
		for (Unit u : unitsChain) {
			Stmt stmt = (Stmt) u;

			if (stmt.containsInvokeExpr()) {
				log.trace("testeIntent ::: invoke=" + stmt);
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				
				if(invokeExpr instanceof StaticInvokeExpr) {
					StaticInvokeExpr staticInvokeExpr = (StaticInvokeExpr) invokeExpr;
					log.trace("testeIntent ::: staticInvokeExpr=" + staticInvokeExpr+" ... ");
				}
				
				
				SootMethod invokeMethod = invokeExpr.getMethod();
				if (invokeMethod.getDeclaringClass().getName().contains(appInfo.getPackage()) && currentDepth < 4) {
					return testeIntent(invokeMethod, currentDepth);
				}
			}

		}
		return null;
	}

	private String findIntentDefinition(SootMethod method) {
		log.trace("findIntentDefinition: " + method.getSignature());
		UnitPatchingChain unitsChain = method.retrieveActiveBody().getUnits();
		for (Unit u : unitsChain) {
			Stmt stmt = (Stmt) u;
			log.trace("findIntentDefinition ::: stmt= " + stmt);
			if (stmt.containsInvokeExpr()) {
				InvokeExpr invokeExpr = stmt.getInvokeExpr();

				if (invokeExpr instanceof SpecialInvokeExpr) {
					SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
					SootMethod invokeMethod = specialInvokeExpr.getMethod();
					String signature = invokeMethod.getSignature();
					if (signature.equals(INTENT_NEW)) {
						Value arg = specialInvokeExpr.getArg(1);
						log.trace("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& INTENT: " + arg + " ::: type=" + arg.getType() + " ::: " + arg.getClass());

						if (arg instanceof ClassConstant) {
							ClassConstant cte = (ClassConstant) arg;
							String internalString = cte.toInternalString();
							log.trace("findIntentDefinition ::: cte= " + cte.getType() + " ::: " + cte.getValue() + " ::: " + cte);
							return internalString.replace('/', '.');
//							System.out.println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"+cte.getValue()+" ::: "+cte.toInternalString()+" ::: "+cte.isRefType());
						}
					}
//					findIntentDefinition(invokeMethod);
				}
			}
		}
		return null;
	}

	private List<Widget> getSubItems(Stmt stmt, UnitGraph cfg) {
		List<Widget> items = new ArrayList<>();
		if (stmt instanceof AssignStmt) {
			AssignStmt assignStmt = (AssignStmt) stmt;
			Value left = assignStmt.getLeftOp();
			if (left.getType().toString().equals("android.view.SubMenu")) {
				Stmt curStmt = assignStmt;
				while (!cfg.getSuccsOf(curStmt).isEmpty()) {
					curStmt = (Stmt) cfg.getSuccsOf(curStmt).get(0);
					if (curStmt.containsInvokeExpr()) {
						InvokeExpr curInvokeExpr = curStmt.getInvokeExpr();
						if (curInvokeExpr instanceof InterfaceInvokeExpr) {
							InterfaceInvokeExpr interfaceInvokeExpr = (InterfaceInvokeExpr) curInvokeExpr;
							Value invokeObj = interfaceInvokeExpr.getBase();
							SootMethod interfaceInvokeMethod = interfaceInvokeExpr.getMethod();
							String interfaceMethodSign = interfaceInvokeMethod.getSignature();
							if (left.equivTo(invokeObj)) {
								if (interfaceMethodSign.equals("<android.view.SubMenu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>")) {
//									MenuItem item = new MenuItem();
//									item.setId(curWidgetId.inc());
									Value subItemIdValue = interfaceInvokeExpr.getArg(1);
//									int subItemId = Integer.parseInt(subItemIdValue.toString());
//									item.setItemId(subItemId);
									Value subItemTextValue = interfaceInvokeExpr.getArg(3);
//									String subItemText = subItemTextValue.toString();
//									item.setText(subItemText);

									Widget item = WidgetBuilderFactory.newMenuItem().widgetId(subItemIdValue.toString()).text(subItemTextValue.toString()).build();

									items.add(item);
								}
								if (interfaceMethodSign.equals("<android.view.SubMenu: android.view.MenuItem add(int,int,int,int)>")) {
//									MenuItem item = new MenuItem();
//									item.setId(curWidgetId.inc());
									Value subItemIdValue = interfaceInvokeExpr.getArg(1);
//									int subItemId = Integer.parseInt(subItemIdValue.toString());
//									item.setItemId(subItemId);
									Value subItemTextIdValue = interfaceInvokeExpr.getArg(3);
									String subItemTextId = getStringName(subItemTextIdValue.toString());
									String text = null;
									if (subItemTextId != null) {
										text = parseAppStrings(subItemTextId);
//										item.setText(subItemText);
									}

									Widget item = WidgetBuilderFactory.newMenuItem().widgetId(subItemIdValue.toString()).text(text).build();

									items.add(item);
								}
							}
						}
					}
				}
			}
		}
		return items;
	}

	public void removeDisEdges(CallGraph cg) {
		log.trace("removeDisEdges ::: qtde_cg=" + cg.size());
		List<Edge> delEdges = new ArrayList<>();
		for (Edge e : cg) {
			MethodOrMethodContext src = e.getSrc();
			MethodOrMethodContext tgt = e.getTgt();
			String srcName = src.method().getName();
			if (!src.toString().contains(appInfo.getPackage()) || src.equals(tgt) || srcName.equals("<clinit>") || src.toString().contains("jacoco")) {
				delEdges.add(e);
				continue;
			}
			if (src.toString().equals("<java.lang.RuntimeException: void <init>(java.lang.String)>") || src.toString().equals("<java.lang.Exception: void <init>()>")) {
				delEdges.add(e);
			}
		}
		log.trace("removeDisEdges ::: qtde_delEdges=" + delEdges.size());
		for (Edge delEdge : delEdges) {
			cg.removeEdge(delEdge);
		}
		log.trace("removeDisEdges ::: qtde_cg_after=" + cg.size());
	}

	private void findStartActivityEdges(CallGraph cg, Edge e, Stack<Edge> path, List<Edge> startActEdges) {
		log.trace("findStartActivityEdges ... " + e.getSrc().method().getSignature() + " >>> " + e.tgt().method().getSignature());
		log.trace("findStartActivityEdges ::: path= " + path);
		MethodOrMethodContext tgt = e.getTgt();
		Iterator<Edge> outEdges = cg.edgesOutOf(tgt);
		if (!path.empty() && isStartActivityMethod(path.peek().tgt())) {
			Edge startActEdge = path.pop();
			log.trace("findStartActivityEdges ::: startActEdge= " + startActEdge);
			startActEdges.add(startActEdge);
			return;
		}
		if (!path.empty() && !outEdges.hasNext()) {
			path.pop();
			return;
		}
		while (outEdges.hasNext()) {
			Edge outEdge = outEdges.next();
			path.push(outEdge);
			log.trace("findStartActivityEdges ::: outEdge=" + outEdge.getSrc().method().getSignature() + " --> " + outEdge.getTgt().method().getSignature());
			findStartActivityEdges(cg, outEdge, path, startActEdges);
		}
		path.pop();
	}

	private void findDepInvokeEdges(CallGraph cg, Edge e, Stack<Edge> path, Set<Edge> depInvokeEdges) {
		log.trace("findDepInvokeEdges: " + e);
		MethodOrMethodContext tgt = e.getTgt();
		Iterator<Edge> outEdges = cg.edgesOutOf(tgt);
		if (!path.empty() && isDepMethod(path.peek().tgt())) {
			Edge depInvokeEdge = path.pop();
			depInvokeEdges.add(depInvokeEdge);
			return;
		}
		if (!path.empty() && !outEdges.hasNext()) {
			path.pop();
			return;
		}
		while (outEdges.hasNext()) {
			Edge outEdge = outEdges.next();
			path.push(outEdge);
			findDepInvokeEdges(cg, outEdge, path, depInvokeEdges);
		}
		path.pop();
	}

	private boolean isStartActivityMethod(SootMethod method) {
		String signature = method.getSignature();
		if (startActivitySignatures.contains(signature)) {
			return true;
		}
		return false;
	}

	private boolean isDepMethod(SootMethod method) {
		String name = method.getName();
		if (name.equals("isChecked")) {
			return true;
		}
		return false;
	}

	private String getTargetAct(UnitGraph cfg, Stmt invokeStmt) {
		log.trace("getTargetAct: " + invokeStmt);
		InvokeExpr startActExpr = invokeStmt.getInvokeExpr();
		Value intentValue = startActExpr.getArg(0);
		log.trace("getTargetAct ::: intentValue: " + intentValue);
		Stmt curStmt = invokeStmt;

		System.out.println("PREDS_OF: " + curStmt);
		cfg.getPredsOf(curStmt).forEach(System.out::println);
		System.out.println("................");
		cfg.getBody().getUnits().forEach(System.out::println);
		System.out.println("................------------");

		while (!cfg.getPredsOf(curStmt).isEmpty()) {
			curStmt = (Stmt) cfg.getPredsOf(curStmt).get(0);
			log.trace("getTargetAct ::: curStmt=" + curStmt);
			if (curStmt instanceof InvokeStmt) {
				InvokeExpr invokeExpr = curStmt.getInvokeExpr();
				if (invokeExpr instanceof VirtualInvokeExpr) {
					VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) invokeExpr;
					SootMethod invokeMethod = virtualInvokeExpr.getMethod();
					String signature = invokeMethod.getSignature();
					if (signature.equals("<android.content.Intent: android.content.Intent setClass(android.content.Context,java.lang.Class)>")) {
						Value invokeObj = virtualInvokeExpr.getBase();
						if (invokeObj.equivTo(intentValue)) {
							return virtualInvokeExpr.getArg(1).toString();
						}
					}
				}
				if (invokeExpr instanceof SpecialInvokeExpr) {
					SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
					log.trace("getTargetAct ::: specialInvokeExpr=" + specialInvokeExpr);
					SootMethod invokeMethod = specialInvokeExpr.getMethod();
					String signature = invokeMethod.getSignature();
					if (signature.equals(INTENT_NEW)) {
						Value invokeObj = specialInvokeExpr.getBase();
						log.trace("getTargetAct ::: invokeObj=" + invokeObj + ":::" + specialInvokeExpr.getArgs() + ":::intentValue=" + intentValue);
						if (invokeObj.equivTo(intentValue)) {
//TODO ...............................
							log.trace("getTargetAct ::: teste ......................................");
							Value arg = specialInvokeExpr.getArg(1);
							String teste = teste(curStmt, arg, cfg);
							log.trace("getTargetAct ::: teste=" + teste);
							if (teste == null) {
								teste = specialInvokeExpr.getArg(1).toString();
							}
							return teste;
//							return specialInvokeExpr.getArg(1).toString();
						}
					}
				}
			}
			if (curStmt instanceof AssignStmt) {
				AssignStmt assign = (AssignStmt) curStmt;
				Value leftValue = assign.getLeftOp();
				if (leftValue.equivTo(intentValue)) {
					Value rightValue = assign.getRightOp();
					if (rightValue instanceof VirtualInvokeExpr) {// intent from other method's return value
						VirtualInvokeExpr intentInvoke = (VirtualInvokeExpr) rightValue;
						SootMethod intentMethod = intentInvoke.getMethod();
						Body intentBody = intentMethod.retrieveActiveBody();
						UnitGraph intentCfg = new BriefUnitGraph(intentBody);
						ReturnStmt returnStmt = getReturnStmt(intentCfg);
						Value returnValue = returnStmt.getOp();
						Stmt intentCurStmt = returnStmt;
						while (!intentCfg.getPredsOf(intentCurStmt).isEmpty()) {
							intentCurStmt = (Stmt) intentCfg.getPredsOf(intentCurStmt).get(0);
							if (intentCurStmt instanceof InvokeStmt) {
								InvokeExpr invokeExpr = intentCurStmt.getInvokeExpr();
								if (invokeExpr instanceof VirtualInvokeExpr) {
									VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) invokeExpr;
									SootMethod invokeMethod = virtualInvokeExpr.getMethod();
									String signature = invokeMethod.getSignature();
									if (signature.equals("<android.content.Intent: android.content.Intent setClass(android.content.Context,java.lang.Class)>")) {
										Value invokeObj = virtualInvokeExpr.getBase();
										if (invokeObj.equivTo(returnValue)) {
											return virtualInvokeExpr.getArg(1).toString();
										}
									}
								}
								if (invokeExpr instanceof SpecialInvokeExpr) {
									SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
									SootMethod invokeMethod = specialInvokeExpr.getMethod();
									String signature = invokeMethod.getSignature();
									if (signature.equals(INTENT_NEW)) {
										Value invokeObj = specialInvokeExpr.getBase();
										if (invokeObj.equivTo(returnValue)) {
											return specialInvokeExpr.getArg(1).toString();
										}
									}
								}
							}
						}
					}
				}
			}
		}
		return null;
	}

	// TODO
	private void getIntentTarget(Stmt stmt) {
		log.trace("getIntentTarget: " + stmt);
		if (stmt instanceof InvokeStmt) {
			InvokeExpr invokeExpr = stmt.getInvokeExpr();
			if (invokeExpr instanceof VirtualInvokeExpr) {
				VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) invokeExpr;
				log.trace("getIntentTarget ::: virtualInvokeExpr=" + virtualInvokeExpr);
				SootMethod invokeMethod = virtualInvokeExpr.getMethod();
				String signature = invokeMethod.getSignature();
				if (signature.equals("<android.content.Intent: android.content.Intent setClass(android.content.Context,java.lang.Class)>")) {
					Value invokeObj = virtualInvokeExpr.getBase();
					log.trace("getIntentTarget ::: virtualInvokeExpr::invokeObj=" + invokeObj + " ::: tmp=" + virtualInvokeExpr.getArg(1));
//					if (invokeObj.equivTo(returnValue)) {
//						return virtualInvokeExpr.getArg(1).toString();
//					}
				}
			}
			if (invokeExpr instanceof SpecialInvokeExpr) {
				SpecialInvokeExpr specialInvokeExpr = (SpecialInvokeExpr) invokeExpr;
				log.trace("getIntentTarget ::: specialInvokeExpr=" + specialInvokeExpr);
				SootMethod invokeMethod = specialInvokeExpr.getMethod();
				String signature = invokeMethod.getSignature();
				if (signature.equals(INTENT_NEW)) {
					Value invokeObj = specialInvokeExpr.getBase();
					log.trace("getIntentTarget ::: specialInvokeExpr::invokeObj=" + invokeObj + " ::: tmp=" + specialInvokeExpr.getArg(1));
					// TODO
//					if (invokeObj.equivTo(returnValue)) {
//						return specialInvokeExpr.getArg(1).toString();
//					}
				}
			}

		}
	}

	private String teste(Stmt curStmt, Value arg, UnitGraph cfg) {
		List<Unit> predsOf = cfg.getPredsOf(curStmt);
		while (!predsOf.isEmpty()) {
			Unit unit = predsOf.remove(0);
			Stmt stmt = (Stmt) unit;
			System.out.println("stmt=" + stmt + "..." + stmt.getClass());
			if (stmt instanceof AssignStmt) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				System.out.println("assignStmt=" + assignStmt);
				if (assignStmt.getLeftOp().equals(arg)) {
					System.out.println("assignStmt ****** right=" + assignStmt.getRightOp());
					return assignStmt.getRightOp().toString();
				}
			}
			if (stmt instanceof IdentityStmt) {
				IdentityStmt idStmt = (IdentityStmt) stmt;
				System.out.println("IdentityStmt: " + idStmt + ":::" + idStmt.getLeftOp() + "::::" + idStmt.getRightOp());
				if (idStmt.getLeftOp().equals(arg)) {
					System.out.println("IdentityStmt ****** right=" + idStmt.getRightOp());
					return idStmt.getRightOp().toString();
				}
			}
			predsOf.addAll(cfg.getPredsOf(unit));
		}
		return null;
	}

	private SootField testeXXXY(Value value, Unit u, UnitGraph cfg, AnalysisType type) {
		List<Unit> units;
		if (type == AnalysisType.FORWARD) {
			units = cfg.getSuccsOf(u);
		} else {
			units = cfg.getPredsOf(u);
		}

		log.trace("testeXXXY ::: value=" + value + " ::: unit=" + u);
//		List<Unit> predsOf = cfg.getPredsOf(u);
		for (Unit unit : units) {
			Stmt stmt = (Stmt) unit;
			log.trace("\t- testeXXXY ::: stmt=" + stmt);
			if (stmt instanceof AssignStmt) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				log.trace("\t- testeXXXY ::: assignStmt=" + assignStmt);
				Value left = assignStmt.getLeftOp();
				Value right = assignStmt.getRightOp();

				if (right instanceof JCastExpr) {
					JCastExpr cast = (JCastExpr) right;
					log.trace("\t- testeXXXY ::: cast=" + cast.getOp());
					if (cast.getOp().equals(value)) {
						log.trace("\t- testeXXXY ::: FOUND cast=" + cast.getOp());
						return testeXXXY(left, unit, cfg, type);
					}
				}
				// TODO identificar quais os outros casos do "right" e tratar ....

				if (left instanceof JInstanceFieldRef) {
					JInstanceFieldRef fieldRef = (JInstanceFieldRef) left;
					log.trace("testeXXXY ::: fieldRef=" + fieldRef + "::right=" + right + ":::value=" + value);
					if (right.equals(value)) {
						log.trace("testeXXXY ::: FIELD=" + fieldRef.getField());
						return fieldRef.getField();
					}
				}
			}
			return testeXXXY(value, unit, cfg, type);
		}
		return null;
	}

	private SootField testeXXX(Value value, Unit u, UnitGraph cfg) {
		return testeXXXY(value, u, cfg, AnalysisType.BACKWARD);
//		log.trace("testeXXX ::: value=" + value + " ::: unit=" + u);
//		List<Unit> predsOf = cfg.getPredsOf(u);
//		for (Unit unit : predsOf) {
//			Stmt stmt = (Stmt) unit;
//			log.trace("\t- testeXXX ::: stmt=" + stmt);
//			if (stmt instanceof AssignStmt) {
//				AssignStmt assignStmt = (AssignStmt) stmt;
//				log.trace("\t- testeXXX ::: assignStmt=" + assignStmt);
//				Value left = assignStmt.getLeftOp();
//				Value right = assignStmt.getRightOp();
//
//				if (right instanceof JCastExpr) {
//					JCastExpr cast = (JCastExpr) right;
//					log.trace("\t- testeXXX ::: cast=" + cast.getOp());
//					if (cast.getOp().equals(value)) {
//						log.trace("\t- testeXXX ::: FOUND cast=" + cast.getOp());
//						return testeXXX(left, unit, cfg);
//					}
//				}
//				// TODO identificar quais os outros casos do "right" e tratar ....
//
//				if (left instanceof JInstanceFieldRef) {
//					JInstanceFieldRef fieldRef = (JInstanceFieldRef) left;
//					log.trace("testeXXX ::: fieldRef=" + fieldRef + "::right=" + right + ":::value=" + value);
//					if (right.equals(value)) {
//						log.trace("testeXXX ::: FIELD=" + fieldRef.getField());
//						return fieldRef.getField();
//					}
//				}
//			}
//			return testeXXX(value, unit, cfg);
//		}
//		return null;
	}

	private SootField findField(Value value, Unit u, UnitGraph cfg) {
		return testeXXXY(value, u, cfg, AnalysisType.FORWARD);
		// TODO .........................ver condicao de parada
//		log.trace("*** findField ::: value=" + value);
//		List<Unit> succsOf = cfg.getSuccsOf(u);
//		for (Unit unit : succsOf) {
//			Stmt stmt = (Stmt) unit;
//			log.trace("findField ::: stmt=" + stmt);
//			if (stmt instanceof AssignStmt) {
//				AssignStmt assignStmt = (AssignStmt) stmt;
//				log.trace("\t- findField ::: assignStmt=" + assignStmt);
//				Value left = assignStmt.getLeftOp();
//				Value right = assignStmt.getRightOp();
//
//				if (right instanceof JCastExpr) {
//					JCastExpr cast = (JCastExpr) right;
//					log.trace("\t- findField ::: cast=" + cast.getOp());
//					if (cast.getOp().equals(value)) {
//						log.trace("\t- findField ::: FOUND cast=" + cast.getOp());
//						return findField(left, unit, cfg);
//					}
//				}
//				// TODO identificar quais os outros casos do "right" e tratar ....
//
//				if (left instanceof JInstanceFieldRef) {
//					JInstanceFieldRef fieldRef = (JInstanceFieldRef) left;
//					log.trace("findField ::: fieldRef=" + fieldRef + "::right=" + right + ":::value=" + value);
//					if (right.equals(value)) {
//						log.trace("findField ::: FIELD=" + fieldRef.getField());
//						return fieldRef.getField();
//					}
//				}
//			}
//		}
//
//		return null;
	}

	public ReturnStmt getReturnStmt(UnitGraph cfg) {
		List<Unit> tails = cfg.getTails();
		return (ReturnStmt) tails.get(0);
	}

	private SootMethod hasOptionsMenu(SootClass act) {
		log.trace("hasOptionsMenu: " + act.getName());
		List<SootMethod> methods = act.getMethods();
		for (SootMethod method : methods) {
			String name = method.getName();
			if (name.equals("onCreateOptionsMenu")) {
				return method;
			}
		}
		return null;
	}

	public void analyseDependencies(List<WindowNode> wNodes) {
		if (app == null) {
			// TODO
			throw new RuntimeException(" iniciar antes..............");
		}

		log.trace("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% analyseDependencies");
		app.constructCallgraph();

		CallGraph cg = Scene.v().getCallGraph();
		removeDisEdges(cg);

		for (WindowNode window : wNodes) {
			log.trace("analyseDependencies ::: window=" + window.getName());
			String windowType = window.getType();
			if (windowType.equals(WindowType.ACT) || windowType.equals(WindowType.DIALOG)) {
				List<Widget> widgets = window.getWidgets();
				for (Widget widget : widgets) {
					log.trace("analyseDependencies ::::: widget=" + widget.getName() + ", " + widget.getType());

					for (Listener listener : widget.getListeners()) {
						log.trace("analyseDependencies :::::::: listener=" + listener.getType());
						List<Widget> dWidgets = new ArrayList<>();
						List<String> w_ids = new ArrayList<>();

						SootMethod cbMethod = listener.getCallbackMethod();
						if (cbMethod == null) {
							MethodOrMethodContext methodContex = findMethodContex(cg, listener);
							if (methodContex != null) {
								cbMethod = methodContex.method();
							}
						}
						log.trace("analyseDependencies :::::::: cbMethod=" + cbMethod);
						if (cbMethod != null) {
							UnitGraph cbCfg = new BriefUnitGraph(cbMethod.retrieveActiveBody());
							Iterator<Unit> stmts = cbCfg.iterator();
							while (stmts.hasNext()) {
								Stmt stmt = (Stmt) stmts.next();
								log.trace("analyseDependencies :::::::: stmt=" + stmt);
								if (isDepStmt(stmt)) {
									log.trace("analyseDependencies :::::::: ************ isDepStmt=" + stmt);
									AssignStmt assignStmt = (AssignStmt) stmt;
									Value rightValue = assignStmt.getRightOp();
									Value invokeObj = ((VirtualInvokeExpr) rightValue).getBase();
									String d_id = findWidgetDef(invokeObj, stmt, cbMethod);
									log.trace("analyseDependencies :::::::: d_id=" + d_id);
									if (d_id != null && !w_ids.contains(d_id)) {
										w_ids.add(d_id);
										// System.out.println(d_id);
//											Widget dWidget = new Widget();
//											dWidget.setId(curWidgetId.inc());
//											dWidget.setWidgetId(d_id);
//											dWidget.setWidgetType(invokeObj.getType().toString());
										// System.out.println(dWidget.getId()+"\t"+dWidget.getWidgetId()+"\t"+dWidget.getWidgetType());

										// TODO buscar pelo id do widget
										Widget dWidget = WidgetBuilderFactory.newWidget(WidgetType.getByWidgetClass(invokeObj.getType().toString())).widgetId(d_id).build();

										dWidgets.add(dWidget);
									}
								}
							}
						}
					}

//					String listener = widget.getListenerName();
//					String eventMethod = "";// TODO w.getEventMethod();
//					CallGraph cg = Scene.v().getCallGraph();
//					removeDisEdges(cg);
//					MethodOrMethodContext cbContext = findMethodContexNovo(listener, eventMethod);
//					if (cbContext != null) {
//                        Iterator<Edge> outEdges = cg.edgesOutOf(cbContext);
//                        Set<Edge> depInvokes = new HashSet<>();
//                        while(outEdges.hasNext()){
//                            Stack<Edge> path = new Stack<>();
//                            Edge outEdge = outEdges.next();
//                            path.push(outEdge);
//                            findDepInvokeEdges(cg,outEdge,path,depInvokes);
//                        }
//                        for(Edge e:depInvokes){
//                            Stmt invokeStmt = e.srcStmt();
//                            if(invokeStmt instanceof AssignStmt){
//                                SootMethod srcMethod = e.src();
//                                InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
//                                if(invokeExpr instanceof VirtualInvokeExpr){
//                                    VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr)invokeExpr;
//                                    Value invokeObj = virtualInvokeExpr.getBase();
//                                    String d_id = findWidgetDef(invokeObj, invokeStmt, srcMethod);
//                                }
//                            }
//                        }
//						SootMethod cbMethod = cbContext.method();
////							if (cbMethod.hasActiveBody()) {
//						UnitGraph cbCfg = new BriefUnitGraph(cbMethod.retrieveActiveBody());
//						Iterator<Unit> stmts = cbCfg.iterator();
//						while (stmts.hasNext()) {
//							Stmt stmt = (Stmt) stmts.next();
//							if (isDepStmt(stmt)) {
//								log.trace("analyseDependencies ::::: isDepStmt="+stmt);
//								AssignStmt assignStmt = (AssignStmt) stmt;
//								Value rightValue = assignStmt.getRightOp();
//								Value invokeObj = ((VirtualInvokeExpr) rightValue).getBase();
//								String d_id = findWidgetDef(invokeObj, stmt, cbMethod);
//								if (d_id != null && !w_ids.contains(d_id)) {
//									w_ids.add(d_id);
//									// System.out.println(d_id);
////										Widget dWidget = new Widget();
////										dWidget.setId(curWidgetId.inc());
////										dWidget.setWidgetId(d_id);
////										dWidget.setWidgetType(invokeObj.getType().toString());
//									// System.out.println(dWidget.getId()+"\t"+dWidget.getWidgetId()+"\t"+dWidget.getWidgetType());
//
//									// TODO rever o type
//									Widget dWidget = WidgetBuilderFactory
//											.newWidget(WidgetType.getByWidgetClass(invokeObj.getType().toString()))
//											.widgetId(d_id)
//											.build();
//
//									dWidgets.add(dWidget);
//								}
//							}
//						}
//							}
//					} 
//					widget.setdWidgets(dWidgets);
				}
			}
		}
	}

	public boolean isDepStmt(Stmt stmt) {
		log.trace("isDepStmt: " + stmt);

//		if(stmt.containsInvokeExpr()) {
//			InvokeExpr invokeExpr = stmt.getInvokeExpr();
//			SootMethod invokeMethod = invokeExpr.getMethod();
//			String name = invokeMethod.getName();
//			// interface android.widget.Checkable: CheckBox, CheckedTextView, CompoundButton, RadioButton, Switch, ToggleButton
//			if (name.equals("isChecked")) {
//				log.trace("isDepStmt ::: isChecked ***********************");
//				return true;
//			}
//		}

		if (stmt instanceof AssignStmt) {
			AssignStmt assignStmt = (AssignStmt) stmt;
			log.trace("isDepStmt ::: assignStmt=" + assignStmt);
			Value right = assignStmt.getRightOp();
			if (right instanceof VirtualInvokeExpr) {
				VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) right;
				log.trace("isDepStmt ::: virtualInvokeExpr=" + virtualInvokeExpr);
				SootMethod invokeMethod = virtualInvokeExpr.getMethod();
				String name = invokeMethod.getName();
				// interface android.widget.Checkable: CheckBox, CheckedTextView,
				// CompoundButton, RadioButton, Switch, ToggleButton
				if (name.equals("isChecked")) {
					log.trace("isDepStmt ::: isChecked ***********************");
					return true;
				}
			}
		}
		return false;
	}

	public TransitionGraph generateTransitionGraph(List<WindowNode> wNodes) {
		log.info("Generating Window Transition Graph ...");
		TransitionGraph graph = new TransitionGraph();
		List<TransitionEdge> edges = new ArrayList<>();
		CallGraph cg = Scene.v().getCallGraph();
		removeDisEdges(cg);
		for (WindowNode window : wNodes) {
			log.trace("generateTransitionGraph ::: window=" + window.getName());
			List<Widget> widgets = window.getWidgets();
			for (Widget widget : widgets) {
				log.trace("generateTransitionGraph :::::: widget=" + widget.getName());
				for (Listener listener : widget.getListeners()) {
					log.trace("generateTransitionGraph ::::::::: listener=" + listener.getType());
					MethodOrMethodContext cbContext = findMethodContex(cg, listener);
					if (cbContext != null) {
						log.trace("generateTransitionGraph ::::::::: cbContext=" + cbContext.method().getSignature());
						Iterator<Edge> outEdges = cg.edgesOutOf(cbContext);
						List<Edge> startActs = new ArrayList<>();
						while (outEdges.hasNext()) {
							Stack<Edge> path = new Stack<>();
							Edge outEdge = outEdges.next();
							path.push(outEdge);
							log.trace("generateTransitionGraph :::::: findStartActivityEdges=" + outEdge);
							findStartActivityEdges(cg, outEdge, path, startActs);
						}
						log.trace("generateTransitionGraph ::::::::: startActs=" + startActs.size());
						for (Edge e : startActs) {
							log.trace("generateTransitionGraph ::::::::: startAct=" + e);
							SootMethod srcMethod = e.src();// the method calling ICC method
//								if (srcMethod.hasActiveBody()) {
							UnitGraph cfg = new BriefUnitGraph(srcMethod.retrieveActiveBody());
							Stmt invokeStmt = e.srcStmt();
							String target = getTargetAct(cfg, invokeStmt);
							if (target != null) {
								log.trace("generateTransitionGraph ::::::::: target=" + e);
								String targetAct = StringUtil.convertToAct(target);
								WindowNode targetWNode = findNodeByName(wNodes, targetAct);
								log.trace("generateTransitionGraph ::::::::: targetWNode=" + targetWNode);
								if (targetWNode != null) {
									TransitionEdge edge = new TransitionEdge();
									edge.setId(++curEdgeId);
									edge.setLabel(appInfo.getLabel());
									edge.setSource(window);
									edge.setTarget(targetWNode);
									edge.setWidget(widget);
									edges.add(edge);
									Set<TransitionEdge> oes = window.getOutEdges();// outedges of source node
									oes.add(edge);
									window.setOutEdges(oes);
								}
							}
//								}
						}
					}
				}

				String listener = widget.getListenerName();
				String eventMethod = "";// TODO w.getEventMethod();
//				CallGraph cg = Scene.v().getCallGraph();
//				removeDisEdges(cg); 
				MethodOrMethodContext cbContext = findMethodContex(cg, listener, eventMethod);
				if (cbContext != null) {
					Iterator<Edge> outEdges = cg.edgesOutOf(cbContext);
					List<Edge> startActs = new ArrayList<>();
					while (outEdges.hasNext()) {
						Stack<Edge> path = new Stack<>();
						Edge outEdge = outEdges.next();
						path.push(outEdge);
						findStartActivityEdges(cg, outEdge, path, startActs);
					}
					for (Edge e : startActs) {
						SootMethod srcMethod = e.src();// the method calling ICC method
//							if (srcMethod.hasActiveBody()) {
						UnitGraph cfg = new BriefUnitGraph(srcMethod.retrieveActiveBody());
						Stmt invokeStmt = e.srcStmt();
						String target = getTargetAct(cfg, invokeStmt);
						if (target != null) {
							System.out.println("TARGET: " + target);
							String targetAct = StringUtil.convertToAct(target);
							WindowNode targetWNode = findNodeByName(wNodes, targetAct);
							if (targetWNode != null) {
								TransitionEdge edge = new TransitionEdge();
								edge.setId(++curEdgeId);
								edge.setLabel(appInfo.getLabel());
								edge.setSource(window);
								edge.setTarget(targetWNode);
								edge.setWidget(widget);
								edges.add(edge);
								Set<TransitionEdge> oes = window.getOutEdges();// outedges of source node
								oes.add(edge);
								window.setOutEdges(oes);
							}
						}
//							}
					}
				}
			}
		}
		graph.setNodes(wNodes);
		graph.setEdges(edges);
		return graph;
	}

	public WindowNode findNodeByName(List<WindowNode> nodes, String name) {
		for (WindowNode node : nodes) {
			if (node.getName().equals(name)) {
				return node;
			}
		}
		return null;
	}

	// TODO usar o findField???
	private String findWidgetDef(Value value, Stmt stmt, SootMethod method) {
		log.trace("findWidgetDef: value=" + value + ", method=" + method.getName() + ", stmt=" + stmt);
		Stmt curStmt = stmt;
		Value curValue = value;
		Stmt dataflowStmt = stmt;
//		if (method.hasActiveBody()) {
		Body body = method.retrieveActiveBody();
		UnitGraph cfg = new BriefUnitGraph(body);
		while (!cfg.getPredsOf(curStmt).isEmpty()) {
			List<Unit> preStmts = cfg.getPredsOf(curStmt);
			curStmt = (Stmt) preStmts.get(0);
			if (curStmt instanceof AssignStmt) {
				AssignStmt curAssignStmt = (AssignStmt) curStmt;
				Value left = curAssignStmt.getLeftOp();
				if (left.equivTo(curValue)) {
					dataflowStmt = curAssignStmt;
					Value right = curAssignStmt.getRightOp();
					if (right instanceof CastExpr) {
						CastExpr castExpr = (CastExpr) right;
						curValue = castExpr.getOp();
					} else {
						curValue = right;
					}
					if (right instanceof VirtualInvokeExpr) {
						VirtualInvokeExpr expr = (VirtualInvokeExpr) right;
						SootMethod rmethod = expr.getMethod();
						String rname = rmethod.getName();
						if (rname.equals("findViewById")) {
							// System.out.println("data flow analyze end, find source findViewById");
							Value arg0 = expr.getArg(0);
							return getStringName(arg0.toString());
						}
					}
				}
			}
		}
		if (dataflowStmt instanceof AssignStmt && dataflowStmt.containsFieldRef()) {
			SootField field = dataflowStmt.getFieldRef().getField();// the ref field
			SootClass refClass = field.getDeclaringClass();
			Stmt refCurStmt = null;
			Value refCurValue = null;
			for (SootMethod refMethod : refClass.getMethods()) {
//					if (refMethod.hasActiveBody()) {
				UnitGraph refCfg = new BriefUnitGraph(refMethod.retrieveActiveBody());
				Iterator<Unit> refStmts = refCfg.iterator();
				while (refStmts.hasNext()) {
					Stmt refStmt = (Stmt) refStmts.next();
					if (refStmt instanceof AssignStmt && refStmt.containsFieldRef()) {
						AssignStmt refAssignStmt = (AssignStmt) refStmt;
						Value refLeft = refAssignStmt.getLeftOp();
						if (refLeft.toString().contains(field.toString())) {
							refCurStmt = refAssignStmt;
							Value refRight = refAssignStmt.getRightOp();
							if (refRight instanceof CastExpr) {
								CastExpr castExpr = (CastExpr) refRight;
								refCurValue = castExpr.getOp();
							} else {
								refCurValue = refRight;
							}
							break;
						}
					}
				}
				if (refCurStmt != null) {
					while (!refCfg.getPredsOf(refCurStmt).isEmpty()) {
						refCurStmt = (Stmt) refCfg.getPredsOf(refCurStmt).get(0);
						if (refCurStmt instanceof AssignStmt) {
							AssignStmt refCurAssignStmt = (AssignStmt) refCurStmt;
							Value refCurLeft = refCurAssignStmt.getLeftOp();
							if (refCurLeft.equivTo(refCurValue)) {
								Value refCurRight = refCurAssignStmt.getRightOp();
								if (refCurRight instanceof CastExpr) {
									CastExpr refCurExpr = (CastExpr) refCurRight;
									refCurValue = refCurExpr.getOp();
								} else {
									refCurValue = refCurRight;
								}
								if (refCurRight instanceof VirtualInvokeExpr) {
									VirtualInvokeExpr invExpr = (VirtualInvokeExpr) refCurRight;
									SootMethod invMethod = invExpr.getMethod();
									String invName = invMethod.getName();
									if (invName.equals("findViewById")) {
										Value invExprArg = invExpr.getArg(0);
										return getStringName(invExprArg.toString());
									}
								}
							}
						}
					}
				}
//					}
			}
		}
//		}
		return null;
	}

	public void runflow() {
		// TODO
		InfoflowAndroidConfiguration conf = new InfoflowAndroidConfiguration();
// androidDirPath is the platforms directory location in android sdk
		conf.getAnalysisFileConfig().setAndroidPlatformDir(sdkPath);
// apkFilePath is the apk file location
		conf.getAnalysisFileConfig().setTargetAPKFile(appInfo.getPath());
// sourceSinkFilePath is the source and sink declaration file
		conf.getAnalysisFileConfig().setSourceSinkFile(sourceSinkFilePath);
// set multi dex flag, if set false, only analyze classes.dex
		conf.setMergeDexFiles(true);
// set AccessPath length limit，the default is 5，setting a negative number means no limit
		conf.getAccessPathConfiguration().setAccessPathLength(-1);
// set Abstraction path length limit，negative number means no limit
		conf.getSolverConfiguration().setMaxAbstractionPathLength(-1);
		SetupApplication setup = new SetupApplication(conf);
// set Callback declaration file（no setting FlowDroid will not find）
		setup.setCallbackFile(callbackPath);
		try {
			setup.runInfoflow();
		} catch (IOException | XmlPullParserException e) {
			e.printStackTrace();
		}
	}

	private String getActivityLayoutFilename(SootClass activity) {
		log.trace("getActivityLayoutFilename(" + activity.getName() + ")");
		Optional<SootMethod> methodOpt = getMethodByName("onCreate", activity);
		if (methodOpt.isPresent()) {
			SootMethod method = methodOpt.get();
			Optional<InvokeExpr> invokeExprOpt = getInvokeExprByMethodName("setContentView", method);
			if (invokeExprOpt.isPresent()) {
				InvokeExpr invokeExpr = invokeExprOpt.get();
				String layoutId = invokeExpr.getArg(0).toString();
				log.trace("\tlayoutId=" + layoutId);
				return getLayoutFieldNameById(layoutId);
			}
		}
		return null;
	}

	private String getLayoutFieldNameById(String layoutId) {
		for (SootField layoutField : rLayoutClass.getFields()) {
			if (layoutField.isFinal() && layoutField.isStatic()) {
				String fieldName = layoutField.getName();
				log.trace("\t  - fieldName=" + fieldName);
				Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					log.trace("\t    tagString=" + tagString);
					String fieldValue = tagString.split(" ")[1];
					if (layoutId.equals(fieldValue)) {
						return fieldName;
					}
				}
			}
		}
		return null;
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

	private List<Unit> getAllInvokeExprByMethodName(String methodName, SootMethod method) {
		List<Unit> invokeExpressions = new ArrayList<>();
		UnitPatchingChain units = method.retrieveActiveBody().getUnits();
		for (Unit u : units) {
			Stmt stmt = (Stmt) u;
			if (stmt.containsInvokeExpr()) {
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				SootMethod invokeMethod = invokeExpr.getMethod();
				if (invokeMethod.getName().equals(methodName)) {
					invokeExpressions.add(u);
				}
			}
		}
		return invokeExpressions;
	}

	private Optional<SootMethod> getMethodByName(String methodName, SootClass clazz) {
		return clazz.getMethods().stream().filter(m -> m.getName().equals(methodName)).findFirst();
	}

	private void initializeR(String basePackage) {
		idMap = new HashMap<>();
		arrayMap = new HashMap<>();
		menuMap = new HashMap<>();
		log.debug("Processing R$ classes");
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			String name = clazz.getName();

			if (name.equals(basePackage + ".R$id")) {
				rIdClass = clazz;
				populateMap(idMap, rIdClass);
			}

			if (name.equals(basePackage + ".R$layout")) {
				rLayoutClass = clazz;
			}

			if (name.equals(basePackage + ".R$menu")) {
				rMenuClass = clazz;
				populateMap(menuMap, rMenuClass);
			}

			if (name.equals(basePackage + ".R$array")) {
				rArrayClass = clazz;
				populateMap(idMap, rArrayClass);
			}
		}
	}

	private void populateMap(final Map<String, String> map, SootClass clazz) {
		log.trace("populateMap: " + clazz.getName());
		for (SootField idField : clazz.getFields()) {
			if (idField.isFinal() && idField.isStatic()) {
				log.trace("populateMap ::: " + idField.getSignature());
				String fieldName = idField.getName();
				Tag fieldTag = idField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					String fieldValue = tagString.split(" ")[1];
					log.trace("\t- " + fieldValue + "=" + fieldName);
					map.put(fieldValue, fieldName);
				}
			}
		}
	}

	private void initSystemCallbacks() {
		systemCallbacks = new ArrayList<>();
		systemCallbacks.add("onSaveInstanceState");
		systemCallbacks.add("onRestoreInstanceState");
		systemCallbacks.add("onTouchEvent");
	}

	private void initStartActSignatures() {
		startActivitySignatures = new ArrayList<>();
		startActivitySignatures.add("<android.app.Activity: void startActivity(android.content.Intent)>");
		startActivitySignatures.add("<android.app.Activity: void startActivity(android.content.Intent,android.os.Bundle)");
		startActivitySignatures.add("<android.app.Activity: void startActivityForResult(android.content.Intent,int)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityForResult(android.content.Intent,int,android.os.Bundle)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityIfNeeded(android.content.Intent,int,android.os.Bundle)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityIfNeeded(android.content.Intent,int)>");
	}

	private void initAddMenuItemSignatures() {
		addMenuItemSignatures = new ArrayList<>();
		addMenuItemSignatures.add("<android.view.Menu: android.view.MenuItem add(int,int,int,int)>");
		addMenuItemSignatures.add("<android.view.Menu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>");
	}

	private void initAddSubMenuSignatures() {
		addSubMenuSignatures = new ArrayList<>();
		addSubMenuSignatures.add("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,int)>");
		addSubMenuSignatures.add("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,java.lang.CharSequence)>");
	}

	private void initAddSubMenuItemSignatures() {
		addSubMenuItemSignatures = new ArrayList<>();
		addSubMenuItemSignatures.add("<android.view.SubMenu: android.view.MenuItem add(int,int,int,int)>");
		addSubMenuItemSignatures.add("<android.view.SubMenu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>");
	}

	public static void main(String[] args) {
		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
		String apk = baseDir + "cryptoapp.apk";

		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
//		String sinksFile = "";
		String callbacksFile = "";

		String outputFile = "/home/pedro/tmp/rvsec-gesda.json";

		SootAnalyze sootAnalyze = new SootAnalyze(androidPlatformsDir, rtJarPath);

		try {
			AppInfo info = sootAnalyze.init(apk);
			List<WindowNode> nodes = sootAnalyze.analyze();

			System.out.println("INFO: ");
			info.getActivities().forEach(System.out::println);
			System.out.println("NODES:");
			nodes.forEach(System.out::println);

//			sootAnalyze.teste123(nodes);

//			sootAnalyze.analyseDependencies(nodes);
//			TransitionGraph graph = sootAnalyze.generateTransitionGraph(nodes);
//			System.out.println("Graph: " + graph);

			ApkInfoOut infoOut = new ApkInfoOut(info, nodes);
			OutputWriter.write(infoOut, new File(outputFile));
		} catch (IOException | XmlPullParserException e) {
			e.printStackTrace();
		}

		System.out.println("FIM DE FESTA !!!");
	}

	private void teste123(List<WindowNode> nodes) {
		for (WindowNode window : nodes) {
			for (Widget widget : window.getWidgets()) {
				for (Listener listener : widget.getListeners()) {
					teste1234(listener);
				}
			}
		}
	}

	private void teste1234(Listener listener) {
		if (listener != null && listener.getCallbackMethod() != null) {
			SootMethod callbackMethod = listener.getCallbackMethod();
			
		}
	}

}
