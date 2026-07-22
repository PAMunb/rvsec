package crylogger;

/**
 * Don't verify certificates for SSL connections
 *
 */
public class TestR25 {

	public void execute(boolean fail) throws Exception {
		new TestR24().execute(fail);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR25().execute(fail);
	}

}
