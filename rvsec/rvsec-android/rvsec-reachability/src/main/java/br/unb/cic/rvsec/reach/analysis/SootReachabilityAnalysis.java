package br.unb.cic.rvsec.reach.analysis;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Queue;
import java.util.Set;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.reach.model.Path;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class SootReachabilityAnalysis implements ReachabilityAnalysis<SootMethod, Path> {

	private CallGraph callGraph;

	@Override
	public void initialize(CallGraph callGraph, AppInfo appInfo) {
		this.callGraph = callGraph;
	}
	
	@Override
	public Optional<Path> findPath(SootMethod origin, SootMethod destination) {
		List<SootMethod> path = computeBestPath(origin, destination);
		return Optional.of(new Path(path));
	}
	
	//TODO testar ...
	private List<SootMethod> computeBestPath(SootMethod origin, SootMethod destination) {
        Queue<SootMethod> queue = new LinkedList<>();
        Set<SootMethod> visited = new HashSet<>();
        Map<SootMethod, SootMethod> parentMap = new HashMap<>();

        queue.add(origin);
        visited.add(origin);

        while (!queue.isEmpty()) {
            SootMethod currentMethod = queue.poll();

            if (currentMethod.equals(destination)) {
                List<SootMethod> path = new ArrayList<>();
                SootMethod tempMethod = currentMethod;

                while (tempMethod != null) {
                    path.add(0, tempMethod);
                    tempMethod = parentMap.get(tempMethod);
                }

                return path;
            }

            Iterator<Edge> edgeIterator = callGraph.edgesOutOf(currentMethod);

            while (edgeIterator.hasNext()) {
                Edge edge = edgeIterator.next();
                SootMethod targetMethod = edge.tgt();

                if (!visited.contains(targetMethod)) {
                    queue.add(targetMethod);
                    visited.add(targetMethod);
                    parentMap.put(targetMethod, currentMethod);
                }
            }
        }

        return new ArrayList<>();
    }

	@Override
	public boolean isSuccessor(SootMethod source, SootMethod target) {
		Iterator<Edge> edges = callGraph.edgesOutOf(source);
		while(edges.hasNext()) {
			Edge edge = edges.next();
			if(edge.tgt().equals(target)) {
				return true;
			}
		}
		return false;
	}

}
