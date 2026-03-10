package br.unb.cic.rvsmart.core;

import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import br.unb.cic.rvsmart.device.AppController;
import br.unb.cic.rvsmart.device.CrashInterceptor;
import br.unb.cic.rvsmart.device.DeviceController;
import br.unb.cic.rvsmart.device.HeapMonitor;
import br.unb.cic.rvsmart.device.InputInjector;
import br.unb.cic.rvsmart.device.LogcatReader;
import br.unb.cic.rvsmart.device.SystemDialogDetector;
import br.unb.cic.rvsmart.device.UiCapture;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;
import br.unb.cic.rvsmart.core.Config.PromptVersion;
import br.unb.cic.rvsmart.strategy.BacktrackStrategy;
import br.unb.cic.rvsmart.strategy.PhaseController;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;
import br.unb.cic.rvsmart.llm.CoordinateNormalizer;
import br.unb.cic.rvsmart.llm.ImageProcessor;
import br.unb.cic.rvsmart.llm.PromptBuilder;
import br.unb.cic.rvsmart.llm.PromptContext;
import br.unb.cic.rvsmart.llm.ScreenshotCapture;
import br.unb.cic.rvsmart.llm.SglangClient;
import br.unb.cic.rvsmart.llm.ToolCallParser;
import br.unb.cic.rvsmart.output.MetricsCollector;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.output.TraceWriter;
import br.unb.cic.rvsmart.recovery.CycleDetector;
import br.unb.cic.rvsmart.recovery.StuckDetector;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.ActionSelector;
import br.unb.cic.rvsmart.strategy.InputValueGenerator;
import br.unb.cic.rvsmart.strategy.PlateauDetector;

import br.unb.cic.rvsmart.strategy.SuccessorTracker;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Main exploration loop. Exits ONLY on timeout (INV-RSM-01).
 *
 * Each iteration: UI capture -> system dialog check -> routing decision ->
 * action selection (LLM or algorithm) -> injection -> multi-attempt retry ->
 * learning -> trace output.
 *
 * LLM path is optional: when routingManager is null (PURE_ALGORITHM mode without
 * LLM components), the loop runs the algorithm path exclusively.
 *
 * Native crash detection uses two complementary mechanisms:
 *   1. CrashInterceptor callback (instant, Java crashes + ANR)
 *   2. Null root fallback (native crashes where the process dies)
 * Both trigger the same recovery: forceStop + startApp + stuckDetector reset.
 */
public class AgentLoop {

    private static final String TAG = "RVSMART";

    // Device display dimensions used for Qwen3-VL coordinate conversion
    private static final int DEVICE_WIDTH = 1080;
    private static final int DEVICE_HEIGHT = 1920;

    // Required dependencies
    private final String packageName;
    private final long deadline;
    private final Config config;
    private final DeviceController devController;
    private final UiCapture uiCapture;
    private final InputInjector inputInjector;
    private final AppController appController;
    private final CrashInterceptor crashInterceptor;
    private final SystemDialogDetector dialogDetector;
    private final LogcatReader logcatReader;
    private final HeapMonitor heapMonitor;
    private final ContentGraph graph;
    private final StaticMap staticMap;
    private final ActionSelector actionSelector;
    private final StuckDetector stuckDetector;
    private final Learner learner;
    private final TraceWriter traceWriter;
    private final MetricsCollector metricsCollector;

    // Optional LLM dependencies — null when running in PURE_ALGORITHM mode
    private final RoutingManager routingManager;
    private final SglangClient sglangClient;
    private final ToolCallParser toolCallParser;
    private final PromptBuilder promptBuilder;
    private final ImageProcessor imageProcessor;
    private final ScreenshotCapture screenshotCapture;

    // Optional scoring enhancements — null when not configured
    private final ConfirmedCoverageScorer confirmedCoverageScorer;

    // Optional transition tracking — null when not configured
    private final SuccessorTracker successorTracker;

    // Optional gh31 components — null when not configured
    private final UICoverageTracker uiCoverageTracker;
    private final PlateauDetector plateauDetector;

    // gh34 dual-hash components — initialized internally from existing fields
    private final StructuralGraph structuralGraph;
    private final NavigationMap navigationMap;
    private final PhaseController phaseController;
    private final BacktrackStrategy backtrackStrategy;

    // Known Android launcher packages for OOA fast-path detection
    private static final String[] LAUNCHER_PACKAGES = {
            "com.android.launcher3",
            "com.google.android.apps.nexuslauncher",
            "com.android.launcher"
    };
    private static final int MAX_CONSECUTIVE_OOA_AFTER_RESTART = 3;

    // BUG-02: Cycle detection for ping-pong recovery
    private final CycleDetector cycleDetector;

    // CAP-6: Periodic restart when exploration has plateaued
    private int iterationsSinceNewState;

    // State
    private int iteration;
    private long startTimeMs;
    private int outOfAppCounter;
    private int consecutiveOoaAfterRestart;
    private int consecutiveSystemDialogs;

    // Tracks visited activities for LLM prompt context
    private final Set<String> visitedActivities = new HashSet<>();

    // Ring buffer of the last 5 executed actions — used to populate V17 recent-actions context
    private final List<Action> recentActionsBuffer = new ArrayList<>(5);

    // Cached post-action screen state, reused as next iteration's initial state
    // Invalidated on crash, out-of-app, or stuck recovery
    private ScreenState cachedScreenState;

    /**
     * Primary constructor: required dependencies only (algorithm-only mode).
     * All LLM-related fields are set to null; the loop never attempts LLM calls.
     */
    public AgentLoop(String packageName, long deadline, Config config,
                     DeviceController devController, UiCapture uiCapture,
                     InputInjector inputInjector, AppController appController,
                     CrashInterceptor crashInterceptor,
                     SystemDialogDetector dialogDetector, LogcatReader logcatReader,
                     HeapMonitor heapMonitor, ContentGraph graph,
                     StaticMap staticMap, ActionSelector actionSelector,
                     StuckDetector stuckDetector, Learner learner,
                     TraceWriter traceWriter, MetricsCollector metricsCollector) {
        this(packageName, deadline, config, devController, uiCapture, inputInjector,
                appController, crashInterceptor, dialogDetector, logcatReader,
                heapMonitor, graph, staticMap, actionSelector, stuckDetector,
                learner, traceWriter, metricsCollector,
                null, null, null, null, null, null, null, null,
                null, null);
    }

    /**
     * Full constructor: all dependencies including optional LLM and scoring components.
     * Pass null for any optional parameter to disable that feature.
     */
    public AgentLoop(String packageName, long deadline, Config config,
                     DeviceController devController, UiCapture uiCapture,
                     InputInjector inputInjector, AppController appController,
                     CrashInterceptor crashInterceptor,
                     SystemDialogDetector dialogDetector, LogcatReader logcatReader,
                     HeapMonitor heapMonitor, ContentGraph graph,
                     StaticMap staticMap, ActionSelector actionSelector,
                     StuckDetector stuckDetector, Learner learner,
                     TraceWriter traceWriter, MetricsCollector metricsCollector,
                     RoutingManager routingManager, SglangClient sglangClient,
                     ToolCallParser toolCallParser, PromptBuilder promptBuilder,
                     ImageProcessor imageProcessor, ScreenshotCapture screenshotCapture,
                     ConfirmedCoverageScorer confirmedCoverageScorer,
                     SuccessorTracker successorTracker,
                     UICoverageTracker uiCoverageTracker,
                     PlateauDetector plateauDetector) {
        this.packageName = packageName;
        this.deadline = deadline;
        this.config = config;
        this.devController = devController;
        this.uiCapture = uiCapture;
        this.inputInjector = inputInjector;
        this.appController = appController;
        this.crashInterceptor = crashInterceptor;
        this.dialogDetector = dialogDetector;
        this.logcatReader = logcatReader;
        this.heapMonitor = heapMonitor;
        this.graph = graph;
        this.staticMap = staticMap;
        this.actionSelector = actionSelector;
        this.stuckDetector = stuckDetector;
        this.learner = learner;
        this.traceWriter = traceWriter;
        this.metricsCollector = metricsCollector;
        this.routingManager = routingManager;
        this.sglangClient = sglangClient;
        this.toolCallParser = toolCallParser;
        this.promptBuilder = promptBuilder;
        this.imageProcessor = imageProcessor;
        this.screenshotCapture = screenshotCapture;
        this.confirmedCoverageScorer = confirmedCoverageScorer;
        this.successorTracker = successorTracker;
        this.uiCoverageTracker = uiCoverageTracker;
        this.plateauDetector = plateauDetector;

        // gh34: initialize dual-hash components internally (not injected — P1 simplicity).
        // PhaseController requires a non-null PlateauDetector; create a fresh one if not provided.
        this.structuralGraph = new StructuralGraph();
        this.navigationMap = new NavigationMap();
        PlateauDetector effectivePlateauDetector = plateauDetector != null
                ? plateauDetector : new PlateauDetector();
        this.phaseController = new PhaseController(graph, uiCoverageTracker, effectivePlateauDetector);
        this.backtrackStrategy = new BacktrackStrategy(navigationMap, structuralGraph);
        this.cycleDetector = new CycleDetector();
    }

    /**
     * Run the exploration loop until timeout.
     * INV-RSM-01: the ONLY exit condition is System.currentTimeMillis() >= deadline.
     */
    public void run() {
        startTimeMs = System.currentTimeMillis();
        iteration = 0;

        while (System.currentTimeMillis() < deadline) {
            try {
                runIteration();
            } catch (Exception e) {
                Log.w(TAG, "Iteration " + iteration + " error: " + e.getMessage());
                // INV-RSM-36: write ERROR trace line instead of silent swallow
                long elapsed = System.currentTimeMillis() - startTimeMs;
                traceWriter.writeLine(iteration, elapsed, "", "", "ERROR", "exception",
                        false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                        -1, -1.0, -1, -1, -1, 0,
                        false, e.getClass().getSimpleName(), e.getMessage());
            }
            iteration++;
        }
    }

    private void runIteration() {
        long iterStart = System.currentTimeMillis();

        // 1. Check CrashInterceptor for Java crashes/ANR detected via callback
        if (crashInterceptor.hasCrash()) {
            CrashInterceptor.CrashInfo info = crashInterceptor.consumeCrash();
            String crashType = (info != null && info.isAnr()) ? "anr" : "java";
            long elapsed = System.currentTimeMillis() - startTimeMs;
            traceWriter.writeLine(iteration, elapsed, "", "", "SKIP", "crash_at_start",
                    false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                    -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                    false, "crash_" + crashType, null);
            handleCrashRecovery(crashType);
            return;
        }

        // 2. Capture UI root
        AccessibilityNodeInfo root = devController.getUiAutomation().getRootInActiveWindow();
        if (root == null) {
            long elapsed = System.currentTimeMillis() - startTimeMs;
            traceWriter.writeLine(iteration, elapsed, "", "", "SKIP", "null_root",
                    false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                    -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                    false, "null_root", null);
            handleNullRoot();
            return;
        }

        // 3. System dialog check (before full capture)
        if (dialogDetector.isSystemDialog(root)) {
            boolean dismissed = dialogDetector.dismiss(root);
            root.recycle();
            consecutiveSystemDialogs++;
            sleep(500); // prevent CPU spinning — without this, spins at 646 it/s
            RvTrack.incrementSystemDialogs();
            metricsCollector.recordSystemDialog();
            long elapsed = System.currentTimeMillis() - startTimeMs;
            traceWriter.writeLine(iteration, elapsed, "", "", "SKIP", "system_dialog",
                    false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                    -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                    false, "system_dialog", null);
            // First escalation: BACK press after 3 failed dismissals
            if (!dismissed && consecutiveSystemDialogs >= 3 && consecutiveSystemDialogs < 6) {
                inputInjector.pressBack();
                sleep(500);
            } else if (!dismissed && consecutiveSystemDialogs >= 6) {
                // Second escalation: force-stop + restart
                appController.forceStop(packageName);
                sleep(200);
                appController.startApp(packageName);
                sleep(800);
                consecutiveSystemDialogs = 0;
                cachedScreenState = null;
            }
            return;
        }

        // 4. Out-of-app detection: check if the foreground window belongs to the target app.
        // root.getPackageName() returns the manifest package of the active window — same
        // namespace as the CLI --package argument.
        CharSequence rootPkg = root.getPackageName();
        if (rootPkg == null || !packageName.equals(rootPkg.toString())) {
            root.recycle();
            String foregroundPkg = rootPkg != null ? rootPkg.toString() : "null";

            // Launcher fast-path: immediate RESTART, no tolerance delay
            if (isLauncherPackage(foregroundPkg)) {
                Log.w(TAG, "Launcher detected (" + foregroundPkg + "), immediate restart");
                RvTrack.ooa(iteration, foregroundPkg, "launcher_fastpath");
                RvTrack.incrementRestarts();
                long elapsed = System.currentTimeMillis() - startTimeMs;
                long iterTotal = System.currentTimeMillis() - iterStart;
                traceWriter.writeLine(iteration, elapsed, "", "", "RESTART", "ooa",
                        false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                        -1, -1.0, -1, -1, -1, iterTotal,
                        true, "launcher_fastpath", foregroundPkg);
                handleOoaRestart(foregroundPkg);
                outOfAppCounter = 0;
                return;
            }

            // Tolerance for other packages (e.g., Chrome from in-app link)
            outOfAppCounter++;
            Log.d(TAG, "Out-of-app iteration " + outOfAppCounter + "/" + config.getOutOfAppTolerance()
                    + " (foreground: " + foregroundPkg + ", target: " + packageName + ")");
            if (outOfAppCounter >= config.getOutOfAppTolerance()) {
                Log.w(TAG, "Out-of-app tolerance exceeded, restarting app");
                RvTrack.ooa(iteration, foregroundPkg, "tolerance_exceeded");
                RvTrack.incrementRestarts();
                long elapsed = System.currentTimeMillis() - startTimeMs;
                long iterTotal = System.currentTimeMillis() - iterStart;
                traceWriter.writeLine(iteration, elapsed, "", "", "RESTART", "ooa",
                        false, 0, graph.size(), elapsed / 1000.0, 0, 0, null,
                        -1, -1.0, -1, -1, -1, iterTotal,
                        true, "tolerance_exceeded", foregroundPkg);
                handleOoaRestart(foregroundPkg);
                outOfAppCounter = 0;
            } else {
                // OOA within tolerance — log SKIP trace for observability
                long elapsed2 = System.currentTimeMillis() - startTimeMs;
                traceWriter.writeLine(iteration, elapsed2, "", "", "SKIP", "ooa_within_tolerance",
                        false, 0, graph.size(), elapsed2 / 1000.0, 0, 0, null,
                        -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                        true, "ooa_within_tolerance", foregroundPkg);
            }
            return;
        }
        outOfAppCounter = 0;
        consecutiveOoaAfterRestart = 0;
        consecutiveSystemDialogs = 0;

        // 5. Full UI capture (reuse cached state when available)
        ScreenState screen;
        List<ScreenItem> items;
        long captureMs;
        if (cachedScreenState != null) {
            screen = cachedScreenState;
            items = screen.getItems();
            captureMs = 0;
            cachedScreenState = null;
        } else {
            long captureStart = System.currentTimeMillis();
            items = uiCapture.capture(root);
            root.recycle();
            captureMs = System.currentTimeMillis() - captureStart;
            screen = new ScreenState(items, appController.getCurrentActivityName());
        }
        // 5a. Empty screen wait (INV-RSM-34): splash screens may auto-transition after 2-3s.
        // If no interactive items AND no backtrack path available, wait and re-capture.
        // SuccessorTracker operates at structHash level (Task 7.5).
        if (items.isEmpty() && successorTracker != null
                && successorTracker.getParents(screen.getStructHash()).isEmpty()) {
            sleep(2000);
            AccessibilityNodeInfo retryRoot = devController.getUiAutomation().getRootInActiveWindow();
            if (retryRoot != null) {
                List<ScreenItem> retryItems = uiCapture.capture(retryRoot);
                retryRoot.recycle();
                if (!retryItems.isEmpty()) {
                    items = retryItems;
                    screen = new ScreenState(retryItems, appController.getCurrentActivityName());
                }
            }
        }

        // CAP-4: Retry capture when too few interactive elements (splash/loading screens)
        int interactiveCount = countInteractive(items);
        for (int retry = 0; retry < config.getCaptureRetryMax() && interactiveCount < config.getCaptureRetryMinElements(); retry++) {
            sleep(config.getCaptureRetryDelayMs());
            AccessibilityNodeInfo retryRoot2 = devController.getUiAutomation().getRootInActiveWindow();
            if (retryRoot2 != null) {
                List<ScreenItem> retryItems2 = uiCapture.capture(retryRoot2);
                retryRoot2.recycle();
                int retryInteractive = countInteractive(retryItems2);
                if (retryInteractive > interactiveCount) {
                    items = retryItems2;
                    interactiveCount = retryInteractive;
                    screen = new ScreenState(items, appController.getCurrentActivityName());
                    RvTrack.parse(iteration, appController.getCurrentActivityName(), items.size(), "retry_" + (retry + 1), 0);
                }
            }
        }

        String hash = screen.getContentHash();
        String structHash = screen.getStructHash();
        String activity = screen.getActivity();

        // 5b. Update graph
        boolean isNewScreen = graph.get(hash) == null;
        graph.getOrCreate(hash, activity);
        graph.recordVisit(hash, activity);
        visitedActivities.add(activity);

        // 5b-gh34. Register in StructuralGraph (structHash → contentHash clustering).
        structuralGraph.register(structHash, hash);

        // 5b-gh34. Content hash explosion safety valve: degrade to structHash when ContentGraph
        // grows beyond 1000 entries to prevent infinite state explosion from dynamic content.
        if (graph.size() > 1000) {
            Log.w(TAG, "ContentGraph size " + graph.size() + " > 1000 — degrading contentHash to structHash");
            hash = structHash;
        }

        // Update totalActions on every visit (INV-RSM-40): Math.max ensures a
        // transient first visit with 0 elements doesn't permanently lock saturation at 1.0.
        br.unb.cic.rvsmart.graph.ContentNode screenNode = graph.get(hash);
        if (screenNode != null) {
            int nodeInteractiveCount = 0;
            for (ScreenItem item : items) {
                if (item.isEnabled() && item.getBounds() != null) {
                    if (item.isClickable() || item.isLongClickable() || item.isEditable() || item.isScrollable()) {
                        nodeInteractiveCount++;
                    }
                }
            }
            screenNode.setTotalActions(nodeInteractiveCount);
        }

        // 5c. Register screen elements for UI coverage tracking
        if (uiCoverageTracker != null) {
            uiCoverageTracker.registerScreenElements(hash, items);
        }

        // BUG-02: Cycle detection — record hash for ping-pong pattern detection
        cycleDetector.recordHash(structHash);
        boolean isCycleDetected = cycleDetector.isCycleDetected();

        // 5d. PhaseController: notify of new content state discovery and Phase 1 cluster entry.
        if (isNewScreen) {
            phaseController.onNewContentState(hash, activity, structHash, isCycleDetected);
            iterationsSinceNewState = 0;
        } else {
            iterationsSinceNewState++;
        }
        Phase phase = phaseController.currentPhase();
        if (phase == Phase.PHASE_1) {
            phaseController.onPhase1Entry(structHash);
        }
        metricsCollector.incrementPhaseDistribution(phase.name().toLowerCase().replace("_", ""));

        RvTrack.parse(iteration, activity, items.size(), hash, captureMs);

        // 6. Drain logcat coverage tags
        List<String> coveredMethods = logcatReader.drainCoverageTags();

        // 6a. Wire ConfirmedCoverageScorer: register coverage for the current screen hash
        if (!coveredMethods.isEmpty()) {
            if (confirmedCoverageScorer != null) {
                confirmedCoverageScorer.addConfirmed(hash, new HashSet<>(coveredMethods));
            }
        }

        // 6c. PhaseController: drive phase transitions via coverage delta.
        // coverageDelta = number of new methods confirmed this iteration.
        int coverageDelta = coveredMethods.size();
        phaseController.onIteration(coverageDelta);

        // 7. Stuck recovery: when stuck, use BFS to find a path to an unsaturated ancestor
        boolean isStuck = stuckDetector.getConsecutiveUnchanged() >= config.getStuckMaxBlocks();
        Action action = null;

        if (isStuck && successorTracker != null) {
            action = stuckDetector.recover(hash, successorTracker, graph);
            stuckDetector.reset();
            RvTrack.route(iteration, "algorithm", "algorithm", "stuck_recovery");
        }

        // BUG-02: Cycle detection — force RESTART when ping-pong detected
        if (isCycleDetected && action == null) {
            action = Action.restart("algorithm");
            cycleDetector.reset();
            RvTrack.route(iteration, "algorithm", "algorithm", "cycle_recovery");
        }

        // CAP-6: Periodic restart when exploration has plateaued
        if (iterationsSinceNewState >= config.getPeriodicRestartThreshold() && action == null) {
            action = Action.restart("algorithm");
            iterationsSinceNewState = 0;
            RvTrack.route(iteration, "algorithm", "algorithm", "periodic_restart");
        }

        // 8. Routing: try LLM path if configured and no stuck recovery action
        if (action == null) {
            action = tryLlmAction(screen, hash, activity);
        }

        if (action == null) {
            // LLM path unavailable or disabled — fall through to algorithm
            action = actionSelector.selectAction(phase, screen, structHash,
                    graph, structuralGraph, navigationMap, uiCoverageTracker, staticMap);
            RvTrack.route(iteration, "algorithm", "algorithm", "llm_unavailable_or_disabled");
        }

        // CAP-1: With menuFuzzRate probability, inject KEYCODE_MENU
        if (Math.random() < config.getMenuFuzzRate()
                && action != null && action.getType() != Action.Type.RESTART) {
            inputInjector.pressKey(KeyEvent.KEYCODE_MENU);
            RvTrack.exec(iteration, "KEY_EVENT", "(menu)", "algorithm", 0);
            sleep(config.getThrottleMs());
            // Continue with normal flow — next iteration will see menu items
        }

        // 9. Execute action (SAT-1: record after execution to avoid counting failed injections)
        long injectStart = System.currentTimeMillis();
        try {
            executeAction(action);
        } finally {
            // Record action in graph after execution. In finally block for crash safety —
            // if the app crashes, we still record the attempt.
            graph.recordAction(hash, action.signature(), action.getWidgetClass());
        }
        long injectMs = System.currentTimeMillis() - injectStart;

        RvTrack.exec(iteration, action.getType().name(),
                "(" + action.getX() + "," + action.getY() + ")",
                action.getSource(), injectMs);

        // BUG-01c: Track BACK executions in metrics for trace analysis
        if (action.getType() == Action.Type.BACK) {
            metricsCollector.recordForcedBack();
        }

        // 9a. Add to recent-actions ring buffer for V17 prompt context (last 5 actions)
        recentActionsBuffer.add(0, action);
        if (recentActionsBuffer.size() > 5) {
            recentActionsBuffer.remove(recentActionsBuffer.size() - 1);
        }

        // 9b. Record interaction for UI coverage tracking
        if (uiCoverageTracker != null && action.getType() != Action.Type.BACK
                && action.getType() != Action.Type.RESTART) {
            String elementId = "coords:" + action.getX() + "," + action.getY();
            uiCoverageTracker.recordInteraction(hash, elementId);
        }

        // 10. Post-action wait (INV-RSM-42: use HeapMonitor's adaptive throttle)
        int throttleMs = heapMonitor.check(iteration);
        sleep(throttleMs);

        // 11. Re-capture for effect detection
        String hashAfter = hash;
        String structHashAfter = structHash;  // gh34: track structural hash after action
        String activityAfter = activity;
        ScreenState postActionState = null;

        // Check if a crash occurred during action execution
        if (crashInterceptor.hasCrash()) {
            CrashInterceptor.CrashInfo info = crashInterceptor.consumeCrash();
            String crashType = (info != null && info.isAnr()) ? "anr" : "java";
            RvTrack.crash(iteration, crashType, action.signature(), 0);
            metricsCollector.recordCrash();
            long elapsed = System.currentTimeMillis() - startTimeMs;
            traceWriter.writeLine(iteration, elapsed, hash, activity, "SKIP", "post_action_crash",
                    false, 0, graph.size(), elapsed / 1000.0,
                    action.getX(), action.getY(), action.getWidgetClass(),
                    -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                    false, "crash_" + crashType, action.signature());
            recoverApp();
            return;
        }

        AccessibilityNodeInfo rootAfter = devController.getUiAutomation().getRootInActiveWindow();
        if (rootAfter != null) {
            List<ScreenItem> itemsAfter = uiCapture.capture(rootAfter);
            rootAfter.recycle();
            activityAfter = appController.getCurrentActivityName();
            postActionState = new ScreenState(itemsAfter, activityAfter);
            hashAfter = postActionState.getContentHash();
            structHashAfter = postActionState.getStructHash();
        } else {
            // Possible native crash — app process may be gone
            if (!appController.isAppRunning(packageName)) {
                RvTrack.crash(iteration, "native", action.signature(), 0);
                metricsCollector.recordCrash();
                long elapsed = System.currentTimeMillis() - startTimeMs;
                traceWriter.writeLine(iteration, elapsed, hash, activity, "SKIP", "native_crash",
                        false, 0, graph.size(), elapsed / 1000.0,
                        action.getX(), action.getY(), action.getWidgetClass(),
                        -1, -1.0, -1, -1, -1, System.currentTimeMillis() - iterStart,
                        false, "crash_native", action.signature());
                recoverApp();
                return;
            }
            // Transient issue — hashAfter stays as hash (no effect)
        }

        boolean hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);

        // SET_TEXT always has an implicit effect (INV-RSM-35): text was injected even if
        // the screen hash didn't change. Treating it as no-effect triggers unnecessary
        // retries and BACK decay, breaking form-filling sequences.
        if (action.getType() == Action.Type.SET_TEXT) hadEffect = true;

        // 11a. Adaptive wait: if no effect detected, wait a bit longer for slow transitions.
        // Only for CLICK and LONG_CLICK — SET_TEXT and SCROLL have immediate effect.
        boolean needsAdaptiveWait = action.getType() == Action.Type.CLICK
                || action.getType() == Action.Type.LONG_CLICK;
        if (!hadEffect && needsAdaptiveWait && config.getAdaptiveWaitMs() > 0) {
            sleep(config.getAdaptiveWaitMs());
            AccessibilityNodeInfo rootAdaptive = devController.getUiAutomation().getRootInActiveWindow();
            if (rootAdaptive != null) {
                List<ScreenItem> itemsAdaptive = uiCapture.capture(rootAdaptive);
                rootAdaptive.recycle();
                activityAfter = appController.getCurrentActivityName();
                postActionState = new ScreenState(itemsAdaptive, activityAfter);
                hashAfter = postActionState.getContentHash();
                structHashAfter = postActionState.getStructHash();
                hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);
            }
        }

        // 11b. Record transition in SuccessorTracker at structHash level (Task 7.5)
        // and in NavigationMap for replay-based backtracking (gh34).
        if (hadEffect && successorTracker != null) {
            successorTracker.record(structHash, structHashAfter);
        }
        if (hadEffect) {
            navigationMap.record(structHash, action.signature(), structHashAfter);
        }

        // Save primary action metadata before retries overwrite the action variable.
        // The trace records the last retried action, so we capture primary separately
        // for the scores — primary is what was SELECTED, retries are alternatives.
        Action primaryAction = action;

        // 12. Multi-attempt retry (INV-RSM-07): try alternative actions if no effect
        int retries = 0;
        Set<String> excludeSignatures = new HashSet<>();
        while (!hadEffect && retries < config.getMaxRetriesPerCycle()) {
            excludeSignatures.add(action.signature());
            Action nextAction = actionSelector.selectNextBest(screen, excludeSignatures, graph, staticMap);
            if (nextAction == null) break;

            action = nextAction;
            try {
                executeAction(action);
            } finally {
                graph.recordAction(hash, action.signature(), action.getWidgetClass());
            }
            if (action.getType() == Action.Type.BACK) {
                metricsCollector.recordForcedBack();
            }
            sleep(config.getThrottleMs());

            rootAfter = devController.getUiAutomation().getRootInActiveWindow();
            if (rootAfter != null) {
                List<ScreenItem> itemsAfter2 = uiCapture.capture(rootAfter);
                rootAfter.recycle();
                activityAfter = appController.getCurrentActivityName();
                postActionState = new ScreenState(itemsAfter2, activityAfter);
                hashAfter = postActionState.getContentHash();
                structHashAfter = postActionState.getStructHash();
            }
            hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);

            // Update BACK decay inside retry so consecutive BACKs get increasing penalty
            boolean retryWasBack = action.getType() == Action.Type.BACK;
            actionSelector.updateBackDecay(retryWasBack, hadEffect, hash);

            retries++;
        }

        // 13. Update BACK decay
        boolean wasBack = action.getType() == Action.Type.BACK;
        actionSelector.updateBackDecay(wasBack, hadEffect, hash);

        // 14. Learn: assign reward and update graph transitions
        double reward = learner.update(action, hadEffect, hash, hashAfter,
                activity, activityAfter, coveredMethods,
                iteration, retries);

        // 14a. Update stuck detector with post-action hash and action type.
        // SET_TEXT is exempted from incrementing the counter (Anomaly 2/INV-RSM-34).
        stuckDetector.updateWithActionType(hashAfter, action.getType());

        // 15. Trace output with RVTRACK observability fields
        long elapsed = System.currentTimeMillis() - startTimeMs;
        // Approximate scoring time: gap between capture end and inject start.
        // When cache is used (captureMs=0), this includes all pre-inject work.
        long scoringMs = injectStart - (iterStart + captureMs);
        long iterTotal = System.currentTimeMillis() - iterStart;
        br.unb.cic.rvsmart.graph.ContentNode traceNode = graph.get(hashAfter);
        double satRate = traceNode != null ? traceNode.getSaturationRate() : -1.0;
        // Attach primary action metadata to score breakdown — action variable may have been
        // overwritten by retries, but scores always belong to the primary selected action.
        Map<String, Object> scoreBreakdown = actionSelector.getLastScoreBreakdown();
        if (scoreBreakdown != null) {
            scoreBreakdown = new HashMap<>(scoreBreakdown); // defensive copy to avoid mutating live map
            scoreBreakdown.put("primary_action_type", primaryAction.getType().name());
            scoreBreakdown.put("primary_widget_class",
                    primaryAction.getWidgetClass() != null ? primaryAction.getWidgetClass() : "");
        }
        traceWriter.writeLine(iteration, elapsed, hashAfter, activityAfter,
                action.getType().name(), action.getSource(),
                hadEffect, retries, graph.size(), elapsed / 1000.0,
                action.getX(), action.getY(), action.getWidgetClass(),
                0, satRate,
                captureMs, scoringMs, injectMs, iterTotal,
                false, null, null,
                scoreBreakdown, phase.name());

        // 16. Metrics
        metricsCollector.recordIteration(action.getSource());
        if (retries > 0) metricsCollector.recordRetries(retries);

        // 16a. gh34 observability: update dual-hash metrics each iteration
        metricsCollector.recordContentStates(graph.size());
        metricsCollector.recordStructuralClusters(structuralGraph.size());
        metricsCollector.recordNavMapEdges(navigationMap.size());

        // 17. Cycle time profiling (also logged to logcat via RVTRACK for real-time debugging)
        RvTrack.cycle(iteration, captureMs, injectMs, iterTotal);

        // 18. Cache post-action state for next iteration (avoids redundant capture)
        cachedScreenState = postActionState;
    }

    /**
     * Handle null root from getRootInActiveWindow().
     * Null root means either native crash (process gone) or transient ANR.
     * Distinguish via isAppRunning(): if process gone, restart; otherwise wait.
     */
    private void handleNullRoot() {
        if (!appController.isAppRunning(packageName)) {
            RvTrack.crash(iteration, "native", "unknown", 0);
            metricsCollector.recordCrash();
            recoverApp();
        } else {
            // Transient ANR or screen transition — wait briefly
            sleep(500);
        }
    }

    /**
     * Handle crash recovery from CrashInterceptor callback.
     * Logs the crash and restarts the app.
     */
    private void handleCrashRecovery(String crashType) {
        RvTrack.crash(iteration, crashType, "unknown", 0);
        metricsCollector.recordCrash();
        recoverApp();
    }

    /**
     * Restart the app and reset stuck detector state.
     */
    private void recoverApp() {
        appController.forceStop(packageName);
        sleep(200);
        appController.startApp(packageName);
        sleep(800);
        stuckDetector.reset();
        cachedScreenState = null;
    }

    /**
     * Check if the given package name belongs to a known Android launcher.
     */
    private static boolean isLauncherPackage(String packageName) {
        for (String launcher : LAUNCHER_PACKAGES) {
            if (launcher.equals(packageName)) return true;
        }
        return false;
    }

    /**
     * Handle OOA restart with multi-stage recovery (INV-RSM-33).
     *
     * Stage 1 (default): simple forceStop + startApp via recoverApp().
     * Stage 2 (after MAX_CONSECUTIVE_OOA_AFTER_RESTART failures): press BACK to
     * dismiss the foreign app, then check if we returned to ours. If still OOA,
     * force-stop the foreign package before restarting our app.
     *
     * @param foregroundPkg the package currently in the foreground (not our target)
     */
    private void handleOoaRestart(String foregroundPkg) {
        consecutiveOoaAfterRestart++;
        if (consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART) {
            Log.w(TAG, "Multi-stage OOA recovery: BACK -> check -> forceStop foreign if needed");
            RvTrack.ooa(iteration, packageName, "multi_stage_recovery");

            // Stage 2a: press BACK to dismiss the foreign app
            inputInjector.pressBack();
            sleep(500);

            // Stage 2b: re-check foreground package
            AccessibilityNodeInfo checkRoot = devController.getUiAutomation().getRootInActiveWindow();
            boolean stillOoa = true;
            if (checkRoot != null) {
                CharSequence checkPkg = checkRoot.getPackageName();
                stillOoa = checkPkg == null || !packageName.equals(checkPkg.toString());
                checkRoot.recycle();
            }

            // Stage 2c: if still OOA, force-stop the foreign app
            if (stillOoa && foregroundPkg != null && !foregroundPkg.equals("null")) {
                Log.w(TAG, "Still OOA after BACK, force-stopping foreign: " + foregroundPkg);
                appController.forceStop(foregroundPkg);
                sleep(200);
            }

            // Stage 2d: restart our app
            appController.forceStop(packageName);
            sleep(200);
            appController.startApp(packageName);
            sleep(800);
            stuckDetector.reset();
            cachedScreenState = null;
            consecutiveOoaAfterRestart = 0;
        } else {
            recoverApp();
        }
    }

    /**
     * Execute an action via InputInjector or AppController based on action type.
     */
    private void executeAction(Action action) {
        switch (action.getType()) {
            case CLICK:
                inputInjector.click(action.getX(), action.getY());
                break;
            case LONG_CLICK:
                inputInjector.longClick(action.getX(), action.getY());
                break;
            case BACK:
                inputInjector.pressBack();
                break;
            case RESTART:
                appController.forceStop(packageName);
                sleep(200);
                appController.startApp(packageName);
                sleep(800);
                RvTrack.incrementRestarts();
                stuckDetector.reset();
                cachedScreenState = null;
                break;
            case SET_TEXT:
                inputInjector.setText(action.getX(), action.getY(),
                        action.getText() != null ? action.getText() : "test");
                break;
            case SCROLL:
                // CAP-8: half-screen displacement for effective scrolling
                int scrollDisplacement = DEVICE_WIDTH / 2;
                String scrollDir = action.getText();
                if ("up".equals(scrollDir)) {
                    inputInjector.scroll(action.getX(), action.getY(), scrollDisplacement);
                } else if ("left".equals(scrollDir)) {
                    inputInjector.swipe(action.getX(), action.getY(),
                            action.getX() - scrollDisplacement, action.getY());
                } else if ("right".equals(scrollDir)) {
                    inputInjector.swipe(action.getX(), action.getY(),
                            action.getX() + scrollDisplacement, action.getY());
                } else {
                    // Default: scroll down
                    inputInjector.scroll(action.getX(), action.getY(), -scrollDisplacement);
                }
                break;
            case SWIPE:
                inputInjector.swipe(action.getX(), action.getY(),
                        action.getX(), action.getY() - DEVICE_WIDTH / 2);
                break;
            case KEY_EVENT:
                // No-op for now — key events require a keycode not carried by Action
                break;
        }
    }

    /**
     * Attempt to produce an action via the LLM path.
     *
     * Returns null when:
     *   - routingManager is null (pure algorithm mode, no LLM components wired)
     *   - routingManager.shouldUseLlm() returns false for this iteration
     *   - screenshot capture fails (returns null)
     *   - image processing fails (returns null)
     *   - LLM call throws an exception
     *   - ToolCallParser cannot parse a valid action from the response
     *
     * On any failure, recordLlmFailure() is called so the circuit breaker can
     * track the error rate. The caller falls through to the algorithm path.
     *
     * On success, recordLlmSuccess() is called and the converted Action is returned
     * with source="llm".
     */
    private Action tryLlmAction(ScreenState screen, String hash, String activity) {
        // LLM components not wired — always use algorithm
        if (routingManager == null || sglangClient == null || toolCallParser == null
                || promptBuilder == null || imageProcessor == null || screenshotCapture == null) {
            return null;
        }

        // Routing decision: algorithm or LLM for this iteration?
        // isOutOfApp is always false here — OOA detection at the top of runIteration()
        // causes an early return before tryLlmAction is ever called.
        if (!routingManager.shouldUseLlm(hash, false)) {
            return null;
        }

        long llmStart = System.currentTimeMillis();
        try {
            // Capture screenshot
            byte[] pngBytes = screenshotCapture.capture(DEVICE_WIDTH, DEVICE_HEIGHT);
            if (pngBytes == null) {
                routingManager.recordLlmFailure();
                return null;
            }

            // Compress and encode for LLM
            String base64Image = imageProcessor.processScreenshot(pngBytes);
            if (base64Image == null) {
                routingManager.recordLlmFailure();
                return null;
            }

            // Build prompt and call LLM
            PromptVersion version = config.getLlmPromptVersion();

            // V17 context: interaction counts from UICoverageTracker (screen-scoped)
            Map<String, Integer> interactionCounts = uiCoverageTracker != null
                    ? uiCoverageTracker.getCountsForScreen(hash) : null;

            // V17 context: MOP element sets — approximated at activity level.
            // StaticMap works at activity granularity; all elements on a MOP-reachable
            // activity receive the marker (direct or transitive).
            Set<String> directMopElements = null;
            Set<String> indirectMopElements = null;
            if (staticMap != null && staticMap.isLoaded()) {
                boolean hasDirect = staticMap.activityHasDirectMop(activity);
                boolean hasTransitive = staticMap.activityHasMop(activity);
                if (hasDirect || hasTransitive) {
                    Set<String> allIds = new HashSet<>();
                    for (ScreenItem si : screen.getItems()) {
                        allIds.add(UICoverageTracker.elementId(si));
                    }
                    if (hasDirect) directMopElements = allIds;
                    else indirectMopElements = allIds;
                }
            }

            // V17 context: navigation hint — nearest WTG successor with MOP reachability
            String navigationHint = null;
            if (staticMap != null && staticMap.isLoaded()) {
                List<String> successors = staticMap.getTransitions(activity);
                for (String successor : successors) {
                    if (staticMap.activityHasDirectMop(successor)) {
                        navigationHint = "Target: " + successor
                                + " (has monitored operations, ~1 transition away)";
                        break;
                    }
                }
                if (navigationHint == null) {
                    for (String successor : successors) {
                        if (staticMap.activityHasMop(successor)) {
                            navigationHint = "Target: " + successor
                                    + " (reaches monitored operations, ~1 transition away)";
                            break;
                        }
                    }
                }
            }

            PromptContext ctx = PromptContext.builder()
                    .base64Screenshot(base64Image)
                    .uiElements(screen.getItems())
                    .currentActivity(activity)
                    .navigationHint(navigationHint)
                    .visitedActivities(visitedActivities)
                    .iterationNumber(iteration)
                    .elementInteractionCounts(interactionCounts)
                    .directMopElements(directMopElements)
                    .indirectMopElements(indirectMopElements)
                    .elementScores(actionSelector.getLastScoreBreakdown())
                    .recentActions(new ArrayList<>(recentActionsBuffer))
                    .build();
            List<SglangClient.Message> messages = promptBuilder.build(version, ctx);
            SglangClient.ChatResponse response = sglangClient.chat(messages);

            // Parse tool call from response
            ToolCallParser.ParsedAction parsed = toolCallParser.parse(response);
            if (parsed == null) {
                routingManager.recordLlmFailure();
                return null;
            }

            // Convert Qwen3-VL normalized coordinates to device pixels
            int[] pixels = CoordinateNormalizer.normalize(
                    parsed.getX(), parsed.getY(), DEVICE_WIDTH, DEVICE_HEIGHT);
            int px = pixels[0];
            int py = pixels[1];

            // Map parsed action type to Action.Type
            Action.Type actionType = mapParsedType(parsed.getActionType());
            if (actionType == null) {
                routingManager.recordLlmFailure();
                return null;
            }

            long llmMs = System.currentTimeMillis() - llmStart;
            routingManager.recordLlmSuccess();
            metricsCollector.recordLlmCall(
                    response.getPromptTokens(), response.getCompletionTokens(),
                    llmMs / 1000.0);
            RvTrack.llm(iteration, response.getPromptTokens(), response.getCompletionTokens(),
                    llmMs, true);
            RvTrack.route(iteration, "llm", "llm", "routing_decision");

            // Boundary protection: reject LLM clicks in status bar (top 5%) or nav bar (bottom 6%)
            if (actionType == Action.Type.CLICK && isInBoundaryZone(py, DEVICE_HEIGHT)) {
                RvTrack.llm(iteration, response.getPromptTokens(), response.getCompletionTokens(),
                        llmMs, false);
                Log.d(TAG, "LLM boundary reject: y=" + py + " in boundary zone");
                return Action.back("llm");
            }

            if (actionType == Action.Type.BACK) {
                return Action.back("llm");
            }
            // Action.text serves dual purpose: SET_TEXT content or SCROLL direction.
            // For SCROLL, prefer the direction field; for SET_TEXT, use text field.
            String actionText = (actionType == Action.Type.SCROLL && parsed.getDirection() != null)
                    ? parsed.getDirection()
                    : parsed.getText();
            return new Action(actionType, px, py, actionText, "llm", "");

        } catch (Exception e) {
            long llmMs = System.currentTimeMillis() - llmStart;
            routingManager.recordLlmFailure();
            RvTrack.llm(iteration, 0, 0, llmMs, false);
            Log.w(TAG, "LLM path failed at iteration " + iteration + ": " + e.getMessage());
            return null;
        }
    }

    /**
     * Map a string action type from ToolCallParser to Action.Type.
     * Returns null for unrecognised strings so the caller can fall back to algorithm.
     */
    private Action.Type mapParsedType(String parsedType) {
        if (parsedType == null) return null;
        switch (parsedType) {
            case "click":       return Action.Type.CLICK;
            case "long_click":  return Action.Type.LONG_CLICK;
            case "scroll":      return Action.Type.SCROLL;
            case "swipe":       return Action.Type.SWIPE;
            case "type_text":   return Action.Type.SET_TEXT;
            case "back":        return Action.Type.BACK;
            default:            return null;
        }
    }

    /**
     * Count interactive (enabled + clickable/scrollable/editable/checkable/longClickable) items.
     * Used by CAP-4 state refresh retry.
     */
    private int countInteractive(List<ScreenItem> items) {
        int count = 0;
        for (ScreenItem item : items) {
            if (item.isEnabled() && item.isInteractive()) count++;
        }
        return count;
    }

    private void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ignored) {
        }
    }

    /**
     * Check if a y-coordinate falls in the status bar (top 5%) or navigation bar (bottom 6%).
     * LLM-generated clicks in these zones are rejected to prevent accidental system interactions.
     * Package-private for testing.
     */
    static boolean isInBoundaryZone(int y, int screenHeight) {
        double statusBarLimit = screenHeight * 0.05;
        double navBarLimit = screenHeight * 0.94;
        return y < statusBarLimit || y > navBarLimit;
    }

    // Accessors for testing and metrics
    public int getIteration() { return iteration; }
    public long getStartTimeMs() { return startTimeMs; }
}
