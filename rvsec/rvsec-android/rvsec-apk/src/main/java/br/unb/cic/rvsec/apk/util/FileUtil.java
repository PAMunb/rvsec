package br.unb.cic.rvsec.apk.util;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class FileUtil {
	private static Logger log = LoggerFactory.getLogger(FileUtil.class);

	public static void delete(File dir) throws IOException {
		log.debug("Deleting dir: "+dir.getAbsolutePath());
		if(dir.exists()) {
			Files.walk(Path.of(dir.getAbsolutePath()))
		      .sorted(Comparator.reverseOrder())
		      .map(Path::toFile)
		      .forEach(File::delete);
		}
	}
	
}
