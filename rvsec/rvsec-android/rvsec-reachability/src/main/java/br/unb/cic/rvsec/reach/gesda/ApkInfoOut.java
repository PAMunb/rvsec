package br.unb.cic.rvsec.reach.gesda;

import java.util.ArrayList;
import java.util.List;

public class ApkInfoOut {
	private String fileName;
	private String appName;
	private String packageName;
	private List<WindowInfoOut> windows = new ArrayList<>();

	public String getFileName() {
		return fileName;
	}

	public void setFileName(String fileName) {
		this.fileName = fileName;
	}

	public String getAppName() {
		return appName;
	}

	public void setAppName(String appName) {
		this.appName = appName;
	}

	public String getPackageName() {
		return packageName;
	}

	public void setPackageName(String packageName) {
		this.packageName = packageName;
	}

	public List<WindowInfoOut> getWindows() {
		return windows;
	}

	public void setWindows(List<WindowInfoOut> windows) {
		this.windows = windows;
	}

	@Override
	public String toString() {
		return String.format("ApkInfoOut [fileName=%s, appName=%s, packageName=%s, windows=%s]", fileName, appName, packageName, windows);
	}

}
