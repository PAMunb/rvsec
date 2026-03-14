package br.unb.cic.rvsmart.core;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

/**
 * Configuration loaded from java.util.Properties file.
 * All ~48 parameters have internal defaults; the properties file
 * overrides only the values it contains.
 */
public class Config {

    private final Properties props;

    // CLI-injected values (not from properties file)
    private String packageName;
    private int timeout;
    private String mode = "pure_algorithm";
    private Integer seed;
    private String staticDataPath;
    private String codePackage;

    // --- Execution (4) ---
    private static final int DEFAULT_THROTTLE_MS = 50;
    private static final int DEFAULT_MAX_RETRIES_PER_CYCLE = 1;
    private static final int DEFAULT_ADAPTIVE_WAIT_MS = 150;

    // --- Routing (2) ---
    private static final float DEFAULT_LLM_PROBABILITY = 0.05f;
    private static final float DEFAULT_LLM_NEW_SCREEN_PHASE2_PROBABILITY = 0.30f;

    /**
     * Prompt template versions matching RVAgent's versioning (v12–v17).
     * V13 and V17 are fully implemented. V12/V14/V15/V16 fall back to V13 at runtime.
     * Use V17 for MOP-aware exploration with test-status tags, scores, and action history.
     */
    public enum PromptVersion { V12, V13, V14, V15, V16, V17 }

    /** Multimode routing strategies. */
    public enum MultimodeStrategy { PROBABILISTIC, NEW_SCREEN_ONLY, STUCK_ONLY, ARRIVAL_FIRST }

    // --- Scorer weights (13) ---
    private static final float DEFAULT_MOP_DIRECT_SCORE = 500.0f;
    private static final float DEFAULT_MOP_TRANSITIVE_SCORE = 300.0f;
    private static final float DEFAULT_WTG_GUIDED_SCORE = 150.0f;
    private static final float DEFAULT_GRADUAL_DECAY_BASE = 200.0f;
    private static final float DEFAULT_GRADUAL_DECAY_RATE = 0.7f;
    private static final int DEFAULT_GRADUAL_DECAY_MIN_VISITS = 5;
    private static final float DEFAULT_COVERAGE_DENSITY_WEIGHT = 200.0f;
    private static final float DEFAULT_SATURATION_BONUS = 100.0f;
    private static final float DEFAULT_COMPONENT_HIGH_PRIORITY = 50.0f;
    private static final float DEFAULT_COMPONENT_MEDIUM_PRIORITY = 40.0f;
    private static final float DEFAULT_STRENGTH_WEIGHT = 50.0f;
    private static final float DEFAULT_VISITATION_PENALTY_FACTOR = 15.0f;
    private static final float DEFAULT_UCB_C = 150.0f;

    // --- Synthetic actions (3) ---
    private static final float DEFAULT_BACK_BASE_SCORE = 50.0f;
    private static final float DEFAULT_RESTART_BASE_SCORE = -500.0f;
    private static final float DEFAULT_BACK_DECAY_PER_REPEAT = 30.0f;

    // --- Menu fuzz (1) ---
    private static final float DEFAULT_MENU_FUZZ_RATE = 0.02f;

    // --- Periodic restart (1) ---
    private static final int DEFAULT_PERIODIC_RESTART_THRESHOLD = 200;

    // --- State refresh (1) ---
    private static final int DEFAULT_CAPTURE_RETRY_MIN_ELEMENTS = 3;
    private static final int DEFAULT_CAPTURE_RETRY_MAX = 3;
    private static final long DEFAULT_CAPTURE_RETRY_DELAY_MS = 1000;

    // --- Stochastic selection (1) ---
    private static final float DEFAULT_STOCHASTIC_PROBABILITY = 0.15f;

    // --- Successor tracker (3) ---
    private static final int DEFAULT_MAX_RE_ENABLES = 6;
    private static final int DEFAULT_MULTI_VALUE_SATURATION_THRESHOLD = 6;
    private static final float DEFAULT_UI_COVERAGE_THRESHOLD = 0.8f;

    // --- Out-of-app detection (1) ---
    private static final int DEFAULT_OUT_OF_APP_TOLERANCE = 3;

    // --- Stuck detection (3) ---
    private static final int DEFAULT_STUCK_MAX_BLOCKS = 7;
    private static final int DEFAULT_MAX_BACKTRACK_FAILURES = 5;
    private static final float DEFAULT_BACKTRACK_SATURATION_THRESHOLD = 0.8f;

    // --- Track B: retry gate, sterile, frontier (3) ---
    private static final float DEFAULT_RETRY_SATURATION_THRESHOLD = 0.95f;
    private static final int DEFAULT_STERILE_THRESHOLD = 3;
    private static final float DEFAULT_FRONTIER_COVERAGE_THRESHOLD = 0.8f;

    // --- Track B2: activity budget (2) ---
    private static final int DEFAULT_ACTIVITY_BASE_BUDGET = 999_999;
    private static final int DEFAULT_BUDGET_PER_WIDGET = 3;

    // --- Track B2: tarpit detection (1) ---
    private static final int DEFAULT_TARPIT_THRESHOLD = 50;

    // --- MOP navigation (3) ---
    private static final float DEFAULT_MOP_NAV_WEIGHT = 2.0f;
    private static final int DEFAULT_MOP_MAX_INPUT_VARIATIONS = 5;
    private static final float DEFAULT_CONFIRMED_COVERAGE_WINDOW_S = 2.0f;
    private static final int DEFAULT_CONFIRMED_COVERAGE_BASE = 150;

    // --- LLM inference (7) ---
    private static final String DEFAULT_LLM_BASE_URL = "http://192.168.0.36:30000/v1";
    private static final String DEFAULT_LLM_MODEL = "Qwen/Qwen3-VL-4B-Instruct";
    private static final float DEFAULT_LLM_TEMPERATURE = 0.01f;
    private static final float DEFAULT_LLM_TOP_P = 0.6f;
    private static final int DEFAULT_LLM_TOP_K = 50;
    private static final int DEFAULT_LLM_MAX_TOKENS = 2048;
    private static final float DEFAULT_LLM_TIMEOUT_S = 30.0f;

    // --- Logcat (1) ---
    private static final int DEFAULT_LOGCAT_BUFFER_SIZE = 10000;

    private Config(Properties props) {
        this.props = props;
    }

    public static Config defaults() {
        return new Config(new Properties());
    }

    public static Config fromFile(File file) {
        Properties props = new Properties();
        try (FileInputStream fis = new FileInputStream(file)) {
            props.load(fis);
        } catch (IOException e) {
            throw new RuntimeException("Failed to load config from " + file.getAbsolutePath(), e);
        }
        return new Config(props);
    }

    // --- CLI-injected getters/setters ---

    public String getPackageName() { return packageName; }
    public void setPackageName(String packageName) { this.packageName = packageName; }

    public int getTimeout() { return timeout; }
    public void setTimeout(int timeout) { this.timeout = timeout; }

    public String getMode() { return mode; }
    public void setMode(String mode) { this.mode = mode; }

    public Integer getSeed() { return seed; }
    public void setSeed(Integer seed) { this.seed = seed; }

    public String getStaticDataPath() { return staticDataPath; }
    public void setStaticDataPath(String staticDataPath) { this.staticDataPath = staticDataPath; }

    public String getCodePackage() { return codePackage; }
    public void setCodePackage(String codePackage) { this.codePackage = codePackage; }

    // --- Execution ---
    public int getThrottleMs() { return getInt("throttle_ms", DEFAULT_THROTTLE_MS); }
    public int getMaxRetriesPerCycle() { return getInt("max_retries_per_cycle", DEFAULT_MAX_RETRIES_PER_CYCLE); }
    public int getAdaptiveWaitMs() { return getInt("adaptive_wait_ms", DEFAULT_ADAPTIVE_WAIT_MS); }

    // --- Routing ---
    public float getLlmProbability() { return getFloat("llm_probability", DEFAULT_LLM_PROBABILITY); }
    public float getLlmNewScreenPhase2Probability() { return getFloat("llm_new_screen_phase2_probability", DEFAULT_LLM_NEW_SCREEN_PHASE2_PROBABILITY); }

    public PromptVersion getLlmPromptVersion() {
        String val = props.getProperty("llm_prompt_version");
        if (val == null) return PromptVersion.V13;
        switch (val.trim().toLowerCase()) {
            case "v12": return PromptVersion.V12;
            case "v14": return PromptVersion.V14;
            case "v15": return PromptVersion.V15;
            case "v16": return PromptVersion.V16;
            case "v17": return PromptVersion.V17;
            default:    return PromptVersion.V13;
        }
    }

    public MultimodeStrategy getLlmMultimodeStrategy() {
        String val = props.getProperty("llm_multimode_strategy");
        if (val == null) return MultimodeStrategy.PROBABILISTIC;
        switch (val.trim().toLowerCase()) {
            case "new_screen_only": return MultimodeStrategy.NEW_SCREEN_ONLY;
            case "stuck_only":      return MultimodeStrategy.STUCK_ONLY;
            case "arrival_first":   return MultimodeStrategy.ARRIVAL_FIRST;
            default:                return MultimodeStrategy.PROBABILISTIC;
        }
    }

    // --- Scorer weights ---
    public float getMopDirectScore() { return getFloat("mop_direct_score", DEFAULT_MOP_DIRECT_SCORE); }
    public float getMopTransitiveScore() { return getFloat("mop_transitive_score", DEFAULT_MOP_TRANSITIVE_SCORE); }
    public float getWtgGuidedScore() { return getFloat("wtg_guided_score", DEFAULT_WTG_GUIDED_SCORE); }
    public float getGradualDecayBase() { return getFloat("gradual_decay_base", DEFAULT_GRADUAL_DECAY_BASE); }
    public float getGradualDecayRate() { return getFloat("gradual_decay_rate", DEFAULT_GRADUAL_DECAY_RATE); }
    public int getGradualDecayMinVisits() { return getInt("gradual_decay_min_visits", DEFAULT_GRADUAL_DECAY_MIN_VISITS); }
    public float getCoverageDensityWeight() { return getFloat("coverage_density_weight", DEFAULT_COVERAGE_DENSITY_WEIGHT); }
    public float getSaturationBonus() { return getFloat("saturation_bonus", DEFAULT_SATURATION_BONUS); }
    public float getComponentHighPriority() { return getFloat("component_high_priority", DEFAULT_COMPONENT_HIGH_PRIORITY); }
    public float getComponentMediumPriority() { return getFloat("component_medium_priority", DEFAULT_COMPONENT_MEDIUM_PRIORITY); }
    public float getStrengthWeight() { return getFloat("strength_weight", DEFAULT_STRENGTH_WEIGHT); }
    public float getVisitationPenaltyFactor() { return getFloat("visitation_penalty_factor", DEFAULT_VISITATION_PENALTY_FACTOR); }
    public float getUcbC() { return getFloat("ucb_c", DEFAULT_UCB_C); }

    // --- Synthetic actions ---
    public float getBackBaseScore() { return getFloat("back_base_score", DEFAULT_BACK_BASE_SCORE); }
    public float getRestartBaseScore() { return getFloat("restart_base_score", DEFAULT_RESTART_BASE_SCORE); }
    public float getBackDecayPerRepeat() { return getFloat("back_decay_per_repeat", DEFAULT_BACK_DECAY_PER_REPEAT); }

    // --- Stochastic selection ---
    public float getStochasticProbability() {
        if (stochasticProbabilityOverride != null) return stochasticProbabilityOverride;
        return getFloat("stochastic_probability", DEFAULT_STOCHASTIC_PROBABILITY);
    }
    private Float stochasticProbabilityOverride;
    public void setStochasticProbability(float value) { this.stochasticProbabilityOverride = value; }

    // --- Successor tracker ---
    public int getMaxReEnables() { return getInt("max_re_enables", DEFAULT_MAX_RE_ENABLES); }
    public int getMultiValueSaturationThreshold() { return getInt("multi_value_saturation_threshold", DEFAULT_MULTI_VALUE_SATURATION_THRESHOLD); }
    public float getUiCoverageThreshold() { return getFloat("ui_coverage_threshold", DEFAULT_UI_COVERAGE_THRESHOLD); }

    // --- Stuck detection ---
    public int getStuckMaxBlocks() { return getInt("stuck_max_blocks", DEFAULT_STUCK_MAX_BLOCKS); }
    public int getMaxBacktrackFailures() { return getInt("max_backtrack_failures", DEFAULT_MAX_BACKTRACK_FAILURES); }
    public float getBacktrackSaturationThreshold() { return getFloat("backtrack_saturation_threshold", DEFAULT_BACKTRACK_SATURATION_THRESHOLD); }

    // --- Track B: retry gate, sterile, frontier ---
    public float getRetrySaturationThreshold() { return getFloat("retry_saturation_threshold", DEFAULT_RETRY_SATURATION_THRESHOLD); }
    public int getSterileThreshold() { return getInt("sterile_threshold", DEFAULT_STERILE_THRESHOLD); }
    public float getFrontierCoverageThreshold() { return getFloat("frontier_coverage_threshold", DEFAULT_FRONTIER_COVERAGE_THRESHOLD); }

    // --- Track B2: activity budget ---
    public int getActivityBaseBudget() { return getInt("activity_base_budget", DEFAULT_ACTIVITY_BASE_BUDGET); }
    public int getBudgetPerWidget() { return getInt("budget_per_widget", DEFAULT_BUDGET_PER_WIDGET); }

    // --- Track B2: tarpit detection ---
    public int getTarpitThreshold() { return getInt("tarpit_threshold", DEFAULT_TARPIT_THRESHOLD); }

    // --- MOP navigation ---
    public float getMopNavWeight() { return getFloat("mop_nav_weight", DEFAULT_MOP_NAV_WEIGHT); }
    public int getMopMaxInputVariations() { return getInt("mop_max_input_variations", DEFAULT_MOP_MAX_INPUT_VARIATIONS); }
    public float getConfirmedCoverageWindowS() { return getFloat("confirmed_coverage_window_s", DEFAULT_CONFIRMED_COVERAGE_WINDOW_S); }
    public int getConfirmedCoverageBase() { return getInt("confirmed_coverage_base", DEFAULT_CONFIRMED_COVERAGE_BASE); }

    // --- LLM inference ---
    public String getLlmBaseUrl() { return getString("llm_base_url", DEFAULT_LLM_BASE_URL); }
    public String getLlmModel() { return getString("llm_model", DEFAULT_LLM_MODEL); }
    public float getLlmTemperature() { return getFloat("llm_temperature", DEFAULT_LLM_TEMPERATURE); }
    public float getLlmTopP() { return getFloat("llm_top_p", DEFAULT_LLM_TOP_P); }
    public int getLlmTopK() { return getInt("llm_top_k", DEFAULT_LLM_TOP_K); }
    public int getLlmMaxTokens() { return getInt("llm_max_tokens", DEFAULT_LLM_MAX_TOKENS); }
    public float getLlmTimeoutS() { return getFloat("llm_timeout_s", DEFAULT_LLM_TIMEOUT_S); }

    // --- Out-of-app detection ---
    public int getOutOfAppTolerance() { return getInt("out_of_app_tolerance", DEFAULT_OUT_OF_APP_TOLERANCE); }

    // --- Logcat ---
    public int getLogcatBufferSize() { return getInt("logcat_buffer_size", DEFAULT_LOGCAT_BUFFER_SIZE); }

    // --- Menu fuzz ---
    public float getMenuFuzzRate() { return getFloat("menu_fuzz_rate", DEFAULT_MENU_FUZZ_RATE); }

    // --- Periodic restart ---
    public int getPeriodicRestartThreshold() { return getInt("periodic_restart_threshold", DEFAULT_PERIODIC_RESTART_THRESHOLD); }

    // --- State refresh ---
    public int getCaptureRetryMinElements() { return getInt("capture_retry_min_elements", DEFAULT_CAPTURE_RETRY_MIN_ELEMENTS); }
    public int getCaptureRetryMax() { return getInt("capture_retry_max", DEFAULT_CAPTURE_RETRY_MAX); }
    public long getCaptureRetryDelayMs() { return getLong("capture_retry_delay_ms", DEFAULT_CAPTURE_RETRY_DELAY_MS); }

    // --- Typed property accessors ---

    private int getInt(String key, int defaultValue) {
        String val = props.getProperty(key);
        return val != null ? Integer.parseInt(val.trim()) : defaultValue;
    }

    private float getFloat(String key, float defaultValue) {
        String val = props.getProperty(key);
        return val != null ? Float.parseFloat(val.trim()) : defaultValue;
    }

    private long getLong(String key, long defaultValue) {
        String val = props.getProperty(key);
        return val != null ? Long.parseLong(val.trim()) : defaultValue;
    }

    private String getString(String key, String defaultValue) {
        return props.getProperty(key, defaultValue);
    }
}
