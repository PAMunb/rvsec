package presto.android.gui.clients.wtg.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

import com.google.gson.Gson;

import presto.android.Configs;
import presto.android.gui.clients.wtg.model.Result;

public class Writer {

	public static void write(Result result) throws IOException {
		write(result, Configs.pathoutfilename);
	}
	
	public static void write(Result result, String out) throws IOException {
		write(result, new File(out));
	}
	
	public static void write(Result result, File out) throws IOException {
		Gson gson = new Gson();
		String json = gson.toJson(result);
		try (FileWriter writer = new FileWriter(out)) {
			writer.write(json);			
		}
	}
	
}
