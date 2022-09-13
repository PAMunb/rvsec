package br.unb.cic.mop.bench01;

import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.spec.IvParameterSpec;
import java.nio.charset.StandardCharsets;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

public class IvParameterSpecTest {

    @Test
    public void ivParameterSpecValidTest1() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        IvParameterSpec ivParameterSpec0 = new IvParameterSpec(genSeed);
        Assertions.hasEnsuredPredicate(ivParameterSpec0);
        Assertions.mustBeInAcceptingState(ivParameterSpec0);

    }

    @Test
    public void ivParameterSpecValidTest2() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        int offset = 0;
        int len = 0;

        IvParameterSpec ivParameterSpec0 = new IvParameterSpec(genSeed, offset, len);
        Assertions.hasEnsuredPredicate(ivParameterSpec0);
        Assertions.mustBeInAcceptingState(ivParameterSpec0);

    }

    @Test
    public void ivParameterSpecInvalidTest1() throws NoSuchAlgorithmException {
        byte[] genSeed = "abcde".getBytes(StandardCharsets.UTF_8);

        Assertions.notHasEnsuredPredicate(genSeed);

        int offset = 0;
        int len = 0;

        IvParameterSpec ivParameterSpec0 = new IvParameterSpec(genSeed);
        Assertions.notHasEnsuredPredicate(ivParameterSpec0);
        Assertions.mustNotBeInAcceptingState(ivParameterSpec0);

    }
}