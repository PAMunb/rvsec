package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

import javax.crypto.Cipher;

public class TestR07 {
	private static final String ENCRYPTION_IV = "4e5Wa71fYoT7MFEX";

	public void execute(boolean fail) throws Exception {		
		if(fail) {
			executeFail();
		} else {
			executeSuccess();
		}		
	}
	
	private void executeSuccess() throws Exception {
		Util.simpleGCM("text_to_encrypt");
	}

	private void executeFail() throws Exception {
		String alg = "AES/CBC/PKCS5Padding";
		Key key = Util.makeKey();
		AlgorithmParameterSpec iv = Util.makeIv(ENCRYPTION_IV);

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key, iv);
		cipher.doFinal("text_to_encrypt".getBytes());
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new TestR07().execute(fail);		
	}

}
