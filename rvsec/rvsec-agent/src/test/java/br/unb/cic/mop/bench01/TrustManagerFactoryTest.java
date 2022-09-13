package br.unb.cic.mop.bench01;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.net.ssl.*;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.*;
import java.security.cert.CertSelector;
import java.security.cert.CertificateException;
import java.security.cert.PKIXBuilderParameters;


public class TrustManagerFactoryTest  {

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
	public void trustManagerFactoryValidTest1()
			throws NoSuchAlgorithmException, IOException, KeyStoreException, CertificateException {

		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		trustManagerFactory0.init(keyStore0);
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	@Test
	public void trustManagerFactoryValidTest2() throws NoSuchAlgorithmException, IOException, KeyStoreException,
			CertificateException, NoSuchProviderException {
		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX", "SunJSSE");
		trustManagerFactory0.init(keyStore0);
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	//TODO: we are ignoring this TC here because we do not have an specification
	//   for PKIXBuilderParameters
	@Ignore
	public void trustManagerFactoryValidTest3() throws NoSuchAlgorithmException, IOException, KeyStoreException,
			CertificateException, InvalidAlgorithmParameterException {

		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		CertSelector certSelector = null;

		PKIXBuilderParameters pKIXBuilderParameters0 = new PKIXBuilderParameters(keyStore0, certSelector);
		Assertions.hasEnsuredPredicate(pKIXBuilderParameters0);
		Assertions.mustBeInAcceptingState(pKIXBuilderParameters0);

		CertPathTrustManagerParameters certPathTrustManagerParameters0 = new CertPathTrustManagerParameters(
				pKIXBuilderParameters0);
		Assertions.hasEnsuredPredicate(certPathTrustManagerParameters0);
		Assertions.mustBeInAcceptingState(certPathTrustManagerParameters0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		trustManagerFactory0.init(certPathTrustManagerParameters0);
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	@Test
	public void trustManagerFactoryValidTest4()
			throws NoSuchAlgorithmException, IOException, KeyStoreException, CertificateException {
		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		trustManagerFactory0.init(keyStore0);
		TrustManager[] trustManager = trustManagerFactory0.getTrustManagers();
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	@Test
	public void trustManagerFactoryValidTest5() throws NoSuchAlgorithmException, IOException, KeyStoreException,
			CertificateException, NoSuchProviderException {
		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX", "SunJSSE");
		trustManagerFactory0.init(keyStore0);
		TrustManager[] trustManager = trustManagerFactory0.getTrustManagers();
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	//TODO: we are ignoring this TC here because we do not have an specification
	//   for PKIXBuilderParameters
	@Ignore
	public void trustManagerFactoryValidTest6() throws NoSuchAlgorithmException, IOException, KeyStoreException,
			CertificateException, InvalidAlgorithmParameterException {

		KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
		keyStore0.load(fileIn, passwordIn);
		Assertions.hasEnsuredPredicate(keyStore0);
		Assertions.mustBeInAcceptingState(keyStore0);

		CertSelector certSelector = null;

		PKIXBuilderParameters pKIXBuilderParameters0 = new PKIXBuilderParameters(keyStore0, certSelector);
		Assertions.hasEnsuredPredicate(pKIXBuilderParameters0);
		Assertions.mustBeInAcceptingState(pKIXBuilderParameters0);

		CertPathTrustManagerParameters certPathTrustManagerParameters0 = new CertPathTrustManagerParameters(
				pKIXBuilderParameters0);
		Assertions.hasEnsuredPredicate(certPathTrustManagerParameters0);
		Assertions.mustBeInAcceptingState(certPathTrustManagerParameters0);

		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		trustManagerFactory0.init(certPathTrustManagerParameters0);
		TrustManager[] trustManager = trustManagerFactory0.getTrustManagers();
		Assertions.hasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustBeInAcceptingState(trustManagerFactory0);
	}

	@Test
	public void trustManagerFactoryInvalidTest1() throws NoSuchAlgorithmException {
		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		Assertions.notHasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustNotBeInAcceptingState(trustManagerFactory0);
	}

	@Test
	public void trustManagerFactoryInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {
		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX", "SunJSSE");
		Assertions.notHasEnsuredPredicate(trustManagerFactory0);
		Assertions.mustNotBeInAcceptingState(trustManagerFactory0);
	}

	@Test(expected = java.lang.IllegalStateException.class)
	public void trustManagerFactoryInvalidTest3() throws NoSuchAlgorithmException {
		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
		TrustManager[] trustManager = trustManagerFactory0.getTrustManagers();
		Assertions.notHasEnsuredPredicate(trustManager);
		Assertions.mustNotBeInAcceptingState(trustManagerFactory0);
	}

	@Test(expected = java.lang.IllegalStateException.class)
	public void trustManagerFactoryInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {
		TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX", "SunJSSE");
		TrustManager[] trustManager = trustManagerFactory0.getTrustManagers();
		Assertions.notHasEnsuredPredicate(trustManager);
		Assertions.mustNotBeInAcceptingState(trustManagerFactory0);
	}
}