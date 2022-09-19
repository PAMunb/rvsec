package br.unb.cic.mop.eh;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

public class ErrorCollector {
    private static ErrorCollector instance;

    static final String HEADER = "spec,class,className,method,location,error,expecting";
    static final String OUT_DIR = "output";

    private PrintWriter pw;
    private Set<ErrorDescription> errors;

    private ErrorCollector() {
        errors = new HashSet<>();
        init();
    }

    public static ErrorCollector instance() {
        if (instance == null) {
            instance = new ErrorCollector();
        }
        return instance;
    }

    public void addError(ErrorType type, String spec, String location) {
        addError(new ErrorDescription(type, spec, location));
    }

    public void addError(ErrorType type, String spec, String location, String expecting) {
        addError(new ErrorDescription(type, spec, location, expecting));
    }

    public void addError(ErrorDescription err) {
        if (pw != null && errors.add(err)) {
            pw.println(err.getErrorSummary() + "," + escape(err.getExpecting()).trim());
        }
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }

    public void reset() {
        errors = new HashSet<>();
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
        if (data.contains(",") || data.contains("\"")
                || data.contains("'")) {
            data = data.replace("\"", "\"\"");
            escapedData = "\"" + data + "\"";
        }
        return escapedData;
    }
}
