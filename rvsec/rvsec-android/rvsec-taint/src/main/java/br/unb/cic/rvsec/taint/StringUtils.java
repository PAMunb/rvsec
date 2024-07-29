package br.unb.cic.rvsec.taint;

import java.util.List;

public class StringUtils {

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

}
