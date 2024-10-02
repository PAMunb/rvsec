package br.unb.cic.rvsec.reach.writer;

import java.io.File;
import java.util.Set;

import br.unb.cic.rvsec.reach.model.RvsecClass;

public interface Writer {

    void write(Set<RvsecClass> result, File out);

}
