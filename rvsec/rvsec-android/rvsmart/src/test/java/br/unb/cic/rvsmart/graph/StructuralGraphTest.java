package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StructuralGraph: structHash → Set<contentHash> clustering.
 */
class StructuralGraphTest {

    private StructuralGraph graph;

    @BeforeEach
    void setUp() {
        graph = new StructuralGraph();
    }

    @Test
    void testRegisterAndGetCluster() {
        graph.register("struct1", "content1");
        graph.register("struct1", "content2");

        Set<String> cluster = graph.getCluster("struct1");
        assertEquals(2, cluster.size());
        assertTrue(cluster.contains("content1"));
        assertTrue(cluster.contains("content2"));
    }

    @Test
    void testGetClusterReturnsEmptyForUnknownStruct() {
        Set<String> cluster = graph.getCluster("nonexistent");
        assertNotNull(cluster);
        assertTrue(cluster.isEmpty());
    }

    @Test
    void testGetStructHashReturnsCorrectMapping() {
        graph.register("struct1", "content1");
        graph.register("struct2", "content2");

        assertEquals("struct1", graph.getStructHash("content1"));
        assertEquals("struct2", graph.getStructHash("content2"));
    }

    @Test
    void testGetStructHashReturnsNullForUnregistered() {
        assertNull(graph.getStructHash("never-registered"));
    }

    @Test
    void testSizeCountsUniqueClusters() {
        assertEquals(0, graph.size());
        graph.register("struct1", "content1");
        graph.register("struct1", "content2"); // same cluster
        assertEquals(1, graph.size());

        graph.register("struct2", "content3");
        assertEquals(2, graph.size());
    }
}
