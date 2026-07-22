package br.unb.cic.rv.descriptor;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DescriptorReaderNegativeTest {

    @Test
    void unknownPropertyFailsFast() {
        // The "monster" field is not in the POJO; FAIL_ON_UNKNOWN_PROPERTIES MUST trip.
        String json = "{"
                + "\"aspectName\":\"X\","
                + "\"monster\":\"should not be here\""
                + "}";

        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(json));
        assertTrue(e.getMessage().contains("monster"),
                "error should cite the unknown field name; got: " + e.getMessage());
    }

    @Test
    void malformedJsonReportsParseError() {
        String json = "{ not valid json";
        assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(json));
    }

    @Test
    void typeMismatchCitesJsonPath() {
        // advices should be an array, here it's an int.
        String json = "{"
                + "\"aspectName\":\"X\","
                + "\"advices\":42"
                + "}";

        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(json));
        assertTrue(e.getMessage().contains("advices"),
                "error should cite the offending JSON path 'advices'; got: " + e.getMessage());
    }

    @Test
    void emptyJsonDeserializesToDefaults() {
        // An empty object is valid — fields default to empty lists / nulls.
        AspectDescriptor desc = DescriptorReader.read("{}");
        assertEquals(0, desc.getImports().size());
        assertEquals(0, desc.getAdvices().size());
        assertEquals(0, desc.getBaseAspectExclusions().size());
    }
}
