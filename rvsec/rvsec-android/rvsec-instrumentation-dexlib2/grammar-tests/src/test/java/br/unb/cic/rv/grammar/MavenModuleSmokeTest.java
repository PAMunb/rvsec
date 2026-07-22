package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Smoke test that keeps the {@code grammar-tests} reactor module green between scaffold commits,
 * before the per-designator grammar tests (§4) and {@code MatrixIntegrityTest} (§6) land.
 */
class MavenModuleSmokeTest {

    @Test
    void moduleBuildsAndTestsRun() {
        assertTrue(true, "grammar-tests module reactor smoke");
    }
}
