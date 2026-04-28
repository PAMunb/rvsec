package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class DescriptorAjParityCheckerTest {

    @Test
    void detectsAdviceCountMismatch(@TempDir Path tmp) throws Exception {
        Path aj = tmp.resolve("MultiSpec_1MonitorAspect.aj");
        Files.writeString(aj, """
                package mop;
                public aspect MultiSpec_1MonitorAspect {
                    before() : call(* A.b()) { }
                    after() : call(* A.c()) { }
                }
                """);
        Path json = tmp.resolve("MultiSpec_1MonitorAspect.json");
        Files.writeString(json, """
                {
                  "aspectName": "MultiSpec_1MonitorAspect",
                  "package": "package mop;",
                  "advices": [
                    { "name": "a1", "specName": "S", "position": "before",
                      "isAround": false, "expression": "call(* A.b())" }
                  ]
                }
                """);
        Report r = DescriptorAjParityChecker.check(aj, json);
        assertFalse(r.passed);
        assertTrue(r.message.contains("advice count"));
    }

    @Test
    void passesWhenShapesAgree(@TempDir Path tmp) throws Exception {
        Path aj = tmp.resolve("MultiSpec_1MonitorAspect.aj");
        Files.writeString(aj, """
                package mop;
                public aspect MultiSpec_1MonitorAspect {
                    before() : call(* A.b()) { }
                }
                """);
        Path json = tmp.resolve("MultiSpec_1MonitorAspect.json");
        Files.writeString(json, """
                {
                  "aspectName": "MultiSpec_1MonitorAspect",
                  "package": "package mop;",
                  "advices": [
                    { "name": "a1", "specName": "S", "position": "before",
                      "isAround": false, "expression": "call(* A.b())" }
                  ]
                }
                """);
        Report r = DescriptorAjParityChecker.check(aj, json);
        assertTrue(r.passed, "expected parity; got: " + r.message);
    }

    @Test
    void failsWhenOneFileMissing(@TempDir Path tmp) throws Exception {
        Path aj = tmp.resolve("only.aj");
        Files.writeString(aj, "package mop;");
        Path json = tmp.resolve("never.json");
        Report r = DescriptorAjParityChecker.check(aj, json);
        assertFalse(r.passed);
        assertTrue(r.message.contains("missing"));
    }
}
