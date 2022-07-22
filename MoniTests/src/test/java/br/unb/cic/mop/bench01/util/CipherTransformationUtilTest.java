package br.unb.cic.mop.bench01.util;

import org.junit.Test;
import static org.junit.Assert.*;

import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*;

public class CipherTransformationUtilTest {

    @Test
    public void testSimpleTransformation() {
        assertEquals("AES", alg("AES"));
    }

    @Test
    public void testCompleteTransformation() {
        String transformation = "AES/PCBC/PKCS5Padding";
        assertEquals("AES", alg(transformation));
        assertEquals("PCBC", mode(transformation));
        assertEquals("PKCS5Padding", pad(transformation));
    }

    @Test
    public void testEmptyPaddingTransformation() {
        String transformation = "AES/PCBC";
        assertEquals("AES", alg(transformation));
        assertEquals("PCBC", mode(transformation));
        assertEquals("", pad(transformation));
    }

    @Test
    public void testValidTransformations() {
        assertTrue(isValid("AES/CBC/PKCS5Padding"));
        assertTrue(isValid("AES/CBC/ISO10126Padding"));
        assertTrue(isValid("AES/PCBC/PKCS5Padding"));
        assertTrue(isValid("AES/PCBC/ISO10126Padding"));

        assertTrue(isValid("AES/GCM/NoPadding"));
        assertTrue(isValid("AES/CTR/NoPadding"));
        assertTrue(isValid("AES/CTS/NoPadding"));
        assertTrue(isValid("AES/CFB/NoPadding"));
        assertTrue(isValid("AES/OFB/NoPadding"));

        assertTrue(isValid("AES/GCM"));
        assertTrue(isValid("AES/CTR"));
        assertTrue(isValid("AES/CTS"));
        assertTrue(isValid("AES/CFB"));
        assertTrue(isValid("AES/OFB"));
    }

    @Test
    public void testInValidTransformations() {
        assertTrue(!isValid("AES"));
        assertTrue(!isValid("AES/CBC"));
        assertTrue(!isValid("AES/PCBC"));
        assertTrue(!isValid("AES/CBC/NoPadding"));
        assertTrue(!isValid("AES/PCBC/NoPadding"));

        assertTrue(!isValid("AES/GCM/PKCS5Padding"));
    }

}
