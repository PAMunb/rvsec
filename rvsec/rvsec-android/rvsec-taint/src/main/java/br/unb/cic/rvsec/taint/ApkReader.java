package br.unb.cic.rvsec.taint;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.taint.model.ActivityInfo;
import br.unb.cic.rvsec.taint.model.ApkInfo;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;
import soot.jimple.infoflow.android.manifest.binary.BinaryManifestActivity;
import soot.jimple.infoflow.android.resources.ARSCFileParser;

public class ApkReader {
	static final String INTENT_FILTER = "intent-filter";
	static final String ACTION = "action";
	static final String MAIN = "android.intent.action.MAIN";

	public ApkInfo readApk(String apkPath) throws IOException, XmlPullParserException {
		final File targetAPK = new File(apkPath);

		ApkInfo apkInfo = new ApkInfo(apkPath);
		boolean samePackage = false;

		// Parse the resource file
		ARSCFileParser resources = new ARSCFileParser();
		resources.parse(targetAPK.getAbsolutePath());

		// To look for callbacks, we need to start somewhere. We use the Android
		// lifecycle methods for this purpose.
		try (ProcessManifest processManifest = new ProcessManifest(targetAPK, resources)) {
			Set<String> appPackage = new HashSet<>();
			AXmlNode manifest = processManifest.getManifest();

			String manifestPackage = manifest.getAttribute("package").getValue().toString();
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
			if(longestCommonPrefix != null && !"".equals(longestCommonPrefix)) {
				apkInfo.setAppPackage(longestCommonPrefix);
			}else {
				apkInfo.setAppPackage(apkInfo.getManifestPackage());
			}
		}
		return apkInfo;
	}

	private ActivityInfo readActivity(BinaryManifestActivity binaryManifestActivity) {
		AXmlNode act = binaryManifestActivity.getAXmlNode();
		String actName = act.getAttribute("name").getValue().toString();
		boolean isMain = false;
		for (AXmlNode child : act.getChildren()) {
			if (INTENT_FILTER.equals(child.getTag())) {
				for (AXmlNode grandchild : child.getChildren()) {
					if (ACTION.equals(grandchild.getTag())) {
						String actionName = grandchild.getAttribute("name").getValue().toString();
						if (MAIN.equals(actionName)) {
							isMain = true;
						}
					}
				}
			}
		}
		return new ActivityInfo(actName, isMain);
	}
}
