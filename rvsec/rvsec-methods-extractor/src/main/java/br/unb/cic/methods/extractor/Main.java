package br.unb.cic.methods.extractor;

import com.beust.jcommander.JCommander;

import br.unb.cic.methods.extractor.cli.CommandLineArgs;

public class Main {
	
	public static void main(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		
		
		JCommander jc = JCommander.newBuilder().addObject(jArgs).build();
		jc.parse(args);
		
		System.out.println(jArgs);
		
		if(jArgs.isHelp()) {
			jc.usage();
			System.exit(0);
		}		

		new MethodsExtractor().execute(jArgs.getApk(), jArgs.getAppPackage(), jArgs.getAndroidPlatformsDir(), jArgs.getOutputFile(), !jArgs.isIncludeConstructors(), !jArgs.isIncludeStaticInitializers());
	}

}
