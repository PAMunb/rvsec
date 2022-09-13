package br.unb.cic.mop.eh.logger;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

import br.unb.cic.mop.eh.ErrorDescription;

public class StdOutLogger implements ILogger {

    static final String HEADER = "spec,class,className,method,location,error,expecting";
    static final String OUT_DIR = "output";

    private PrintWriter pw;

    public StdOutLogger() {
        init();
    }

    @Override
    public void logError(ErrorDescription err) {
        if (pw != null) {
            pw.println(err.getErrorSummary() + "," + escape(err.getExpecting()).trim());
        }
    }

    private void init() {
        createOutputDir();
        createOutputFile();
    }

    private void createOutputDir() {
        File outDir = new File(OUT_DIR);

        if (!outDir.exists()) {
            outDir.mkdir();
        }
    }

    private void createOutputFile() {
        File logger = new File(OUT_DIR + "/summary.csv");

        boolean generateHeader = !logger.exists();

        try {
            pw = new PrintWriter(new FileWriter(logger, true), true);

            if (generateHeader) {
                pw.println(HEADER);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private String escape(String data) {
        String escapedData = data.replaceAll("\\R", " ");
        if (data.contains(",") || data.contains("\"") || data.contains("'")) {
            data = data.replace("\"", "\"\"");
            escapedData = "\"" + data + "\"";
        }
        return escapedData;
    }
}
