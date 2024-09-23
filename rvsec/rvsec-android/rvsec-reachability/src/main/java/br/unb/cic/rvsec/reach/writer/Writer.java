package br.unb.cic.rvsec.reach.writer;

import br.unb.cic.rvsec.reach.model.RvsecClass;

import java.io.File;
import java.util.Set;

public interface Writer {

    void write(Set<RvsecClass> result, File out);

}
