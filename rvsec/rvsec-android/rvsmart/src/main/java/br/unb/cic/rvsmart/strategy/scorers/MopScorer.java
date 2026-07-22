package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions based on MOP (monitored operation) reachability from static analysis.
 *
 * Uses widget-level lookup first: if the action's widget has static data with a
 * MOP-reaching handler, it gets the direct or transitive score. Falls back to
 * activity-level lookup when no widget-level data is available.
 *
 * Direct reachability scores higher than transitive. Returns 0 when static data
 * is unavailable or neither widget nor activity reaches any monitored operation.
 */
public class MopScorer implements Scorer {

    private final int directScore;
    private final int transitiveScore;

    public MopScorer(int directScore, int transitiveScore) {
        this.directScore = directScore;
        this.transitiveScore = transitiveScore;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        if (staticMap == null || !staticMap.isLoaded()) return 0;

        String activity = screen.getActivity();

        // Widget-level scoring: match action's widget to static data
        String widgetClass = candidate.getWidgetClass();
        if (widgetClass != null) {
            String resourceId = findResourceIdForAction(candidate, screen);
            if (resourceId != null) {
                StaticMap.WidgetStaticData widgetData = staticMap.getWidgetData(activity, resourceId);
                if (widgetData != null) {
                    if (widgetData.directMop) return directScore;
                    if (widgetData.transitiveMop) return transitiveScore;
                    // Widget on MOP activity but without MOP handler: reduced score
                    if (staticMap.activityHasDirectMop(activity) || staticMap.activityHasMop(activity)) {
                        return 100;
                    }
                    return 0;
                }
            }
        }

        // Fallback: activity-level MOP lookup
        if (staticMap.activityHasDirectMop(activity)) return directScore;
        if (staticMap.activityHasMop(activity)) return transitiveScore;
        return 0;
    }

    /**
     * Find the resourceId of the screen item that corresponds to this action's coordinates.
     */
    private String findResourceIdForAction(Action candidate, ScreenState screen) {
        int actionX = candidate.getX();
        int actionY = candidate.getY();
        for (ScreenItem item : screen.getItems()) {
            if (item.getBounds() != null) {
                int cx = item.getBounds().centerX();
                int cy = item.getBounds().centerY();
                if (cx == actionX && cy == actionY) {
                    return item.getResourceId();
                }
            }
        }
        return null;
    }
}
