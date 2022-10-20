package br.unb.cic.mop.bench01;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.net.ssl.KeyManager;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.KeyStoreBuilderParameters;
import javax.net.ssl.ManagerFactoryParameters;
import java.io.*;
import java.security.*;
import java.security.cert.CertificateException;


public class KeyManagerFactoryTest  {

	private String keyStoreAlgorithm = "JKS";
	private char[] passwordIn = "password".toCharArray();

	private File ksInputFile;
	private InputStream fileIn;

	private ManagerFactoryParameters params;

	@Before
	public void setUp() throws IOException {
		ksInputFile = new File(getClass().getClassLoader().getResource("testInput-ks").getFile());
		fileIn = new FileInputStream(ksInputFile);
		params = new KeyStoreBuilderParameters(KeyStore.Builder.newInstance("JKS",
				Security.getProvider("SUN"),
				ksInputFile, new KeyStore.PasswordProtection("password".toCharArray())));
	}

	@Test
	public void keyManagerFactoryValidTest1() throws NoSuchAlgorithmException, UnrecoverableKeyException, IOException,
			KeyStoreException, CertificateException {

		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		char[] password = null;

		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		keyManagerFactory0.init(keyStore0, password);
		Assertions.hasEnsuredPredicate(keyManagerFactory0);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);

	}

	@Ignore
	public void keyManagerFactoryValidTest2() throws NoSuchAlgorithmException, UnrecoverableKeyException, IOException,
			KeyStoreException, CertificateException, NoSuchProviderException {


		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		char[] password = null;

		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX", (String) null);
		keyManagerFactory0.init(keyStore0, password);
		Assertions.hasEnsuredPredicate(keyManagerFactory0);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);

	}

	@Test
	public void keyManagerFactoryValidTest3() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		keyManagerFactory0.init(params);
		Assertions.hasEnsuredPredicate(keyManagerFactory0);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);
	}

	@Test
	public void keyManagerFactoryValidTest4() throws NoSuchAlgorithmException, UnrecoverableKeyException, IOException,
			KeyStoreException, CertificateException {


		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		char[] password = null;

		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		keyManagerFactory0.init(keyStore0, password);
		KeyManager[] keyManager = keyManagerFactory0.getKeyManagers();
		Assertions.hasEnsuredPredicate(keyManager);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);

	}

	@Test
	public void keyManagerFactoryValidTest5() throws NoSuchAlgorithmException, UnrecoverableKeyException, IOException,
			KeyStoreException, CertificateException, NoSuchProviderException {

		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		char[] password = null;

		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX", "SunJSSE");
		keyManagerFactory0.init(keyStore0, password);
		KeyManager[] keyManager = keyManagerFactory0.getKeyManagers();
		Assertions.hasEnsuredPredicate(keyManager);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);
	}

	@Test
	public void keyManagerFactoryValidTest6() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		keyManagerFactory0.init(params);
		KeyManager[] keyManager = keyManagerFactory0.getKeyManagers();
		Assertions.hasEnsuredPredicate(keyManager);
		Assertions.mustBeInAcceptingState(keyManagerFactory0);
	}

	@Test
	public void keyManagerFactoryInvalidTest1() throws NoSuchAlgorithmException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		Assertions.notHasEnsuredPredicate(keyManagerFactory0);
		Assertions.mustNotBeInAcceptingState(keyManagerFactory0);
	}

	@Test
	public void keyManagerFactoryInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX", "SunJSSE");
		Assertions.notHasEnsuredPredicate(keyManagerFactory0);
		Assertions.mustNotBeInAcceptingState(keyManagerFactory0);
	}

	@Test(expected = IllegalStateException.class)
	public void keyManagerFactoryInvalidTest3() throws NoSuchAlgorithmException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX");
		KeyManager[] keyManager = keyManagerFactory0.getKeyManagers();
		Assertions.notHasEnsuredPredicate(keyManager);
		Assertions.mustNotBeInAcceptingState(keyManagerFactory0);
	}

	/*
	 * This is an interesting case, because the API
	 * throws an exception IllegalStateException when
	 * we call `getKeyManagers()` without having called
	 * the `init` operation. In this case, the API enforces
	 * the constraint.
	 */
	@Test(expected = IllegalStateException.class)
	public void keyManagerFactoryInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {
		KeyManagerFactory keyManagerFactory0 = KeyManagerFactory.getInstance("PKIX", "SunJSSE");
		KeyManager[] keyManager = keyManagerFactory0.getKeyManagers();
		Assertions.notHasEnsuredPredicate(keyManager);
		Assertions.mustNotBeInAcceptingState(keyManagerFactory0);
	}
}