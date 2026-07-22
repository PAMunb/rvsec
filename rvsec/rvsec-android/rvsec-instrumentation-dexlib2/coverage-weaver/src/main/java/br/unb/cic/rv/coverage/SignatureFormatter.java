package br.unb.cic.rv.coverage;

import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodParameter;

/**
 * Formats a method reference into the Soot-style signature string that
 * appears in RVSEC-COV logcat events:
 * <pre>
 *   &lt;FQN: ReturnType method(paramType1,paramType2)&gt;
 * </pre>
 *
 * <p>The legacy {@code Coverage.aj} emits exactly this shape via an AspectJ
 * template; the dexlib2 variant reproduces it byte-for-byte so the Layer-5
 * RVSEC-COV recall check comparing ajc output against dexlib2 output lines
 * up without per-apk tweaks.
 */
public final class SignatureFormatter {

    private SignatureFormatter() {}

    /**
     * @return the signature string, e.g.
     *         {@code <com.example.Foo: java.lang.String bar(int,java.lang.String)>}.
     */
    public static String format(ClassDef classDef, Method method) {
        StringBuilder sb = new StringBuilder();
        sb.append('<').append(toFqn(classDef.getType())).append(": ")
                .append(toFqn(method.getReturnType())).append(' ')
                .append(method.getName()).append('(');
        boolean first = true;
        for (MethodParameter p : method.getParameters()) {
            if (!first) sb.append(',');
            sb.append(toFqn(p.getType()));
            first = false;
        }
        sb.append(")>");
        return sb.toString();
    }

    /** Convert a DEX type descriptor to a Java FQN. */
    static String toFqn(CharSequence desc) {
        if (desc == null) return "";
        String s = desc.toString();
        int arrayDepth = 0;
        while (s.startsWith("[")) { arrayDepth++; s = s.substring(1); }
        String base;
        switch (s) {
            case "V": base = "void";    break;
            case "Z": base = "boolean"; break;
            case "B": base = "byte";    break;
            case "S": base = "short";   break;
            case "C": base = "char";    break;
            case "I": base = "int";     break;
            case "J": base = "long";    break;
            case "F": base = "float";   break;
            case "D": base = "double";  break;
            default:
                if (s.startsWith("L") && s.endsWith(";")) {
                    base = s.substring(1, s.length() - 1).replace('/', '.');
                } else {
                    base = s;
                }
        }
        StringBuilder out = new StringBuilder(base);
        for (int i = 0; i < arrayDepth; i++) out.append("[]");
        return out.toString();
    }
}
