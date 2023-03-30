package crylogger;

import java.net.URL;

public class TestR22 {

	public void execute(boolean fail) throws Exception {
		String str = "https://www.google.com";

		if (fail) {
			str = "http://www.google.com";
		}

		new URL(str);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR22().execute(fail);
	}

}
