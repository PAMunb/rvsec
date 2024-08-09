package br.unb.cic.rvsec.taint;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.model.ActivityInfo;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;
import soot.jimple.infoflow.android.manifest.binary.BinaryManifestActivity;
import soot.jimple.infoflow.android.resources.ARSCFileParser;

public class ApkReader {
	private static final String PACKAGE = "package";
	private static final String NAME = "name";

	static final String INTENT_FILTER = "intent-filter";
	static final String ACTION = "action";
	static final String MAIN = "android.intent.action.MAIN";

	public ApkInfo readApk(String apkPath) throws IOException, XmlPullParserException {
		final File targetAPK = new File(apkPath);

		ApkInfo apkInfo = new ApkInfo(apkPath);
		boolean samePackage = false;

		ARSCFileParser resources = new ARSCFileParser();
		resources.parse(targetAPK.getAbsolutePath());

		try (ProcessManifest processManifest = new ProcessManifest(targetAPK, resources)) {
			Set<String> appPackage = new HashSet<>();
			AXmlNode manifest = processManifest.getManifest();

			String manifestPackage = getAttributeAsString(PACKAGE, manifest);
			apkInfo.setManifestPackage(manifestPackage);
			apkInfo.setAppName(processManifest.getApplication().getName());

			for (BinaryManifestActivity binaryManifestActivity : processManifest.getActivities()) {
				ActivityInfo activityInfo = readActivity(binaryManifestActivity);
				if (!activityInfo.getPackageName().startsWith(apkInfo.getManifestPackage())) {
					samePackage = false;
					appPackage.add(activityInfo.getPackageName());
				}
				apkInfo.addActivity(activityInfo);
			}

			apkInfo.setActivitiesAreInSamePackage(samePackage);
			String longestCommonPrefix = StringUtils.longestCommonPrefix(new ArrayList<>(appPackage));
			if (longestCommonPrefix != null && !longestCommonPrefix.isEmpty()) {
				apkInfo.setAppPackage(longestCommonPrefix);
			} else {
				apkInfo.setAppPackage(apkInfo.getManifestPackage());
			}
		}
		return apkInfo;
	}

	private ActivityInfo readActivity(BinaryManifestActivity binaryManifestActivity) {
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

	private String getAttributeAsString(String attributeName, AXmlNode node) {
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
