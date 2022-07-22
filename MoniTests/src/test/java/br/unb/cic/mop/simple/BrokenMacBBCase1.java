package br.unb.cic.mop.simple;

import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.Mac;
import java.security.Key;
import java.security.SecureRandom;
import javax.crypto.KeyGenerator;

public class BrokenMacBBCase1 {

    @Test
    public void test() throws Exception {
        Internal i = new Internal();
        i.run();
    }

    class Internal {
        public void run() throws Exception {
            KeyGenerator keyGen = KeyGenerator.getInstance("AES");
            SecureRandom secRandom = new SecureRandom();
            keyGen.init(secRandom);
            Key key = keyGen.generateKey();


            Mac mac = Mac.getInstance("HmacMD5");
            mac.init(key);

            String msg = new String("TSE2021");
            byte[] bytes = msg.getBytes();
            byte[] macResult = mac.doFinal(bytes);
            Assertions.expectingNonEmptySetOfErrors();
        }
    }
}
