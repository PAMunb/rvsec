package br.unb.cic.rvsec.taint.xml;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.taint.model.ActivityInfo;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.model.SootActivity;
import br.unb.cic.rvsec.taint.model.ViewInfo;
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
import soot.jimple.internal.JCastExpr;
import soot.jimple.internal.JInstanceFieldRef;
import soot.tagkit.Tag;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.UnitGraph;

public class XmlAnalysis {
	private static Logger log = LoggerFactory.getLogger(XmlAnalysis.class);
	
	private SootClass rIdClass;
	private SootClass rLayoutClass;
	private SootClass rStringClass;
	private SootClass rArrayClass;

	private XmlParser xmlParser;
	
	// map ID to FIELD_NAME in R$id
	private Map<String, String> idMap = new HashMap<>();

	
	public List<SootActivity> processActivities(ApkInfo apkInfo) {		
		log.info("Processing activities ...");
		log.debug("Processing activities ... debug");
		log.trace("Processing activities ... trace");
		log.warn("Processing activities ... warn");
		log.error("Processing activities ... error");
		
		initializeR(apkInfo.getManifestPackage());
		xmlParser = new XmlParser(apkInfo.getPath(), idMap);
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
		log.debug("Processing Activity: " + clazz.getName());

		SootActivity sootActivity = new SootActivity(actInfo, clazz);
		// TODO Auto-generated method stub
//		System.out.println("..." + getActLayout(c));
		String layoutFileName = getActivityLayoutFilename(clazz);
		actInfo.setLayoutFileName(layoutFileName);
		
		List<ViewInfo> views = xmlParser.parseActivityLayout(layoutFileName);
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
			Map<String, SootField> mapa = getAllViewsAssignments(method);

			for (ViewInfo view : views) {
				SootField field = mapa.get(view.getName());
				if(field != null) {
					view.setField(field);
				}
			}
		}
	}
	
	private Map<String, SootField> getAllViewsAssignments(SootMethod method) {
		System.out.println("\ngetAllViewsAssignments");

		// view_name --> soot field ::: soot_field = findViewById(view_name)
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
					String invokedMethodName = expr.getMethod().getName();
					if (invokedMethodName.equals("findViewById")) {
						String viewName = idMap.get(expr.getArg(0).toString());
						SootField field = findField(assignStmt.getLeftOp(), unit, cfg);
						System.out.println("arg0: " + expr.getArg(0) + "::name=" + viewName + ":::left=" + assignStmt.getLeftOp());
						mapa.put(viewName, field);
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
				System.out.println("assignStmt="+assignStmt);

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
	
	
	private Optional<SootMethod> getMethodByName(String methodName, SootClass clazz) {
		return clazz.getMethods().stream().filter(m -> m.getName().equals(methodName)).findFirst();
	}
	
	private void initializeR(String basePackage) {
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			String name = clazz.getName();

			if (name.equals(basePackage + ".R$id")) {
				rIdClass = clazz;
				initializeIdMap();
			}

			if (name.equals(basePackage + ".R$layout")) {
				rLayoutClass = clazz;
			}

			if (name.equals(basePackage + ".R$string")) {
				rStringClass = clazz;
			}

			if (name.equals(basePackage + ".R$array")) {
				rArrayClass = clazz;
			}
		}
	}
	
	
	private void initializeIdMap() {
		idMap = new HashMap<>();
		for (SootField idField : rIdClass.getFields()) {
			if (idField.isFinal() && idField.isStatic()) {
				String fieldName = idField.getName();
				Tag fieldTag = idField.getTag("IntegerConstantValueTag");
				if (fieldTag != null) {
					String tagString = fieldTag.toString();
					String fieldValue = tagString.split(" ")[1];
					idMap.put(fieldValue, fieldName);
				}
			}
		}
	}
	

}
