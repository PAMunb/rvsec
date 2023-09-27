package br.unb.cic.mop.extractor;

import java.io.File;
import java.util.Set;

import com.beust.jcommander.JCommander;

import br.unb.cic.mop.extractor.cli.CommandLineArgs;
import br.unb.cic.mop.extractor.cli.CommandLineArgs.TYPE;
import br.unb.cic.mop.extractor.model.JcaMethod;
import br.unb.cic.mop.extractor.writer.Writer;

public class Main {

	public static void main(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		JCommander.newBuilder().addObject(jArgs).build().parse(args);

		JavamopFacade facade = new JavamopFacade();
		Writer writer = jArgs.getWriter().getWriter();
		try {
			if (jArgs.getType() == TYPE.CLASSES) {
				Set<String> classes = facade.listUsedClasses(jArgs.getMopSpecsDir());
				writer.writeClasses(classes, new File(jArgs.getOutputFile()));
			} else {
				Set<JcaMethod> methods = facade.listUsedMethods(jArgs.getMopSpecsDir());
				boolean withParams = false;
				if (jArgs.getType() == TYPE.METHODS_PARAMS) {
					withParams = true;
				}
				writer.writeMethods(methods, new File(jArgs.getOutputFile()), withParams);
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

}
