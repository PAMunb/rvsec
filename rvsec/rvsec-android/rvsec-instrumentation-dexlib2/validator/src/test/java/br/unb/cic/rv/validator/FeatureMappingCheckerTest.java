package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class FeatureMappingCheckerTest {

    @Test
    void passesWhenEveryInventoryConstructIsMappedOrLimited(@TempDir Path tmp) throws Exception {
        Path inv = tmp.resolve("INVENTORY.md");
        Files.writeString(inv, "`call` `execution` `around`\n");
        Path map = tmp.resolve("MAPPING.md");
        Files.writeString(map, "| `call` | ... | `execution` | ... |\n");
        Path lim = tmp.resolve("LIMITATIONS.md");
        Files.writeString(lim, "| `around` | not supported |\n");

        Report r = FeatureMappingChecker.check(inv, map, lim);
        assertTrue(r.passed, "mapping closure with inventory ⊆ mapping ∪ limitations");
        assertTrue(r.message.contains("every inventory"));
    }

    @Test
    void failsWhenInventoryConstructIsNeitherMappedNorLimited(@TempDir Path tmp) throws Exception {
        Path inv = tmp.resolve("INVENTORY.md");
        Files.writeString(inv, "`call` `execution` `around` `handler`\n");
        Path map = tmp.resolve("MAPPING.md");
        Files.writeString(map, "`call` `execution`\n");
        Path lim = tmp.resolve("LIMITATIONS.md");
        Files.writeString(lim, "`around`\n");
        // handler appears nowhere — INV-INS-17 violation.
        Report r = FeatureMappingChecker.check(inv, map, lim);
        assertFalse(r.passed);
        assertTrue(r.message.contains("handler"),
                "the violating construct must be named in the message");
    }
}
