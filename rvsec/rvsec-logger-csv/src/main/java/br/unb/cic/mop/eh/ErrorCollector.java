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

    /**
     * Escapes a newline as the two characters {@code \n} — the same rule the logcat collector
     * applies — and only then quotes the value if the CSV needs it.
     *
     * <p>
     * The order matters and used to be the other way round: the newline replacement wrote into a
     * local while the quoting branch re-read the original, so a value carrying both a comma and a
     * newline was quoted with its newline intact and broke the row in two. Both collectors now
     * agree on the newline rule, so a message escaped for one file reads the same in the other.
     */
    private String escape(String data) {
        String escapedData = data.replaceAll("\\R", "\\\\n");
        if (escapedData.contains(",") || escapedData.contains("\"")
                || escapedData.contains("'")) {
            escapedData = "\"" + escapedData.replace("\"", "\"\"") + "\"";
        }
        return escapedData;
    }
}
