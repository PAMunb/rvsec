package com.fdu.se.sootanalyze.utils;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class FileUtil {

	public static List<String> getApkPaths(String path) {
		List<String> apkPaths = new ArrayList<>();
		File apkDir = new File(path);
		File[] files = apkDir.listFiles();
		for (File f : Objects.requireNonNull(files)) {
			if (f.isFile() && f.getName().endsWith(".apk")) {
				String apkPath = f.getAbsolutePath();
				apkPaths.add(apkPath);
			}
		}
		return apkPaths;
	}

	public static void filePrintln(String fileName, String content) {
		try (BufferedWriter out = new BufferedWriter(new FileWriter(fileName, true))) {
			out.write(content);
			out.newLine();
		} catch (IOException e) {
			e.printStackTrace();
		}
	}

}
