package br.unb.cic.rvsec.taint.info;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.ApkReader;
import br.unb.cic.rvsec.taint.SootConfig;
import br.unb.cic.rvsec.taint.model.ActivityInfo;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.model.SootActivity;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;
import soot.tagkit.Tag;

public class Teste01 {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
		ApkReader apkReader = new ApkReader();
		ApkInfo apkInfo = apkReader.readApk(apkPath);

		SootConfig sootConfig = new SootConfig();
//		sootConfig.initializeSoot(null, apkPath, androidPlatformsDir, rtJarPath);
		SetupApplication app = sootConfig.initialize(apkPath, androidPlatformsDir, rtJarPath);

		processActivities(apkInfo);

//		LayoutReader layoutReader = new LayoutReader();
//		SootClass layoutClass = layoutReader.getRLayout();
//
//		for (SootField layoutField : layoutClass.getFields()) {
//			if (layoutField.isFinal() && layoutField.isStatic()) {
//				String fieldName = layoutField.getName();
//				System.out.println("FIELD=" + fieldName);
//				Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
//				if (fieldTag != null) {
//					String tagString = fieldTag.toString();
//					System.out.println("\t-tag=" + tagString);
//					String fieldValue = tagString.split(" ")[1];
////				if (layoutValue.equals(fieldValue)) {
////					return fieldName;
////				}
//				}
//			}

//		for (SootClass appClass : Scene.v().getApplicationClasses()) {
//		if (appClass.getName().endsWith("R$layout")) {
//			SootClass layoutClass = appClass;
//			for (SootField layoutField : layoutClass.getFields()) {
//				if (layoutField.isFinal() && layoutField.isStatic()) {
//					String fieldName = layoutField.getName();
//					Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
//					if (fieldTag != null) {
//						String tagString = fieldTag.toString();
//						String fieldValue = tagString.split(" ")[1];
//						if (layoutValue.equals(fieldValue)) {
//							return fieldName;
//						}
//					}
//				}
//			}
//		}
//	}
	}

	private List<SootActivity> processActivities(ApkInfo apkInfo) {
		List<SootActivity> activities = new ArrayList<>();
		for (SootClass c : Scene.v().getApplicationClasses()) {
			for (ActivityInfo actInfo : apkInfo.getActivities()) {
				if (actInfo.getName().equals(c.getName())) {
					System.out.println("CLASS: " + c.getName() + "::" + c.getPackageName() + ":::" + c.getJavaStyleName());
					processActivity(actInfo, c, apkInfo.getPath());
				}
			}
		}
		return activities;
	}

	private SootActivity processActivity(ActivityInfo actInfo, SootClass c, String apkPath) {
		SootActivity sootActivity = new SootActivity(actInfo, c);
		// TODO Auto-generated method stub
		System.out.println("..." + getActLayout(c));
		String layoutFileName = getActLayout(c);
		
		parseAppLayout(layoutFileName, apkPath);

		return sootActivity;
	}
	
	public void parseAppLayout(String filename, String apkPath) {
        String layoutPath = "res/layout/" + filename + ".xml";
        try {
            ApkHandler apkHandler = new ApkHandler(apkPath);
            InputStream layoutStream = apkHandler.getInputStream(layoutPath);
            if (layoutStream != null) {
                AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);
                List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Button");
                if (!buttonNodes.isEmpty()) {
                    for (AXmlNode bNode : buttonNodes) {
//                    System.out.println(getIdName(bNode.getAttribute("id").getValue().toString()));
//                    System.out.println("onClick="+bNode.getAttribute("onClick").getValue());
//                    System.out.println("*******************************");
                        AXmlAttribute<String> callbackAttr = (AXmlAttribute<String>) bNode.getAttribute("onClick");
                        System.out.println("callbackAttr="+callbackAttr);
                        if (callbackAttr != null) {
                            String callback = callbackAttr.getValue();
                            System.out.println("callback="+callback);
                            AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) bNode.getAttribute("id");
                            System.out.println("idAttr="+idAttr);
                            //Integer idValue = (Integer)bNode.getAttribute("id").getValue();
                            String buttonId = idAttr == null ? null : getIdName(idAttr.getValue().toString());
                            System.out.println("buttonId="+buttonId);
//                            Widget button = new Widget();
//                            button.setWidgetType("android.widget.Button");
//                            button.setEvent("click");
//                            button.setEventMethod(callback);
//                            button.setLayoutRegister(1);
//                            button.setWidgetId(buttonId);
//                            layoutWidgets.add(button);
                        }
                    }
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
//        return layoutWidgets;
    }
	
	public String getIdName(String idValue) {
        for (SootClass appClass : Scene.v().getApplicationClasses()) {
            if (appClass.getName().endsWith("R$id")) {
                SootClass idClass = appClass;
                for (SootField idField : idClass.getFields()) {
                    if (idField.isFinal() && idField.isStatic()) {
                        String fieldName = idField.getName();
                        Tag fieldTag = idField.getTag("IntegerConstantValueTag");
                        if (fieldTag != null) {
                            String tagString = fieldTag.toString();
                            String fieldValue = tagString.split(" ")[1];
                            if (idValue.equals(fieldValue)) {
                                return fieldName;
                            }
                        }
                    }
                }
            }
        }
        return null;
    }

	public String getActLayout(SootClass act) {
		List<SootMethod> actMethods = act.getMethods();
		for (SootMethod actMethod : actMethods) {
			String name = actMethod.getName();
			System.out.println("method=" + name);
			if (name.equals("onCreate")) {// && actMethod.hasActiveBody()) {
				System.out.println("\t" + actMethod.getSignature());

				UnitPatchingChain units = actMethod.retrieveActiveBody().getUnits();
				for(Unit u: units) {
					Stmt stmt = (Stmt) u;
					if(stmt.containsInvokeExpr()) {
						InvokeExpr invokeExpr = stmt.getInvokeExpr();
						SootMethod invokeMethod = invokeExpr.getMethod();
						if (invokeMethod.getName().equals("setContentView")) {
							System.out.println(invokeMethod.getSignature());
							String layoutArg = invokeExpr.getArg(0).toString();
							System.out.println("layoutArg=" + layoutArg);
							return getLayoutName(layoutArg);
						}
					}
				}
//				
//				UnitGraph onCreateCfg = new BriefUnitGraph(actMethod.getActiveBody());
//				Iterator<Unit> stmts = onCreateCfg.iterator();
//				while (stmts.hasNext()) {
//					Stmt stmt = (Stmt) stmts.next();
//					if (stmt instanceof InvokeStmt) {
//						InvokeStmt invokeStmt = (InvokeStmt) stmt;
//						InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
//						SootMethod invokeMethod = invokeExpr.getMethod();
//						if (invokeMethod.getName().equals("setContentView")) {
//							System.out.println(invokeMethod.getSignature());
//							String layoutArg = invokeExpr.getArg(0).toString();
//							System.out.println("layoutArg=" + layoutArg);
//							return getLayoutName(layoutArg);
//						}
//					}
//				}
			}
		}
		return null;
	}

	public String getLayoutName(String layoutValue) {
		for (SootClass appClass : Scene.v().getApplicationClasses()) {
			if (appClass.getName().endsWith("R$layout")) {
				SootClass layoutClass = appClass;
				for (SootField layoutField : layoutClass.getFields()) {
					if (layoutField.isFinal() && layoutField.isStatic()) {
						String fieldName = layoutField.getName();
						System.out.println("fieldName=" + fieldName);
						Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
						if (fieldTag != null) {
							String tagString = fieldTag.toString();
							System.out.println("tagString=" + tagString);
							String fieldValue = tagString.split(" ")[1];
							if (layoutValue.equals(fieldValue)) {
								return fieldName;
							}
						}
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

		Teste01 t = new Teste01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
