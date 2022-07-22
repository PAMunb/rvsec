package br.unb.cic.mop.eh.report;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Set;

import br.unb.cic.mop.eh.ErrorDescription;

@Deprecated
public class CsvReport implements IErrorReport {

    public static final String HEADER = "spec,class,className,method,location,error";

    @Override
    public void exportErrors(Set<ErrorDescription> errors) throws Exception {
        File outDir = new File("output");

        if (!outDir.exists()) {
            outDir.mkdir();
        }

        File logger = new File("output/summary.csv");

        boolean generateHeader = !logger.exists();

        try (PrintWriter pw = new PrintWriter(new FileWriter(logger, true))) {
            if (generateHeader) {
                pw.println(HEADER);
            }
            errors.forEach(err -> pw.println(err.getErrorSummary().toString()));
        } catch (Exception e) { }
    }

}
