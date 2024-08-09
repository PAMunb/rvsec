package br.unb.cic.rvsec.taint.util;

import java.util.Arrays;
import java.util.List;

import br.unb.cic.rvsec.taint.model.ApkInfo;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.infoflow.android.manifest.ProcessManifest;

public class AndroidUtil {

	@Deprecated
    public static String getPackageName(String apkPath) {
        String packageName = "";
        try (ProcessManifest manifest = new ProcessManifest(apkPath)) {
            packageName = manifest.getPackageName();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return packageName;
    }

    public static boolean isAndroidMethod(SootMethod sootMethod){
        String clsSig = sootMethod.getDeclaringClass().getName();
        List<String> androidPrefixPkgNames = Arrays.asList("android.", "com.google.android", "androidx.");
        return androidPrefixPkgNames.stream().map(clsSig::startsWith).reduce(false, (res, curr) -> res || curr);
    }
    
    public static boolean isAppClass(SootClass c, ApkInfo apkInfo) {
		return checkPackage(c, apkInfo.getManifestPackage()) || checkPackage(c, apkInfo.getAppPackage());
	}
	
	private static boolean checkPackage(SootClass c, String appPackage) {
		return c.getName().startsWith(appPackage) 
				&& !c.getName().startsWith(appPackage + ".R")
				&& !c.getName().startsWith(appPackage + ".BuildConfig");
	}

//    public static InfoflowAndroidConfiguration getFlowDroidConfig(String apkPath, String androidJar) {
//        return getFlowDroidConfig(apkPath, androidJar, InfoflowConfiguration.CallgraphAlgorithm.SPARK);
//    }
//
//    public static InfoflowAndroidConfiguration getFlowDroidConfig(String apkPath, String androidJar, InfoflowConfiguration.CallgraphAlgorithm cgAlgorithm) {
//        final InfoflowAndroidConfiguration config = new InfoflowAndroidConfiguration();
//        config.getAnalysisFileConfig().setTargetAPKFile(apkPath);
//        config.getAnalysisFileConfig().setAndroidPlatformDir(androidJar);
//        config.setCodeEliminationMode(InfoflowConfiguration.CodeEliminationMode.NoCodeElimination);
//        config.setEnableReflection(true);
//        config.setCallgraphAlgorithm(cgAlgorithm);
//        return config;
//    }
}
