package br.unb.cic.rvsec.taint.model;

import java.io.File;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

public class ApkInfo {

	private String path;
	private String fileName;
	@Deprecated
	private String appName;
	private String appPackage;
	private String manifestPackage;

	private boolean activitiesAreInSamePackage = true;

	private Set<ActivityInfo> activityInfos = new HashSet<>();
	private ActivityInfo mainActivity;

	public ApkInfo(String path) {
		this.path = path;
		this.fileName = new File(path).getName();
	}

	public String getPath() {
		return path;
	}

	public String getFileName() {
		return fileName;
	}

	public String getAppName() {
		return appName;
	}

	public void setAppName(String appName) {
		this.appName = appName;
	}

	public String getAppPackage() {
		return appPackage;
	}

	public void setAppPackage(String appPackage) {
		this.appPackage = appPackage;
	}

	public String getManifestPackage() {
		return manifestPackage;
	}

	public void setManifestPackage(String manifestPackage) {
		this.manifestPackage = manifestPackage;
	}

	public boolean isActivitiesAreInSamePackage() {
		return activitiesAreInSamePackage;
	}

	public void setActivitiesAreInSamePackage(boolean activitiesAreInSamePackage) {
		this.activitiesAreInSamePackage = activitiesAreInSamePackage;
	}

	public Set<ActivityInfo> getActivities() {
		return Collections.unmodifiableSet(activityInfos);
	}

	public ActivityInfo getMainActivity() {
		return mainActivity;
	}

	public void addActivity(ActivityInfo activityInfo) {
		activityInfos.add(activityInfo);
		if (activityInfo.isMain()) {
			this.mainActivity = activityInfo;
		}
	}

	@Override
	public String toString() {
		return String.format("Apk [path=%s, fileName=%s, appName=%s, appPackage=%s, manifestPackage=%s, activitiesAreInSamePackage=%s, activities=%s, mainActivity=%s]", path,
				fileName, appName, appPackage, manifestPackage, activitiesAreInSamePackage, activityInfos, mainActivity);
	}

}
