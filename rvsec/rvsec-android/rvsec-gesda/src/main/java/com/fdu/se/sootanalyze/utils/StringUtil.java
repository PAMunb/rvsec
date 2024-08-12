package com.fdu.se.sootanalyze.utils;

public class StringUtil {
    public static String convertToAct(String classStr){
    	System.out.println("convertToAct="+classStr);
        int len = classStr.length();
        String str = classStr.substring(8, len - 2);
        return str.replace('/', '.');
    }

    public static String convertToLabel(String apkPath){
    	System.out.println("convertToLabel: "+apkPath);
        String[] nameArray = null;
        if(apkPath.contains("/")){
            nameArray = apkPath.split("/");
        }else{
            nameArray = apkPath.split("\\\\");
        }
        String appFullName = nameArray[nameArray.length - 1];
        int length = appFullName.length();
        return appFullName.substring(0, length - 4);
    }
}
