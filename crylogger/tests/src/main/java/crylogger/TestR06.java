package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;
import java.util.Random;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class TestR06 {

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
		AlgorithmParameterSpec iv = Util.makeIv();
		
		Random random = new Random();
		byte[] seed = new byte[32];			
		random.nextBytes(seed);
		Key key = new SecretKeySpec(seed, "AES");

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key, iv);
		cipher.doFinal("text_to_encrypt".getBytes());
		
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new TestR06().execute(fail);		
	}

}
