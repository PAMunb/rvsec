package br.unb.cic.rvsmart.strategy;

import android.graphics.Rect;
import android.util.Log;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.graph.ScreenNode;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.scorers.ComponentPriorityScorer;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;
import br.unb.cic.rvsmart.strategy.scorers.CoverageDensityScorer;
import br.unb.cic.rvsmart.strategy.scorers.GradualDecayScorer;
import br.unb.cic.rvsmart.strategy.scorers.MopScorer;

import br.unb.cic.rvsmart.strategy.scorers.Scorer;
import br.unb.cic.rvsmart.strategy.scorers.SystemElementFilter;
import br.unb.cic.rvsmart.strategy.scorers.WtgScorer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Selects the next action to execute on the current screen using a 4-tier priority system.
 *
 * Tier 1 (PathBuffer): if a planned backtrack path is active, dispense the next BACK.
 * Tier 2 (untested actions): prefer actions never executed on this screen.
 * Tier 3 (proactive backtrack): when all candidates score below saturation threshold,
 *   trigger a BACK toward a less-visited parent state.
 * Tier 4 (unified queue): all widgets + BACK + RESTART, scored and sorted.
 *
 * selectAction() NEVER returns null (INV-RSM-12): at minimum, RESTART is always present
 * in Tier 4. BACK is excluded on root screens (no parents in SuccessorTracker) to
 * prevent the agent from exiting the app.
 *
 * Scoring uses 6 pluggable scorers (additive):
 *   1. MopScorer: static analysis reachability (+500 direct, +300 transitive)
 *   2. GradualDecayScorer: visit-based decay (200->0 over configured visits)
 *   3. SystemElementFilter: system UI penalty (-5000)
 *   4. ComponentPriorityScorer: action type priority (SET_TEXT=200, CLICK=100, SCROLL=25)
 *   5. WtgScorer: activity-level BFS on WTG transitions (+200/+100/+50 by hop depth)
 *   6. ConfirmedCoverageScorer: boosts screens with confirmed MOP coverage (+150)
 *
 * Scorers NOT included (evaluated and excluded):
 *   - VisitationPenaltyScorer: redundant with GradualDecayScorer (both penalize revisits)
 *   - CoverageDensityScorer: redundant with MopScorer (hardcoded count=1 makes it a constant)
 *   - SaturationScorer: screen-level penalty — handled by proactive backtrack (Tier 3) instead
 *   - StrengthScorer: master aggregator with weights — keeping chain simple and additive
 *
 * After scoring, stochastic selection (default 15%) picks a random action instead
 * of the top-scored one, preventing deterministic loops.
 *
 * BACK actions use per-hash decay: each ineffective BACK (no screen change) on the same
 * screen increases the penalty, discouraging repeated BACKs on stuck screens.
 */
public class ActionSelector {

    private static final String TAG = "RVSMART";
    private static final String ALGORITHM_SOURCE = "algorithm";
    private static final double SOFTMAX_TEMPERATURE = 50.0;

    private final List<Scorer> scorers;
    private final float backBaseScore;
    private final float backDecayPerRepeat;
    private final float restartBaseScore;
    private final float stochasticProbability;
    private final Random random;
    private final InputValueGenerator inputValueGenerator;

    // Per-hash count of ineffective BACK presses (no screen change)
    private final Map<String, Integer> backDecayCountPerHash;

    // Plateau mode: when active, stochastic probability is boosted to 0.5
    private static final float PLATEAU_STOCHASTIC_PROBABILITY = 0.5f;
    private boolean plateauActive;

    // Last selected tier (1-4), exposed for trace observability
    private int lastSelectedTier;

    // Last score breakdown for trace observability (per-scorer contributions)
    private Map<String, Object> lastScoreBreakdown;

    // Phase 2 dependencies: PathBuffer (Tier 1) and SuccessorTracker (Tier 3)
    private final PathBuffer pathBuffer;
    private final SuccessorTracker successorTracker;

    public ActionSelector(Config config) {
        this(config, null, null, null, null, null);
    }

    public ActionSelector(Config config, PathBuffer pathBuffer, SuccessorTracker successorTracker) {
        this(config, pathBuffer, successorTracker, null, null, null);
    }

    public ActionSelector(Config config, PathBuffer pathBuffer, SuccessorTracker successorTracker,
                          ConfirmedCoverageScorer confirmedCoverageScorer) {
        this(config, pathBuffer, successorTracker, confirmedCoverageScorer, null, null);
    }

    /**
     * Full constructor with all optional dependencies.
     *
     * @param confirmedCoverageScorer shared instance also used by AgentLoop for addConfirmed() calls;
     *                                 null to skip confirmed-coverage scoring
     * @param inputValueGenerator generates context-aware text input for SET_TEXT actions;
     *                             null to use default "test" string
     * @param uiCoverageTracker shared instance for coverage-density scoring;
     *                           null to disable CoverageDensityScorer
     */
    public ActionSelector(Config config, PathBuffer pathBuffer, SuccessorTracker successorTracker,
                          ConfirmedCoverageScorer confirmedCoverageScorer,
                          InputValueGenerator inputValueGenerator,
                          UICoverageTracker uiCoverageTracker) {
        this.scorers = new ArrayList<>();
        this.scorers.add(new MopScorer(
                (int) config.getMopDirectScore(),
                (int) config.getMopTransitiveScore()));
        this.scorers.add(new GradualDecayScorer(
                (int) config.getGradualDecayBase(),
                config.getGradualDecayRate(),
                config.getGradualDecayMinVisits()));
        this.scorers.add(new SystemElementFilter());
        this.scorers.add(new ComponentPriorityScorer());
        this.scorers.add(new WtgScorer());
        if (uiCoverageTracker != null) {
            this.scorers.add(new CoverageDensityScorer(100, uiCoverageTracker));
        }
        if (confirmedCoverageScorer != null) {
            this.scorers.add(confirmedCoverageScorer);
        }

        this.backBaseScore = config.getBackBaseScore();
        this.backDecayPerRepeat = config.getBackDecayPerRepeat();
        this.restartBaseScore = config.getRestartBaseScore();
        this.stochasticProbability = config.getStochasticProbability();
        this.random = config.getSeed() != null ? new Random(config.getSeed()) : new Random();

        this.backDecayCountPerHash = new HashMap<>();
        this.pathBuffer = pathBuffer;
        this.successorTracker = successorTracker;
        this.inputValueGenerator = inputValueGenerator;
    }

    /**
     * Select the best action to execute on the current screen.
     * Uses a 4-tier priority system.
     *
     * @return selected action, NEVER null (INV-RSM-12)
     */
    public Action selectAction(ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        String hash = screen.getHash();
        ScreenNode node = graph.get(hash);

        // Invalidate PathBuffer if the agent diverged from the planned route
        if (pathBuffer != null) {
            pathBuffer.invalidateIfDiverged(hash);
        }

        // TIER 1: PathBuffer — if a planned backtrack path is active, follow it
        if (pathBuffer != null && pathBuffer.hasPath()) {
            Action action = pathBuffer.consumeNext(hash);
            if (action != null) {
                lastSelectedTier = 1;
                lastScoreBreakdown = null;
                RvTrack.strategy(0, 1, "path_buffer", 0, 0.0);
                return action;
            }
            // Path invalidated due to position mismatch — fall through to Tier 2
        }

        // TIER 2: Untested actions — prefer actions never executed on this screen
        List<Action> candidates = generateCandidateActions(screen);

        // Filter out actions with 3+ failures to avoid wasting budget on known-bad elements.
        // Safety net: if filtering would empty the list, keep unfiltered candidates — the agent
        // must always have widget actions available to avoid falling through to RESTART-only.
        if (node != null) {
            final ScreenNode nodeRef = node;
            List<Action> filtered = candidates.stream()
                    .filter(a -> getFailureCount(nodeRef, a.signature()) < 3)
                    .collect(Collectors.toList());
            if (!filtered.isEmpty()) {
                candidates = filtered;
            } else if (!candidates.isEmpty()) {
                if (RvTrack.logEnabled) {
                    Log.w(TAG, "Failure filter would empty candidates on " + hash
                            + ", keeping " + candidates.size() + " unfiltered");
                }
            }
        }

        List<Action> untested = filterUntested(candidates, node);

        if (!untested.isEmpty()) {
            lastSelectedTier = 2;
            double saturation = node != null ? node.getSaturationRate() : 0.0;
            RvTrack.strategy(0, 2, "untested", untested.size(), saturation);
            return selectBestScored(untested, screen, graph, staticMap);
        }

        // TIER 3: Proactive backtrack — when screen is saturated (>= 0.8),
        // return BACK toward a parent state. Self-calibrating: depends only on
        // how many actions have been tried, not on scorer weights.
        if (successorTracker != null && node != null && node.getSaturationRate() >= 0.8f) {
            Set<String> parents = successorTracker.getParents(hash);
            if (!parents.isEmpty()) {
                // Prefer a re-enabled parent, otherwise any parent
                for (String parent : parents) {
                    if (successorTracker.isReEnabled(parent)) {
                        successorTracker.consumeReEnable(parent);
                        lastSelectedTier = 3;
                        RvTrack.strategy(0, 3, "re_enabled_parent", 0, node.getSaturationRate());
                        return Action.back(ALGORITHM_SOURCE);
                    }
                }
                lastSelectedTier = 3;
                RvTrack.strategy(0, 3, "saturated", 0, node.getSaturationRate());
                return Action.back(ALGORITHM_SOURCE);
            }
        }

        // TIER 4: Unified priority queue (all widgets + BACK + RESTART)
        lastSelectedTier = 4;
        double saturation = node != null ? node.getSaturationRate() : 0.0;
        RvTrack.strategy(0, 4, "unified_queue", candidates.size(), saturation);
        return selectFromUnifiedQueue(candidates, screen, graph, staticMap, hash);
    }

    /**
     * Select the next best action excluding previously failed signatures.
     * Used for multi-attempt retries within a single cycle.
     *
     * @param excludeSignatures action signatures to skip (already attempted)
     * @return best alternative action, or null if no candidates remain
     */
    public Action selectNextBest(ScreenState screen, Set<String> excludeSignatures,
                                 DynamicStateGraph graph, StaticMap staticMap) {
        String hash = screen.getHash();
        ScreenNode node = graph.get(hash);

        List<Action> candidates = generateCandidateActions(screen);

        // Only add BACK when not on root screen (same check as Tier 4)
        boolean isRootScreen = successorTracker == null
                || successorTracker.getParents(hash).isEmpty();
        if (!isRootScreen) {
            candidates.add(Action.back(ALGORITHM_SOURCE));
        }
        candidates.add(Action.restart(ALGORITHM_SOURCE));

        // Filter out excluded signatures and actions with >= 3 consecutive failures
        candidates = candidates.stream()
                .filter(a -> !excludeSignatures.contains(a.signature()))
                .filter(a -> node == null || getFailureCount(node, a.signature()) < 3)
                .collect(Collectors.toList());

        // If PathBuffer has an active plan, only allow BACK/RESTART to protect the route
        if (pathBuffer != null && pathBuffer.hasPath()) {
            candidates = candidates.stream()
                    .filter(a -> a.getType() == Action.Type.BACK || a.getType() == Action.Type.RESTART)
                    .collect(Collectors.toList());
        }

        if (candidates.isEmpty()) return null;

        // Score and sort
        Map<Action, Integer> scores = new HashMap<>();
        for (Action action : candidates) {
            if (action.getType() == Action.Type.BACK) {
                int backDecay = backDecayCountPerHash.getOrDefault(hash, 0);
                scores.put(action, (int) (backBaseScore - (backDecay * backDecayPerRepeat)));
            } else if (action.getType() == Action.Type.RESTART) {
                scores.put(action, (int) restartBaseScore);
            } else {
                int score = 0;
                for (Scorer scorer : scorers) {
                    score += scorer.score(action, screen, graph, staticMap);
                }
                scores.put(action, score);
            }
        }

        candidates.sort((a, b) -> Integer.compare(
                scores.getOrDefault(b, 0), scores.getOrDefault(a, 0)));

        Action selected = candidates.get(0);
        RvTrack.rank(0, "retry: " + selected.getType() + "="
                + scores.getOrDefault(selected, 0)
                + " candidates=" + candidates.size()
                + " excluded=" + excludeSignatures.size());
        return selected;
    }

    public int getLastSelectedTier() {
        return lastSelectedTier;
    }

    /**
     * Get the score breakdown for the last selected action.
     * Contains per-scorer contributions, total, and stochastic flag.
     */
    public Map<String, Object> getLastScoreBreakdown() {
        return lastScoreBreakdown;
    }

    /**
     * Update BACK decay state after action execution.
     * Ineffective BACKs (no screen change) increase the per-hash penalty.
     * Effective BACKs reset the counter for that hash.
     *
     * @param wasBack    true if the executed action was BACK
     * @param hadEffect  true if screen hash changed after action
     * @param screenHash the screen hash BEFORE the action
     */
    public void updateBackDecay(boolean wasBack, boolean hadEffect, String screenHash) {
        if (wasBack && !hadEffect) {
            backDecayCountPerHash.merge(screenHash, 1, Integer::sum);
        } else if (wasBack && hadEffect) {
            backDecayCountPerHash.put(screenHash, 0);
        }
    }

    /**
     * Get the BACK decay count for a specific screen hash. Used for testing.
     */
    public int getBackDecayCount(String hash) {
        return backDecayCountPerHash.getOrDefault(hash, 0);
    }

    /**
     * Set plateau mode. When active, stochastic probability is boosted to 0.5
     * to escape local optima detected by PlateauDetector.
     */
    public void setPlateauActive(boolean active) {
        this.plateauActive = active;
    }

    public boolean isPlateauActive() {
        return plateauActive;
    }

    /**
     * Get the effective stochastic probability, accounting for plateau mode.
     */
    private float getEffectiveStochasticProbability() {
        return plateauActive ? PLATEAU_STOCHASTIC_PROBABILITY : stochasticProbability;
    }

    /**
     * Get the scorer chain. Used for testing to verify which scorers are active.
     */
    public List<Scorer> getScorers() {
        return scorers;
    }

    // --- Private methods ---

    /**
     * Generate candidate actions from screen items.
     * Creates CLICK for clickable items, LONG_CLICK for long-clickable items,
     * and SET_TEXT for editable items. Coordinates are the center of the item bounds.
     * Filters out system UI elements (com.android.systemui package).
     * Package-private for testing.
     */
    List<Action> generateCandidateActions(ScreenState screen) {
        List<Action> actions = new ArrayList<>();

        for (ScreenItem item : screen.getItems()) {
            if (!item.isEnabled()) continue;

            // Filter out system UI elements (e.g., status bar, navigation bar)
            // that belong to Android's system UI package (INV-RSM-27)
            String pkg = item.getPackageName();
            if ("com.android.systemui".equals(pkg)) continue;

            Rect bounds = item.getBounds();
            if (bounds == null) continue;

            int centerX = bounds.centerX();
            int centerY = bounds.centerY();
            String widgetClass = simpleName(item.getClassName());

            if (item.isClickable()) {
                actions.add(new Action(Action.Type.CLICK, centerX, centerY,
                        null, ALGORITHM_SOURCE, widgetClass, pkg));
            }
            if (item.isLongClickable()) {
                actions.add(new Action(Action.Type.LONG_CLICK, centerX, centerY,
                        null, ALGORITHM_SOURCE, widgetClass, pkg));
            }
            if (item.isEditable()) {
                String text = inputValueGenerator != null
                        ? inputValueGenerator.generateInput(item) : "test";
                actions.add(new Action(Action.Type.SET_TEXT, centerX, centerY,
                        text, ALGORITHM_SOURCE, widgetClass, pkg));
            }
            if (item.isScrollable()) {
                // DOWN (primary, same priority as CLICK)
                actions.add(new Action(Action.Type.SCROLL, centerX, centerY,
                        "down", ALGORITHM_SOURCE, widgetClass, pkg));
                // UP, LEFT, RIGHT (secondary directions)
                actions.add(new Action(Action.Type.SCROLL, centerX, centerY,
                        "up", ALGORITHM_SOURCE, widgetClass, pkg));
                actions.add(new Action(Action.Type.SCROLL, centerX, centerY,
                        "left", ALGORITHM_SOURCE, widgetClass, pkg));
                actions.add(new Action(Action.Type.SCROLL, centerX, centerY,
                        "right", ALGORITHM_SOURCE, widgetClass, pkg));
            }
        }

        return actions;
    }

    /**
     * Filter to actions that have never been executed on this screen.
     * If the screen has never been visited (node is null), all actions are untested.
     */
    private List<Action> filterUntested(List<Action> candidates, ScreenNode node) {
        if (node == null) return candidates;
        return candidates.stream()
                .filter(a -> node.getExecutionCount(a.signature()) == 0)
                .collect(Collectors.toList());
    }

    /**
     * Score all actions using the scorer chain and return the highest-scored one.
     * Applies stochastic selection: with configured probability, picks a random
     * action instead of the best one to avoid deterministic loops.
     */
    private Action selectBestScored(List<Action> actions, ScreenState screen,
                                    DynamicStateGraph graph, StaticMap staticMap) {
        Map<Action, Integer> scores = new HashMap<>();
        for (Action action : actions) {
            int score = 0;
            for (Scorer scorer : scorers) {
                score += scorer.score(action, screen, graph, staticMap);
            }
            scores.put(action, score);
        }

        actions.sort((a, b) -> Integer.compare(
                scores.getOrDefault(b, 0), scores.getOrDefault(a, 0)));

        boolean wasStochastic = false;
        Action selected;
        if (random.nextDouble() < getEffectiveStochasticProbability() && actions.size() > 1) {
            selected = softmaxSelect(actions, scores);
            wasStochastic = true;
        } else {
            selected = actions.get(0);
        }
        lastScoreBreakdown = computeScoreBreakdown(selected, screen, graph, staticMap,
                scores.getOrDefault(selected, 0), wasStochastic);
        return selected;
    }

    /**
     * Tier 4: unified priority queue with all widget actions + RESTART (+ BACK if not root).
     * BACK is excluded on root screens (no parents in SuccessorTracker) to prevent exiting
     * the app. When included, BACK score decays per-hash as ineffective presses accumulate.
     * RESTART has a fixed low score, acting as the last resort.
     * Guarantees non-null return (INV-RSM-12).
     */
    private Action selectFromUnifiedQueue(List<Action> widgetActions, ScreenState screen,
                                          DynamicStateGraph graph, StaticMap staticMap,
                                          String hash) {
        Map<Action, Integer> scores = new HashMap<>();

        // Score widget actions
        for (Action action : widgetActions) {
            int score = 0;
            for (Scorer scorer : scorers) {
                score += scorer.score(action, screen, graph, staticMap);
            }
            scores.put(action, score);
        }

        // Only add BACK when the current screen has known parents (i.e., the agent
        // navigated here from another screen). On root screens (no parents recorded),
        // BACK would exit the app entirely, so it is excluded.
        boolean isRootScreen = successorTracker == null
                || successorTracker.getParents(hash).isEmpty();

        List<Action> allActions = new ArrayList<>(widgetActions);

        if (!isRootScreen) {
            int backDecayCount = backDecayCountPerHash.getOrDefault(hash, 0);
            int backScore = (int) (backBaseScore - (backDecayCount * backDecayPerRepeat));
            Action backAction = Action.back(ALGORITHM_SOURCE);
            scores.put(backAction, backScore);
            allActions.add(backAction);
        }

        // Score RESTART (fixed low score, always present as fallback)
        Action restartAction = Action.restart(ALGORITHM_SOURCE);
        scores.put(restartAction, (int) restartBaseScore);
        allActions.add(restartAction);
        allActions.sort((a, b) -> Integer.compare(
                scores.getOrDefault(b, 0), scores.getOrDefault(a, 0)));

        // Log top-3 scored actions and BACK exclusion status
        StringBuilder top3 = new StringBuilder();
        int limit = Math.min(3, allActions.size());
        for (int i = 0; i < limit; i++) {
            Action a = allActions.get(i);
            if (i > 0) top3.append(", ");
            top3.append(a.getType()).append("=").append(scores.getOrDefault(a, 0));
        }
        if (isRootScreen) {
            top3.append(" [BACK excluded: root]");
        }
        RvTrack.rank(0, top3.toString());

        // Stochastic selection (softmax-weighted, boosted during plateau)
        boolean wasStochastic = false;
        Action selected;
        if (random.nextDouble() < getEffectiveStochasticProbability() && allActions.size() > 1) {
            selected = softmaxSelect(allActions, scores);
            wasStochastic = true;
        } else {
            selected = allActions.get(0);
        }
        lastScoreBreakdown = computeScoreBreakdown(selected, screen, graph, staticMap,
                scores.getOrDefault(selected, 0), wasStochastic);
        return selected; // NEVER null: at least RESTART is always present
    }

    /**
     * Derive failure count from ScreenNode as (executions - successes).
     * ScreenNode tracks successes (state transitions) separately from executions,
     * so failures = executions that did not cause a transition.
     */
    private int getFailureCount(ScreenNode node, String signature) {
        int executions = node.getExecutionCount(signature);
        // ActionStrength = successes / executions, so successes = strength * executions
        float strength = node.getActionStrength(signature);
        if (executions == 0) return 0;
        int successes = Math.round(strength * executions);
        return executions - successes;
    }

    /**
     * Softmax-weighted selection: p(a) = exp((score(a) - maxScore) / T) / Z.
     * Subtracts maxScore before exp() for numerical stability.
     * Package-private for testing.
     */
    Action softmaxSelect(List<Action> actions, Map<Action, Integer> scores) {
        int maxScore = Integer.MIN_VALUE;
        for (Action a : actions) {
            int s = scores.getOrDefault(a, 0);
            if (s > maxScore) maxScore = s;
        }
        double[] weights = new double[actions.size()];
        double sum = 0;
        for (int i = 0; i < actions.size(); i++) {
            weights[i] = Math.exp((scores.getOrDefault(actions.get(i), 0) - maxScore) / SOFTMAX_TEMPERATURE);
            sum += weights[i];
        }
        double rand = random.nextDouble() * sum;
        double cumulative = 0;
        for (int i = 0; i < actions.size(); i++) {
            cumulative += weights[i];
            if (rand <= cumulative) return actions.get(i);
        }
        return actions.get(actions.size() - 1);
    }

    /**
     * Compute per-scorer score breakdown for a single action.
     */
    private Map<String, Object> computeScoreBreakdown(Action action, ScreenState screen,
                                                       DynamicStateGraph graph, StaticMap staticMap,
                                                       int totalScore, boolean wasStochastic) {
        Map<String, Object> breakdown = new HashMap<>();
        for (Scorer scorer : scorers) {
            int contribution = scorer.score(action, screen, graph, staticMap);
            String name = scorer.getClass().getSimpleName()
                    .replace("Scorer", "").replace("Filter", "");
            // Simplify names for readability
            if (name.equals("Mop")) breakdown.put("mop", contribution);
            else if (name.equals("GradualDecay")) breakdown.put("decay", contribution);
            else if (name.equals("SystemElement")) breakdown.put("system", contribution);
            else if (name.equals("ComponentPriority")) breakdown.put("component", contribution);
            else if (name.equals("Wtg")) breakdown.put("wtg", contribution);
            else if (name.equals("CoverageDensity")) breakdown.put("coverage", contribution);
            else if (name.equals("ConfirmedCoverage")) breakdown.put("confirmed", contribution);
            else if (name.equals("Reward")) breakdown.put("reward", contribution);
            else breakdown.put(name.toLowerCase(), contribution);
        }
        breakdown.put("total", totalScore);
        breakdown.put("stochastic", wasStochastic);
        return breakdown;
    }

    /**
     * Extract simple class name from fully qualified name.
     * "android.widget.Button" -> "Button"
     */
    private static String simpleName(String className) {
        if (className == null) return "";
        int dot = className.lastIndexOf('.');
        return dot >= 0 ? className.substring(dot + 1) : className;
    }
}
