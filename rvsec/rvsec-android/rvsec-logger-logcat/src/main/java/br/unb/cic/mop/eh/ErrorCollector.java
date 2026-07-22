package br.unb.cic.mop.eh;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import android.util.Log;

public class ErrorCollector {
    private static ErrorCollector instance;
    private Set<ErrorDescription> errors;

    private ErrorCollector() {
        errors = new HashSet<>();
    }

    public static ErrorCollector instance() {
        if (instance == null) {
            instance = new ErrorCollector();
        }
        return instance;
    }

    public void reset() {
        errors = new HashSet<>();
    }

    public void addError(ErrorType type, String spec, String location) {
        addError(new ErrorDescription(type, spec, location));
    }

    public void addError(ErrorType type, String spec, String location, String expecting) {
        addError(new ErrorDescription(type, spec, location, expecting));
    }

    public void addError(ErrorDescription err) {
        if (errors.add(err)) {
        	String message = err.getErrorSummary() + "," + err.getExpecting().trim();
            //Log.v("RVSEC", escapeSpecialCharacters(message));
        	Log.v("RVSEC", message);
        }
    }
    
    private String escapeSpecialCharacters(String data) {
        String escapedData = data.replaceAll("\\R", " ");
        if (data.contains(",") || data.contains("\"") || data.contains("'")) {
            data = data.replace("\"", "\"\"");
            escapedData = "\"" + data + "\"";
        }
        return escapedData;
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }
}
