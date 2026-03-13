package br.unb.cic.rvsmart.strategy;

import android.graphics.Rect;
import android.util.Log;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;
import br.unb.cic.rvsmart.strategy.scorers.ComponentPriorityScorer;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;
import br.unb.cic.rvsmart.strategy.scorers.CoverageDensityScorer;
import br.unb.cic.rvsmart.strategy.scorers.GradualDecayScorer;
import br.unb.cic.rvsmart.strategy.scorers.MopScorer;

import br.unb.cic.rvsmart.strategy.scorers.Scorer;
import br.unb.cic.rvsmart.strategy.scorers.UCBScorer;
import br.unb.cic.rvsmart.strategy.scorers.SystemElementFilter;
import br.unb.cic.rvsmart.strategy.scorers.WtgScorer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Selects the next action to execute on the current screen using phase-based dispatch.
 *
 * Phase 1 (DFS/broad exploration): prefer untested actions in the current content state.
 *   Uses the scoring chain to rank candidates. When the current content node is exhausted,
 *   navigates toward the nearest structural cluster with untested content states
 *   (via NavigationMap BFS). Falls back to Phase 3 if no path is available.
 *
 * Phase 2 (Coverage-Guided): targets UI coverage gaps. If uiCoverageTracker shows a gap
 *   above config.uiCoverageThreshold, finds the highest-gap screen reachable via
 *   NavigationMap and navigates there. Falls back to Phase 1 if no target or no path.
 *
 * Phase 3 (Stochastic): softmax-selected action with stochastic probability boosted to 0.5,
 *   escaping local optima and saturated areas.
 *
 * selectAction() NEVER returns null (INV-RSM-12): at minimum, RESTART is always present
 * in the unified queue. BACK is excluded on root screens (no parents in SuccessorTracker)
 * to prevent the agent from exiting the app.
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
 *   - SaturationScorer: screen-level penalty — handled by phase transitions instead
 *   - StrengthScorer: master aggregator with weights — keeping chain simple and additive
 *
 * After scoring, stochastic selection (default 15%, Phase 3: 50%) picks a random action
 * instead of the top-scored one, preventing deterministic loops.
 *
 * BACK actions use per-hash decay: each ineffective BACK (no screen change) on the same
 * screen increases the penalty, discouraging repeated BACKs on stuck screens.
 */
public class ActionSelector {

    private static final String TAG = "RVSMART";
    private static final String ALGORITHM_SOURCE = "algorithm";
    private static final double SOFTMAX_TEMPERATURE = 50.0;

    /** Stochastic probability override for Phase 3 (escape saturation). */
    private static final float PHASE3_STOCHASTIC_PROBABILITY = 0.5f;

    /** CAP-12: Widget types that may report clickable=false in UIAutomator but are inherently interactive.
     *  Aligned with rv-screen-parser's ALWAYS_CLICKABLE_TYPES and Spinner special case. */
    private static final Set<String> ALWAYS_CLICKABLE_WIDGETS = new HashSet<>();
    static {
        // Spinner — explicitly documented as clickable=false in UIAutomator dumps
        ALWAYS_CLICKABLE_WIDGETS.add("Spinner");
        ALWAYS_CLICKABLE_WIDGETS.add("AppCompatSpinner");
        // Tab navigation
        ALWAYS_CLICKABLE_WIDGETS.add("TabLayout");
        ALWAYS_CLICKABLE_WIDGETS.add("TabView");
        // Bottom/rail navigation
        ALWAYS_CLICKABLE_WIDGETS.add("BottomNavigationItemView");
        ALWAYS_CLICKABLE_WIDGETS.add("NavigationBarItemView");
        // Material components
        ALWAYS_CLICKABLE_WIDGETS.add("Chip");
        ALWAYS_CLICKABLE_WIDGETS.add("FloatingActionButton");
    }

    private final List<Scorer> scorers;
    private final float backBaseScore;
    private final float backDecayPerRepeat;
    private final float restartBaseScore;
    private final float stochasticProbability;
    private final float uiCoverageThreshold;
    private final Random random;
    private final InputValueGenerator inputValueGenerator;

    // Per-hash count of ineffective BACK presses (no screen change)
    private final Map<String, Integer> backDecayCountPerHash;

    // Last selected phase, exposed for trace observability
    private Phase lastSelectedPhase;

    // Last score breakdown for trace observability (per-scorer contributions)
    private Map<String, Object> lastScoreBreakdown;

    private final SuccessorTracker successorTracker;
    private final NavigationMap navigationMap;
    private final PhaseController phaseController;

    public ActionSelector(Config config) {
        this(config, null, null, null, null, null, null);
    }

    public ActionSelector(Config config, SuccessorTracker successorTracker) {
        this(config, successorTracker, null, null, null, null, null);
    }

    public ActionSelector(Config config, SuccessorTracker successorTracker,
                          ConfirmedCoverageScorer confirmedCoverageScorer) {
        this(config, successorTracker, confirmedCoverageScorer, null, null, null, null);
    }

    public ActionSelector(Config config, SuccessorTracker successorTracker,
                          ConfirmedCoverageScorer confirmedCoverageScorer,
                          InputValueGenerator inputValueGenerator,
                          UICoverageTracker uiCoverageTracker) {
        this(config, successorTracker, confirmedCoverageScorer, inputValueGenerator,
                uiCoverageTracker, null, null);
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
     * @param navigationMap structural transition map for Phase 3 random exploration;
     *                       null to disable NavigationMap random edges
     * @param phaseController phase controller for cluster forcing checks;
     *                         null to skip cluster forcing
     */
    public ActionSelector(Config config, SuccessorTracker successorTracker,
                          ConfirmedCoverageScorer confirmedCoverageScorer,
                          InputValueGenerator inputValueGenerator,
                          UICoverageTracker uiCoverageTracker,
                          NavigationMap navigationMap,
                          PhaseController phaseController) {
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
        this.scorers.add(new UCBScorer(config.getUcbC()));
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
        this.uiCoverageThreshold = config.getUiCoverageThreshold();
        this.random = config.getSeed() != null ? new Random(config.getSeed()) : new Random();

        this.backDecayCountPerHash = new HashMap<>();
        this.successorTracker = successorTracker;
        this.inputValueGenerator = inputValueGenerator;
        this.navigationMap = navigationMap;
        this.phaseController = phaseController;
    }

    /**
     * Select the best action to execute on the current screen.
     * Legacy overload — dispatches to phase-based selection using Phase 1 by default.
     * Callers that have not yet been updated to Group 7 wiring use this path.
     *
     * @return selected action, NEVER null (INV-RSM-12)
     */
    public Action selectAction(ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        return selectAction(Phase.PHASE_1, screen, screen.getStructHash(),
                graph, null, null, null, staticMap);
    }

    /**
     * Phase-based action selection. Group 7 will call this full signature once AgentLoop
     * is wired with PhaseController, StructuralGraph, NavigationMap, and UICoverageTracker.
     *
     * @param phase          current exploration phase from PhaseController
     * @param screen         current screen state
     * @param structHash     structural hash of the current screen (from ScreenState.getStructHash())
     * @param contentGraph   content-level state graph
     * @param structuralGraph structural clusters (structHash → contentHashes); may be null
     * @param navigationMap  structural transition map for BFS navigation; may be null
     * @param uiCoverageTracker per-screen UI element coverage tracker; may be null
     * @param staticMap      static analysis data
     * @return selected action, NEVER null (INV-RSM-12)
     */
    public Action selectAction(Phase phase, ScreenState screen, String structHash,
                               ContentGraph contentGraph,
                               StructuralGraph structuralGraph,
                               NavigationMap navigationMap,
                               UICoverageTracker uiCoverageTracker,
                               StaticMap staticMap) {
        switch (phase) {
            case PHASE_1:
                return selectPhase1(screen, structHash, contentGraph,
                        structuralGraph, navigationMap, staticMap);
            case PHASE_2:
                return selectPhase2(screen, structHash, contentGraph,
                        structuralGraph, navigationMap, uiCoverageTracker, staticMap);
            case PHASE_3:
                return selectPhase3(screen, structHash, contentGraph, staticMap);
            default:
                return selectPhase1(screen, structHash, contentGraph,
                        structuralGraph, navigationMap, staticMap);
        }
    }

    /**
     * Phase 1: Broad DFS exploration.
     * Returns an untested action in the current content state using the scoring chain.
     * When the current content node is exhausted, navigates toward the nearest structural
     * cluster with untested content states. Falls back to Phase 3 if no path exists.
     */
    private Action selectPhase1(ScreenState screen, String structHash,
                                 ContentGraph contentGraph,
                                 StructuralGraph structuralGraph,
                                 NavigationMap navigationMap,
                                 StaticMap staticMap) {
        // GAP-1: Skip Phase 1 for force-exhausted clusters
        if (phaseController != null && phaseController.isClusterForced(structHash)) {
            return selectPhase3(screen, structHash, contentGraph, staticMap);
        }

        String hash = screen.getContentHash();
        ContentNode node = contentGraph.get(hash);

        List<Action> candidates = generateCandidateActions(screen);

        // GAP-3: Adaptive failure threshold (safety net: keep all if filter empties the list)
        // BUG-01b: BACK and RESTART are exempt — system actions must always remain available.
        // BACK over-use is already controlled by score decay (backDecayCountPerHash).
        if (node != null) {
            final ContentNode nodeRef = node;
            List<Action> filtered = candidates.stream()
                    .filter(a -> a.getType() == Action.Type.BACK
                            || a.getType() == Action.Type.RESTART
                            || getFailureCount(nodeRef, a.signature()) < getFailureThreshold(nodeRef, a.signature()))
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
            lastSelectedPhase = Phase.PHASE_1;
            double saturation = node != null ? node.getSaturationRate() : 0.0;
            RvTrack.strategy(0, 1, "p1_untested", untested.size(), saturation);
            return selectBestScored(untested, screen, contentGraph, staticMap);
        }

        // Current content node exhausted — navigate to nearest untested cluster
        Action navAction = navigateToNearestUntestedCluster(
                structHash, contentGraph, structuralGraph, navigationMap);
        if (navAction != null) {
            lastSelectedPhase = Phase.PHASE_1;
            RvTrack.strategy(0, 1, "p1_nav_cluster", 0, 1.0);
            return navAction;
        }

        // No path to untested cluster — fall back to Phase 3
        return selectPhase3(screen, structHash, contentGraph, staticMap);
    }

    /**
     * Phase 2: Coverage-guided exploration.
     * Finds the screen with the highest UI coverage gap reachable via NavigationMap
     * and navigates toward it. Falls back to Phase 1 if no target or no path.
     */
    private Action selectPhase2(ScreenState screen, String structHash,
                                 ContentGraph contentGraph,
                                 StructuralGraph structuralGraph,
                                 NavigationMap navigationMap,
                                 UICoverageTracker uiCoverageTracker,
                                 StaticMap staticMap) {
        if (uiCoverageTracker != null && navigationMap != null) {
            // Find the structural cluster with the highest average coverage gap
            String targetStructHash = findHighestGapCluster(
                    structHash, contentGraph, structuralGraph, navigationMap, uiCoverageTracker);

            if (targetStructHash != null) {
                List<String> path = navigationMap.findPath(structHash, targetStructHash);
                if (!path.isEmpty()) {
                    lastSelectedPhase = Phase.PHASE_2;
                    RvTrack.strategy(0, 2, "p2_coverage_nav", path.size(), 0.0);
                    // Execute the first step on the path toward the high-gap cluster
                    return actionFromSignature(path.get(0));
                }
            }
        }

        // No coverage gap target or no path — fall back to Phase 1
        return selectPhase1(screen, structHash, contentGraph, structuralGraph, navigationMap, staticMap);
    }

    /**
     * Phase 3: Stochastic exploration with boosted randomness.
     * Uses the unified priority queue (all widgets + BACK + RESTART) with stochastic
     * probability boosted to 0.5, escaping local optima.
     * GAP-2: With 10% probability, tries a random NavigationMap outgoing edge.
     */
    private Action selectPhase3(ScreenState screen, String structHash,
                                 ContentGraph contentGraph, StaticMap staticMap) {
        lastSelectedPhase = Phase.PHASE_3;
        String hash = screen.getContentHash();
        ContentNode node = contentGraph.get(hash);
        double saturation = node != null ? node.getSaturationRate() : 0.0;
        RvTrack.strategy(0, 3, "p3_stochastic", 0, saturation);

        // GAP-2: With 10% probability, try NavigationMap random edge
        if (this.navigationMap != null && random.nextDouble() < 0.10) {
            List<String> edges = this.navigationMap.getOutgoingActions(structHash);
            if (edges != null && !edges.isEmpty()) {
                String randomEdge = edges.get(random.nextInt(edges.size()));
                Action navAction = actionFromSignature(randomEdge);
                if (navAction.getType() != Action.Type.RESTART) {
                    RvTrack.strategy(0, 3, "p3_nav_random", edges.size(), saturation);
                    return navAction;
                }
            }
        }

        return selectFromUnifiedQueue(
                generateCandidateActions(screen), screen, contentGraph, staticMap, hash, structHash,
                PHASE3_STOCHASTIC_PROBABILITY);
    }

    /**
     * Select the next best action excluding previously failed signatures.
     * Used for multi-attempt retries within a single cycle.
     *
     * @param excludeSignatures action signatures to skip (already attempted)
     * @return best alternative action, or null if no candidates remain
     */
    public Action selectNextBest(ScreenState screen, Set<String> excludeSignatures,
                                 ContentGraph graph, StaticMap staticMap) {
        String hash = screen.getContentHash();
        String structHash = screen.getStructHash();
        ContentNode node = graph.get(hash);

        List<Action> candidates = generateCandidateActions(screen);

        // BUG-01: Use structHash for parent check (SuccessorTracker records at structural level)
        boolean isRootScreen = successorTracker == null
                || successorTracker.getParents(structHash).isEmpty();
        if (!isRootScreen) {
            candidates.add(Action.back(ALGORITHM_SOURCE));
        }
        candidates.add(Action.restart(ALGORITHM_SOURCE));

        // Filter out excluded signatures and actions with high failure counts.
        // BUG-01b: BACK and RESTART are exempt — system actions must always remain available.
        candidates = candidates.stream()
                .filter(a -> !excludeSignatures.contains(a.signature()))
                .filter(a -> a.getType() == Action.Type.BACK
                        || a.getType() == Action.Type.RESTART
                        || node == null
                        || getFailureCount(node, a.signature()) < getFailureThreshold(node, a.signature()))
                .collect(Collectors.toList());

        if (candidates.isEmpty()) return null;

        // Score and sort (BACK decay uses contentHash for per-visit granularity)
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

    /**
     * Returns the phase selected in the most recent selectAction() call.
     * Used for trace observability.
     */
    public Phase getLastSelectedPhase() {
        return lastSelectedPhase;
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
     * Get the scorer chain. Used for testing to verify which scorers are active.
     */
    public List<Scorer> getScorers() {
        return scorers;
    }

    // --- Private methods ---

    /**
     * Navigate to the nearest structural cluster that contains at least one ContentNode
     * with untested actions. Uses NavigationMap BFS hops to find the path.
     * Returns the first action on the path, or null if no path exists or graphs are null.
     */
    private Action navigateToNearestUntestedCluster(String structHash,
                                                     ContentGraph contentGraph,
                                                     StructuralGraph structuralGraph,
                                                     NavigationMap navigationMap) {
        if (structHash == null || structuralGraph == null || navigationMap == null) {
            return null;
        }

        // Find all structural clusters that have at least one ContentNode with untested actions
        List<String> candidateClusters = new ArrayList<>();
        for (Map.Entry<String, ContentNode> entry : contentGraph.getNodes().entrySet()) {
            String contentHash = entry.getKey();
            ContentNode node = entry.getValue();

            // A node has untested actions when it has fewer executed actions than total
            boolean hasUntested = node.getTotalActions() == 0
                    || node.getExecutedActions().size() < node.getTotalActions();
            if (!hasUntested) continue;

            String clusterHash = structuralGraph.getStructHash(contentHash);
            if (clusterHash != null && !clusterHash.equals(structHash)) {
                candidateClusters.add(clusterHash);
            }
        }

        if (candidateClusters.isEmpty()) return null;

        // Find the nearest reachable cluster via BFS distance proxy:
        // try each candidate and return the first step of the shortest path
        List<String> shortestPath = null;
        for (String candidate : candidateClusters) {
            List<String> path = navigationMap.findPath(structHash, candidate);
            if (!path.isEmpty()) {
                if (shortestPath == null || path.size() < shortestPath.size()) {
                    shortestPath = path;
                }
            }
        }

        if (shortestPath == null || shortestPath.isEmpty()) return null;

        return actionFromSignature(shortestPath.get(0));
    }

    /**
     * Find the structural cluster with the highest average UI coverage gap that is
     * reachable from the current structural hash via NavigationMap.
     * Returns null if no suitable target exists.
     */
    private String findHighestGapCluster(String currentStructHash,
                                          ContentGraph contentGraph,
                                          StructuralGraph structuralGraph,
                                          NavigationMap navigationMap,
                                          UICoverageTracker uiCoverageTracker) {
        if (structuralGraph == null || navigationMap == null || uiCoverageTracker == null) {
            return null;
        }

        String bestCluster = null;
        float bestGap = uiCoverageThreshold; // only consider clusters above threshold

        for (Map.Entry<String, ContentNode> entry : contentGraph.getNodes().entrySet()) {
            String contentHash = entry.getKey();
            String clusterHash = structuralGraph.getStructHash(contentHash);
            if (clusterHash == null || clusterHash.equals(currentStructHash)) continue;

            float gap = uiCoverageTracker.getCoverageGap(contentHash);
            if (gap <= bestGap) continue;

            // Only consider reachable clusters
            if (!navigationMap.hasPath(currentStructHash, clusterHash)) continue;

            bestGap = gap;
            bestCluster = clusterHash;
        }

        return bestCluster;
    }

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

            // CAP-9/10/11: Generate actions for special non-clickable/non-scrollable widgets
            if (!item.isClickable() && !item.isScrollable()) {
                String simpleCls = simpleName(item.getClassName());
                // CAP-9: SeekBar/RatingBar — generate CLICK at center
                if ("SeekBar".equals(simpleCls) || "AppCompatSeekBar".equals(simpleCls)
                        || "RatingBar".equals(simpleCls) || "AppCompatRatingBar".equals(simpleCls)) {
                    actions.add(new Action(Action.Type.CLICK, centerX, centerY,
                            null, ALGORITHM_SOURCE, widgetClass, pkg));
                }
                // CAP-10: SwipeRefreshLayout — generate swipe-down for pull-to-refresh
                if ("SwipeRefreshLayout".equals(simpleCls)) {
                    int topY = bounds.top + 10;
                    actions.add(new Action(Action.Type.SCROLL, centerX, topY,
                            "down", ALGORITHM_SOURCE, widgetClass, pkg));
                }
                // CAP-11: DrawerLayout — generate edge swipe from left
                if ("DrawerLayout".equals(simpleCls)) {
                    actions.add(new Action(Action.Type.SCROLL, 10, centerY,
                            "right", ALGORITHM_SOURCE, widgetClass, pkg));
                }
                // CAP-12: Always-clickable widgets (Spinner, TabView, BottomNav, Chip, FAB)
                if (ALWAYS_CLICKABLE_WIDGETS.contains(simpleCls)) {
                    actions.add(new Action(Action.Type.CLICK, centerX, centerY,
                            null, ALGORITHM_SOURCE, widgetClass, pkg));
                }
            }
        }

        return actions;
    }

    /**
     * Filter to actions that have never been executed on this screen.
     * If the screen has never been visited (node is null), all actions are untested.
     */
    private List<Action> filterUntested(List<Action> candidates, ContentNode node) {
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
                                    ContentGraph graph, StaticMap staticMap) {
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
        if (random.nextDouble() < stochasticProbability && actions.size() > 1) {
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
     * Unified priority queue with all widget actions + RESTART (+ BACK if not root).
     * BACK is excluded on root screens (no parents in SuccessorTracker) to prevent exiting
     * the app. When included, BACK score decays per-hash as ineffective presses accumulate.
     * RESTART has a fixed low score, acting as the last resort.
     * Guarantees non-null return (INV-RSM-12).
     *
     * @param hash       contentHash for BACK decay tracking (per-content-hash granularity)
     * @param structHash structural hash for parent check (SuccessorTracker records at structural level)
     * @param effectiveStochasticProbability stochastic probability override (e.g., 0.5 for Phase 3)
     */
    private Action selectFromUnifiedQueue(List<Action> widgetActions, ScreenState screen,
                                          ContentGraph graph, StaticMap staticMap,
                                          String hash, String structHash,
                                          float effectiveStochasticProbability) {
        Map<Action, Integer> scores = new HashMap<>();

        // Score widget actions
        for (Action action : widgetActions) {
            int score = 0;
            for (Scorer scorer : scorers) {
                score += scorer.score(action, screen, graph, staticMap);
            }
            scores.put(action, score);
        }

        // BUG-01: Use structHash for parent check (SuccessorTracker records at structural level).
        // BACK is only added when the current structural cluster has known parents.
        boolean isRootScreen = successorTracker == null
                || successorTracker.getParents(structHash).isEmpty();

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

        // Stochastic selection (softmax-weighted, boosted in Phase 3)
        boolean wasStochastic = false;
        Action selected;
        if (random.nextDouble() < effectiveStochasticProbability && allActions.size() > 1) {
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
     * Derive failure count from ContentNode as (executions - successes).
     * ContentNode tracks successes (state transitions) separately from executions,
     * so failures = executions that did not cause a transition.
     */
    private int getFailureCount(ContentNode node, String signature) {
        int executions = node.getExecutionCount(signature);
        // ActionStrength = successes / executions, so successes = strength * executions
        float strength = node.getActionStrength(signature);
        if (executions == 0) return 0;
        int successes = Math.round(strength * executions);
        return executions - successes;
    }

    /**
     * Adaptive failure threshold: actions with high failure counts should be
     * filtered, but the threshold adapts based on execution count to avoid
     * premature filtering. Minimum threshold is 3.
     */
    private int getFailureThreshold(ContentNode node, String signature) {
        int executions = node.getExecutionCount(signature);
        if (executions <= 3) return 3; // Never filter with fewer than 3 executions
        return Math.max(3, executions / 2); // Allow up to half-failure rate
    }

    /**
     * Reconstruct an Action object from a NavigationMap action signature string.
     * NavigationMap stores signatures in the format produced by Action.signature()
     * (e.g., "click@540,960"). Parses type and coordinates.
     * Returns a RESTART action if the signature cannot be parsed.
     */
    private Action actionFromSignature(String signature) {
        if (signature == null) return Action.restart(ALGORITHM_SOURCE);
        try {
            // Format: "type@x,y" or "type:text@x,y"
            int atIdx = signature.lastIndexOf('@');
            if (atIdx < 0) return Action.restart(ALGORITHM_SOURCE);
            String coords = signature.substring(atIdx + 1);
            String typeAndText = signature.substring(0, atIdx);

            String typePart;
            String text = null;
            int colonIdx = typeAndText.indexOf(':');
            if (colonIdx >= 0) {
                typePart = typeAndText.substring(0, colonIdx);
                text = typeAndText.substring(colonIdx + 1);
            } else {
                typePart = typeAndText;
            }

            String[] xy = coords.split(",");
            int x = Integer.parseInt(xy[0]);
            int y = Integer.parseInt(xy[1]);

            Action.Type type;
            switch (typePart.toLowerCase()) {
                case "click":      type = Action.Type.CLICK; break;
                case "long_click": type = Action.Type.LONG_CLICK; break;
                case "set_text":   type = Action.Type.SET_TEXT; break;
                case "scroll":     type = Action.Type.SCROLL; break;
                case "back":       return Action.back(ALGORITHM_SOURCE);
                case "restart":    return Action.restart(ALGORITHM_SOURCE);
                default:           return Action.restart(ALGORITHM_SOURCE);
            }

            return new Action(type, x, y, text, ALGORITHM_SOURCE, null, null);
        } catch (Exception e) {
            return Action.restart(ALGORITHM_SOURCE);
        }
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
                                                       ContentGraph graph, StaticMap staticMap,
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
        breakdown.put("phase", lastSelectedPhase != null ? lastSelectedPhase.name() : "UNKNOWN");
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
