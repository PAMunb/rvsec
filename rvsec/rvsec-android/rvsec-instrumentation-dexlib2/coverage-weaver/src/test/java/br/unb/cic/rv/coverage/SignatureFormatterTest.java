package br.unb.cic.rv.coverage;

import org.junit.jupiter.api.Test;

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
}
