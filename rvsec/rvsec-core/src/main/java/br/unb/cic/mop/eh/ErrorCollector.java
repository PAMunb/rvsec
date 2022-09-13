package br.unb.cic.mop.eh;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import br.unb.cic.mop.eh.logger.ILogger;
import br.unb.cic.mop.eh.logger.LoggerLocator;

/**
 * A singleton class for collecting errors while running the monitoring process.
 */
public class ErrorCollector {
    private static ErrorCollector instance;

    private Set<ErrorDescription> errors;
    private Set<ILogger> loggers;

    public static ErrorCollector instance() {
        if (instance == null) {
            instance = new ErrorCollector();
        }
        return instance;
    }

    private ErrorCollector() {
        errors = new HashSet<>();
        loggers = LoggerLocator.findLoggers();
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
            loggers.forEach(l -> l.logError(err));
        }
    }

    public Set<ErrorDescription> getErrors() {
        return Collections.unmodifiableSet(errors);
    }

//    public void addLogger(ILogger logger) {
//        loggers.put(logger.getClass(), logger);
//    }
//
//    public void removeLogger(Class<? extends ILogger> clazz) {
//        loggers.remove(clazz);
//    }
//
//    public Set<Class<? extends ILogger>> listLoggers() {
//        return Collections.unmodifiableSet(loggers.keySet());
//    }

//    @Deprecated
//    public void printErrors() throws Exception {
//        ILogger logger = new StdOutLogger();
//
//        for (ErrorDescription error : errors) {
//            logger.logError(error);
//        }
//    }
}
