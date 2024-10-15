package com.fdu.se.sootanalyze;

import static com.fdu.se.sootanalyze.model.Constants.addMenuItemSignatures;
import static com.fdu.se.sootanalyze.model.Constants.addSubMenuItemSignatures;
import static com.fdu.se.sootanalyze.model.Constants.addSubMenuSignatures;
import static com.fdu.se.sootanalyze.model.Constants.startActivitySignatures;

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
import com.fdu.se.sootanalyze.utils.NumberIncrementer;
import com.fdu.se.sootanalyze.utils.StringUtil;
import com.fdu.se.sootanalyze.writer.OutputFactory;
import com.fdu.se.sootanalyze.writer.OutputWriter;

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
import soot.jimple.IntConstant;
import soot.jimple.InterfaceInvokeExpr;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.ReturnStmt;
import soot.jimple.SpecialInvokeExpr;
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

	private static final Logger log = LoggerFactory.getLogger(SootAnalyze.class);

	private SetupApplication app;

	private static String sdkPath;
	private static String rtJarPath;

	private static String callbackPath = "AndroidCallbacks.txt";
	private static String sourceSinkFilePath = "SourcesAndSinks.txt";

	private SootClass rIdClass;
	private SootClass rLayoutClass;
	private SootClass rMenuClass;
	private SootClass rArrayClass;

	private XmlParser xmlParser;

	// map ID to FIELD_NAME in R$id
	private Map<String, String> idMap = new HashMap<>();
	private Map<String, String> arrayMap = new HashMap<>();
	private Map<String, String> menuMap = new HashMap<>();

	private long curNodeId = 0;// the current id of WindowNode when constructing Transition Graph
	private final NumberIncrementer curWidgetId = new NumberIncrementer();// the current id of Widget when constructing Transition Graph
	private long curEdgeId = 0;// the current id of TransitionEdge when constructing Transition Graph

	private AppInfo appInfo;

	public SootAnalyze(String androiPlatformsDir, String rtJar) {
		sdkPath = androiPlatformsDir;
		rtJarPath = rtJar;
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

	public List<WindowNode> analyze() throws XmlPullParserException {
		checkSoot();
		log.info("Begin to analyse app: " + StringUtil.convertToLabel(appInfo.getPath()));

		List<WindowNode> activities = new ArrayList<>();// all activities' window node
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			for (ActivityInfo actInfo : appInfo.getActivities()) {
				if (actInfo.getName().equals(clazz.getName())) {
					WindowNode activity = processActivity(actInfo, clazz);
					activities.add(activity);
				}
			}
		}

		return activities;
	}

	private void checkSoot() {
		if (app == null) {
			throw new RuntimeException("Soot not initialized");
		}
	}

	private WindowNode processActivity(ActivityInfo activityInfo, SootClass activitySoot) {
		log.debug("Processing activity: " + activityInfo.getName());
		List<Widget> widgets = new ArrayList<>();// all widgets binding events of the activity

		String layoutFileName = getActivityLayoutFilename(activitySoot);
		activityInfo.setLayoutFileName(layoutFileName);
		log.debug("Activity layout file name: " + layoutFileName);

		if (layoutFileName != null) {
			List<Widget> layoutWidgets = xmlParser.parseActivityLayout(layoutFileName);
			widgets.addAll(layoutWidgets);
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

	private void processWidgets(List<Widget> views, SootClass activity) {
		processViewAssignements(views, activity);
		processDeclaredCallbacks(views, activity);
		processListeners(views, activity);
	}

	private void processListeners(List<Widget> views, SootClass activity) {
		for (SootMethod method : activity.getMethods()) {
			Body body = method.retrieveActiveBody();
			UnitGraph cfg = new BriefUnitGraph(body);
			UnitPatchingChain units = body.getUnits();
			for (Unit u : units) {
				Stmt stmt = (Stmt) u;
				if (stmt.containsInvokeExpr()) {
					InvokeExpr invokeExpr = stmt.getInvokeExpr();
					if (invokeExpr instanceof VirtualInvokeExpr) {
						VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) invokeExpr;
						SootMethod invokeMethod = virtualInvokeExpr.getMethod();
						String invokeMethodName = invokeMethod.getName();
						ListenerType listenerType = BaseListeners.getByListenerMethod(invokeMethodName);
						if (listenerType != null) {
							Value base = virtualInvokeExpr.getBase();// object of call method
							SootField field = findFieldB(base, u, cfg);
							Widget widget = findWidgetByField(field, views);
							if (widget != null) {
								Value arg = virtualInvokeExpr.getArg(0);
								Type listenerArgType = arg.getType();// class name of the listener

								Listener listener = new Listener(listenerType);
								listener.setListenerClass(listenerArgType.toString());
								SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(listenerArgType.toString());
								if (sootClassUnsafe != null) {
									SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe(listenerType.getEventCallback());
									listener.setCallbackMethod(methodByNameUnsafe);
								}
								widget.addListener(listener);
							}
						}
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
		for (Widget widget : views) {
			if (widget.getListeners() != null) {
				for (Listener listener : widget.getListeners()) {
					if (listener.isEventRegisteredInLayoutFile()) {
						Optional<SootMethod> methodOpt = getMethodByName(listener.getCallbackMethodName(), activity);
						if (methodOpt.isPresent()) {
							SootMethod method = methodOpt.get();
							listener.setCallbackMethod(method);
							listener.setListenerClass(method.getDeclaringClass().getName());
						}
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
						if(viewName != null) {
							try {
								SootField field = findField(assignStmt.getLeftOp(), unit, cfg);
								views.put(viewName, field);
							} catch (Throwable e) {								
							}
						}
						
//						SootField field = findField(assignStmt.getLeftOp(), unit, cfg);
//						views.put(viewName, field);
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

	private String getStringName(String stringValue) {
		return idMap.get(stringValue);
	}

	private String getMenuName(String menuValue) {
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
	private MethodOrMethodContext findMethodContext(CallGraph cg, String declClass, String method) {
		for (Edge callEdge : cg) {
			MethodOrMethodContext src = callEdge.getSrc();
			SootMethod srcMethod = src.method();
			String dClassName = srcMethod.getDeclaringClass().getName();
			String methodName = srcMethod.getName();
			if (declClass.equals(dClassName) && method.equals(methodName)) {
				return src;
			}
		}
		return null;
	}

	private MethodOrMethodContext findMethodContext(CallGraph cg, Listener listener) {
		return findMethodContext(cg, listener.getListenerClass(), listener.getEventCallback());
	}

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
	private List<Widget> getMenuWidgets(SootMethod menuMethod) {
		List<Widget> menuWidgets = new ArrayList<>();
//		boolean hasMenuWidget = false;

		Optional<InvokeExpr> invokeExprInflateOpt = getInvokeExprByMethodName("inflate", menuMethod);
		if (invokeExprInflateOpt.isPresent()) {
			InvokeExpr invokeExpr = invokeExprInflateOpt.get();
			SootMethod invokeMethod = invokeExpr.getMethod();
			String signature = invokeMethod.getSignature();
			Value menuIdValue = invokeExpr.getArg(0);
			String menuName = getMenuName(menuIdValue.toString());
			if (menuName != null) {
				menuWidgets = parseAppMenu(menuName);
			}
		}

		// TODO lista
		ListenerType listenerEnum = ListenerType.OnMenuItemClickListener;
		UnitGraph cfg = new BriefUnitGraph(menuMethod.retrieveActiveBody());
		List<Unit> allInvokeExprSetOnMenuItemClickListenerUnits = getAllInvokeExprByMethodName(listenerEnum.getListenerMethod(), menuMethod);
		for (Unit unit : allInvokeExprSetOnMenuItemClickListenerUnits) {
			Stmt stmt = (Stmt) unit;
			InvokeExpr invokeExprMenuItemClickListener = stmt.getInvokeExpr();
			Value invokeParameter = invokeExprMenuItemClickListener.getArg(0);
			SootClass sootClassUnsafe = Scene.v().getSootClassUnsafe(invokeParameter.getType().toString());
			if (sootClassUnsafe != null) {
				SootMethod methodByNameUnsafe = sootClassUnsafe.getMethodByNameUnsafe(listenerEnum.getEventCallback());
				if (methodByNameUnsafe != null) {
					Widget widget = findMenuWidget(menuWidgets, invokeParameter, cfg, unit);
					if (widget != null) {
						Listener listener = new Listener(listenerEnum);
						listener.setCallbackMethod(methodByNameUnsafe);
						listener.setListenerClass(sootClassUnsafe.getName());
						widget.addListener(listener);
					}
				}
			}
		}

		UnitPatchingChain unitsChain = menuMethod.retrieveActiveBody().getUnits();
		for (Unit u : unitsChain) {
			Stmt stmt = (Stmt) u;
			if (stmt.containsInvokeExpr()) {
				InvokeExpr invokeExpr = stmt.getInvokeExpr();
				SootMethod invokeMethod = invokeExpr.getMethod();
				String signature = invokeMethod.getSignature();

				if (addMenuItemSignatures.contains(signature) || addSubMenuSignatures.contains(signature) || addSubMenuItemSignatures.contains(signature)) {
//					hasMenuWidget = true;
					if (signature.equals("<android.view.Menu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>")) {
						Value idValue = invokeExpr.getArg(1);
						Value textValue = invokeExpr.getArg(3);

						Widget menuItem = WidgetBuilderFactory.newMenuItem().widgetId(idValue.toString()).text(textValue.toString()).build();

						menuWidgets.add(menuItem);
					}
					if (signature.equals("<android.view.Menu: android.view.MenuItem add(int,int,int,int)>")) {
						Value idValue = invokeExpr.getArg(1);
						String textIdValue = invokeExpr.getArg(3).toString();
						String textId = getStringName(textIdValue);
						String text = null;
						if (textId != null) {
							text = parseAppStrings(textId);
						}

						Widget menuItem = WidgetBuilderFactory.newMenuItem().widgetId(idValue.toString()).text(text).build();

						menuWidgets.add(menuItem);
					}
					if (signature.equals("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,java.lang.CharSequence)>")) {
						WidgetBuilder builder = WidgetBuilderFactory.newSubMenu();
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
		return menuWidgets;
	}

	private Value findMenuDefinitionId(Value value, UnitGraph cfg, Unit unit) {
		Stmt stmt = (Stmt) unit;

		if (stmt.containsInvokeExpr()) {
			InvokeExpr invokeExpr = stmt.getInvokeExpr();
			if (invokeExpr instanceof InterfaceInvokeExpr) {
				InterfaceInvokeExpr interfaceInvokeExpr = (InterfaceInvokeExpr) invokeExpr;
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
			if (assignStmt.getLeftOp().equivTo(value)) {
				Value rightOp = assignStmt.getRightOp();
				if (rightOp instanceof InterfaceInvokeExpr) {
					return assignStmt.getInvokeExpr().getArg(0);
				}
			}
		}

		for (Unit pred : cfg.getPredsOf(unit)) {
			return findMenuDefinitionId(value, cfg, pred);
		}

		return null;
	}

	private Widget findMenuWidget(List<Widget> menuWidgets, Value arg, UnitGraph cfg, Unit unit) {
		Value menuId = findMenuDefinitionId(arg, cfg, unit);
		if (menuId instanceof IntConstant) {
			IntConstant cte = (IntConstant) menuId;
			int id = cte.value;
			for (Widget widget : menuWidgets) {
				if (widget.getWidgetId().equals(id + "")) {
					return widget;
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
									Value subItemIdValue = interfaceInvokeExpr.getArg(1);
									Value subItemTextValue = interfaceInvokeExpr.getArg(3);

									Widget item = WidgetBuilderFactory.newMenuItem().widgetId(subItemIdValue.toString()).text(subItemTextValue.toString()).build();

									items.add(item);
								}
								if (interfaceMethodSign.equals("<android.view.SubMenu: android.view.MenuItem add(int,int,int,int)>")) {
									Value subItemIdValue = interfaceInvokeExpr.getArg(1);
									Value subItemTextIdValue = interfaceInvokeExpr.getArg(3);
									String subItemTextId = getStringName(subItemTextIdValue.toString());
									String text = null;
									if (subItemTextId != null) {
										text = parseAppStrings(subItemTextId);
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

	private void removeDisEdges(CallGraph cg) {
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
		for (Edge delEdge : delEdges) {
			cg.removeEdge(delEdge);
		}
	}

	private void findStartActivityEdges(CallGraph cg, Edge e, Stack<Edge> path, List<Edge> startActEdges) {
		MethodOrMethodContext tgt = e.getTgt();
		Iterator<Edge> outEdges = cg.edgesOutOf(tgt);
		if (!path.empty() && isStartActivityMethod(path.peek().tgt())) {
			Edge startActEdge = path.pop();
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
		return startActivitySignatures.contains(signature);
	}

	private boolean isDepMethod(SootMethod method) {
		String name = method.getName();
		return name.equals("isChecked");
	}

	private String getTargetAct(UnitGraph cfg, Stmt invokeStmt) {
		InvokeExpr startActExpr = invokeStmt.getInvokeExpr();
		Value intentValue = startActExpr.getArg(0);
		Stmt curStmt = invokeStmt;

		while (!cfg.getPredsOf(curStmt).isEmpty()) {
			curStmt = (Stmt) cfg.getPredsOf(curStmt).get(0);
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
					SootMethod invokeMethod = specialInvokeExpr.getMethod();
					String signature = invokeMethod.getSignature();
					if (signature.equals(INTENT_NEW)) {
						Value invokeObj = specialInvokeExpr.getBase();
						if (invokeObj.equivTo(intentValue)) {
							return specialInvokeExpr.getArg(1).toString();
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

	private SootField findField(Value value, Unit u, UnitGraph cfg, AnalysisType type) {
//		System.out.println("findField: value="+value+", unit="+u+", type="+type);
		List<Unit> units;
		if (type == AnalysisType.FORWARD) {
			units = cfg.getSuccsOf(u);
		} else {
			units = cfg.getPredsOf(u);
		}

		for (Unit currentUnit : units) {
			Stmt stmt = (Stmt) currentUnit;
//			System.out.println(" - findField: value="+value+", unit="+currentUnit);
			if (stmt instanceof AssignStmt) {
				AssignStmt assignStmt = (AssignStmt) stmt;
				Value left = assignStmt.getLeftOp();
				Value right = assignStmt.getRightOp();

				if (right instanceof JCastExpr) {
					JCastExpr cast = (JCastExpr) right;
					if (cast.getOp().equals(value)) {
						return findField(left, currentUnit, cfg, type);
					}
				}
				// TODO identificar quais os outros casos do "right" e tratar ....
				if (left instanceof JInstanceFieldRef) {
					JInstanceFieldRef fieldRef = (JInstanceFieldRef) left;
					if (right.equals(value)) {
						return fieldRef.getField();
					}
				}
			}
			return findField(value, currentUnit, cfg, type);
		}
		return null;
	}

	private SootField findFieldB(Value value, Unit u, UnitGraph cfg) {
		return findField(value, u, cfg, AnalysisType.BACKWARD);
	}

	private SootField findField(Value value, Unit u, UnitGraph cfg) {
		return findField(value, u, cfg, AnalysisType.FORWARD);
	}

	private ReturnStmt getReturnStmt(UnitGraph cfg) {
		List<Unit> tails = cfg.getTails();
		return (ReturnStmt) tails.get(0);
	}

	private SootMethod hasOptionsMenu(SootClass act) {
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
		log.info("Analyzing Dependencies ...");
		checkSoot();

//		app.constructCallgraph();
//
//		CallGraph cg = Scene.v().getCallGraph();
//		removeDisEdges(cg);

		for (WindowNode window : wNodes) {
			String windowType = window.getType();
			if (windowType.equals(WindowType.ACT) || windowType.equals(WindowType.DIALOG)) {
				List<Widget> widgets = window.getWidgets();
				for (Widget widget : widgets) {
					List<Widget> dWidgets = new ArrayList<>();
					widget.setdWidgets(dWidgets);
					for (Listener listener : widget.getListeners()) {
						List<String> w_ids = new ArrayList<>();

						SootMethod cbMethod = listener.getCallbackMethod();
//						if (cbMethod == null) {
//							MethodOrMethodContext methodContex = findMethodContex(cg, listener);
//							if (methodContex != null) {
//								cbMethod = methodContex.method();
//							}
//						}
						if (cbMethod != null && cbMethod.hasActiveBody()) {
							UnitGraph cbCfg = new BriefUnitGraph(cbMethod.retrieveActiveBody());
							for (Unit unit : cbCfg) {
								Stmt stmt = (Stmt) unit;
								if (isDepStmt(stmt)) {
									AssignStmt assignStmt = (AssignStmt) stmt;
									Value rightValue = assignStmt.getRightOp();
									Value invokeObj = ((VirtualInvokeExpr) rightValue).getBase();
									String d_id = findWidgetDef(invokeObj, stmt, cbMethod);
									if (d_id != null && !w_ids.contains(d_id)) {
										w_ids.add(d_id);

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

	private boolean isDepStmt(Stmt stmt) {
		if (stmt instanceof AssignStmt) {
			AssignStmt assignStmt = (AssignStmt) stmt;
			Value right = assignStmt.getRightOp();
			if (right instanceof VirtualInvokeExpr) {
				VirtualInvokeExpr virtualInvokeExpr = (VirtualInvokeExpr) right;
				SootMethod invokeMethod = virtualInvokeExpr.getMethod();
				String name = invokeMethod.getName();
				// interface android.widget.Checkable: CheckBox, CheckedTextView,
				// CompoundButton, RadioButton, Switch, ToggleButton
				return name.equals("isChecked");
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
			List<Widget> widgets = window.getWidgets();
			for (Widget widget : widgets) {
				for (Listener listener : widget.getListeners()) {
					MethodOrMethodContext cbContext = findMethodContext(cg, listener);
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
							UnitGraph cfg = new BriefUnitGraph(srcMethod.retrieveActiveBody());
							Stmt invokeStmt = e.srcStmt();
							String target = getTargetAct(cfg, invokeStmt);
							if (target != null) {
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
						}
					}
				}

				String listener = ""; // widget.getListenerName();
				String eventMethod = "";// TODO w.getEventMethod();
//				CallGraph cg = Scene.v().getCallGraph();
//				removeDisEdges(cg); 
				MethodOrMethodContext cbContext = findMethodContext(cg, listener, eventMethod);
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
						UnitGraph cfg = new BriefUnitGraph(srcMethod.retrieveActiveBody());
						Stmt invokeStmt = e.srcStmt();
						String target = getTargetAct(cfg, invokeStmt);
						if (target != null) {
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
					}
				}
			}
		}
		graph.setNodes(wNodes);
		graph.setEdges(edges);
		return graph;
	}

	private WindowNode findNodeByName(List<WindowNode> nodes, String name) {
		for (WindowNode node : nodes) {
			if (node.getName().equals(name)) {
				return node;
			}
		}
		return null;
	}

	// TODO use findField???
	private String findWidgetDef(Value value, Stmt stmt, SootMethod method) {
		Stmt curStmt = stmt;
		Value curValue = value;
		Stmt dataflowStmt = stmt;
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
				UnitGraph refCfg = new BriefUnitGraph(refMethod.retrieveActiveBody());
				for (Unit unit : refCfg) {
					Stmt refStmt = (Stmt) unit;
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
		InfoflowAndroidConfiguration conf = new InfoflowAndroidConfiguration();
		// androidDirPath is the platforms directory location in android sdk
		conf.getAnalysisFileConfig().setAndroidPlatformDir(sdkPath);
		// apkFilePath is the apk file location
		conf.getAnalysisFileConfig().setTargetAPKFile(appInfo.getPath());
		// sourceSinkFilePath is the source and sink declaration file
		conf.getAnalysisFileConfig().setSourceSinkFile(sourceSinkFilePath);
		// set multi dex flag, if set false, only analyze classes.dex
		conf.setMergeDexFiles(true);
		// set AccessPath length limit，the default is 5，setting a negative number means
		// no limit
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
		Optional<SootMethod> methodOpt = getMethodByName("onCreate", activity);
		if (methodOpt.isPresent()) {
			SootMethod method = methodOpt.get();
			Optional<InvokeExpr> invokeExprOpt = getInvokeExprByMethodName("setContentView", method);
			if (invokeExprOpt.isPresent()) {
				InvokeExpr invokeExpr = invokeExprOpt.get();
				String layoutId = invokeExpr.getArg(0).toString();
				return getLayoutFieldNameById(layoutId);
			}
		}
		return null;
	}

	private String getLayoutFieldNameById(String layoutId) {
		if (rLayoutClass != null) {
			for (SootField layoutField : rLayoutClass.getFields()) {
				if (layoutField.isFinal() && layoutField.isStatic()) {
					String fieldName = layoutField.getName();
					Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
					if (fieldTag != null) {
						String tagString = fieldTag.toString();
						String fieldValue = tagString.split(" ")[1];
						if (layoutId.equals(fieldValue)) {
							return fieldName;
						}
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
				populateMap(arrayMap, rArrayClass);
				populateMap(idMap, rArrayClass);
			}
		}
	}

	private void populateMap(final Map<String, String> map, SootClass clazz) {
		for (SootField idField : clazz.getFields()) {
			if (idField.isFinal() && idField.isStatic()) {
				String fieldName = idField.getName();
				Tag fieldTag = idField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					String fieldValue = tagString.split(" ")[1];
					map.put(fieldValue, fieldName);
				}
			}
		}
	}

	private static Map<String, Throwable> problemas = new HashMap<>();

	public static void main(String[] args) {
		ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
		root.setLevel(ch.qos.logback.classic.Level.TRACE);

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
//		String apk = baseDir + "cryptoapp.apk";
//		String apk = baseDir + "media.apk";
//		String apk = baseDir + "osmtracker.apk";
		String apk = "/home/pedro/desenvolvimento/RV_ANDROID/apks/11/com.zzzmode.appopsx_125.apk";

		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
//		String sinksFile = "";
		String callbacksFile = "";

		String outputFile = "/home/pedro/tmp/rvsec-gesda.json";

//		run(androidPlatformsDir, rtJarPath, apk, outputFile);
		
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/09/com.saverio.wordoftheday_en_15.apk=UnitThrowAnalysis StmtSwitch: type of throw argument is not a RefType!
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/11/com.zoffcc.applications.zanavi_257.apk=No method source set for method <com.zoffcc.applications.zanavi.Navit: void AppCrashC()>
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/08/com.paranoiaworks.unicus.android.sse_118.apk=UnitThrowAnalysis StmtSwitch: type of throw argument is not a RefType!
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/07/com.koushikdutta.superuser_1030.apk=null
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/06/com.hwloc.lstopo_271.apk=No method source set for method <com.hwloc.lstopo.MainActivity: int start(com.hwloc.lstopo.Lstopo,int,java.lang.String,java.util.ArrayList)>
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/16/idv.markkuo.ambitsync_9.apk=No method source set for method <idv.markkuo.ambitsync.MainActivity: int getBatteryPercent(long)>
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/06/com.jvillalba.apod.classic_11.apk=null
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/11/com.xabber.android_644.apk=The property "type" is null.
//		*** /home/pedro/desenvolvimento/RV_ANDROID/apks/02/com.Bisha.TI89EmuDonation_1133.apk=No method source set for method <com.graph89.emulationcore.EmulatorActivity: void nativeCleanGraph89()>
		
		List<String> apksComProblemas = List.of("/home/pedro/desenvolvimento/RV_ANDROID/apks/11/com.zzzmode.appopsx_125.apk");
		
		for(int i=1; i< 29; i++) {
			String idx = String.format("%02d", i);
			System.out.println("\n\n\n**************************\n**************************\n**************************\n"+idx+"\n**************************\n**************************\n**************************");
			printProblems();
			System.out.println("**************************\n**************************\n**************************");
			File apksDir = new File("/home/pedro/desenvolvimento/RV_ANDROID/apks/"+idx);
			for (File file : apksDir.listFiles()) {
				if(apksComProblemas.contains(file.getAbsolutePath())) {
					continue;
				}
				run(androidPlatformsDir, rtJarPath, file.getAbsolutePath(), outputFile);
			}
		}

//		File apksDir = new File("/home/pedro/desenvolvimento/RV_ANDROID/apks/03");
//		for (File file : apksDir.listFiles()) {
//			run(androidPlatformsDir, rtJarPath, file.getAbsolutePath(), outputFile);
//		}
//
		
		// /home/pedro/desenvolvimento/RV_ANDROID/apks/11/com.zzzmode.appopsx_125.apk
		
//		printProblems();

		System.out.println("FIM DE FESTA !!!");
	}

	private static void printProblems() {
		System.out.println("PROBLEMAS: "+problemas.size());
		for (String chave : problemas.keySet()) {
			System.out.println("*** "+chave+"="+problemas.get(chave).getMessage());
		}
	}

	private static void run(String androidPlatformsDir, String rtJarPath, String apk, String outputFile) {
		SootAnalyze sootAnalyze = new SootAnalyze(androidPlatformsDir, rtJarPath);

		try {
			AppInfo info = sootAnalyze.init(apk);
			List<WindowNode> nodes = sootAnalyze.analyze();

			System.out.println("INFO: ");
			info.getActivities().forEach(System.out::println);
			System.out.println("NODES:");
			nodes.forEach(System.out::println);

//			sootAnalyze.teste123(nodes);

			sootAnalyze.analyseDependencies(nodes);
//			TransitionGraph graph = sootAnalyze.generateTransitionGraph(nodes);
//			System.out.println("Graph: " + graph);

			ApkInfoOut infoOut = OutputFactory.createApkInfoOut(info, nodes);
			OutputWriter.write(infoOut, new File(outputFile));
		} catch (Throwable t) {
			t.printStackTrace();
			problemas.put(apk, t);
		}
	}

}
