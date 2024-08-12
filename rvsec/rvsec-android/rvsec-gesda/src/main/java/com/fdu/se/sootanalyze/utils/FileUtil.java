package com.fdu.se.sootanalyze.utils;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.FileSystems;
import java.util.ArrayList;
import java.util.List;

import brut.androlib.ApkDecoder;
import brut.androlib.exceptions.AndrolibException;
import brut.directory.DirectoryException;

public class FileUtil {
    public static List<String> getApkPaths(String path){
        List<String> apkPaths = new ArrayList<>();
        File apkDir = new File(path);
        File[] files = apkDir.listFiles();
        for(File f:files){
            if(f.isFile() && f.getName().endsWith(".apk")){
                String apkPath = f.getAbsolutePath();
                apkPaths.add(apkPath);
            }
        }
        return apkPaths;
    }

    public static void filePrintln(String fileName, String content){
        try{
            BufferedWriter out=new BufferedWriter(new FileWriter(fileName,true));
            out.write(content);
            out.newLine();
            out.close();
        }catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    public static void decompileApp(String apkPath, String appName) {
		System.out.println("Decompiling app: " + apkPath);
		File outDir = new File("apks" + FileSystems.getDefault().getSeparator() + appName);
		// Config config = Config.getInstance();
		// config.setDecodeAssets(Config.DECODE_ASSETS_FULL);
		// config.setDecodeResources(Config.DECODE_RESOURCES_FULL);
		// config.setDecodeSources(Config.DECODE_SOURCES_NONE); // does not decompile
		// sources
		// config.setForceDecodeManifest(Config.FORCE_DECODE_MANIFEST_FULL);
		// ApkDecoder decoder = new ApkDecoder(config, new File(apkPath));

		ApkDecoder decoder = new ApkDecoder(new File(apkPath));
		try {
			decoder.decode(outDir);
			System.out.println("decompile " + appName + " successfully");
		} catch (AndrolibException | DirectoryException | IOException e) {
			// TODO Auto-generated catch block
			System.out.println("decompile " + appName + " failed");
			e.printStackTrace();
		}
	}

    public static void main(String[] args) {
        List<String> apkPaths = getApkPaths("E:\\E backup\\AndroidTesting\\test app\\APP1");
        for(String apkPath:apkPaths){
            System.out.println(apkPath);
        }
    }
}
