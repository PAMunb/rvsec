package br.unb.cic.rvsec.reach.analysis;

import java.util.Optional;

import br.unb.cic.rvsec.apk.model.AppInfo;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * Interface for analyzing the reachability of methods in a given application.
 *
 * @param <I> The type of identifier used for methods or other program elements.
 * @param <P> The type of path representing a sequence of methods or program elements.
 */
public interface ReachabilityStrategy<I, P> {

    /**
     * Initializes the analysis with a soot call graph.
     *
     * @param callGraph The call graph representing the relationships between methods.
     */
    void initialize(CallGraph callGraph, AppInfo appInfo);

    /**
     * Finds a path from a source to a target.
     *
     * @param source The source identifier.
     * @param target The target identifier.
     * @return An optional path if a path exists, or Optional.empty() if no path exists.
     */
    Optional<P> findPath(I source, I target);

    /**
     * Checks if a target is a successor of a source in the call graph.
     *
     * @param source The source identifier.
     * @param target The target identifier.
     * @return True if the target is a successor of the source, false otherwise.
     */
    boolean isSuccessor(I source, I target);
    
    
    default boolean isValid(Edge edge, AppInfo appInfo) {
    	return true;
    }
}
