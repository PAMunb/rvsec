package br.unb.cic.rvsec.reach.analysis;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.PriorityQueue;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.util.AndroidUtil;
import br.unb.cic.rvsec.reach.model.Path;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

@Deprecated
public class TesteReachabilityStrategy implements ReachabilityStrategy<SootMethod, Path> {
	private static final Logger log = LoggerFactory.getLogger(TesteReachabilityStrategy.class);

	private Graph graph;
	
	@Override
	public void initialize(CallGraph callGraph, AppInfo appInfo) {
		log.info("Initializing TesteReachabilityStrategy ...");
		graph = convertCallGraph(callGraph, appInfo);
	}

	@Override
	public Optional<Path> findPath(SootMethod source, SootMethod target) {
//		log.debug("findPath ::: "+source.getSignature()+" ===>>> "+target.getSignature());
//		List<SootMethod> path = shortestPath(source, target);
		List<SootMethod> path = dijkstra(source, target);
		if (path != null) {
			return Optional.of(new Path(path));
		}
		return Optional.empty();
	}

	@Override
	public boolean isSuccessor(SootMethod source, SootMethod target) {
		return graph.isSuccessor(source, target);
	}
	
	private Graph convertCallGraph(CallGraph callGraph, AppInfo appInfo) {
		log.debug("Converting callgraph (soot) to custom graph");
        Graph g = new Graph();
        for (Edge edge : callGraph) {
			if (isValid(edge, appInfo)) {
//				g.addNode(edge.src());
//				g.addNode(edge.tgt());
				g.addEdge(edge.src(), edge.tgt());
			}
		}
        return g;
    }
	
	@Override
	public boolean isValid(Edge edge, AppInfo appInfo) {
		return AndroidUtil.isClassInApplicationPackage(edge.src().getDeclaringClass(), appInfo);
	}
	
	public List<SootMethod> dijkstra(SootMethod start, SootMethod end) {
        // Map to store the shortest path to each node
        Map<SootMethod, List<SootMethod>> paths = new HashMap<>();
        // Priority queue for processing nodes
        PriorityQueue<SootMethod> queue = new PriorityQueue<>(Comparator.comparingInt(a -> paths.get(a).size()));
//        PriorityQueue<SootMethod> queue = new PriorityQueue<>((a, b) -> 0); // Heurística A* pode ser adicionada aqui
        // Set to keep track of visited nodes
        Set<SootMethod> visited = new HashSet<>();

        // Initialize the start node
        paths.put(start, new ArrayList<>(Collections.singletonList(start)));
        queue.add(start);

        while (!queue.isEmpty()) {
            SootMethod current = queue.poll();
            visited.add(current);

            if (current.equals(end)) {
                return paths.get(current);
            }

            for (SootMethod neighbor : getNeighbors(current)) {
                if (!visited.contains(neighbor)) {
                    List<SootMethod> newPath = new ArrayList<>(paths.get(current));
                    newPath.add(neighbor);

                    // If this path is shorter, update the map and add to the queue
                    if (!paths.containsKey(neighbor) || newPath.size() < paths.get(neighbor).size()) {
                        paths.put(neighbor, newPath);
                        queue.add(neighbor);
                    }
                }
            }
        }
        
        return Collections.emptyList(); // Return empty if no path found
    }
	
	private Set<SootMethod> getNeighbors(SootMethod method) {
		return graph.getAdjacencyList().getOrDefault(method, new HashSet<>());
	}

	private List<SootMethod> shortestPath(SootMethod origem, SootMethod destino) {
//		log.debug("shortestPath .......................");
    	if(graph == null) {
    		return Collections.emptyList();
    	}    	
    	Map<SootMethod,Set<SootMethod>> adjacencia = graph.getAdjacencyList();
    	
		Map<SootMethod, Integer> distancia = new HashMap<>();
		Map<SootMethod, SootMethod> predecessor = new HashMap<>();
        Set<SootMethod> visitados = new HashSet<>();
        PriorityQueue<SootMethod> fronteira = new PriorityQueue<>((a, b) -> 0); // Heurística A* pode ser adicionada aqui

        // Inicialização
        distancia.put(origem, 0);
        fronteira.add(origem);

        while (!fronteira.isEmpty()) {
            SootMethod atual = fronteira.poll();
            if (visitados.contains(atual)) {
                continue;
            }
            visitados.add(atual);

            if (atual.equals(destino)) {
                // Caminho encontrado
            	// Reconstruir o caminho
                return extracted(destino, predecessor);
            }

            for (SootMethod vizinho : adjacencia.getOrDefault(atual, Collections.emptySet())) {
                if (!visitados.contains(vizinho)) { // Evitar ciclos
                	int novaDistancia = distancia.get(atual) + 1; // Como não temos pesos, a distância é sempre +1
                    if (!distancia.containsKey(vizinho) || novaDistancia < distancia.get(vizinho)) {
                        distancia.put(vizinho, novaDistancia);
                        predecessor.put(vizinho, atual);
                        fronteira.add(vizinho);
                    }
                }
            }
        }
        
        return Collections.emptyList();
	}

	private List<SootMethod> extracted(SootMethod destino, Map<SootMethod, SootMethod> predecessor) {
		List<SootMethod> caminho = new ArrayList<>();
        SootMethod atual = destino;
        while (atual != null) {
            caminho.add(0, atual);
            atual = predecessor.get(atual);
        }
        return caminho;
	}

//    private List<SootMethod> shortestPathOld(SootMethod source, SootMethod destination) {
//    	log.debug("shortestPath .......................");
//    	if(graph == null) {
//    		return Collections.emptyList();
//    	}    	
//    	Map<SootMethod,List<SootMethod>> adjacencyList = graph.getAdjacencyList();
//        Map<SootMethod,Map<SootMethod,Integer>> weights = graph.getWeights();
//    	
//        Map<SootMethod, Integer> distances = new HashMap<>();
//        Map<SootMethod, SootMethod> previous = new HashMap<>();
//        PriorityQueue<SootMethod> queue = new PriorityQueue<>(Comparator.comparingInt(distances::get));
//
//        for (SootMethod node : adjacencyList.keySet()) {
//            distances.put(node, Integer.MAX_VALUE);
//            previous.put(node, null);
//        }
//        distances.put(source, 0);
//        queue.add(source);
//
//        while (!queue.isEmpty()) {
//            SootMethod currentNode = queue.poll();
//            log.trace("shortestPath ::: currentNode="+currentNode);
//            if (currentNode.equals(destination)) {
//                List<SootMethod> path = new ArrayList<>();
//                while (currentNode != null) {
//                    path.add(0, currentNode);
//                    currentNode = previous.get(currentNode);
//                }
//                log.trace("shortestPath ::: ACHOU ................................");
//                return path;
//            }
//            List<SootMethod> list = adjacencyList.get(currentNode);
//            log.trace("shortestPath ::: list="+list);
//			for (SootMethod neighbor : list) {
//                int newDistance = distances.get(currentNode) + weights.get(currentNode).get(neighbor);
//                if (newDistance < distances.get(neighbor)) {
//                    distances.put(neighbor, newDistance);
//                    previous.put(neighbor, currentNode);
//                    queue.add(neighbor);
//                }
//            }
//        }
//        return Collections.emptyList();
//    }

	
	class Graph {
		private final Map<SootMethod, Set<SootMethod>> adjacencyList;

		Graph() {
			this.adjacencyList = new HashMap<>();
		}

		void addEdge(SootMethod source, SootMethod destination) {
			adjacencyList.computeIfAbsent(source, k -> new HashSet<>()).add(destination);
		}
		
		public boolean isSuccessor(SootMethod source, SootMethod target) {
			Set<SootMethod> successors = adjacencyList.get(source);
			if(successors != null) {
				return successors.contains(target);
			}
			return false;
		}

		public Map<SootMethod, Set<SootMethod>> getAdjacencyList() {
			return adjacencyList;
		}
		
	}

}
