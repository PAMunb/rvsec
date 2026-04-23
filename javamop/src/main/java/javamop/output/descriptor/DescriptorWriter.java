// Copyright (c) 2026 RVSec. Released under the same license as JavaMOP.
package javamop.output.descriptor;

import javamop.JavaMOPMain;
import javamop.output.combinedaspect.CombinedAspect;
import javamop.output.combinedaspect.event.EventManager;
import javamop.output.combinedaspect.event.advice.AdviceAndPointCut;
import javamop.output.combinedaspect.event.advice.AdviceBody;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.MOPParameter;
import javamop.parser.ast.mopspec.MOPParameters;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Converts the AspectJ output model (CombinedAspect / EventManager / AdviceAndPointCut) into a
 * tree of {@link Map} / {@link List} nodes suitable for Jackson serialization.
 *
 * <p>The goal is to emit the <em>same information</em> that {@link AdviceAndPointCut#toString()}
 * writes into the {@code .aj} file, but in a structured form that the prototipo-dexlib2 weaver
 * can consume without parsing textual AspectJ. Pointcut expressions are kept as strings (via
 * {@code PointCut.toString()}) because the rv-monitor-generated expressions are regular and the
 * weaver operates on simple pattern-matching; richer AST serialization can be added later.
 *
 * <p>This class intentionally mirrors the loop inside
 * {@link AdviceAndPointCut#toString()} (monitorCalls emission) so that the descriptor stays in
 * sync with the {@code .aj} file. If that method changes, update here too.
 */
public final class DescriptorWriter {

    private DescriptorWriter() {}

    /**
     * Build the descriptor tree for an entire aspect (one {@code .aj} file).
     *
     * @param aspectName      Aspect name (e.g. {@code "MultiSpec_1"}). The generated aspect will be
     *                        {@code aspectName + "MonitorAspect"}.
     * @param combinedAspect  The fully-built {@link CombinedAspect} produced by the JavaMOP
     *                        pipeline (after {@code new CombinedAspect(...)}).
     */
    public static Map<String, Object> buildAspect(String aspectName, CombinedAspect combinedAspect) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("aspectName", combinedAspect.getAspectName());
        root.put("fileName", combinedAspect.getFileName());
        root.put("shortName", aspectName);
        root.put("commonPointcut",
                "!within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) "
                        + "&& !adviceexecution() && BaseAspect.notwithin()");
        root.put("baseAspectExclusions", defaultBaseAspectExclusions());

        EventManager eventManager = combinedAspect.getEventManager();
        List<AdviceAndPointCut> advices = eventManager.getAdvices();
        List<Map<String, Object>> adviceTrees = new ArrayList<>(advices.size());
        for (AdviceAndPointCut advice : advices) {
            adviceTrees.add(buildAdvice(advice));
        }
        root.put("advices", adviceTrees);

        return root;
    }

    /**
     * Build the descriptor tree for a single {@link AdviceAndPointCut}.
     *
     * <p>Shape:
     * <pre>
     * {
     *   "name"       : "CipherSpec_g1",
     *   "parameters" : [ { "type": "...", "name": "..." }, ... ],
     *   "position"   : "after" | "before" | "around",
     *   "returning"  : [ { "type": "...", "name": "..." }, ... ] | null,
     *   "throwing"   : [ { "type": "...", "name": "..." }, ... ] | null,
     *   "expression" : "(call(...) && target(t)) && MOP_CommonPointCut()",   // textual
     *   "monitorCalls": [ { "target": "...MonitorAspect", "method": "...",
     *                      "args": [ "arg1", "arg2", ... ] } , ... ]
     * }
     * </pre>
     */
    public static Map<String, Object> buildAdvice(AdviceAndPointCut advice) {
        Map<String, Object> tree = new LinkedHashMap<>();
        tree.put("name", advice.getPointCutName());
        tree.put("specName", advice.getSpecName());
        tree.put("parameters", parametersToList(advice.getParameters()));
        tree.put("position", advice.pos);
        tree.put("isAround", advice.isAround);
        if (advice.isAround) {
            tree.put("returnType", advice.retType);
        }
        tree.put("returning", nullIfEmpty(parametersToList(advice.retVal)));
        tree.put("throwing", nullIfEmpty(parametersToList(advice.throwVal)));

        // The raw pointcut expression as AspectJ source (e.g.
        // "call(public static Cipher Cipher.getInstance(String)) && args(transformation)").
        String expr = advice.getPointCut() == null ? "" : advice.getPointCut().toString();
        tree.put("expression", expr);

        tree.put("monitorCalls", buildMonitorCalls(advice));
        return tree;
    }

    /**
     * Mirror of the loop in {@link AdviceAndPointCut#toString()} that emits
     * {@code Monitor.XxxEvent(args);} calls.
     */
    private static List<Map<String, Object>> buildMonitorCalls(AdviceAndPointCut advice) {
        List<Map<String, Object>> calls = new ArrayList<>();
        for (EventDefinition event : advice.getEvents()) {
            AdviceBody body = advice.getAdvices().get(event);
            if (body == null) {
                continue;
            }
            String method = EventManager.EventMethodHelper.methodName(
                    body.getMOPSpec(), event, advice.getFileName());
            List<String> args = new ArrayList<>();
            // Original parameters (including threadVar).
            String original = event.getParameters().parameterString();
            appendCsv(args, original);
            // Returning parameters.
            if (event.getRetVal() != null && event.getRetVal().size() > 0) {
                appendCsv(args, event.getRetVal().parameterString());
            }
            // Throwing parameters.
            if (event.getThrowVal() != null && event.getThrowVal().size() > 0) {
                appendCsv(args, event.getThrowVal().parameterString());
            }
            // __STATICSIG (if requested).
            if (event.has__STATICSIG()) {
                args.add("thisJoinPoint.getStaticPart().getSignature()");
            }

            Map<String, Object> call = new LinkedHashMap<>();
            call.put("method", method);
            call.put("specName", body.getMOPSpec().getName());
            call.put("eventId", event.getId());
            call.put("uniqueId", event.getUniqueId());
            call.put("args", args);
            call.put("countCond", nullIfBlank(event.getCountCond()));
            calls.add(call);
        }
        return calls;
    }

    private static void appendCsv(List<String> into, String csv) {
        if (csv == null || csv.isEmpty()) {
            return;
        }
        for (String part : csv.split(",")) {
            String trimmed = part.trim();
            if (!trimmed.isEmpty()) {
                into.add(trimmed);
            }
        }
    }

    private static List<Map<String, Object>> parametersToList(MOPParameters parameters) {
        if (parameters == null || parameters.size() == 0) {
            return new ArrayList<>();
        }
        List<Map<String, Object>> list = new ArrayList<>(parameters.size());
        for (MOPParameter p : parameters) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("type", p.getType() == null ? null : p.getType().toString());
            entry.put("name", p.getName());
            list.add(entry);
        }
        return list;
    }

    private static <T> List<T> nullIfEmpty(List<T> list) {
        return (list == null || list.isEmpty()) ? null : list;
    }

    private static String nullIfBlank(String s) {
        return (s == null || s.trim().isEmpty()) ? null : s;
    }

    /**
     * The standard {@code BaseAspect.notwithin()} exclusions emitted when
     * {@code --baseaspect} is not overridden. Mirrors {@code AspectJCode.initBaseAspect()}.
     */
    private static List<String> defaultBaseAspectExclusions() {
        List<String> list = new ArrayList<>();
        list.add("sun..*");
        list.add("java..*");
        list.add("javax..*");
        list.add("com.sun..*");
        list.add("org.dacapo.harness..*");
        list.add("org.apache.commons..*");
        list.add("org.apache.geronimo..*");
        list.add("net.sf.cglib..*");
        list.add("mop..*");
        list.add("javamoprt..*");
        list.add("rvmonitorrt..*");
        list.add("com.runtimeverification..*");
        return list;
    }
}
