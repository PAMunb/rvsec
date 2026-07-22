package br.unb.cic.rv.descriptor;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DescriptorReaderTest {

    /**
     * Fixture is one concrete descriptor produced by running the patched
     * JavaMOP ({@code --emit-descriptor}) over one of the two specification
     * sets in use by this project — specifically the JCA set merged from
     * {@code rvsec/rvsec-mop/src/main/resources/jca/} (22 source specs →
     * 115 advices). The descriptor-reader is set-agnostic; this fixture is
     * the first concrete payload we had from the patched compiler, and the
     * generic-spec fixture exercises identical code paths.
     */
    private static final String FIXTURE = "/MultiSpec_1MonitorAspect.json";

    @Test
    void readsJcaMultiSpecDescriptor() {
        AspectDescriptor desc;
        try (InputStream in = DescriptorReaderTest.class.getResourceAsStream(FIXTURE)) {
            assertNotNull(in, "fixture MultiSpec_1MonitorAspect.json must be on the test classpath");
            desc = DescriptorReader.read(in);
        } catch (Exception e) {
            throw new AssertionError("failed to load fixture", e);
        }

        assertEquals("MultiSpec_1MonitorAspect", desc.getAspectName());
        assertEquals("MultiSpec_1", desc.getFileName());
        assertEquals("MultiSpec_1", desc.getShortName());
        assertEquals("package mop;", desc.getPackageDecl());
        assertNotNull(desc.getCommonPointcut());
        assertFalse(desc.getImports().isEmpty());

        List<String> exclusions = desc.getBaseAspectExclusions();
        assertTrue(exclusions.contains("java..*"), "baseAspectExclusions must include java..*");
        assertTrue(exclusions.contains("mop..*"), "baseAspectExclusions must include mop..*");

        // The JCA merge used as test fixture contains 115 advice entries; any
        // other spec-set fixture would carry its own advice count. See
        // docs/20260423_javamop.md §D2 for provenance.
        List<AdviceDescriptor> advices = desc.getAdvices();
        assertEquals(115, advices.size(),
                "expected 115 advice entries in the bundled test fixture");

        // Sanity-check against a specific advice we know is in the fixture.
        // CipherSpec_g1 happens to come from the JCA set — for a generic-set
        // fixture the probe would target an Iterator/InputStream advice name
        // instead; the check exists to prove the POJO tree is reachable by
        // name and fields are populated, not to assert any spec-set identity.
        AdviceDescriptor cipherG1 = advices.stream()
                .filter(a -> "CipherSpec_g1".equals(a.getName()))
                .findFirst()
                .orElse(null);
        assertNotNull(cipherG1, "CipherSpec_g1 must be present");
        assertEquals("after", cipherG1.getPosition());
        assertFalse(cipherG1.isAround());
        assertNotNull(cipherG1.getReturning(), "CipherSpec_g1 is after-returning, so returning must be non-null");
        assertEquals(1, cipherG1.getReturning().size());
        assertEquals("Cipher", cipherG1.getReturning().get(0).getType());
        assertFalse(cipherG1.getMonitorCalls().isEmpty());
        assertTrue(cipherG1.getExpression().contains("Cipher.getInstance"),
                "CipherSpec_g1 should match Cipher.getInstance calls");
        assertEquals("MultiSpec_1RuntimeMonitor.CipherSpec_g1Event",
                cipherG1.getMonitorCalls().get(0).getMethod());
    }
}
