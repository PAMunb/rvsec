package com.fdu.se.sootanalyze.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fdu.se.sootanalyze.model.out.ApkInfoOut;
import com.fdu.se.sootanalyze.model.out.WidgetInfoOut;
import com.fdu.se.sootanalyze.model.out.WindowInfoOut;
import com.google.gson.Gson;

public class OutputWriter {
	private static final Logger log = LoggerFactory.getLogger(OutputWriter.class);

	public static void write(ApkInfoOut info, File out) throws IOException {
		log.info("Writing results file: "+out.getAbsolutePath());
		Gson gson = new Gson();
//		Gson gson = new GsonBuilder()
//                .addSerializationExclusionStrategy()
//                .create();

		emptyListsToNull(info);

		String json = gson.toJson(info);

		try (FileWriter writer = new FileWriter(out)) {
			writer.write(json);
		}
	}

	private static void emptyListsToNull(ApkInfoOut info) {
		if (info.getWindows() != null) {
			if (info.getWindows().isEmpty()) {
				info.setWindows(null);
			}else {
				for (WindowInfoOut windowInfoOut : info.getWindows()) {
					if (windowInfoOut.getWidgets() != null) {
						if (windowInfoOut.getWidgets().isEmpty()) {
							windowInfoOut.setWidgets(null);
						}else {
							for (WidgetInfoOut widgetInfoOut : windowInfoOut.getWidgets()) {
								if(isEmpty(widgetInfoOut.getEntries())) {
									widgetInfoOut.setEntries(null);
								}
								if(isEmpty(widgetInfoOut.getItems())) {
									widgetInfoOut.setItems(null);
								}
								if(isEmpty(widgetInfoOut.getListeners())) {
									widgetInfoOut.setListeners(null);
								}
							}
						}
					}
				}
			}
		}
	}

	private static boolean isEmpty(List<?> list) {
		return list != null && list.isEmpty();
	}

}
