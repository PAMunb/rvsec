package br.unb.cic.rvsec.taint.tmp;

//import java.io.File;
//import java.io.IOException;
//import java.util.ArrayList;
//import java.util.HashSet;
//import java.util.List;
//import java.util.Set;
//
//import org.dom4j.Document;
//import org.dom4j.DocumentException;
//import org.dom4j.Element;
//import org.dom4j.io.SAXReader;
//
//import br.unb.cic.rvsec.taint.model.Activity;
//import brut.androlib.ApkDecoder;
//import brut.androlib.Config;

public class TesteApktool {
//
//	private void decodeApk(File apk, File outDir) throws Exception {
//		Config config = Config.getDefaultConfig();
//		config.setDecodeResources(Config.DECODE_RESOURCES_FULL);
//		config.setDecodeSources(Config.DECODE_SOURCES_NONE);
//		config.setDecodeAssets(Config.DECODE_ASSETS_FULL);
////		config.setDecodeResolveMode(Config.);
//		ApkDecoder decoder = new ApkDecoder(config, apk);
//		decoder.decode(outDir);
////		String appName = "cryptoapp";
////		try {
////			decoder.setOutDir(new File("apks\\" + appName));
////			decoder.setApkFile(apk);
////			decoder.setDecodeSources((short) 0);// does not decompile sources
////			decoder.decode();
////			System.out.println("decompile " + appName + " successfully");
////		} catch (Exception e) {
////			System.out.println("decompile " + appName + " failed");
////			e.printStackTrace();
////		}
//	}
//
//	private void listActivities(File decodedDir) throws IOException, DocumentException {
//		System.out.println("listActivities....");
//		Set<Activity> atividades = new HashSet<>();
//		File[] activityFiles = decodedDir.listFiles((dir, name) -> name.endsWith(".xml") && name.startsWith("AndroidManifest"));
//		System.out.println("activityFiles=" + activityFiles.length);
//		for (File activityFile : activityFiles) {
//			System.out.println("activityFile=" + activityFile.getAbsolutePath());
//			List<Activity> list = parseActivityFile(activityFile);
//			atividades.addAll(list);
//		}
//		for (Activity atv : atividades) {
//			System.out.println(atv+":::"+atv.isMain());
//		}
//	}
//
//	private void parseActivityFileNovo(File activityFile) {
//		System.out.println("parseActivityFileNovo ...");
//	}
//
//	private static List<Activity> parseActivityFile(File activityFile) throws IOException, DocumentException {
//		System.out.println("parseActivityFile ...");
//
//		List<Activity> activities = new ArrayList<>();
//
//		SAXReader reader = new SAXReader();
//		Document document = reader.read(activityFile);
//		Element rootElement = document.getRootElement();
//
//		Element application = rootElement.element("application");
//		if (application != null) {
//			for (Element activity : application.elements("activity")) {
//				boolean isMain = false;
//				String activityName = activity.attribute("name").getStringValue();
//				List<Element> intents = activity.elements("intent-filter");
//				if (intents != null && intents.size() > 0) {
//					for (Element intent : intents) {
//						Element actionElement = intent.element("action");
//						if (actionElement != null) {
//							String action = actionElement.attribute("name").getStringValue();
//							if ("android.intent.action.MAIN".equals(action)) {
//								isMain = true;
//							}
//						}
//					}
//				}
//				activities.add(new Activity(activityName, isMain));
//			}
//		}
//		return activities;
//	}
//
//	public static void main(String[] args) {
//		File apk = new File("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/cryptoapp.apk");
//		File outDir = new File("/home/pedro/tmp/apktool/cryptoapp");
//		TesteApktool t1 = new TesteApktool();
//		try {
////			t1.decodeApk(apk, outDir);
//
//			t1.listActivities(outDir);
//
//		} catch (Exception e) {
//			e.printStackTrace();
//		}
//	}

}
