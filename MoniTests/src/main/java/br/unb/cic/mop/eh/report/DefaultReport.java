package br.unb.cic.mop.eh.report;

import java.io.File;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Set;

import br.unb.cic.mop.eh.ErrorDescription;

/**
 * This report exports the list of errors to a CSV file. This is a short
 * representation of the erros. And a given type of error appears only once in a
 * given method.
 */
@Deprecated
public class DefaultReport implements IErrorReport {
    static final String HEADER = "spec,error,class,className,method";

    DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    @Override
    public void exportErrors(Set<ErrorDescription> errors) throws Exception {
        File outDir = new File("output");

        if (!outDir.exists()) {
            outDir.mkdir();
        }

        File csvOutputFile = new File(generateFileName());

        try (PrintWriter pw = new PrintWriter(csvOutputFile)) {
            pw.println(HEADER);
            errors.stream()
                    .map(ErrorDescription::getErrorSummary)
                    .map(s -> String.format("%s,%s,%s,%s,%s", s.getSpec(), s.getError(), s.getClassQualifiedName(), s.getClassQualifiedName(), s.getMethodName()))
                    .forEach(pw::println);
        }
    }

    private String generateFileName() {
        LocalDateTime now = LocalDateTime.now();

        return "output"+File.separator+"report-" + dtf.format(now) + ".csv";
    }
}
