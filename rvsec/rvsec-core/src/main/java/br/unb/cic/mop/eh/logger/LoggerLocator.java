package br.unb.cic.mop.eh.logger;

import java.lang.reflect.Constructor;
import java.util.HashSet;
import java.util.Set;

import org.reflections.Reflections;
import org.reflections.scanners.SubTypesScanner;

public class LoggerLocator {

//    public static Set<ILogger> findLoggers() {
//
//        Set<ILogger> loggers = new HashSet<>();
//
//        try {
//            Class clazz = Class.forName("br.unb.cic.mop.eh.logger.CsvLogger");
//            Constructor constructor = clazz.getConstructor();
//            ILogger instance = (ILogger) constructor.newInstance();
//            loggers.add(instance);
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//
//        return loggers;
//
//    }

    public static Set<ILogger> findLoggers() {
        Reflections reflections = new Reflections("", new SubTypesScanner(false));
        Set<Class<? extends ILogger>> subTypesOfLogger = reflections.getSubTypesOf(ILogger.class);
        
        //subTypesOfLogger.forEach(System.out::println);

        Set<ILogger> loggers = new HashSet<>();

        try {
            for (Class<? extends ILogger> clazz : subTypesOfLogger) {
                
                System.err.println("************************* "+clazz.getCanonicalName());
                
                Constructor<? extends ILogger> constructor = clazz.getConstructor();
                ILogger instance = constructor.newInstance();
                loggers.add(instance);
            }
        } catch (Exception e) {   }

        return loggers;

    }

//    public static void main(String[] args) {
//        System.out.println(System.getProperty("java.class.path"));
//        try {
//            new LoggerLocator().findLoggers();
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }

}
