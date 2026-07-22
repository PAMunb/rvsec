package br.unb.cic.rv.cli;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.VersionMap;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * gh73: the dexlib2 instrumenter must preserve each input DEX's format version
 * on output. Reading with {@code Opcodes.getDefault()} (== forApi(20) → dex035
 * in smali 3.0.9) downgraded every output DEX to 035; Kotlin/Compose interface
 * static/default methods are legal only in dex >= 037, so a downgraded 037+ app
 * crashed at runtime with {@code IncompatibleClassChangeError}. These tests pin
 * the read+write round-trip: a dex038 input stays dex038, a dex035 input stays
 * dex035.
 */
class DexVersionPreservationTest {

    /** Parse the DEX format version from the 8-byte magic "dex\n0XY\0". */
    private static int magicVersion(byte[] dex) {
        return (dex[4] - '0') * 100 + (dex[5] - '0') * 10 + (dex[6] - '0');
    }

    /** Build an empty (class-less) DEX at the given format version. */
    private static byte[] emptyDexAtVersion(int version, Path dir) throws Exception {
        DexFile empty = new ImmutableDexFile(
                Opcodes.forDexVersion(version), Collections.emptySet());
        Path p = dir.resolve("in" + version + ".dex");
        DexPool.writeTo(p.toString(), empty);
        byte[] bytes = Files.readAllBytes(p);
        assertEquals(version, magicVersion(bytes),
                "fixture builder must produce a dex" + version + " header");
        return bytes;
    }

    /** Read bytes with BatchRunner's version-preserving opcodes, then re-write. */
    private static int roundTripVersion(byte[] input, Path dir) throws Exception {
        Opcodes opcodes = BatchRunner.opcodesForDex(input, "classes.dex");
        DexBackedDexFile read = new DexBackedDexFile(opcodes, input);
        Path out = dir.resolve("out.dex");
        DexPool.writeTo(out.toString(), read);
        return magicVersion(Files.readAllBytes(out));
    }

    @Test
    void dex038InputRoundTripsToDex038(@TempDir Path tmp) throws Exception {
        byte[] in = emptyDexAtVersion(38, tmp);
        // opcodesForDex must resolve to the dex038 opcodes, not getDefault().
        Opcodes op = BatchRunner.opcodesForDex(in, "classes.dex");
        assertEquals(38, VersionMap.mapApiToDexVersion(op.api),
                "opcodesForDex must preserve the dex038 container version");
        assertEquals(38, roundTripVersion(in, tmp),
                "a dex038 input must stay dex038 after read + DexPool.writeTo");
    }

    @Test
    void dex035InputStaysDex035(@TempDir Path tmp) throws Exception {
        byte[] in = emptyDexAtVersion(35, tmp);
        assertEquals(35, roundTripVersion(in, tmp),
                "a dex035 input must not be spuriously upgraded");
    }
}
