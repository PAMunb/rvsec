package presto.android.gui.clients.wtg.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

import com.google.gson.Gson;

import presto.android.Configs;
import presto.android.gui.clients.wtg.model.Result;

/**
 * Serializes a WTG {@link Result} to a JSON file using Gson.
 *
 * <p>Provides three overloads so callers can specify the output destination
 * as a default path (from {@link Configs#pathoutfilename}), a string path,
 * or a {@link File} object. The JSON output is consumed by the RV-Android
 * module {@code rv-static-analysis} to reconstruct the application's
 * Window Transition Graph.</p>
 */
public class Writer {

	/**
	 * Writes the result to the default output path defined in
	 * {@link Configs#pathoutfilename}.
	 *
	 * @param result the WTG analysis result to serialize
	 * @throws IOException if the file cannot be written
	 */
	public static void write(Result result) throws IOException {
		write(result, Configs.pathoutfilename);
	}

	/**
	 * Writes the result to the specified file path.
	 *
	 * @param result the WTG analysis result to serialize
	 * @param out    the file path to write to
	 * @throws IOException if the file cannot be written
	 */
	public static void write(Result result, String out) throws IOException {
		write(result, new File(out));
	}

	/**
	 * Writes the result to the specified file as JSON.
	 *
	 * @param result the WTG analysis result to serialize
	 * @param out    the target file
	 * @throws IOException if the file cannot be written
	 */
	public static void write(Result result, File out) throws IOException {
		Gson gson = new Gson();
		String json = gson.toJson(result);
		try (FileWriter writer = new FileWriter(out)) {
			writer.write(json);
		}
	}
	
}
