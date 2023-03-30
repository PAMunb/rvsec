package crylogger;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;

/**
 * A1: Don't use a short key (< 2048 bits) for RSA
 *
 */
public class TestR19 {

	public void execute(boolean fail) throws Exception {
		if (fail) {
			testR19(1024);
		} else {
			testR19(2048);
		}
	}

	private void testR19(int keySize) throws Exception {
		KeyPair pair = Util.generateKeyPair(keySize);

		String secretMessage = "secret message";
		byte[] encryptedMessageBytes = Util.encrypt(secretMessage, pair.getPublic());

		byte[] decryptedMessageBytes = Util.decrypt(encryptedMessageBytes, pair.getPrivate());
		String decryptedMessage = new String(decryptedMessageBytes, StandardCharsets.UTF_8);

		//assert secretMessage.equals(decryptedMessage);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR19().execute(fail);
	}

}
