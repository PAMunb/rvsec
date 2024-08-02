package br.unb.cic.rvsec.taint.tmp;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import br.unb.cic.rvsec.taint.model.ApkInfo;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;
import soot.jimple.infoflow.android.manifest.binary.BinaryManifestActivity;

public class Teste01 {


	public ApkInfo getAppInfo(File apkPath) {
		ApkInfo apkInfo = new ApkInfo(apkPath.getAbsolutePath());
		try (ProcessManifest processManifest = new ProcessManifest(apkPath)) {
			AXmlNode manifest = processManifest.getManifest();
			String pack = manifest.getAttribute("package").getValue().toString();
			System.out.println("package name: " + pack);
//			packageName = pack;
			apkInfo.setAppPackage(pack);
			boolean samePackage = true;
			List<String> actNames = new ArrayList<>();
			for (BinaryManifestActivity binaryManifestActivity : processManifest.getActivities()) {
				AXmlNode act = binaryManifestActivity.getAXmlNode();
				String actName = act.getAttribute("name").getValue().toString();
				System.out.println(actName);
				if(!actName.startsWith(apkInfo.getAppPackage())) {
					samePackage = false;
				}
				System.out.println("activity: "+actName);
				actNames.add(actName);
			}
//            List<AXmlNode> activities = processManifest.getActivities();
//            List<String> actNames = new ArrayList<>();
//            for (AXmlNode act : activities) {
//                String actName = act.getAttribute("name").getValue().toString();
//                System.out.println(actName);
//                actNames.add(actName);
//            }
//			apk.setActivitiesSamePackage(samePackage);
//			appInfo.setActivities(actNames);
		} catch (Exception e) {
			e.printStackTrace();
		}
		return apkInfo;
	}


	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

		Teste01 t = new Teste01();

		ApkInfo appInfo = t.getAppInfo(new File(apk));
		System.out.println(appInfo);
	}
}
