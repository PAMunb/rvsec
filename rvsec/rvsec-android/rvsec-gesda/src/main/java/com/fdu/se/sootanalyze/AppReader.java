package com.fdu.se.sootanalyze;

import java.io.File;
import java.io.IOException;
import java.nio.file.FileSystems;
import java.util.HashSet;
import java.util.Set;

import org.xmlpull.v1.XmlPullParserException;

import com.fdu.se.sootanalyze.model.xml.ActivityInfo;
import com.fdu.se.sootanalyze.model.xml.AppInfo;

import brut.androlib.ApkDecoder;
import brut.androlib.exceptions.AndrolibException;
import brut.directory.DirectoryException;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;
import soot.jimple.infoflow.android.manifest.binary.BinaryManifestActivity;
import soot.jimple.infoflow.android.resources.ARSCFileParser;

public class AppReader {
	private static final String PACKAGE = "package";
	private static final String NAME = "name";

	static final String INTENT_FILTER = "intent-filter";
	static final String ACTION = "action";
	static final String MAIN = "android.intent.action.MAIN";

	public static AppInfo readApk(String apkPath) throws IOException, XmlPullParserException {
		final File targetAPK = new File(apkPath);

		AppInfo appInfo = new AppInfo(apkPath);
		boolean samePackage = false;

		ARSCFileParser resources = new ARSCFileParser();
		resources.parse(targetAPK.getAbsolutePath());

		try (ProcessManifest processManifest = new ProcessManifest(targetAPK, resources)) {
			Set<String> appPackage = new HashSet<>();
			AXmlNode manifest = processManifest.getManifest();

			String manifestPackage = getAttributeAsString(PACKAGE, manifest);
			appInfo.setPackage(manifestPackage);
			appInfo.setAppName(processManifest.getApplication().getName());

			for (BinaryManifestActivity binaryManifestActivity : processManifest.getActivities()) {
				ActivityInfo activityInfo = readActivity(binaryManifestActivity);
				if (!activityInfo.getPackageName().startsWith(appInfo.getPackage())) {
					samePackage = false;
					appPackage.add(activityInfo.getPackageName());
				}
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
	
	public static File decompileApp(AppInfo appInfo) {
		System.out.println("Decompiling app: " + appInfo.getPath());
		String appName = appInfo.getLabel();
		File outDir = new File("apks" + FileSystems.getDefault().getSeparator() + appName);
		// Config config = Config.getInstance();
		// config.setDecodeAssets(Config.DECODE_ASSETS_FULL);
		// config.setDecodeResources(Config.DECODE_RESOURCES_FULL);
		// config.setDecodeSources(Config.DECODE_SOURCES_NONE); // does not decompile
		// sources
		// config.setForceDecodeManifest(Config.FORCE_DECODE_MANIFEST_FULL);
		// ApkDecoder decoder = new ApkDecoder(config, new File(apkPath));

		ApkDecoder decoder = new ApkDecoder(new File(appInfo.getPath()));
		try {
			decoder.decode(outDir);
			System.out.println("decompile " + appName + " successfully");
			return outDir;
		} catch (AndrolibException | DirectoryException | IOException e) {
			// TODO Auto-generated catch block
			System.out.println("decompile " + appName + " failed");
			throw new RuntimeException("Error decompiling: "+appInfo.getPath(), e);
		}
	}

	private static ActivityInfo readActivity(BinaryManifestActivity binaryManifestActivity) {
		AXmlNode act = binaryManifestActivity.getAXmlNode();
		String activityName = getAttributeAsString(NAME, act);
		boolean isMain = false;
		for (AXmlNode child : act.getChildren()) {
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
