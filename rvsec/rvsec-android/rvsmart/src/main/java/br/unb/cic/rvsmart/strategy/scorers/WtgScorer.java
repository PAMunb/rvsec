package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Queue;
import java.util.Set;

/**
 * Scores actions based on WTG (Window Transition Graph) transitions from static analysis.
 * Uses multi-hop BFS (depth 3) on the WTG to find unvisited or under-visited activities
 * reachable from the current screen.
 *
 * Since Action objects carry coordinates but not resource_id, widget-level matching
 * against WTG transitions is not feasible. Instead, this scorer operates at the
 * activity level: if the current activity has any WTG transition leading to an
 * unvisited activity (within 3 hops), ALL click/long-click actions on this screen
 * receive a boost. This directs exploration toward screens with known outbound
 * transitions to unexplored parts of the app.
 *
 * BFS depth boosts (diminishing returns):
 *   - 1-hop to unvisited activity: +200
 *   - 2-hop to unvisited activity: +100
 *   - 3-hop to under-visited activity: +50
 *
 * Returns 0 for SCROLL, BACK, RESTART, SET_TEXT actions and when no static data
 * is available (graceful degradation).
 */
public class WtgScorer implements Scorer {

    private static final int BOOST_1_HOP = 200;
    private static final int BOOST_2_HOP = 100;
    private static final int BOOST_3_HOP = 50;
    private static final int MAX_BFS_DEPTH = 3;

    // Under-visited threshold: activities with fewer visits than this are considered worth exploring
    private static final int UNDER_VISITED_THRESHOLD = 3;

    public WtgScorer() {
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        if (staticMap == null || !staticMap.isLoaded()) return 0;

        // Only boost CLICK and LONG_CLICK actions — other types don't trigger WTG transitions
        Action.Type type = candidate.getType();
        if (type != Action.Type.CLICK && type != Action.Type.LONG_CLICK) return 0;

        String currentActivity = screen.getActivity();
        if (currentActivity == null || currentActivity.isEmpty()) return 0;

        // BFS on WTG transitions, up to MAX_BFS_DEPTH hops
        return bfsBoost(currentActivity, graph, staticMap);
    }

    /**
     * BFS on WTG transitions from the current activity. Returns the highest boost
     * found among unvisited/under-visited target activities within MAX_BFS_DEPTH hops.
     *
     * Uses diminishing boosts by depth: deeper targets are less valuable because
     * the agent needs more steps to reach them.
     */
    int bfsBoost(String startActivity, ContentGraph graph, StaticMap staticMap) {
        int bestBoost = 0;

        Set<String> visited = new HashSet<>();
        Queue<ActivityAtDepth> queue = new LinkedList<>();
        queue.add(new ActivityAtDepth(startActivity, 0));
        visited.add(startActivity);

        while (!queue.isEmpty()) {
            ActivityAtDepth current = queue.poll();
            if (current.depth >= MAX_BFS_DEPTH) continue;

            List<String> targets = staticMap.getTransitions(current.activity);
            for (String target : targets) {
                if (visited.contains(target)) continue;
                visited.add(target);

                int depth = current.depth + 1;
                int visitCount = getActivityVisitCount(target, graph);

                int boost = 0;
                if (visitCount == 0) {
                    // Unvisited activity — full boost based on depth
                    boost = boostForDepth(depth);
                } else if (depth == MAX_BFS_DEPTH && visitCount < UNDER_VISITED_THRESHOLD) {
                    // Under-visited at max depth — minimal boost
                    boost = BOOST_3_HOP;
                }

                if (boost > bestBoost) {
                    bestBoost = boost;
                }

                // Continue BFS if not at max depth
                if (depth < MAX_BFS_DEPTH) {
                    queue.add(new ActivityAtDepth(target, depth));
                }
            }
        }

        return bestBoost;
    }

    private int boostForDepth(int depth) {
        switch (depth) {
            case 1: return BOOST_1_HOP;
            case 2: return BOOST_2_HOP;
            case 3: return BOOST_3_HOP;
            default: return 0;
        }
    }

    /**
     * Count how many times any screen with the given activity name has been visited.
     * Scans all graph nodes because the graph is indexed by hash, not by activity.
     */
    private int getActivityVisitCount(String activity, ContentGraph graph) {
        int total = 0;
        for (ContentNode node : graph.getNodes().values()) {
            if (activity.equals(node.getActivity())) {
                total += node.getVisitCount();
            }
        }
        return total;
    }

    private static class ActivityAtDepth {
        final String activity;
        final int depth;

        ActivityAtDepth(String activity, int depth) {
            this.activity = activity;
            this.depth = depth;
        }
    }
}
