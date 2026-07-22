package crylogger;

public class Main {

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);

		new TestR01().execute(fail);
		new TestR02().execute(fail);
		new TestR03().execute(fail);
		new TestR04().execute(fail);
		new TestR05().execute(fail);
		new TestR06().execute(fail);
		new TestR07().execute(fail);
		new TestR08().execute(fail);
		new TestR09().execute(fail);
		new TestR10().execute(fail);
		new TestR11().execute(fail);
		new TestR12().execute(fail);
		new TestR13().execute(fail);
		new TestR14().execute(fail);
		new TestR15().execute(fail);
		new TestR16().execute(fail);
		new TestR17().execute(fail); // problem!!!
		new TestR18().execute(fail);
		new TestR19().execute(fail);
		new TestR20().execute(fail);
		new TestR21().execute(fail);
		new TestR22().execute(fail);
		new TestR23().execute(fail);
		new TestR24().execute(fail);
		new TestR25().execute(fail);
		new TestR26().execute(fail);

		System.out.println("FINISHED !!!");
	}

}
