import com.runtimeverification.rvmonitor.logicrepository.plugins.ere.ERE;
import com.runtimeverification.rvmonitor.logicrepository.plugins.ere.parser.EREParser;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.*;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.FSMParser;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.ast.State;
import com.runtimeverification.rvmonitor.logicrepository.plugins.fsm.parser.ast.Symbol;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Prices a property before you spend a minute of CPU on it.
 *
 * <p>Mirrors what {@code FSMPlugin.process} and {@code EREPlugin.process} do, using the
 * production classes, and stops before any code generation. So the counts it prints are
 * authority, not a model: it is the shipped {@code FSMCoenables} doing the walk.
 *
 * <p>Takes either notation, which is the point — an {@code ere} and an {@code fsm} for the
 * same language should produce the same numbers, and when they do not, the difference is
 * about the notation rather than the language.
 *
 * <pre>
 * java -Xss1g -cp "$CP" CoenableProbe fsm body.fsm "g1 g2 i1 …" "fail match1"
 * java -Xss1g -cp "$CP" CoenableProbe ere body.ere "g1 g2 i1 …" "fail match"
 * </pre>
 *
 * The third argument is the whole alphabet, space separated; the fourth is the category list,
 * which is the specification's handler names — remember that {@code fail} counts, and that it
 * is the one that costs.
 */
public class CoenableProbe {

    /** Same conversion EREPlugin performs before handing the result to the fsm plugin. */
    private static String ereToFsm(String expression, String[] events) {
        com.runtimeverification.rvmonitor.logicrepository.plugins.ere.Symbol[] symbols =
            new com.runtimeverification.rvmonitor.logicrepository.plugins.ere.Symbol[events.length];
        for (int i = 0; i < events.length; i++) {
            symbols[i] =
                com.runtimeverification.rvmonitor.logicrepository.plugins.ere.Symbol.get(events[i]);
        }
        ERE ere = EREParser.parse(expression).getERE();
        var dfa = com.runtimeverification.rvmonitor.logicrepository.plugins.ere.FSM.get(ere, symbols);
        ByteArrayOutputStream os = new ByteArrayOutputStream();
        dfa.print(new PrintStream(os));
        return os.toString();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            System.err.println("usage: CoenableProbe <fsm|ere> <body-file> "
                    + "\"<space separated events>\" \"<space separated categories>\"");
            System.exit(2);
        }
        String kind = args[0];
        String body = Files.readString(Path.of(args[1]));
        String[] eventNames = args[2].trim().split("\\s+");
        String[] categoryNames = args[3].trim().split("\\s+");

        if ("ere".equals(kind)) body = ereToFsm(body, eventNames);

        ArrayList<Symbol> events = new ArrayList<>();
        for (String s : eventNames) events.add(Symbol.get(s));
        ArrayList<State> categories = new ArrayList<>();
        for (String s : categoryNames) categories.add(State.get(s));

        FSMParser parsed = FSMParser.parse(body);
        parsed.check();

        FSMMin min = new FSMMin(parsed.getStartState(), events, parsed.getStates(),
                categories, parsed.getAliases(), parsed.getStateMap());
        System.out.println("events            = " + events.size());
        System.out.println("states_after_min  = " + min.getStates().size());

        long t0 = System.currentTimeMillis();
        new FSMEnables(min.getStartState(), events, min.getStates(), categories,
                min.getAliases(), min.getStateMap());
        long t1 = System.currentTimeMillis();
        System.out.println("enables_ms        = " + (t1 - t0));

        FSMCoenables co = new FSMCoenables(min.getStartState(), events, min.getStates(),
                categories, min.getAliases(), min.getStateMap());
        System.out.println("coenables_ms      = " + (System.currentTimeMillis() - t1));

        long total = 0;
        for (var e : co.getCoenables().entrySet()) {
            long n = 0;
            for (HashSet<HashSet<Symbol>> sets : e.getValue().values()) n += sets.size();
            System.out.println("coenable_sets[" + e.getKey() + "] = " + n);
            total += n;
        }
        System.out.println("coenable_sets_tot = " + total);

        // n * (2^n - 1) is what a saturated `fail` category costs. Printing the prediction
        // beside the measurement is the cheap version of the closed-form check.
        int n = events.size();
        System.out.println("saturated_predict = "
                + (n <= 62 ? Long.toString((long) n * ((1L << n) - 1)) : "overflow"));

        // The string is what rv-monitor's regex has to parse, and it is the thing that
        // overflows the stack long before the walk itself becomes the problem.
        if (total < 5_000_000L) {
            System.out.println("coenable_chars    = " + co.toString().length());
        } else {
            System.out.println("coenable_chars    = SKIPPED (too large to materialise safely)");
        }
    }
}
