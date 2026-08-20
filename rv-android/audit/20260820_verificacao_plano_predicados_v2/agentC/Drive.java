import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;

import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.FSMCoenables;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.ast.State;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.ast.Symbol;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.ast.Transition;

/**
 * Driver replicating the first audit's measurement over FSMCoenables.
 * 6-state FSM (start, s1, s2, s3, match + implicit fail), alphabet of n symbols.
 * Usage: java Drive <n> <withFail: true|false> [--tostring]
 */
public class Drive {
    public static void main(String[] args) throws Exception {
        int n = Integer.parseInt(args[0]);
        boolean withFail = Boolean.parseBoolean(args[1]);
        boolean doToString = args.length > 2 && args[2].equals("--tostring");

        ArrayList<Symbol> events = new ArrayList<>();
        for (int i = 1; i <= n; i++) events.add(Symbol.get("e" + i));

        State start = State.get("start");
        State s1 = State.get("s1");
        State s2 = State.get("s2");
        State s3 = State.get("s3");
        State match = State.get("match");
        State fail = State.get("fail");

        ArrayList<State> states = new ArrayList<>();
        states.add(start); states.add(s1); states.add(s2); states.add(s3); states.add(match);

        // chain start -e1-> s1 -e2-> s2 -e3-> s3 -e4-> match -e1-> s1 ; everything else defaults to fail
        HashMap<State, Transition> stateMap = new HashMap<>();
        Transition t;
        t = new Transition(); t.put(Symbol.get("e1"), s1); stateMap.put(start, t);
        t = new Transition(); t.put(Symbol.get("e2"), s2); stateMap.put(s1, t);
        t = new Transition(); t.put(Symbol.get("e3"), s3); stateMap.put(s2, t);
        t = new Transition(); t.put(Symbol.get("e4"), match); stateMap.put(s3, t);
        t = new Transition(); t.put(Symbol.get("e1"), s1); stateMap.put(match, t);

        ArrayList<State> categories = new ArrayList<>();
        categories.add(match);
        if (withFail) categories.add(fail);

        HashMap<State, HashSet<State>> aliases = new HashMap<>();

        long t0 = System.nanoTime();
        FSMCoenables co = new FSMCoenables(start, events, states, categories, aliases, stateMap);
        long t1 = System.nanoTime();

        HashMap<State, HashMap<Symbol, HashSet<HashSet<Symbol>>>> result = co.getCoenables();
        StringBuilder sb = new StringBuilder();
        long total = 0;
        for (State cat : categories) {
            long catTotal = 0;
            for (Symbol ev : events) catTotal += result.get(cat).get(ev).size();
            sb.append("  category ").append(cat).append(": ").append(catTotal).append(" entries\n");
            total += catTotal;
        }
        double ms = (t1 - t0) / 1e6;
        System.out.printf("n=%d withFail=%b  compute=%.1f ms%n", n, withFail, ms);
        System.out.print(sb);
        long nFormula = (long) n * ((1L << n) - 1);
        System.out.printf("  formula n*(2^n-1) = %d%n", nFormula);

        if (doToString) {
            long t2 = System.nanoTime();
            String s = co.toString();
            long t3 = System.nanoTime();
            System.out.printf("  toString length = %d chars (%.1f ms)%n", s.length(), (t3 - t2) / 1e6);
        }
        System.out.printf("  total entries all categories = %d%n", total);
    }
}
