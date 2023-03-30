package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;
import java.util.Random;

import javax.crypto.spec.IvParameterSpec;

/**
 * Don't use a 'badly-derived' iv for encryption
 *
 */
public class TestR08 {

	public void execute(boolean fail) throws Exception {
		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {
		Key key = Util.makeKey();
		AlgorithmParameterSpec iv = Util.makeIv();

		Util.encrypt("text_to_encrypt", key, iv);
	}

	private void executeFail() throws Exception {
		Key key = Util.makeKey();

		Random random = new Random();
		byte[] seed = new byte[16];
		random.nextBytes(seed);
		AlgorithmParameterSpec iv = new IvParameterSpec(seed);

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR08().execute(fail);
	}

}
