package br.unb.cic.rvsmart.strategy;

import java.util.HashMap;
import java.util.Map;

/**
 * Tracks iteration spending per Activity. Each Activity gets a budget
 * proportional to its interactive widget count. When budget is exhausted,
 * AgentLoop should force backtrack/restart to distribute time across Activities.
 */
public class ActivityBudgetTracker {
    private final int baseBudget;
    private final int budgetPerWidget;
    private final Map<String, Integer> budgets = new HashMap<>();
    private final Map<String, Integer> counters = new HashMap<>();

    public ActivityBudgetTracker(int baseBudget, int budgetPerWidget) {
        this.baseBudget = baseBudget;
        this.budgetPerWidget = budgetPerWidget;
    }

    public void registerActivity(String activityName, int widgetCount) {
        if (activityName == null || budgets.containsKey(activityName)) return;
        budgets.put(activityName, baseBudget + (widgetCount * budgetPerWidget));
        counters.put(activityName, 0);
    }

    public void recordIteration(String activityName) {
        if (activityName == null || !counters.containsKey(activityName)) return;
        counters.merge(activityName, 1, Integer::sum);
    }

    public boolean isBudgetExhausted(String activityName) {
        if (activityName == null || !budgets.containsKey(activityName)) return false;
        return counters.getOrDefault(activityName, 0) >= budgets.get(activityName);
    }

    public int getRemainingBudget(String activityName) {
        if (activityName == null || !budgets.containsKey(activityName)) return Integer.MAX_VALUE;
        return Math.max(0, budgets.get(activityName) - counters.getOrDefault(activityName, 0));
    }
}
