package br.unb.cic.rvsec.reach.gesda;

import java.io.File;
import java.io.FileReader;

import com.google.gson.Gson;

public class GesdaReader {

	public static ApkInfoOut read(String gesdaFile) {
		return read(new File(gesdaFile));
	}
	
	public static ApkInfoOut read(File in) {
		ApkInfoOut data = null;
		if (in != null && in.exists()) {
			try (FileReader reader = new FileReader(in)) {
				Gson gson = new Gson();
				data = gson.fromJson(reader, ApkInfoOut.class);
			} catch (Exception e) {
				e.printStackTrace();
				throw new RuntimeException("Error reading gesda json: " + e.getMessage(), e);
			}
		}
		return data;
	}

	public static void main(String[] args) {
		String json = "/home/pedro/tmp/rvsec-gesda.json";
		ApkInfoOut info = GesdaReader.read(new File(json));
		System.out.println("INFO: " + info);
	}

}
