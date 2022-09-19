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
            Log.v("RVSEC", err.getErrorSummary() + "," + err.getExpecting().trim());
        }
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }
}
