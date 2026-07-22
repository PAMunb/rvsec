package br.unb.cic.rvsec.apk.util;

import java.util.Arrays;
import java.util.List;

import br.unb.cic.rvsec.apk.model.AppInfo;
import soot.SootClass;
import soot.SootMethod;

public class AndroidUtil {

    public static boolean isAndroidMethod(SootMethod sootMethod){
        String clsSig = sootMethod.getDeclaringClass().getName();
        List<String> androidPrefixPkgNames = Arrays.asList("android.", "com.google.android", "androidx.");
        return androidPrefixPkgNames.stream()
        		.map(clsSig::startsWith)
        		.reduce(false, (res, curr) -> res || curr);
    }
    
    public static boolean isClassInApplicationPackage(SootClass c, AppInfo apkInfo) {
    	return isClassInApplicationPackage(c, apkInfo.getPackage());
//		return isClassInApplicationPackage(c, apkInfo.getManifestPackage()) 
//    	|| isClassInApplicationPackage(c, apkInfo.getAppPackage());
	}
	
	public static boolean isClassInApplicationPackage(SootClass c, String appPackage) {
		return c.getName().startsWith(appPackage) 
				&& !c.getName().startsWith(appPackage + ".R")
				&& !c.getName().startsWith(appPackage + ".BuildConfig");
	}
	
	/**
	 * FROM: soot.jimple.infoflow.util.SystemClassHandler
	 * 
	 * Checks whether the given class name belongs to a system package
	 * 
	 * @param className The class name to check
	 * @return True if the given class name belongs to a system package, otherwise
	 *         false
	 */
	public static boolean isClassInSystemPackage(String className) {
		List<String> systemPackages = List.of("android.", "androidx.", "java.", "javax."
				, "sun.", "org.omg.", "org.w3c.dom.", "com.google.", "com.android.");
		return isClassInSystemPackage(className, systemPackages);
//		return className.startsWith("android.") || className.startsWith("java.") || className.startsWith("javax.")
//				|| className.startsWith("sun.") || className.startsWith("org.omg.")
//				|| className.startsWith("org.w3c.dom.") || className.startsWith("com.google.")
//				|| className.startsWith("com.android.");
	}
	
	public static boolean isClassInSystemPackage(String className, List<String> systemPackages) {
		return systemPackages.stream().anyMatch(p -> className.startsWith(p));
	}

}
