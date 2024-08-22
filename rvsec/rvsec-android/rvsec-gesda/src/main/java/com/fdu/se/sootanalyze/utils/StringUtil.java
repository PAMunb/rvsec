package com.fdu.se.sootanalyze.utils;

import java.util.List;

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
    
    public static String longestCommonPrefix(List<String> strs) {
        if (strs == null || strs.size() == 0) {
            return "";
        }

        String prefix = strs.get(0);
        for (int i = 1; i < strs.size(); i++) {
            while (!strs.get(i).startsWith(prefix)) {
                prefix = prefix.substring(0, prefix.length() - 1);
                if (prefix.isEmpty()){
                    return "";
                }
            }
        }
        return prefix;
    }
    
    
    public static boolean isHexadecimal(String strNum) {
        if (strNum == null) {
        	System.err.println("null");
            return false;
        }
        try {
            Integer.parseInt(strNum.substring(2), 16);
        } catch (NumberFormatException nfe) {
        	System.err.println("NumberFormatException: "+nfe.getMessage());
            return false;
        }
        return true;
    }
    
}
