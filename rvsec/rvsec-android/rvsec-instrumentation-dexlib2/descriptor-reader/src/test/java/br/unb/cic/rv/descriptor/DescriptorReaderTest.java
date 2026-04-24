package br.unb.cic.rv.descriptor;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DescriptorReaderTest {

    /**
     * Fixture is the JSON produced by running the patched JavaMOP
     * ({@code --emit-descriptor}) over the 22 JCA specs in
     * {@code rvsec/rvsec-mop/src/main/resources/jca/}.
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

        // The merge of the 22 JCA specs in rvsec/rvsec-mop/src/main/resources/jca/ yields
        // 115 advice entries — see docs/20260423_javamop.md §D2.
        List<AdviceDescriptor> advices = desc.getAdvices();
        assertEquals(115, advices.size(),
                "expected 115 advice entries from the JCA merge");

        // Sanity-check: CipherSpec_g1 is an "after returning Cipher" advice we know is present.
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
