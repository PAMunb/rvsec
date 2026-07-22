package br.unb.cic.rvsec.apk.reader;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.apk.model.ActivityInfo;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.util.FileUtil;
import brut.androlib.ApkDecoder;
import brut.androlib.exceptions.AndrolibException;
import brut.directory.DirectoryException;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;
import soot.jimple.infoflow.android.manifest.binary.BinaryManifestActivity;
import soot.jimple.infoflow.android.resources.ARSCFileParser;

public class AppReader {
	private static Logger log = LoggerFactory.getLogger(AppReader.class);
	
	private static final String PACKAGE = "package";
	private static final String NAME = "name";

	static final String INTENT_FILTER = "intent-filter";
	static final String ACTION = "action";
	static final String MAIN = "android.intent.action.MAIN";

	public static AppInfo readApk(String apkPath) throws IOException, XmlPullParserException {
		log.info("Reading APK: "+apkPath);
		final File targetAPK = new File(apkPath);

		AppInfo appInfo = new AppInfo(apkPath);
//		boolean samePackage = false;

		ARSCFileParser resources = new ARSCFileParser();
		resources.parse(targetAPK.getAbsolutePath());

		try (ProcessManifest processManifest = new ProcessManifest(targetAPK, resources)) {
			log.debug("Processing manifest");
//			Set<String> appPackage = new HashSet<>();
			AXmlNode manifest = processManifest.getManifest();

			String manifestPackage = getAttributeAsString(PACKAGE, manifest);
			log.debug("Package: "+manifestPackage);
			appInfo.setPackage(manifestPackage);
			appInfo.setAppName(processManifest.getApplication().getName());

			for (BinaryManifestActivity binaryManifestActivity : processManifest.getActivities()) {
				ActivityInfo activityInfo = readActivity(binaryManifestActivity, manifestPackage);
//				if (!activityInfo.getPackageName().startsWith(appInfo.getPackage())) {
//					samePackage = false;
//					appPackage.add(activityInfo.getPackageName());
//				}
				appInfo.addActivity(activityInfo);
			}

//			appInfo.setActivitiesAreInSamePackage(samePackage);
//			String longestCommonPrefix = StringUtils.longestCommonPrefix(new ArrayList<>(appPackage));
//			if (longestCommonPrefix != null && !longestCommonPrefix.isEmpty()) {
//				appInfo.setAppPackage(longestCommonPrefix);
//			} else {
//				appInfo.setAppPackage(appInfo.getManifestPackage());
//			}
		}
		return appInfo;
	}	
	
	public static File decompileApp(AppInfo appInfo) throws IOException {
		log.info("Decompiling app: " + appInfo.getPath());
		String appName = appInfo.getLabel();
		File outDir = Files.createTempDirectory(appName).toFile();
		ApkDecoder decoder = new ApkDecoder(new File(appInfo.getPath()));
		try {
			FileUtil.delete(outDir);
			decoder.decode(outDir);
			log.info("Decompile '" + appName + "' successfully: "+outDir.getAbsolutePath());
			return outDir;
		} catch (AndrolibException | DirectoryException | IOException e) {
			log.error("Decompile '" + appName + "' failed: "+e.getMessage(), e);
			throw new RuntimeException("Error decompiling: "+appInfo.getPath(), e);
		}
	}

	private static ActivityInfo readActivity(BinaryManifestActivity binaryManifestActivity, String manifestPackage) {
		AXmlNode activityNode = binaryManifestActivity.getAXmlNode();
		String activityName = getAttributeAsString(NAME, activityNode);
		if(activityName.startsWith(".")) {
			activityName = manifestPackage + activityName;
		}
		log.debug("Reading activity: "+activityName);
		boolean isMain = false;
		for (AXmlNode child : activityNode.getChildren()) {
			if (INTENT_FILTER.equals(child.getTag())) {
				for (AXmlNode grandchild : child.getChildren()) {
					if (ACTION.equals(grandchild.getTag())) {
						String actionName = getAttributeAsString(NAME, grandchild);
						if (MAIN.equals(actionName)) {
							isMain = true;
						}
					}
				}
			}
		}
		return new ActivityInfo(activityName, isMain);
	}

	private static String getAttributeAsString(String attributeName, AXmlNode node) {
		AXmlAttribute<?> attribute = node.getAttribute(attributeName);
		if (attribute == null) {
			return null;
		}
		Object value = attribute.getValue();
		if (value == null) {
			return null;
		}
		return value.toString();
	}
	
}
