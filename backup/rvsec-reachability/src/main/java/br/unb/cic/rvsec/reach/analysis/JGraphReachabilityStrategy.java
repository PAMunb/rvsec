package br.unb.cic.rvsec.reach.analysis;

import java.util.Optional;

import org.jgrapht.Graph;
import org.jgrapht.GraphPath;
import org.jgrapht.alg.shortestpath.DijkstraShortestPath;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.reach.model.Path;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

public class JGraphReachabilityStrategy implements ReachabilityStrategy<SootMethod, Path> {
	private static final Logger log = LoggerFactory.getLogger(JGraphReachabilityStrategy.class);
	
	private Graph<SootMethod, DefaultEdge> graph;
	private DijkstraShortestPath<SootMethod, DefaultEdge> dijkstra;
	
	@Override
	public void initialize(CallGraph callGraph, AppInfo appInfo) {
		graph = toJGraph(callGraph, appInfo);
		dijkstra = new DijkstraShortestPath<>(graph);
	}
	
	@Override
	public Optional<Path> findPath(SootMethod source, SootMethod target) {
		try {
			GraphPath<SootMethod, DefaultEdge> path = dijkstra.getPath(source, target);
			if (path != null) {
				return Optional.of(new Path(path.getVertexList()));
			}
		} catch (Exception ignored) {
		}
		return Optional.empty();
	}

	@Override
	public boolean isSuccessor(SootMethod source, SootMethod target) {
		return graph.containsEdge(source, target);
	}

	private Graph<SootMethod, DefaultEdge> toJGraph(CallGraph callGraph, AppInfo appInfo) {
		Graph<SootMethod, DefaultEdge> g = new DefaultDirectedGraph<>(DefaultEdge.class);
		log.debug("CallGraph (soot) = " + callGraph.size());
		for (Edge edge : callGraph) {
			if (isValid(edge, appInfo)) {
				g.addVertex(edge.src());
				g.addVertex(edge.tgt());
//				if (g.containsEdge(edge.src(), edge.tgt())) {
//					System.out.println("******************* JA CONTEM");
//				}
				g.addEdge(edge.src(), edge.tgt());
			}
		}
		log.debug("CallGraph (jgraph) = " + g.edgeSet().size());
		return g;
	}
	
	
	@Override
	public boolean isValid(Edge edge, AppInfo appInfo) {
		//AndroidUtil.isClassInApplicationPackage(edge.src().getDeclaringClass(), appInfo);
        return !edge.src().equals(edge.tgt());
    }
	
}
