package br.unb.cic.mop.bench01;

import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.spec.GCMParameterSpec;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

public class GCMParameterSpecTest {

	@Test
	public void gCMParameterSpecValidTest1() throws NoSuchAlgorithmException {

		int num = 0;

		SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
		byte[] genSeed = secureRandom0.generateSeed(num);
		Assertions.hasEnsuredPredicate(genSeed);
		Assertions.mustBeInAcceptingState(secureRandom0);

		GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
		Assertions.hasEnsuredPredicate(gCMParameterSpec0);
		Assertions.mustBeInAcceptingState(gCMParameterSpec0);

	}

	@Test
	public void gCMParameterSpecValidTest2() throws NoSuchAlgorithmException {

		int num = 0;

		SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
		byte[] genSeed = secureRandom0.generateSeed(num);
		Assertions.hasEnsuredPredicate(genSeed);
		Assertions.mustBeInAcceptingState(secureRandom0);

		int offset = 0;
		int len = 0;

		GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed, offset, len);
		Assertions.hasEnsuredPredicate(gCMParameterSpec0);
		Assertions.mustBeInAcceptingState(gCMParameterSpec0);

	}
}