package br.unb.cic.rvsec.taint.tmp;

import java.io.File;
import java.nio.file.Path;

import com.googlecode.dex2jar.tools.Dex2jarCmd;

public class TesteDex2jar {

	private void execute(String apk) {
		// TODO Auto-generated method stub
		String jarPath = dex2jar(Path.of(apk));
		System.out.println(jarPath);
	}

	private String dex2jar(Path path) {
	    String apkPath = path.toAbsolutePath().toString();
	    String outDir = "./tmp/";
	    int start = apkPath.lastIndexOf(File.separator);
	    int end = apkPath.lastIndexOf(".apk");
	    String outputFile = outDir + apkPath.substring(start + 1, end) + ".jar";
	    Dex2jarCmd.main("-f", apkPath, "-o", outputFile);
	    return outputFile;
	  }

	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";
		TesteDex2jar t = new TesteDex2jar();
		t.execute(apk);
	}

}
