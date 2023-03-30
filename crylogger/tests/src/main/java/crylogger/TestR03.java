package crylogger;

/**
 * Don't use the operation mode ECB with > 1 block
 *
 */
public class TestR03 {

	public void execute(boolean fail) throws Exception {
		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {
	}

	private void executeFail() throws Exception {
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR03().execute(fail);
	}

}
