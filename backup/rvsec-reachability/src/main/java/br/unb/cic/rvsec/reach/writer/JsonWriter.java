package br.unb.cic.rvsec.reach.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Set;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.Gson;

import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.writer.json.RvsecClassJson;

public class JsonWriter implements Writer {
	private static final Logger log = LoggerFactory.getLogger(JsonWriter.class);

	@Override
	public void write(Set<RvsecClass> result, File out) {
		log.info("Saving results in: " + out.getAbsolutePath());
		Gson gson = new Gson();
		Set<RvsecClassJson> jsonResult = result.stream().map(RvsecClassJson::new).collect(Collectors.toSet());
		String json = gson.toJson(jsonResult);
		try (FileWriter writer = new FileWriter(out)) {
			writer.write(json);
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

}
