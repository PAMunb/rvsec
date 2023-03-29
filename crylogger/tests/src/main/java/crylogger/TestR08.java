package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;
import java.util.Random;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;

public class TestR08 {

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
		
		Random random = new Random();
		byte[] seed = new byte[16];		
		random.nextBytes(seed);
		AlgorithmParameterSpec iv = new IvParameterSpec(seed);	

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key, iv);
		cipher.doFinal("text_to_encrypt".getBytes());
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new TestR08().execute(fail);		
	}

}
