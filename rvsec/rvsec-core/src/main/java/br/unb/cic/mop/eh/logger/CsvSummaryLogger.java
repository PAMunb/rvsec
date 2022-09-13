package br.unb.cic.mop.eh.logger;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

import br.unb.cic.mop.eh.ErrorDescription;

public class CsvSummaryLogger {// implements ILogger {

//    static final String HEADER = "spec,error,location";
//    static final String OUT_DIR = "output";
//    static final DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
//
//    private PrintWriter pw;
//
//    public CsvSummaryLogger() {
//        init();
//    }
//
//    @Override
//    public void logError(ErrorDescription err) {
//        if (pw != null) {
//            String msg = String.format("%s,%s,%s", err.getSpec(), err.getType(), err.getLocation());
//            pw.println(msg.trim());
//        }
//    }
//
//    private void init() {
//        createOutputDir();
//        createOutputFile();
//    }
//
//    private void createOutputDir() {
//        File outDir = new File(OUT_DIR);
//
//        if (!outDir.exists()) {
//            outDir.mkdir();
//        }
//    }
//
//    private String generateFileName() {
//        LocalDateTime now = LocalDateTime.now();
//
//        return OUT_DIR + File.separator + "report-" + dtf.format(now) + ".csv";
//    }
//
//    private void createOutputFile() {
//        File logger = new File(generateFileName());
//
//        boolean generateHeader = !logger.exists();
//
//        try {
//            pw = new PrintWriter(new FileWriter(logger, true), true);
//
//            if (generateHeader) {
//                pw.println(HEADER);
//            }
//        } catch (IOException e) {
//            e.printStackTrace();
//        }
//    }

}
