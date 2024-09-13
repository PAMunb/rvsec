package com.fdu.se.sootanalyze.model.out;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

import com.google.gson.Gson;

public class OutputWriter {

	public static void write(ApkInfoOut info, File out) throws IOException {
		Gson gson = new Gson();
//		Gson gson = new GsonBuilder()
//                .addSerializationExclusionStrategy()
//                .create();
		
		String json = gson.toJson(info);
		
		try (FileWriter writer = new FileWriter(out)) {
		    writer.write(json);
		} 
	}
	
}
