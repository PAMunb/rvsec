package crylogger;

import java.security.Key;

import javax.crypto.Cipher;

/**
 * Don't use the operation mode ECB with > 1 block
 *
 */
public class TestR03 {

	public void execute(boolean fail) throws Exception {
		String text = "password";
		Key key = Util.makeKey();

		Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
		cipher.init(Cipher.ENCRYPT_MODE, key);

		if (fail) {
			text = "passwordpasswordpasswordpassword";
		}

		cipher.doFinal(text.getBytes());
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR03().execute(fail);
	}

}
