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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.reach.model.Path;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class SootReachabilityStrategy implements ReachabilityStrategy<SootMethod, Path> {
	private static final Logger log = LoggerFactory.getLogger(SootReachabilityStrategy.class);

	private CallGraph callGraph;

	@Override
	public void initialize(CallGraph callGraph, AppInfo appInfo) {
		log.info("Initializing: "+appInfo.getFileName());
		this.callGraph = callGraph;
	}
	
	@Override
	public Optional<Path> findPath(SootMethod origin, SootMethod destination) {
		List<SootMethod> path = computePath(origin, destination);
		if(isValid(path)) {
			return Optional.of(new Path(path));
		}
		return Optional.empty();
	}
	
	private boolean isValid(List<SootMethod> pathToCheck) {
		return pathToCheck != null && pathToCheck.size() > 1;
	}
	
	private List<SootMethod> computePath(SootMethod origin, SootMethod destination) {
        Queue<SootMethod> queue = new LinkedList<>();
        Set<SootMethod> visited = new HashSet<>();
        Map<SootMethod, SootMethod> parentMap = new HashMap<>();

        queue.add(origin);
        visited.add(origin);

        while (!queue.isEmpty()) {
            SootMethod currentMethod = queue.poll();

            if (currentMethod.equals(destination)) {
				return getPath(currentMethod, parentMap);
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

	private static List<SootMethod> getPath(SootMethod currentMethod, Map<SootMethod, SootMethod> parentMap) {
		List<SootMethod> path = new ArrayList<>();
		SootMethod tempMethod = currentMethod;

		while (tempMethod != null) {
			path.add(0, tempMethod);
			tempMethod = parentMap.get(tempMethod);
		}

		return path;
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
