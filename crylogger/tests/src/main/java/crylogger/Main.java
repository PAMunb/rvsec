package crylogger;

public class Main {
	
	public static void main(String[] args) throws Exception {
		System.err.println(">>>> "+args[0]);
		
		boolean fail = Util.parseArgs(args);
		
		new TestR01().execute(fail);
		new TestR02().execute(fail);
		new TestR03().execute(fail);
		new TestR04().execute(fail);
		new TestR05().execute(fail);
		new TestR06().execute(fail);
		new TestR07().execute(fail);
		new TestR08().execute(fail);
		new TestR09().execute(fail); //breaks 04, 05, 07
		new TestR10().execute(fail);
		
		System.out.println("FINISHED !!!");
	}
	
	
	
}
