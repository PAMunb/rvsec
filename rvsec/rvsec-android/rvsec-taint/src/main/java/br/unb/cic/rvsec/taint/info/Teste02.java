package br.unb.cic.rvsec.taint.info;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
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

public class Teste02 {

	private String apkPath;

	private SootClass rId;
	private SootClass rLayout;
	private SootClass rString;
	private SootClass rArray;


	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) throws MOPException, IOException, XmlPullParserException {
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


	private void recuperarClassesR(ApkInfo apkInfo) {
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			String name = clazz.getName();

			if (name.equals(apkInfo.getManifestPackage()+".R$id")) {
				rId = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage()+".R$layout")) {
				rLayout = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage()+".R$string")) {
				rString = clazz;
			}

			if (name.equals(apkInfo.getManifestPackage()+".R$array")) {
				rArray = clazz;
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
			if(entryName.startsWith("res/")) {
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
		String layoutFileName = getActivityLayout(clazz);

		List<ViewInfo> views = parseActivityLayout(layoutFileName);
		actInfo.setViews(views);

		return sootActivity;
	}

	public List<ViewInfo> parseActivityLayout(String filename) {
		List<ViewInfo> views = new ArrayList<>();
        String layoutPath = "res/layout/" + filename + ".xml";
        try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
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
                        System.out.println("\tcallbackAttr="+callbackAttr);
                        if (callbackAttr != null) {
                            String callback = callbackAttr.getValue();
                            System.out.println("\tcallback="+callback);
                            AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) bNode.getAttribute("id");
                            System.out.println("\tidAttr="+idAttr);
                            //Integer idValue = (Integer)bNode.getAttribute("id").getValue();
                            String buttonId = idAttr == null ? null : getIdName(idAttr.getValue().toString());
                            System.out.println("\tbuttonId="+buttonId);
                            ViewInfo info = new ViewInfo();
                            info.setId(idAttr.getValue().toString());
                            info.setName(buttonId);
                            views.add(info);
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
        	//TODO
            e.printStackTrace();
        }
        return views;
    }

	public String getIdName(String idValue) {
//        for (SootClass appClass : Scene.v().getApplicationClasses()) {
//            if (appClass.getName().endsWith("R$id")) {
                SootClass idClass = rId;
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
//            }
//        }
        return null;
    }

	public String getActivityLayout(SootClass activity) {
		List<SootMethod> actMethods = activity.getMethods();
		for (SootMethod actMethod : actMethods) {
			String name = actMethod.getName();
//			System.out.println("method=" + name);
			if (name.equals("onCreate")) {// && actMethod.hasActiveBody()) {
//				System.out.println("\t" + actMethod.getSignature());
				UnitPatchingChain units = actMethod.retrieveActiveBody().getUnits();
				for(Unit u: units) {
					Stmt stmt = (Stmt) u;
					if(stmt.containsInvokeExpr()) {
						InvokeExpr invokeExpr = stmt.getInvokeExpr();
						SootMethod invokeMethod = invokeExpr.getMethod();
						if (invokeMethod.getName().equals("setContentView")) {
							System.out.println(invokeMethod.getSignature());
							String layoutId = invokeExpr.getArg(0).toString();
							System.out.println("layoutId=" + layoutId);
							return getLayoutName(layoutId);
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
//		for (SootClass appClass : Scene.v().getApplicationClasses()) {
//			if (appClass.getName().endsWith("R$layout")) {
				SootClass layoutClass = rLayout;
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
//			}
//		}
		return null;
	}

	public static void main(String[] args) {
		String mopSpecsDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
//		String sinksFile = "";
		String callbacksFile = "";

		Teste02 t = new Teste02();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
