package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.RW — the {@code *} (match-any) return-type wildcard in {@code call(...)}, plus a re-grounding of
 * the matcher-group closures (§4.O/§4.X/§4.V/§4.TT/§4.AT/§4.N) on the REAL corpus pointcut forms.
 *
 * <p>The forms asserted here are pulled verbatim (modulo binding-name spellings) from the
 * {@code generic}/{@code generic_new} corpora's {@code MultiSpec_1MonitorAspect.aj}, where every
 * matched call site is spelled {@code call(* Owner+.name*(..)) && target(...) && args(...)} — i.e.
 * with a {@code *} return type. Demand: 240 such sites in {@code generic}, 67 in {@code generic_new},
 * 0 in {@code jca} (DemandCounter {@code CALL_RETURN_WILDCARD}).
 *
 * <p>This is the LOAD-BEARING evidence for the call-pattern matcher groups: prior to the §4.RW fix,
 * {@code matchCall} rejected every {@code call(* ...)} site at the return-type equality gate
 * ({@code toDescriptor("*")} → {@code Ljava/lang/*;}, never equal to a real return descriptor), so the
 * sibling constructs were exercised only by concrete-return substitutes ({@code call(boolean ...)}) —
 * tests that passed by AVOIDING the form the pipeline actually produces. With the gate now skipped for
 * a {@code *} return (symmetric to the existing {@code *} handling for args positions and method-name
 * globs), the real forms match end-to-end.
 */
class CallReturnWildcardGrammarTest {

    // --- §4.RW: * return wildcard --------------------------------------------------------------

    /** {@code call(* java.util.Collection+.add*(..))} — the real generic-corpus shape — matches a
     *  {@code boolean}-returning {@code add(Object)} and an {@code addAll(Collection)} (the {@code *}
     *  return accepts any descriptor), and rejects a method whose name is not under the {@code add*}
     *  glob. */
    @Test
    void returnWildcardMatchesAnyReturnOnRealCorpusForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.util.Collection+.add*(..))");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "call(* ...) must match add(Object):boolean — the * return accepts any descriptor");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "addAll",
                List.of("Ljava/util/Collection;"), "Z")).isPresent(),
                "call(* Collection+.add*(..)) must match addAll(Collection):boolean");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "remove",
                List.of("Ljava/lang/Object;"), "Z")).isEmpty(),
                "the add* glob must still reject a remove() invoke");
    }

    /** The {@code *} return is independent of the actual return descriptor: an Object-returning and a
     *  void-returning method on the same name both match. */
    @Test
    void returnWildcardIsReturnDescriptorIndependent() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.io.Writer+.write(..))");
        ClassDef writer = cls("Ljava/io/Writer;", "Ljava/lang/Object;", List.of());
        assertTrue(match(pc, ref("Ljava/io/Writer;", "write", List.of("Ljava/lang/String;"), "V"), writer).isPresent(),
                "* return matches a void method");
        assertTrue(match(pc, ref("Ljava/io/Writer;", "write", List.of("I"), "Ljava/lang/Object;"), writer).isPresent(),
                "* return matches an Object-returning method too");
    }

    // --- §4.RW: PipelineDemand for the * return position --------------------------------------

    /** The {@code *} return-type wildcard is the dominant call() shape in the generic corpora and
     *  absent from jca (whose call() sites spell concrete returns). Pins the demand the §4.RW closure
     *  ships against: 240 / 67 / 0 (per-occurrence, compiled .aj snapshot). The prior demand audit had
     *  measured only the {@code T+}-in-return position ({@code call_return_tsubtype} = 0 everywhere) and
     *  never the {@code *}-return position — this assertion closes that gap. */
    @Test
    void returnWildcardPipelineDemand() {
        assertEquals(240, DemandCounter.countCompiledAj(DemandCounter.CALL_RETURN_WILDCARD, Corpus.GENERIC),
                "call(* ...) demand in the generic compiled .aj");
        assertEquals(67, DemandCounter.countCompiledAj(DemandCounter.CALL_RETURN_WILDCARD, Corpus.GENERIC_NEW),
                "call(* ...) demand in the generic_new compiled .aj");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CALL_RETURN_WILDCARD, Corpus.JCA),
                "jca call() sites spell concrete returns — zero * return demand");
    }

    // --- §4.O: T+ owner subtype, real form (with * return) ------------------------------------

    /** {@code call(* java.util.Collection+.addAll(Collection))} matches a {@code TreeSet} receiver — a
     *  {@code Collection} subtype via the dex interface chain. */
    @Test
    void ownerSubtypeOnRealForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.util.Collection+.addAll(Collection))");
        ClassDef treeSet = cls("Ljava/util/TreeSet;", "Ljava/lang/Object;",
                List.of("Ljava/util/Collection;"));
        assertTrue(match(pc, ref("Ljava/util/TreeSet;", "addAll",
                List.of("Ljava/util/Collection;"), "Z"), treeSet).isPresent(),
                "Collection+ owner must match a TreeSet receiver (Collection subtype)");
    }

    // --- §4.X: method-name glob, real form (with * return) ------------------------------------

    /** {@code call(* java.io.Writer+.write*(..))} matches {@code write} / {@code write} variants and
     *  rejects {@code flush}. */
    @Test
    void nameGlobOnRealForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.io.Writer+.write*(..))");
        ClassDef writer = cls("Ljava/io/Writer;", "Ljava/lang/Object;", List.of());
        assertTrue(match(pc, ref("Ljava/io/Writer;", "write", List.of("Ljava/lang/String;"), "V"), writer).isPresent(),
                "write* must match write(String)");
        assertTrue(match(pc, ref("Ljava/io/Writer;", "flush", List.of(), "V"), writer).isEmpty(),
                "write* must reject flush()");
    }

    // --- §4.V: trailing-mixed varargs, real form (with * return + args) -----------------------

    /** {@code call(* java.util.Map+.put(Object, Object)) && args(key, ..)} matches a two-arg put on a
     *  Map receiver — head pinned, trailing accept-any. */
    @Test
    void trailingVarargsOnRealForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.util.Map+.put(Object, Object)) && args(key, ..)");
        assertTrue(match(pc, ref("Ljava/util/Map;", "put",
                List.of("Ljava/lang/Object;", "Ljava/lang/Object;"), "Ljava/lang/Object;")).isPresent(),
                "put(Object, Object) with args(key, ..) must match a two-arg put");
    }

    // --- §4.TT: target(Type), real form (with * return) ---------------------------------------

    /** {@code call(* java.util.Collection+.add*(..)) && target(TreeSet)} matches only when the
     *  receiver is (a subtype of) TreeSet. */
    @Test
    void targetTypeOnRealForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.util.Collection+.add*(..)) && target(TreeSet)");
        ClassDef treeSet = cls("Ljava/util/TreeSet;", "Ljava/lang/Object;",
                List.of("Ljava/util/Collection;"));
        assertTrue(match(pc, ref("Ljava/util/TreeSet;", "add",
                List.of("Ljava/lang/Object;"), "Z"), treeSet).isPresent(),
                "target(TreeSet) must match a TreeSet receiver");
        // A plain Collection receiver is NOT a TreeSet → target(TreeSet) rejects.
        ClassDef collection = cls("Ljava/util/Collection;", "Ljava/lang/Object;", List.of());
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;"), "Z"), collection).isEmpty(),
                "target(TreeSet) must reject a plain Collection receiver");
    }

    // --- §4.AT: args(Type)/args wildcard, real form (with * return) ---------------------------

    /** {@code call(* java.util.Map+.put(Object, Object)) && args(*, enc)} matches: {@code *} accepts
     *  position 0, {@code enc} is a binding name (no filter) at position 1. */
    @Test
    void argsWildcardOnRealForm() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(* java.util.Map+.put(Object, Object)) && args(*, enc)");
        assertTrue(match(pc, ref("Ljava/util/Map;", "put",
                List.of("Ljava/lang/Object;", "Ljava/lang/Object;"), "Ljava/lang/Object;")).isPresent(),
                "args(*, enc) must match a two-arg put");
    }

    // --- §4.N: !target(Type), real composed form (with * return + ||) -------------------------

    /** The full real clause
     *  {@code (call(* Writer+.write*(..)) || call(* Writer+.flush(..))) && target(w)
     *   && !target(CharArrayWriter) && !target(StringWriter)} matches a plain Writer receiver and
     *  excludes a StringWriter receiver. */
    @Test
    void notTargetCompositionOnRealForm() {
        String expr = "(call(* java.io.Writer+.write*(..)) || call(* java.io.Writer+.flush(..)))"
                + " && target(w) && !target(CharArrayWriter) && !target(StringWriter)";
        PointcutExpression pc = PointcutExpressionParser.parse(expr);
        ClassDef writer = cls("Ljava/io/Writer;", "Ljava/lang/Object;", List.of());
        assertTrue(match(pc, ref("Ljava/io/Writer;", "write", List.of("Ljava/lang/String;"), "V"), writer).isPresent(),
                "plain Writer receiver must match the composed !target(...) clause");
        ClassDef stringWriter = cls("Ljava/io/StringWriter;", "Ljava/io/Writer;", List.of());
        assertTrue(match(pc, ref("Ljava/io/StringWriter;", "write", List.of("Ljava/lang/String;"), "V"), stringWriter).isEmpty(),
                "!target(StringWriter) must exclude a StringWriter receiver");
    }

    // --- fixture -------------------------------------------------------------------------------

    private static Optional<Match> match(PointcutExpression pc, MethodReference callee,
                                         ClassDef... extra) {
        Instruction invoke = new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, callee.getParameterTypes().size() + 1, 0, 1, 2, 3, 4, callee);
        Instruction ret = new ImmutableInstruction10x(Opcode.RETURN_VOID);
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                5, List.of(invoke, ret), Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod("LCaller;", "m", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef caller = new ImmutableClassDef("LCaller;", AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, null, List.of(m));
        List<ClassDef> classes = new ArrayList<>();
        classes.add(caller);
        Collections.addAll(classes, extra);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), classes);
        TypeResolver tr = new TypeResolver(List.of(
                "java.util.Collection", "java.util.Map", "java.util.TreeSet", "java.util.TreeMap",
                "java.io.Writer", "java.io.CharArrayWriter", "java.io.StringWriter",
                "java.lang.Object", "java.lang.String"));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        PointcutMatcher pm = new PointcutMatcher(tr, ir);
        Method method = caller.getMethods().iterator().next();
        return pm.match(pc, caller, method, invoke, 0, 2, List.of(invoke, ret));
    }

    private static MethodReference ref(String owner, String name, List<String> params, String ret) {
        return new ImmutableMethodReference(owner, name, params, ret);
    }

    private static ClassDef cls(String desc, String superDesc, List<String> ifaces) {
        return new ImmutableClassDef(desc, AccessFlags.PUBLIC.getValue(), superDesc,
                ifaces, null, null, null, Collections.emptyList());
    }
}
