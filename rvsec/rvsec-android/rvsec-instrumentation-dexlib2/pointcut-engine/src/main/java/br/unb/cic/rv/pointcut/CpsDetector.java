package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.iface.Annotation;
import com.android.tools.smali.dexlib2.iface.AnnotationElement;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.value.ArrayEncodedValue;
import com.android.tools.smali.dexlib2.iface.value.EncodedValue;
import com.android.tools.smali.dexlib2.iface.value.StringEncodedValue;

/**
 * Recognizes Kotlin coroutine state-machine classes so that {@link PointcutMatcher}
 * can lower pointcuts targeting user-facing suspend-fun signatures into matches
 * against the generated {@code invokeSuspend(Object, Throwable)} body
 * (INV-INS-61).
 *
 * <p>Detection heuristics, in order:
 * <ol>
 *   <li>Superclass is {@code kotlin/coroutines/jvm/internal/BaseContinuationImpl}
 *       or a descendant we recognize by name
 *       ({@code ContinuationImpl}, {@code SuspendLambda},
 *       {@code RestrictedSuspendLambda}, {@code RestrictedContinuationImpl}).</li>
 *   <li>Class name matches the compiler-generated suffix
 *       {@code Outer$name$N} where {@code N} is a digit — the shape produced by
 *       kotlinc for inline suspend lambdas.</li>
 *   <li>Class carries a {@code @DebugMetadata} annotation (Kotlin compiler
 *       attaches this to synthetic state machines; its {@code c} element holds
 *       the source suspend class FQN).</li>
 * </ol>
 *
 * <p>When a class matches, {@link #enclosingSuspendFun(Method)} returns the
 * suspend-fun name parsed from {@code @DebugMetadata.m} (or {@code null} when
 * unavailable — in that case the matcher relies on naming-based recovery).
 */
public final class CpsDetector {

    private static final String CONT_IMPL = "Lkotlin/coroutines/jvm/internal/ContinuationImpl;";
    private static final String BASE_CONT = "Lkotlin/coroutines/jvm/internal/BaseContinuationImpl;";
    private static final String SUSPEND_LAMBDA = "Lkotlin/coroutines/jvm/internal/SuspendLambda;";
    private static final String RESTRICTED_SL =
            "Lkotlin/coroutines/jvm/internal/RestrictedSuspendLambda;";
    private static final String RESTRICTED_CI =
            "Lkotlin/coroutines/jvm/internal/RestrictedContinuationImpl;";

    private static final String DEBUG_METADATA = "Lkotlin/coroutines/jvm/internal/DebugMetadata;";

    private CpsDetector() {}

    /**
     * @return true when {@code cd} looks like a Kotlin coroutine state machine
     *         and therefore deserves CPS-aware pointcut lowering.
     */
    public static boolean isStateMachine(ClassDef cd) {
        String sup = cd.getSuperclass();
        if (sup == null) return false;
        switch (sup) {
            case CONT_IMPL:
            case BASE_CONT:
            case SUSPEND_LAMBDA:
            case RESTRICTED_SL:
            case RESTRICTED_CI:
                return true;
            default:
                break;
        }
        return hasDebugMetadata(cd) || hasGeneratedSuffix(cd);
    }

    /**
     * @return source suspend-fun name (parsed from {@code @DebugMetadata.m} if
     *         present on the class), or {@code null} when undetectable.
     */
    public static String enclosingSuspendFun(ClassDef cd) {
        for (Annotation ann : cd.getAnnotations()) {
            if (!DEBUG_METADATA.equals(ann.getType())) continue;
            for (AnnotationElement el : ann.getElements()) {
                if (!"m".equals(el.getName())) continue;
                EncodedValue val = el.getValue();
                if (val instanceof StringEncodedValue) {
                    return ((StringEncodedValue) val).getValue();
                }
            }
        }
        return null;
    }

    /**
     * @return the source class FQN reported by {@code @DebugMetadata.c} when
     *         present ({@code null} otherwise).
     */
    public static String debugMetadataOwner(ClassDef cd) {
        for (Annotation ann : cd.getAnnotations()) {
            if (!DEBUG_METADATA.equals(ann.getType())) continue;
            for (AnnotationElement el : ann.getElements()) {
                if (!"c".equals(el.getName())) continue;
                EncodedValue val = el.getValue();
                if (val instanceof StringEncodedValue) {
                    return ((StringEncodedValue) val).getValue();
                }
                if (val instanceof ArrayEncodedValue) {
                    // Older kotlinc emits "c" as an array of strings; take the first.
                    for (EncodedValue e : ((ArrayEncodedValue) val).getValue()) {
                        if (e instanceof StringEncodedValue) {
                            return ((StringEncodedValue) e).getValue();
                        }
                    }
                }
            }
        }
        return null;
    }

    /**
     * @return true when {@code m} is the CPS state-machine entry that we want
     *         to match pointcuts against ({@code invokeSuspend(Object, Throwable)}).
     */
    public static boolean isInvokeSuspend(Method m) {
        if (!"invokeSuspend".equals(m.getName())) return false;
        if (m.getParameterTypes().size() != 1) return false;
        return "Ljava/lang/Object;".equals(m.getParameterTypes().get(0));
    }

    private static boolean hasDebugMetadata(ClassDef cd) {
        for (Annotation ann : cd.getAnnotations()) {
            if (DEBUG_METADATA.equals(ann.getType())) return true;
        }
        return false;
    }

    private static boolean hasGeneratedSuffix(ClassDef cd) {
        String t = cd.getType();
        // "Lcom/example/Foo$bar$1;" / "Lcom/example/Foo$1;" etc.
        int dollar = t.lastIndexOf('$');
        if (dollar < 0) return false;
        String tail = t.substring(dollar + 1, t.length() - 1); // drop leading $ and trailing ;
        if (tail.isEmpty()) return false;
        for (int i = 0; i < tail.length(); i++) {
            if (!Character.isDigit(tail.charAt(i))) return false;
        }
        return true;
    }
}
