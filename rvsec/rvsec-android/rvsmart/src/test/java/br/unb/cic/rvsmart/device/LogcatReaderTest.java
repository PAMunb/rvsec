package br.unb.cic.rvsmart.device;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for LogcatReader tag parsing logic.
 * Tests extractSignature() which parses logcat lines into method signatures.
 */
class LogcatReaderTest {

    @Test
    void testExtractSignatureFromBriefFormat() {
        // logcat -v brief format: "V/RVSEC-COV( 1234): javax.crypto.Cipher.getInstance"
        String line = "V/RVSEC-COV( 1234): javax.crypto.Cipher.getInstance";
        assertEquals("javax.crypto.Cipher.getInstance", LogcatReader.extractSignature(line));
    }

    @Test
    void testExtractSignatureFromThreadtimeFormat() {
        // logcat -v threadtime: "03-05 11:00:00.123  1234  1234 V RVSEC-COV: javax.crypto.Mac.init"
        String line = "03-05 11:00:00.123  1234  1234 V RVSEC-COV: javax.crypto.Mac.init";
        assertEquals("javax.crypto.Mac.init", LogcatReader.extractSignature(line));
    }

    @Test
    void testExtractSignatureNullLine() {
        assertNull(LogcatReader.extractSignature(null));
    }

    @Test
    void testExtractSignatureNoTag() {
        assertNull(LogcatReader.extractSignature("V/SomeOtherTag: data"));
    }

    @Test
    void testExtractSignatureEmptyAfterColon() {
        assertNull(LogcatReader.extractSignature("V/RVSEC-COV( 1234): "));
    }

    @Test
    void testExtractSignatureWithSpaces() {
        String line = "V/RVSEC-COV( 1234):   java.security.MessageDigest.getInstance  ";
        assertEquals("java.security.MessageDigest.getInstance", LogcatReader.extractSignature(line));
    }

    @Test
    void testDrainEmptyBuffer() {
        LogcatReader reader = new LogcatReader(100);
        assertTrue(reader.drainCoverageTags().isEmpty());
    }

    @Test
    void testBufferedCountInitiallyZero() {
        LogcatReader reader = new LogcatReader(100);
        assertEquals(0, reader.bufferedCount());
    }
}
