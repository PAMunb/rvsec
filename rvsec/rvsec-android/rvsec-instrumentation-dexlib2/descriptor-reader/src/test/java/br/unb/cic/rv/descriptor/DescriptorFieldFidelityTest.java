package br.unb.cic.rv.descriptor;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Locks the descriptor-reader's core contract: every field JavaMOP emits is surfaced
 * verbatim through the POJO getters.
 *
 * <p>The bundled {@code MultiSpec_1MonitorAspect.json} fixture (used by
 * {@code DescriptorReaderTest}) is a JCA <em>after-returning</em> merge, so it never
 * exercises several descriptor shapes on the read side: an {@code around} advice
 * ({@code isAround:true}), a declared {@code returnType}, an {@code after() throwing}
 * clause, named advice {@code parameters}, or the per-call {@code specName}/{@code eventId}/
 * {@code uniqueId}/{@code @count} metadata (the fixture-reading test only asserts
 * {@code method}). Those getters were therefore dark. This test feeds one hand-built
 * descriptor that populates all of them and asserts each getter returns the deserialized
 * value — proving the reader does not silently drop any documented field during weaving.
 *
 * <p>Concrete payload: one {@code around} advice {@code adv1} of spec {@code CipherSpec}
 * declaring {@code void} return, one {@code int count} parameter, a
 * {@code throwing java.lang.Exception ex} clause, and one monitor call
 * {@code M.event} carrying {@code eventId=e1}, {@code uniqueId=u1}, {@code args=[count]},
 * {@code countCond=@count(2)}.
 */
class DescriptorFieldFidelityTest {

    private static final String FULL_ADVICE = "{"
            + "\"aspectName\":\"TestAspect\","
            + "\"advices\":[{"
            + "  \"name\":\"adv1\","
            + "  \"specName\":\"CipherSpec\","
            + "  \"position\":\"around\","
            + "  \"isAround\":true,"
            + "  \"returnType\":\"void\","
            + "  \"parameters\":[{\"type\":\"int\",\"name\":\"count\"}],"
            + "  \"throwing\":[{\"type\":\"java.lang.Exception\",\"name\":\"ex\"}],"
            + "  \"monitorCalls\":[{"
            + "    \"method\":\"M.event\","
            + "    \"specName\":\"CipherSpec\","
            + "    \"eventId\":\"e1\","
            + "    \"uniqueId\":\"u1\","
            + "    \"args\":[\"count\"],"
            + "    \"countCond\":\"@count(2)\""
            + "  }]"
            + "}]"
            + "}";

    @Test
    void everyAdviceFieldIsSurfaced() {
        AspectDescriptor desc = DescriptorReader.read(FULL_ADVICE);
        assertEquals(1, desc.getAdvices().size());
        AdviceDescriptor adv = desc.getAdvices().get(0);

        assertEquals("adv1", adv.getName());
        assertEquals("CipherSpec", adv.getSpecName());
        assertEquals("around", adv.getPosition());
        assertTrue(adv.isAround(), "isAround:true must deserialize to isAround()==true");
        assertEquals("void", adv.getReturnType());

        // Named parameters (the JCA fixture's params carry a type but no name, so setName
        // and the parameters getter were dark).
        List<ParameterDescriptor> params = adv.getParameters();
        assertEquals(1, params.size());
        assertEquals("int", params.get(0).getType());
        assertEquals("count", params.get(0).getName());

        // after() throwing clause.
        List<ParameterDescriptor> throwing = adv.getThrowing();
        assertNotNull(throwing, "throwing clause must be non-null when present in JSON");
        assertEquals(1, throwing.size());
        assertEquals("java.lang.Exception", throwing.get(0).getType());
        assertEquals("ex", throwing.get(0).getName());
    }

    @Test
    void everyMonitorCallFieldIsSurfaced() {
        AspectDescriptor desc = DescriptorReader.read(FULL_ADVICE);
        MonitorCallDescriptor call = desc.getAdvices().get(0).getMonitorCalls().get(0);

        assertEquals("M.event", call.getMethod());
        assertEquals("CipherSpec", call.getSpecName());
        assertEquals("e1", call.getEventId());
        assertEquals("u1", call.getUniqueId());
        assertEquals(List.of("count"), call.getArgs());
        assertEquals("@count(2)", call.getCountCond());
    }

    /**
     * The two-arg {@link ParameterDescriptor} constructor and {@code toString} are used
     * when the weaver builds diagnostics for a parameter (never by Jackson, which uses
     * the no-arg constructor plus setters). {@code toString} renders {@code "type name"};
     * the weaver relies on that exact shape in log lines, so lock it with concrete values.
     */
    @Test
    void parameterDescriptorValueSemantics() {
        ParameterDescriptor p = new ParameterDescriptor("byte[]", "input");
        assertEquals("byte[]", p.getType());
        assertEquals("input", p.getName());
        assertEquals("byte[] input", p.toString());
    }
}
