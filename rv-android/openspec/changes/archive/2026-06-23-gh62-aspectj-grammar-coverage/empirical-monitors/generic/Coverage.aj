import android.util.Log;
import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Set;
import org.aspectj.lang.Signature;
import org.aspectj.lang.reflect.MethodSignature;

public aspect Coverage {
    private static final class SignatureConstants {
        static final String PREFIX = "<";
        static final String SUFFIX = ">";
        static final String TYPE_SEPARATOR = ": ";
        static final String PARAM_SEPARATOR = ",";
        static final String PARAM_START = "(";
        static final String PARAM_END = ")";
        static final String UNKNOWN = "unknown";
    }

    private final Set<String> messages = new HashSet<>();

    // Define packages that should be excluded from analysis
    pointcut excludedPackages() :
        within(sun..*) ||
        within(java..*) ||
        within(javax..*) ||
        within(jakarta..*) ||
        within(com.sun..*) ||
        within(android..*) ||
        within(androidx..*) ||
        within(kotlin..*) ||
        within(net.sf.cglib..*) ||
        within(org.aspectj..*) ||
        within(com.google.android..*) ||
        within(com.android..*) ||
        within(com.google..*) ||
        within(com.facebook..*) ||
        within(org.apache..*) ||
        within(libcore..*) ||
        within(mop..*) ||
        within(javamop..*) ||
        within(javamoprt..*) ||
        within(rvmonitorrt..*) ||
        within(com.runtimeverification..*) ||
        within(br.unb.cic.mop..*) ||
        within(*..Log) ||
        within(Coverage+);

    // Define which executions should be traced
    pointcut traced() : 
        execution(* *.*(..)) &&
        !excludedPackages();

    before() : traced() {
        Signature signature = thisJoinPointStaticPart.getSignature();
        
        if (signature instanceof MethodSignature) {
            String methodSignature = buildMethodSignature((MethodSignature) signature);
            logMethodSignature(methodSignature);
        }
    }

    private String buildMethodSignature(MethodSignature methodSig) {
        Method method = methodSig.getMethod();
        String className = method.getDeclaringClass().getName();
        String returnType = getReturnTypeString(method.getReturnType());
        String parameters = getParametersString(methodSig);

        return new StringBuilder()
            .append(SignatureConstants.PREFIX)
            .append(className)
            .append(SignatureConstants.TYPE_SEPARATOR)
            .append(returnType)
            .append(" ")
            .append(method.getName())
            .append(parameters)
            .append(SignatureConstants.SUFFIX)
            .toString();
    }

    private String getReturnTypeString(Class<?> type) {
        if (type == null) {
            return SignatureConstants.UNKNOWN;
        }
        
        if (type.isArray()) {
            return buildArrayTypeString(type);
        }
        
        return type.getName();
    }

    private String buildArrayTypeString(Class<?> arrayType) {
        StringBuilder typeBuilder = new StringBuilder();
        Class<?> componentType = arrayType;
        int dimensions = 0;

        while (componentType.isArray()) {
            dimensions++;
            componentType = componentType.getComponentType();
        }

        typeBuilder.append(componentType.getName());
        
        for (int i = 0; i < dimensions; i++) {
            typeBuilder.append("[]");
        }

        return typeBuilder.toString();
    }

    private String getParametersString(MethodSignature methodSig) {
        String longString = methodSig.toLongString();               
        
        int startIndex = longString.indexOf(SignatureConstants.PARAM_START);
        return startIndex != -1 ? removeSpacesAfterCommas(longString.substring(startIndex)) : "()";        
        // return startIndex != -1 ? longString.substring(startIndex) + tmp : "()";
    }

    private String removeSpacesAfterCommas(String input) {
        // Check if the string is empty or null
        if (input == null || input.isEmpty()) {
            return input;
        }
        
        // If it's "()" return as is
        if (input.equals("()")) {
            return input;
        }
        
        // For case "(OneElement)" no change needed
        if (!input.contains(",")) {
            return input;
        }
        
        // Remove spaces after commas
        StringBuilder result = new StringBuilder();
        boolean afterComma = false;
        
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            
            if (afterComma && c == ' ') {
                // Skip the space after the comma
                continue;
            }
            
            result.append(c);
            afterComma = (c == ',');
        }
        
        return result.toString();
    }
    
    private void logMethodSignature(String methodSignature) {
        if (messages.add(methodSignature)) {
            Log.v("RVSEC-COV", methodSignature);
        }
    }
}
