package br.unb.cic.mop.extractor.writer;

import java.io.File;
import java.util.Set;

import br.unb.cic.mop.extractor.model.JcaMethod;

public interface Writer {

	void writeClasses(Set<String> classes, File out);
	void writeMethods(Set<JcaMethod> methods, File out);
	void writeMethods(Set<JcaMethod> methods, File out, boolean withParameters);

}
