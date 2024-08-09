package br.unb.cic.rvsec.taint.reach;

public interface CallGraphFilter {
    boolean isValidEdge(soot.jimple.toolkits.callgraph.Edge edge);
}
