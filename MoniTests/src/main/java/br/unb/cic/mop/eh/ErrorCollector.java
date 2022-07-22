package br.unb.cic.mop.eh;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import br.unb.cic.mop.eh.logger.CsvLogger;
import br.unb.cic.mop.eh.logger.ILogger;
import br.unb.cic.mop.eh.logger.StdOutLogger;

/**
 * A singleton class for collecting errors while running the monitoring process.
 */
public class ErrorCollector {
    private static ErrorCollector instance;

    private Set<ErrorDescription> errors;

    private Map<Class<? extends ILogger>, ILogger> loggers;

    public static ErrorCollector instance() {
        if (instance == null) {
            instance = new ErrorCollector();
        }
        return instance;
    }

    private ErrorCollector() {
        errors = new HashSet<>();

        loggers = new HashMap<>();
        addLogger(new CsvLogger());
//        addLogger(new CsvSummaryLogger());
//        addLogger(new StdOutLogger());

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
            loggers.values().forEach(l -> l.logError(err));
        }
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }

    public void addLogger(ILogger logger) {
        loggers.put(logger.getClass(), logger);
    }

    public void removeLogger(Class<? extends ILogger> clazz) {
        loggers.remove(clazz);
    }

    public Set<Class<? extends ILogger>> listLoggers() {
        return Collections.unmodifiableSet(loggers.keySet());
    }

    @Deprecated
    public void printErrors() throws Exception {
        ILogger logger = new StdOutLogger();

        for (ErrorDescription error : errors) {
            logger.logError(error);
        }
    }
}
