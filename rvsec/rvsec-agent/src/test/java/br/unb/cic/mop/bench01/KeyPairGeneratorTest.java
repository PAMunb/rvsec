package br.unb.cic.mop.bench01;

import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.spec.DHGenParameterSpec;
import java.security.*;

public class KeyPairGeneratorTest {

	@Test
	public void keyPairGeneratorValidTest1() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(4096);
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorValidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA", "SunRsaSign");
		keyPairGenerator0.initialize(4096);
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorValidTest3() throws NoSuchAlgorithmException {
		SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(4096, secureRandom0);
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Ignore("Could not find a fix for DHGen")
	public void keyPairGeneratorValidTest4() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

		int exponentSize = 0;
		int primeSize = 0;

		DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
		Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
		Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(dHGenParameterSpec0);
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Ignore("Could not find a fix for DHGen")
	public void keyPairGeneratorValidTest5() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

		int exponentSize = 0;
		int primeSize = 0;

		DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
		Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
		Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(dHGenParameterSpec0, (SecureRandom) null);
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorValidTest6() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(4096);
		KeyPair keyPair = keyPairGenerator0.genKeyPair();
		Assertions.hasEnsuredPredicate(keyPair);
		Assertions.mustBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest1() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA", "SunRsaSign");
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest3() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(4096);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA", "SunRsaSign");
		keyPairGenerator0.initialize(4096);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest5() throws NoSuchAlgorithmException {
		SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(4096, secureRandom0);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Ignore("Could not find a fix for DHGen")
	public void keyPairGeneratorInvalidTest6() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

		int exponentSize = 0;
		int primeSize = 0;

		DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
		Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
		Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(dHGenParameterSpec0);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Ignore("Could not find a fix for DHGen")
	public void keyPairGeneratorInvalidTest7() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

		int exponentSize = 0;
		int primeSize = 0;

		DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
		Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
		Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		keyPairGenerator0.initialize(dHGenParameterSpec0, (SecureRandom) null);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest8() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.notHasEnsuredPredicate(keyPair);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest9() throws NoSuchAlgorithmException, NoSuchProviderException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA", "SunRsaSign");
		KeyPair keyPair = keyPairGenerator0.generateKeyPair();
		Assertions.notHasEnsuredPredicate(keyPair);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}

	@Test
	public void keyPairGeneratorInvalidTest10() throws NoSuchAlgorithmException {

		KeyPairGenerator keyPairGenerator0 = KeyPairGenerator.getInstance("RSA");
		KeyPair keyPair = keyPairGenerator0.genKeyPair();
		Assertions.notHasEnsuredPredicate(keyPair);
		Assertions.mustNotBeInAcceptingState(keyPairGenerator0);

	}
}