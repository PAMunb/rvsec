package br.unb.cic.rvsec.reach.writer;

import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Set;

public class CsvWriter implements Writer {
    private static final Logger log = LoggerFactory.getLogger(CsvWriter.class);

    @Override
    public void write(Set<RvsecClass> result, File out) {
        log.info("Saving results in: "+out.getAbsolutePath());
        try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
            pw.println("className,isActivity,isMainActivity,methodName,reachable,reachesMop,directlyReachesMop");
            for (RvsecClass clazz : result) {
                for (RvsecMethod method : clazz.getMethods()) {
                    pw.println(String.format("%s,%b,%b,%s,%b,%b,%b",
                            clazz.getClassName(),
                            clazz.isActivity(),
                            clazz.isMainActivity(),
                            method.getMethodName(),
                            method.isReachable(),
                            method.isReachesMop(),
                            method.isDirectlyReachesMop()));
                }
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

}
