package com.fdu.se.sootanalyze.model.xml;

import java.io.File;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import com.fdu.se.sootanalyze.utils.StringUtil;

public class AppInfo {
	private String path;
	private String fileName;
	private String appName;
	private String label;

	private String packageName;
//    private String appPackage;
//	  private String manifestPackage;
//    private boolean activitiesAreInSamePackage = true;

	private Set<ActivityInfo> activities = new HashSet<>();
	private ActivityInfo mainActivity;

	public AppInfo(String path) {
		this.path = path;
		this.fileName = new File(path).getName();
		this.label = StringUtil.convertToLabel(path);
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

	public String getPackage() {
		return packageName;
	}

	public void setPackage(String appPackage) {
		this.packageName = appPackage;
	}

	public Set<ActivityInfo> getActivities() {
		return Collections.unmodifiableSet(activities);
	}

	public String getLabel() {
		return label;
	}

	public ActivityInfo getMainActivity() {
		return mainActivity;
	}

	public void addActivity(ActivityInfo activityInfo) {
		activities.add(activityInfo);
		if (activityInfo.isMain()) {
			this.mainActivity = activityInfo;
		}
	}

	@Override
	public String toString() {
		return String.format("AppInfo [path=%s, fileName=%s, appName=%s, label=%s, packageName=%s, mainActivity=%s, activities=%s]", path, fileName, appName, label, packageName, mainActivity, activities);
	}

}
