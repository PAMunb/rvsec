package com.fdu.se.sootanalyze.model.out;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import com.fdu.se.sootanalyze.model.WindowNode;
import com.fdu.se.sootanalyze.model.xml.AppInfo;

public class ApkInfoOut {
	private String fileName;
	private String appName; // TODO ??
	private String packageName;

	private List<WindowInfoOut> windows = new ArrayList<>();

	public ApkInfoOut(AppInfo appInfo, List<WindowNode> windows) {
		this.fileName = appInfo.getFileName();
		this.appName = appInfo.getAppName();
		this.packageName = appInfo.getPackage();
		this.windows = windows.stream().map(WindowInfoOut::new).collect(Collectors.toList());
	}

	public String getFileName() {
		return fileName;
	}

	public String getAppName() {
		return appName;
	}

	public String getPackageName() {
		return packageName;
	}

	public List<WindowInfoOut> getWindows() {
		return windows;
	}

	@Override
	public String toString() {
		return String.format("ApkInfoOut [fileName=%s, appName=%s, packageName=%s, windows=%s]", fileName, appName, packageName, windows);
	}

}
