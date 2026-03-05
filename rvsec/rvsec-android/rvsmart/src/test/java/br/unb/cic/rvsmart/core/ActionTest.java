package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Action signature format and factory methods.
 */
class ActionTest {

    @Test
    void testClickSignature() {
        Action action = new Action(Action.Type.CLICK, 540, 960, "algorithm", "Button");
        assertEquals("click@540,960", action.signature());
    }

    @Test
    void testSetTextSignature() {
        Action action = new Action(Action.Type.SET_TEXT, 100, 200, "hello", "algorithm", "EditText");
        assertEquals("set_text:hello@100,200", action.signature());
    }

    @Test
    void testBackSignature() {
        Action back = Action.back("algorithm");
        assertEquals("back@0,0", back.signature());
        assertEquals(Action.Type.BACK, back.getType());
    }

    @Test
    void testRestartSignature() {
        Action restart = Action.restart("algorithm");
        assertEquals("restart@0,0", restart.signature());
        assertEquals(Action.Type.RESTART, restart.getType());
    }

    @Test
    void testSourceIsMetadataOnly() {
        Action alg = new Action(Action.Type.CLICK, 10, 20, "algorithm", "Button");
        Action llm = new Action(Action.Type.CLICK, 10, 20, "llm", "Button");
        // Same signature regardless of source (INV-RSM-08)
        assertEquals(alg.signature(), llm.signature());
    }

    @Test
    void testLongClickSignature() {
        Action action = new Action(Action.Type.LONG_CLICK, 300, 400, "algorithm", "ImageView");
        assertEquals("long_click@300,400", action.signature());
    }

    @Test
    void testScrollSignature() {
        Action action = new Action(Action.Type.SCROLL, 540, 800, "algorithm", "RecyclerView");
        assertEquals("scroll@540,800", action.signature());
    }
}
