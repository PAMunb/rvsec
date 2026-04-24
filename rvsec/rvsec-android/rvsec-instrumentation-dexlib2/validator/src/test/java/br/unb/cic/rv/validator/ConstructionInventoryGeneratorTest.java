package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class ConstructionInventoryGeneratorTest {

    @Test
    void scanPicksUpCallAndExecutionUsages(@TempDir Path tmp) throws Exception {
        Path mop = tmp.resolve("DummySpec.mop");
        Files.writeString(mop, """
                DummySpec() {
                    event next before: call(* Iterator.next()) {}
                    event coverage before: execution(* *.*(..)) {}
                }
                """);
        var inv = ConstructionInventoryGenerator.scan(tmp);
        assertTrue(inv.hasAny("call"), "call usage missed");
        assertTrue(inv.hasAny("execution"), "execution usage missed");
        assertTrue(inv.hasAny("before"), "before usage missed");
        assertFalse(inv.hasAny("around"), "around must be absent from the fixture");
    }

    @Test
    void writeEmitsCountsForBothSupportedAndOutOfScope(@TempDir Path tmp) throws Exception {
        Path mop = tmp.resolve("Sample.mop");
        Files.writeString(mop, "event x after: call(* A.b()) returning(Object r) {}\n");
        var inv = ConstructionInventoryGenerator.scan(tmp);
        Path out = tmp.resolve("docs/INVENTORY.md");
        ConstructionInventoryGenerator.write(inv, out);
        String body = Files.readString(out);
        assertTrue(body.contains("## Supported constructs"));
        assertTrue(body.contains("## Out-of-scope constructs"));
        assertTrue(body.contains("`around`"),
                "out-of-scope constructs must be listed even when unused");
    }
}
