package br.unb.cic.rvsec.reach.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Collection;
import java.util.Set;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.reach.model.RvsecClass;
import br.unb.cic.rvsec.reach.model.RvsecMethod;

public class CsvWriter implements Writer {
    private static final Logger log = LoggerFactory.getLogger(CsvWriter.class);

    @Override
    public void write(Set<RvsecClass> result, File out) {
        log.info("Saving results in: "+out.getAbsolutePath());
        try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
            pw.println("class,is_activity,is_main_activity,method,params,reachable,reaches_target,directly_reaches_target,signature,target_methods_reached");
            for (RvsecClass clazz : result) {
                for (RvsecMethod method : clazz.getMethods()) {
                	String params = "["+join(method.getMethodParams(), ",")+"]";
                	String targetMethodsReached = "["+join(method.getMopMethodsReached(), ";")+"]";
                    pw.println(String.format("%s,%b,%b,%s,\"%s\",%b,%b,%b,\"%s\",\"%s\"",
                            clazz.getClassName(),
                            clazz.isActivity(),
                            clazz.isMainActivity(),
                            method.getMethodName(),
                            params,
                            method.isReachable(),
                            method.isReachesMop(),
                            method.isDirectlyReachesMop(),
                            method.getMethodSignature(),
                    		targetMethodsReached));
                }
            }
        } catch (IOException e) {
        	log.error("Error writing csv file: "+e.getMessage());
            throw new RuntimeException(e);
        }
    }

    
    private String join(Collection<String> collection, String join) {
    	return collection.stream().collect(Collectors.joining(";"));
    }
}
