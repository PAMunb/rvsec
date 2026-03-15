package br.unb.cic.rvsmart;

import android.os.Build;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import br.unb.cic.rvsmart.core.AgentLoop;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.Learner;
import br.unb.cic.rvsmart.core.RoutingManager;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.device.AppController;
import br.unb.cic.rvsmart.device.CrashInterceptor;
import br.unb.cic.rvsmart.device.DeviceController;
import br.unb.cic.rvsmart.device.HeapMonitor;
import br.unb.cic.rvsmart.device.InputInjector;
import br.unb.cic.rvsmart.device.LogcatReader;
import br.unb.cic.rvsmart.device.SystemDialogDetector;
import br.unb.cic.rvsmart.device.UiCapture;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.llm.ImageProcessor;
import br.unb.cic.rvsmart.llm.LlmCircuitBreaker;
import br.unb.cic.rvsmart.llm.PromptBuilder;
import br.unb.cic.rvsmart.llm.ScreenshotCapture;
import br.unb.cic.rvsmart.llm.SglangClient;
import br.unb.cic.rvsmart.llm.ToolCallParser;
import br.unb.cic.rvsmart.output.MetricsCollector;
import br.unb.cic.rvsmart.output.TraceWriter;
import br.unb.cic.rvsmart.recovery.BacktrackBfs;
import br.unb.cic.rvsmart.recovery.FrontierFinder;
import br.unb.cic.rvsmart.recovery.StuckDetector;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.ActionSelector;
import br.unb.cic.rvsmart.strategy.InputValueGenerator;
import br.unb.cic.rvsmart.strategy.PlateauDetector;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;

import java.io.File;
import java.util.List;

/**
 * Entry point for the rvsmart exploration agent.
 *
 * Launched via: adb shell CLASSPATH=/data/local/tmp/rvsmart.jar
 *               /system/bin/app_process /system/bin br.unb.cic.rvsmart.Main
 *               --package <pkg> --timeout <secs> [options]
 *
 * The process runs under Shell UID 2000 with INJECT_EVENTS permission.
 * ART provides android.jar classes at runtime; compile-time stubs are
 * excluded from the fat JAR.
 */
public class Main {

    private static final String TAG = "RVSMART";
    private static final int REQUIRED_API_LEVEL = 29;

    public static void main(String[] args) {
        try {
            CliArgs cli = parseArgs(args);

            if (cli.healthCheck) {
                runHealthCheck();
                return;
            }

            assertApiLevel();

            Log.i(TAG, "rvsmart starting: package=" + cli.packageName
                    + " timeout=" + cli.timeout + "s"
                    + " mode=" + cli.mode
                    + (cli.seed != null ? " seed=" + cli.seed : ""));

            Config config = loadConfig(cli);

            if (cli.benchmarkMode) {
                runBenchmark(cli.packageName);
                return;
            }

            if (cli.pocMode) {
                runPoC(cli.packageName);
                return;
            }

            runAgent(cli, config);

        } catch (Exception e) {
            Log.e(TAG, "Fatal error: " + e.getMessage(), e);
            System.exit(1);
        }
    }

    /**
     * Validate the Android API level. rvsmart uses internal APIs that are
     * only validated against API 29 (Android 10). Other API levels may
     * have different reflection targets or hidden API restrictions.
     */
    private static void assertApiLevel() {
        int sdkInt = Build.VERSION.SDK_INT;
        if (sdkInt != REQUIRED_API_LEVEL) {
            Log.w(TAG, "API level " + sdkInt + " detected, expected "
                    + REQUIRED_API_LEVEL + ". Reflection targets may differ.");
        }
    }

    /**
     * Bootstrap all components and run the agent exploration loop.
     * Cleanup runs in a finally block to release resources on timeout or error.
     */
    private static void runAgent(CliArgs cli, Config config) {
        DeviceController devController = null;
        LogcatReader logcatReader = null;
        MetricsCollector metricsCollector = null;

        try {
            // 1. Device connection
            devController = new DeviceController();
            devController.connect();
            Log.i(TAG, "DeviceController connected");

            // 2. Device components
            UiCapture uiCapture = new UiCapture();
            InputInjector inputInjector = new InputInjector(
                    devController.getInputManager_(), devController.getInjectInputEventMethod());
            AppController appController = new AppController(devController.getActivityManager());
            CrashInterceptor crashInterceptor = new CrashInterceptor(cli.packageName);
            crashInterceptor.register(devController.getActivityManager());
            SystemDialogDetector dialogDetector = new SystemDialogDetector(inputInjector);

            // 3. Logcat reader (coverage tags from instrumented APKs)
            logcatReader = new LogcatReader(config.getLogcatBufferSize());
            logcatReader.start();

            // 4. Heap monitor
            HeapMonitor heapMonitor = new HeapMonitor(
                    config.getThrottleMs(), 2000, uiCapture);

            // 5. Graph and static data
            ContentGraph graph = new ContentGraph();
            StaticMap staticMap = new StaticMap(config.getStaticDataPath());
            staticMap.setCodePackage(config.getCodePackage());

            // 6. Strategy and recovery
            SuccessorTracker successorTracker = new SuccessorTracker(
                    config.getMaxReEnables(), config.getMultiValueSaturationThreshold());
            BacktrackBfs backtrackBfs = new BacktrackBfs();
            FrontierFinder frontierFinder = new FrontierFinder();
            ConfirmedCoverageScorer confirmedCoverageScorer = new ConfirmedCoverageScorer(
                    config.getConfirmedCoverageBase());
            InputValueGenerator inputValueGenerator = new InputValueGenerator();
            UICoverageTracker uiCoverageTracker = new UICoverageTracker();
            PlateauDetector plateauDetector = new PlateauDetector();
            ActionSelector actionSelector = new ActionSelector(config, successorTracker,
                    confirmedCoverageScorer, inputValueGenerator, uiCoverageTracker);
            StuckDetector stuckDetector = new StuckDetector(
                    config.getStuckMaxBlocks(), backtrackBfs, null,
                    frontierFinder, config.getFrontierCoverageThreshold());
            Learner learner = new Learner(graph, stuckDetector);

            // 7. Output
            TraceWriter traceWriter = new TraceWriter();
            metricsCollector = new MetricsCollector(
                    cli.packageName, config.getMode(), config.getTimeout());

            // 8. Bootstrap LLM components when mode requires them
            RoutingManager routingManager = null;
            SglangClient sglangClient = null;
            ToolCallParser toolCallParser = null;
            PromptBuilder promptBuilder = null;
            ImageProcessor imageProcessor = null;
            ScreenshotCapture screenshotCapture = null;

            String mode = config.getMode();
            if ("multimode".equals(mode) || "llm_only".equals(mode)) {
                Log.i(TAG, "Bootstrapping LLM components for mode=" + mode);
                sglangClient = new SglangClient(
                        config.getLlmBaseUrl(), config.getLlmModel(),
                        config.getLlmTemperature(), config.getLlmTopP(),
                        config.getLlmTopK(), config.getLlmMaxTokens(),
                        (int) (config.getLlmTimeoutS() * 1000));
                toolCallParser = new ToolCallParser();
                promptBuilder = new PromptBuilder();
                imageProcessor = new ImageProcessor();
                screenshotCapture = new ScreenshotCapture();
                LlmCircuitBreaker circuitBreaker = new LlmCircuitBreaker();
                RoutingManager.Mode routingMode = "llm_only".equals(mode)
                        ? RoutingManager.Mode.LLM_ONLY
                        : RoutingManager.Mode.MULTIMODE;
                long seed = config.getSeed() != null ? config.getSeed() : -1;
                RoutingManager.Strategy routingStrategy;
                switch (config.getLlmMultimodeStrategy()) {
                    case ARRIVAL_FIRST:   routingStrategy = RoutingManager.Strategy.ARRIVAL_FIRST; break;
                    case NEW_SCREEN_ONLY: routingStrategy = RoutingManager.Strategy.NEW_SCREEN_ONLY; break;
                    case STUCK_ONLY:      routingStrategy = RoutingManager.Strategy.STUCK_ONLY; break;
                    default:              routingStrategy = RoutingManager.Strategy.PROBABILISTIC; break;
                }
                routingManager = new RoutingManager(routingMode, routingStrategy,
                        config.getLlmProbability(), circuitBreaker, seed);
            }

            // 9. Start target app
            appController.startApp(cli.packageName);
            try { Thread.sleep(2000); } catch (InterruptedException e) { /* wait for app launch */ }

            // 10. Compute deadline and run
            long deadline = System.currentTimeMillis() + (config.getTimeout() * 1000L);
            AgentLoop loop = new AgentLoop(cli.packageName, deadline, config,
                    devController, uiCapture, inputInjector, appController,
                    crashInterceptor, dialogDetector, logcatReader,
                    heapMonitor, graph, staticMap, actionSelector,
                    stuckDetector, learner, traceWriter, metricsCollector,
                    routingManager, sglangClient, toolCallParser,
                    promptBuilder, imageProcessor, screenshotCapture,
                    confirmedCoverageScorer, successorTracker,
                    uiCoverageTracker, plateauDetector);

            Log.i(TAG, "AgentLoop starting, deadline in " + config.getTimeout() + "s");
            loop.run();

            // 10. Final metrics
            metricsCollector.recordCoverageEvent(
                    learner.getConfirmedMethods().size(),
                    learner.getTotalCoverageEvents(), 0);
            if (routingManager != null) {
                metricsCollector.setCircuitBreakerTrips(routingManager.getCircuitBreakerTripCount());
            }
            metricsCollector.writeFinalReport(loop.getStartTimeMs(), graph,
                    0, 0, learner.getUniqueActivities());

        } finally {
            if (logcatReader != null) logcatReader.stop();
            if (devController != null) devController.disconnect();
            Log.i(TAG, "Cleanup complete");
        }
    }

    /**
     * Quick validation: connect to services, capture one UI screen, report item count.
     * Exits with code 0 on success, 1 on failure.
     * Used by RVSmartTool for fast failure detection before full execution.
     */
    private static void runHealthCheck() {
        assertApiLevel();
        try {
            DeviceController dc = new DeviceController();
            dc.connect();

            UiCapture uiCapture = new UiCapture();
            AccessibilityNodeInfo root = dc.getUiAutomation().getRootInActiveWindow();
            if (root == null) {
                throw new RuntimeException("getRootInActiveWindow() returned null");
            }
            List<ScreenItem> items = uiCapture.capture(root);
            root.recycle();
            dc.disconnect();

            Log.i(TAG, "HEALTHCHECK OK: " + items.size() + " items");
            System.exit(0);
        } catch (Exception e) {
            Log.e(TAG, "Health check FAILED: " + e.getMessage());
            System.exit(1);
        }
    }

    /**
     * PoC test harness: bootstrap → capture UI → inject click → detect crash → print results.
     *
     * Validates all fundamental capabilities:
     *   1. ServiceManager connections (DeviceController)
     *   2. UI tree capture (UiCapture)
     *   3. Event injection (InputInjector)
     *   4. App lifecycle (AppController)
     *   5. Crash detection (CrashInterceptor)
     *
     * Run via: adb shell CLASSPATH=/data/local/tmp/rvsmart.jar \
     *          /system/bin/app_process /system/bin br.unb.cic.rvsmart.Main \
     *          --poc --package <pkg>
     */
    private static void runPoC(String packageName) {
        Log.i(TAG, "=== PoC Test Harness ===");

        // 1. Bootstrap DeviceController
        Log.i(TAG, "[1/5] Connecting to system services...");
        DeviceController dc = new DeviceController();
        dc.connect();
        Log.i(TAG, "[1/5] OK — ActivityManager, WindowManager, InputManager connected");

        // 2. Set up components
        AppController appCtrl = new AppController(dc.getActivityManager());
        InputInjector injector = new InputInjector(dc.getInputManager_(), dc.getInjectInputEventMethod());
        CrashInterceptor crashInterceptor = new CrashInterceptor(packageName);
        crashInterceptor.register(dc.getActivityManager());
        UiCapture uiCapture = new UiCapture();

        // 3. Start the target app
        Log.i(TAG, "[2/5] Starting target app: " + packageName);
        appCtrl.startApp(packageName);
        try { Thread.sleep(2000); } catch (InterruptedException e) { /* wait for app launch */ }

        // 4. Capture UI tree via UiAutomation.getRootInActiveWindow()
        Log.i(TAG, "[3/5] Capturing UI tree...");
        String activityName = appCtrl.getCurrentActivityName();
        Log.i(TAG, "  Current activity: " + activityName);

        AccessibilityNodeInfo root = dc.getUiAutomation().getRootInActiveWindow();
        List<ScreenItem> items = uiCapture.capture(root);
        Log.i(TAG, "  Captured " + items.size() + " items from accessibility tree");

        // Dump resource IDs for Task 2.8 validation
        for (int i = 0; i < Math.min(items.size(), 20); i++) {
            ScreenItem item = items.get(i);
            Log.i(TAG, "  [" + i + "] " + item.getClassName()
                    + " resId=" + item.getResourceId()
                    + " text=" + item.getText()
                    + " bounds=" + item.getBounds()
                    + " click=" + item.isClickable());
        }
        if (items.size() > 20) {
            Log.i(TAG, "  ... and " + (items.size() - 20) + " more items");
        }

        // Recycle root node
        if (root != null) {
            root.recycle();
        }

        // 5. Test event injection
        Log.i(TAG, "[4/5] Testing event injection...");
        long injectStart = System.nanoTime();
        boolean clickResult = injector.click(540, 960);  // Center of 1080x1920
        long injectTime = (System.nanoTime() - injectStart) / 1_000_000;
        Log.i(TAG, "  Click injection: " + (clickResult ? "OK" : "FAILED") + " (" + injectTime + "ms)");

        boolean backResult = injector.pressBack();
        Log.i(TAG, "  Back key injection: " + (backResult ? "OK" : "FAILED"));

        // 6. Test crash detection
        Log.i(TAG, "[5/5] Crash interceptor status: " + (crashInterceptor.hasCrash() ? "CRASH PENDING" : "no crash"));

        // 7. Test app lifecycle
        Log.i(TAG, "  App running: " + appCtrl.isAppRunning(packageName));
        Log.i(TAG, "  Force-stopping...");
        appCtrl.forceStop(packageName);
        try { Thread.sleep(500); } catch (InterruptedException e) { /* wait */ }
        Log.i(TAG, "  App running after stop: " + appCtrl.isAppRunning(packageName));
        appCtrl.startApp(packageName);
        try { Thread.sleep(1000); } catch (InterruptedException e) { /* wait */ }
        Log.i(TAG, "  App running after restart: " + appCtrl.isAppRunning(packageName));

        Log.i(TAG, "=== PoC Test Harness Complete ===");
        System.exit(0);
    }

    /**
     * Go/No-Go benchmark: 1000 UI captures + 1000 event injections.
     * Collects latency and success metrics, prints results table.
     */
    private static void runBenchmark(String packageName) {
        DeviceController dc = new DeviceController();
        dc.connect();

        AppController appCtrl = new AppController(dc.getActivityManager());
        InputInjector injector = new InputInjector(dc.getInputManager_(), dc.getInjectInputEventMethod());
        CrashInterceptor crashInterceptor = new CrashInterceptor(packageName);
        crashInterceptor.register(dc.getActivityManager());
        UiCapture uiCapture = new UiCapture();

        // Start the target app
        appCtrl.startApp(packageName);
        try { Thread.sleep(2000); } catch (InterruptedException e) { /* wait for app launch */ }

        PocBenchmark benchmark = new PocBenchmark(dc, appCtrl, injector,
                crashInterceptor, uiCapture, packageName);
        benchmark.run();

        dc.disconnect();
        System.exit(0);
    }

    private static Config loadConfig(CliArgs cli) {
        Config config;
        if (cli.configPath != null) {
            config = Config.fromFile(new File(cli.configPath));
        } else {
            config = Config.defaults();
        }
        // Override with CLI args
        config.setPackageName(cli.packageName);
        config.setTimeout(cli.timeout);
        config.setMode(cli.mode);
        if (cli.seed != null) {
            config.setSeed(cli.seed);
        }
        if (cli.staticDataPath != null) {
            config.setStaticDataPath(cli.staticDataPath);
        }
        if (cli.codePackage != null) {
            config.setCodePackage(cli.codePackage);
        } else {
            config.setCodePackage(cli.packageName);
            Log.w(TAG, "No --code-package provided. MOP scoring may be inaccurate for multi-package apps.");
        }
        return config;
    }

    static CliArgs parseArgs(String[] args) {
        CliArgs cli = new CliArgs();

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--package":
                    cli.packageName = requireArg(args, ++i, "--package");
                    break;
                case "--timeout":
                    cli.timeout = Integer.parseInt(requireArg(args, ++i, "--timeout"));
                    break;
                case "--static-data":
                    cli.staticDataPath = requireArg(args, ++i, "--static-data");
                    break;
                case "--config":
                    cli.configPath = requireArg(args, ++i, "--config");
                    break;
                case "--mode":
                    cli.mode = requireArg(args, ++i, "--mode");
                    break;
                case "--seed":
                    cli.seed = Integer.parseInt(requireArg(args, ++i, "--seed"));
                    break;
                case "--code-package":
                    cli.codePackage = requireArg(args, ++i, "--code-package");
                    break;
                case "--health-check":
                    cli.healthCheck = true;
                    break;
                case "--poc":
                    cli.pocMode = true;
                    break;
                case "--benchmark":
                    cli.benchmarkMode = true;
                    break;
                default:
                    throw new IllegalArgumentException("Unknown argument: " + args[i]);
            }
        }

        if (!cli.healthCheck) {
            if (cli.packageName == null) {
                throw new IllegalArgumentException("--package is required");
            }
            if (!cli.pocMode && !cli.benchmarkMode && cli.timeout <= 0) {
                throw new IllegalArgumentException("--timeout must be positive");
            }
        }

        return cli;
    }

    private static String requireArg(String[] args, int index, String flag) {
        if (index >= args.length) {
            throw new IllegalArgumentException(flag + " requires a value");
        }
        return args[index];
    }

    static class CliArgs {
        String packageName;
        int timeout;
        String staticDataPath;
        String configPath;
        String mode = "pure_algorithm";
        Integer seed;
        String codePackage;
        boolean healthCheck;
        boolean pocMode;
        boolean benchmarkMode;
    }
}
