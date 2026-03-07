package br.unb.cic.rvsmart.core;

import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import br.unb.cic.rvsmart.device.AppController;
import br.unb.cic.rvsmart.device.CrashInterceptor;
import br.unb.cic.rvsmart.device.DeviceController;
import br.unb.cic.rvsmart.device.HeapMonitor;
import br.unb.cic.rvsmart.device.InputInjector;
import br.unb.cic.rvsmart.device.LogcatReader;
import br.unb.cic.rvsmart.device.SystemDialogDetector;
import br.unb.cic.rvsmart.device.UiCapture;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.llm.CoordinateNormalizer;
import br.unb.cic.rvsmart.llm.ImageProcessor;
import br.unb.cic.rvsmart.llm.PromptBuilder;
import br.unb.cic.rvsmart.llm.ScreenshotCapture;
import br.unb.cic.rvsmart.llm.SglangClient;
import br.unb.cic.rvsmart.llm.ToolCallParser;
import br.unb.cic.rvsmart.output.MetricsCollector;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.output.TraceWriter;
import br.unb.cic.rvsmart.recovery.StuckDetector;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.ActionSelector;
import br.unb.cic.rvsmart.strategy.InputValueGenerator;
import br.unb.cic.rvsmart.strategy.PlateauDetector;
import br.unb.cic.rvsmart.strategy.RewardPropagator;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;

import java.util.HashSet;
import java.util.List;
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
    private final DynamicStateGraph graph;
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
    private final RewardPropagator rewardPropagator;

    // Optional transition tracking — null when not configured
    private final SuccessorTracker successorTracker;

    // Optional gh31 components — null when not configured
    private final UICoverageTracker uiCoverageTracker;
    private final PlateauDetector plateauDetector;

    // Known Android launcher packages for OOA fast-path detection
    private static final String[] LAUNCHER_PACKAGES = {
            "com.android.launcher3",
            "com.google.android.apps.nexuslauncher",
            "com.android.launcher"
    };
    private static final int MAX_CONSECUTIVE_OOA_AFTER_RESTART = 3;

    // State
    private int iteration;
    private long startTimeMs;
    private int outOfAppCounter;
    private int consecutiveOoaAfterRestart;

    // Tracks visited activities for LLM prompt context
    private final Set<String> visitedActivities = new HashSet<>();

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
                     HeapMonitor heapMonitor, DynamicStateGraph graph,
                     StaticMap staticMap, ActionSelector actionSelector,
                     StuckDetector stuckDetector, Learner learner,
                     TraceWriter traceWriter, MetricsCollector metricsCollector) {
        this(packageName, deadline, config, devController, uiCapture, inputInjector,
                appController, crashInterceptor, dialogDetector, logcatReader,
                heapMonitor, graph, staticMap, actionSelector, stuckDetector,
                learner, traceWriter, metricsCollector,
                null, null, null, null, null, null, null, null, null,
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
                     HeapMonitor heapMonitor, DynamicStateGraph graph,
                     StaticMap staticMap, ActionSelector actionSelector,
                     StuckDetector stuckDetector, Learner learner,
                     TraceWriter traceWriter, MetricsCollector metricsCollector,
                     RoutingManager routingManager, SglangClient sglangClient,
                     ToolCallParser toolCallParser, PromptBuilder promptBuilder,
                     ImageProcessor imageProcessor, ScreenshotCapture screenshotCapture,
                     ConfirmedCoverageScorer confirmedCoverageScorer,
                     RewardPropagator rewardPropagator,
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
        this.rewardPropagator = rewardPropagator;
        this.successorTracker = successorTracker;
        this.uiCoverageTracker = uiCoverageTracker;
        this.plateauDetector = plateauDetector;
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
            handleCrashRecovery(crashType);
            return;
        }

        // 2. Capture UI root
        AccessibilityNodeInfo root = devController.getUiAutomation().getRootInActiveWindow();
        if (root == null) {
            handleNullRoot();
            return;
        }

        // 3. System dialog check (before full capture)
        if (dialogDetector.isSystemDialog(root)) {
            dialogDetector.dismiss(root);
            RvTrack.incrementSystemDialogs();
            metricsCollector.recordSystemDialog();
            return;
        }

        // 4. Out-of-app detection: check if the foreground window belongs to the target app.
        // root.getPackageName() returns the manifest package of the active window — same
        // namespace as the CLI --package argument.
        CharSequence rootPkg = root.getPackageName();
        if (rootPkg == null || !packageName.equals(rootPkg.toString())) {
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
                handleOoaRestart();
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
                handleOoaRestart();
                outOfAppCounter = 0;
            }
            return;
        }
        outOfAppCounter = 0;
        consecutiveOoaAfterRestart = 0;

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
            captureMs = System.currentTimeMillis() - captureStart;
            screen = new ScreenState(items, appController.getCurrentActivityName());
        }
        String hash = screen.getHash();
        String activity = screen.getActivity();

        // 5b. Update graph
        boolean isNewScreen = graph.get(hash) == null;
        graph.getOrCreate(hash, activity);
        graph.recordVisit(hash, activity);
        visitedActivities.add(activity);

        // Initialize totalActions on first visit so getSaturationRate() works correctly
        if (isNewScreen) {
            br.unb.cic.rvsmart.graph.ScreenNode screenNode = graph.get(hash);
            if (screenNode != null) {
                int interactiveCount = 0;
                for (ScreenItem item : items) {
                    if (item.isEnabled() && item.getBounds() != null) {
                        if (item.isClickable() || item.isLongClickable() || item.isEditable() || item.isScrollable()) {
                            interactiveCount++;
                        }
                    }
                }
                screenNode.setTotalActions(interactiveCount);
            }
        }

        // 5c. Register screen elements for UI coverage tracking
        if (uiCoverageTracker != null) {
            uiCoverageTracker.registerScreenElements(hash, items);
        }

        RvTrack.parse(iteration, activity, items.size(), hash, captureMs);

        // 6. Drain logcat coverage tags
        List<String> coveredMethods = logcatReader.drainCoverageTags();

        // 6a. Wire ConfirmedCoverageScorer: register coverage for the current screen hash
        if (!coveredMethods.isEmpty()) {
            if (confirmedCoverageScorer != null) {
                confirmedCoverageScorer.addConfirmed(hash, new HashSet<>(coveredMethods));
            }
            // 6b. Wire RewardPropagator: boost the trajectory that led to this coverage
            if (rewardPropagator != null) {
                rewardPropagator.propagateConfirmedCoverage(hash, new HashSet<>(coveredMethods), graph);
            }
        }

        // 6c. Plateau detection: record iteration and update stochastic probability
        if (plateauDetector != null) {
            boolean hasNewMopCoverage = !coveredMethods.isEmpty();
            plateauDetector.recordIteration(isNewScreen, hasNewMopCoverage);
            actionSelector.setPlateauActive(plateauDetector.isPlateauDetected());
        }

        // 7. Stuck recovery: when stuck, use BFS to find a path to an unsaturated ancestor
        boolean isStuck = stuckDetector.getConsecutiveUnchanged() >= config.getStuckMaxBlocks();
        Action action = null;

        if (isStuck && successorTracker != null) {
            action = stuckDetector.recover(hash, successorTracker, graph);
            stuckDetector.reset();
            RvTrack.route(iteration, "algorithm", "algorithm", "stuck_recovery");
        }

        // 8. Routing: try LLM path if configured and no stuck recovery action
        if (action == null) {
            action = tryLlmAction(screen, hash, activity, isNewScreen, isStuck);
        }

        if (action == null) {
            // LLM path unavailable or disabled — fall through to algorithm
            action = actionSelector.selectAction(screen, graph, staticMap);
            RvTrack.route(iteration, "algorithm", "algorithm", "llm_unavailable_or_disabled");
        }

        // 8. Pre-record action in graph for crash safety
        graph.recordAction(hash, action.signature(), action.getWidgetClass());

        // 9. Execute action
        long injectStart = System.currentTimeMillis();
        executeAction(action);
        long injectMs = System.currentTimeMillis() - injectStart;

        RvTrack.exec(iteration, action.getType().name(),
                "(" + action.getX() + "," + action.getY() + ")",
                action.getSource(), injectMs);

        // 9b. Record interaction for UI coverage tracking
        if (uiCoverageTracker != null && action.getType() != Action.Type.BACK
                && action.getType() != Action.Type.RESTART) {
            String elementId = "coords:" + action.getX() + "," + action.getY();
            uiCoverageTracker.recordInteraction(hash, elementId);
        }

        // 10. Post-action wait
        sleep(config.getThrottleMs());

        // 11. Re-capture for effect detection
        String hashAfter = hash;
        String activityAfter = activity;
        ScreenState postActionState = null;

        // Check if a crash occurred during action execution
        if (crashInterceptor.hasCrash()) {
            CrashInterceptor.CrashInfo info = crashInterceptor.consumeCrash();
            String crashType = (info != null && info.isAnr()) ? "anr" : "java";
            RvTrack.crash(iteration, crashType, action.signature(), 0);
            metricsCollector.recordCrash();
            recoverApp();
            return;
        }

        AccessibilityNodeInfo rootAfter = devController.getUiAutomation().getRootInActiveWindow();
        if (rootAfter != null) {
            List<ScreenItem> itemsAfter = uiCapture.capture(rootAfter);
            activityAfter = appController.getCurrentActivityName();
            postActionState = new ScreenState(itemsAfter, activityAfter);
            hashAfter = postActionState.getHash();
        } else {
            // Possible native crash — app process may be gone
            if (!appController.isAppRunning(packageName)) {
                RvTrack.crash(iteration, "native", action.signature(), 0);
                metricsCollector.recordCrash();
                recoverApp();
                return;
            }
            // Transient issue — hashAfter stays as hash (no effect)
        }

        boolean hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);

        // 11a. Adaptive wait: if no effect detected, wait a bit longer for slow transitions.
        // Only for CLICK and LONG_CLICK — SET_TEXT and SCROLL have immediate effect.
        boolean needsAdaptiveWait = action.getType() == Action.Type.CLICK
                || action.getType() == Action.Type.LONG_CLICK;
        if (!hadEffect && needsAdaptiveWait && config.getAdaptiveWaitMs() > 0) {
            sleep(config.getAdaptiveWaitMs());
            AccessibilityNodeInfo rootAdaptive = devController.getUiAutomation().getRootInActiveWindow();
            if (rootAdaptive != null) {
                List<ScreenItem> itemsAdaptive = uiCapture.capture(rootAdaptive);
                activityAfter = appController.getCurrentActivityName();
                postActionState = new ScreenState(itemsAdaptive, activityAfter);
                hashAfter = postActionState.getHash();
                hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);
            }
        }

        // 11b. Record transition in SuccessorTracker for proactive backtracking
        if (hadEffect && successorTracker != null) {
            successorTracker.record(hash, hashAfter);
        }

        // 12. Multi-attempt retry (INV-RSM-07): try alternative actions if no effect
        int retries = 0;
        Set<String> excludeSignatures = new HashSet<>();
        while (!hadEffect && retries < config.getMaxRetriesPerCycle()) {
            excludeSignatures.add(action.signature());
            Action nextAction = actionSelector.selectNextBest(screen, excludeSignatures, graph, staticMap);
            if (nextAction == null) break;

            action = nextAction;
            graph.recordAction(hash, action.signature(), action.getWidgetClass());
            executeAction(action);
            sleep(config.getThrottleMs());

            rootAfter = devController.getUiAutomation().getRootInActiveWindow();
            if (rootAfter != null) {
                List<ScreenItem> itemsAfter2 = uiCapture.capture(rootAfter);
                activityAfter = appController.getCurrentActivityName();
                postActionState = new ScreenState(itemsAfter2, activityAfter);
                hashAfter = postActionState.getHash();
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

        // 14a. Record step in RewardPropagator for N-step TD propagation
        if (rewardPropagator != null) {
            rewardPropagator.recordStep(hashAfter, reward);
            rewardPropagator.propagate();
        }

        // 15. Trace output with RVTRACK observability fields
        long elapsed = System.currentTimeMillis() - startTimeMs;
        // Approximate scoring time: gap between capture end and inject start.
        // When cache is used (captureMs=0), this includes all pre-inject work.
        long scoringMs = injectStart - (iterStart + captureMs);
        long iterTotal = System.currentTimeMillis() - iterStart;
        br.unb.cic.rvsmart.graph.ScreenNode traceNode = graph.get(hashAfter);
        double satRate = traceNode != null ? traceNode.getSaturationRate() : -1.0;
        traceWriter.writeLine(iteration, elapsed, hashAfter, activityAfter,
                action.getType().name(), action.getSource(),
                hadEffect, retries, graph.size(), elapsed / 1000.0,
                action.getX(), action.getY(), action.getWidgetClass(),
                actionSelector.getLastSelectedTier(), satRate,
                captureMs, scoringMs, injectMs, iterTotal,
                false, null, null,
                actionSelector.getLastScoreBreakdown());

        // 16. Metrics
        metricsCollector.recordIteration(action.getSource());
        if (retries > 0) metricsCollector.recordRetries(retries);

        // 17. Cycle time profiling (also logged to logcat via RVTRACK for real-time debugging)
        RvTrack.cycle(iteration, captureMs, injectMs, iterTotal);

        // 18. Heap monitor — may adjust throttle for subsequent iterations
        heapMonitor.check(iteration);

        // 19. Cache post-action state for next iteration (avoids redundant capture)
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
     * Handle OOA restart with consecutive-failure fallback.
     * If the app keeps redirecting to an external intent immediately after restart
     * (3 consecutive OOA-after-RESTART events), escalate to forceStop + startApp
     * instead of the standard restart.
     */
    private void handleOoaRestart() {
        consecutiveOoaAfterRestart++;
        if (consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART) {
            Log.w(TAG, "Consecutive OOA-after-RESTART fallback: forceStop + startApp");
            RvTrack.ooa(iteration, packageName, "force_restart_fallback");
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
                cachedScreenState = null;
                break;
            case SET_TEXT:
                inputInjector.setText(action.getX(), action.getY(),
                        action.getText() != null ? action.getText() : "test");
                break;
            case SCROLL:
                String scrollDir = action.getText();
                if ("up".equals(scrollDir)) {
                    inputInjector.scroll(action.getX(), action.getY(), 300);
                } else if ("left".equals(scrollDir)) {
                    inputInjector.swipe(action.getX(), action.getY(),
                            action.getX() - 300, action.getY());
                } else if ("right".equals(scrollDir)) {
                    inputInjector.swipe(action.getX(), action.getY(),
                            action.getX() + 300, action.getY());
                } else {
                    // Default: scroll down
                    inputInjector.scroll(action.getX(), action.getY(), -300);
                }
                break;
            case SWIPE:
                inputInjector.swipe(action.getX(), action.getY(),
                        action.getX(), action.getY() - 300);
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
    private Action tryLlmAction(ScreenState screen, String hash, String activity,
                                boolean isNewScreen, boolean isStuck) {
        // LLM components not wired — always use algorithm
        if (routingManager == null || sglangClient == null || toolCallParser == null
                || promptBuilder == null || imageProcessor == null || screenshotCapture == null) {
            return null;
        }

        // Routing decision: algorithm or LLM for this iteration?
        if (!routingManager.shouldUseLlm(screen, isNewScreen, isStuck)) {
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
            List<SglangClient.Message> messages = promptBuilder.buildExplorationPrompt(
                    base64Image, screen.getItems(), activity, null, visitedActivities);
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
            return new Action(actionType, px, py, parsed.getText(), "llm", "");

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
