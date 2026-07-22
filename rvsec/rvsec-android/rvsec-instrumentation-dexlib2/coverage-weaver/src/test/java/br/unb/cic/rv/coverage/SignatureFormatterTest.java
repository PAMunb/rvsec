package br.unb.cic.rv.coverage;

import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SignatureFormatterTest {

    @Test
    void primitiveDescriptorsToFqn() {
        assertEquals("void",    SignatureFormatter.toFqn("V"));
        assertEquals("boolean", SignatureFormatter.toFqn("Z"));
        assertEquals("int",     SignatureFormatter.toFqn("I"));
        assertEquals("long",    SignatureFormatter.toFqn("J"));
        assertEquals("byte",    SignatureFormatter.toFqn("B"));
        assertEquals("char",    SignatureFormatter.toFqn("C"));
    }

    @Test
    void referenceDescriptorToFqn() {
        assertEquals("java.lang.String", SignatureFormatter.toFqn("Ljava/lang/String;"));
        assertEquals("java.util.List",   SignatureFormatter.toFqn("Ljava/util/List;"));
    }

    @Test
    void arrayDescriptorToFqn() {
        assertEquals("int[]",             SignatureFormatter.toFqn("[I"));
        assertEquals("int[][]",           SignatureFormatter.toFqn("[[I"));
        assertEquals("java.lang.String[]", SignatureFormatter.toFqn("[Ljava/lang/String;"));
    }

    // ------------------------------------------------------------------
    // format(ClassDef, Method) — the full <FQN: Ret name(params)> string.
    // The toFqn helper was covered above, but the public formatter (param
    // loop, comma joining, empty-parens, the surrounding <...> and ": ")
    // was untested. This exact byte shape is what the Layer-5 RVSEC-COV
    // recall check compares against the ajc Coverage.aj output, so any drift
    // in spacing/commas/angle-brackets silently breaks ajc↔dexlib2 parity.
    // ------------------------------------------------------------------

    private static final String OWNER = "Lcom/example/Foo;";

    private static ClassDef owner() {
        return new ImmutableClassDef(OWNER, 0, "Ljava/lang/Object;",
                null, null, null, List.of(), List.of());
    }

    private static Method method(String name, String returnType, String... paramTypes) {
        List<ImmutableMethodParameter> params = new java.util.ArrayList<>();
        for (String t : paramTypes) params.add(new ImmutableMethodParameter(t, null, null));
        return new ImmutableMethod(OWNER, name, params, returnType,
                0, null, null, null);
    }

    @Test
    void formatMultiArgSignatureShape() {
        assertEquals("<com.example.Foo: java.lang.String bar(int,java.lang.String)>",
                SignatureFormatter.format(owner(),
                        method("bar", "Ljava/lang/String;", "I", "Ljava/lang/String;")));
    }

    @Test
    void formatVoidZeroArgHasEmptyParens() {
        assertEquals("<com.example.Foo: void run()>",
                SignatureFormatter.format(owner(), method("run", "V")));
    }

    @Test
    void formatArrayAndNestedClassParams() {
        // Array param renders with [] and the nested-class '$' is intentionally
        // kept (only '/' becomes '.'), matching the AspectJ signature template.
        assertEquals("<com.example.Foo: void m(int[],com.example.Outer$Inner)>",
                SignatureFormatter.format(owner(),
                        method("m", "V", "[I", "Lcom/example/Outer$Inner;")));
    }
}
