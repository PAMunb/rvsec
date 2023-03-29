package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

import javax.crypto.Cipher;

public class TestR05 {
	private static final String ENCRYPTION_KEY = "RwcmlVpg";

	public void execute(boolean fail) throws Exception {
		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {
		Util.simpleGCM("text_to_encrypt");
		//TODO se criar um caso de sucesso (gerando a key com secureRandom) quebra a regra 04, que nao deixa usar o modo CBC
	}

	private void executeFail() throws Exception {
		String alg = "AES/CBC/PKCS5Padding";
		Key key = Util.makeKey(ENCRYPTION_KEY);
		AlgorithmParameterSpec iv = Util.makeIv();

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key, iv);
		cipher.doFinal("text_to_encrypt".getBytes());
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR05().execute(fail);
	}

}
