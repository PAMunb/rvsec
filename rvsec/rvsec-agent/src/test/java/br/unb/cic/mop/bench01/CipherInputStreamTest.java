package br.unb.cic.mop.bench01;

import br.unb.cic.misc.Assertions;
import br.unb.cic.mop.eh.ErrorCollector;

import org.junit.Before;
import org.junit.Test;

import javax.crypto.Cipher;
import javax.crypto.CipherInputStream;
import javax.crypto.CipherOutputStream;
import javax.crypto.KeyGenerator;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.security.Key;

public class CipherInputStreamTest {

    @Before
    public void setUp() {
        ErrorCollector.instance().reset();
    }

    @Test
    public void simpleTest() throws Exception {
        KeyGenerator keygen = KeyGenerator.getInstance("AES");
        Key k = keygen.generateKey();

        Cipher aes = Cipher.getInstance("AES/ECB/PKCS5Padding");
        aes.init(Cipher.ENCRYPT_MODE, k);
        FileOutputStream fs = new FileOutputStream(getClass().getClassLoader().getResource("texto.txt").getFile());
        CipherOutputStream out = new CipherOutputStream(fs, aes);
        out.write("[Hello:Okay]\nOkay".getBytes());
        out.close();

        Cipher aes2 = Cipher.getInstance("AES/ECB/PKCS5Padding");
        aes2.init(Cipher.DECRYPT_MODE, k);

        byte[] arr = new byte[100];
        FileInputStream fis = new FileInputStream(getClass().getClassLoader().getResource("texto.txt").getFile());
        CipherInputStream in = new CipherInputStream(fis, aes2);
        in.read(arr, 0, 10);

        in.close();
        Assertions.expectingNonEmptySetOfErrors();
    }

    @Test
    public void invalidSequence() throws Exception {
        KeyGenerator keygen = KeyGenerator.getInstance("AES");
        Key k = keygen.generateKey();


        Cipher aes = Cipher.getInstance("AES/CBC/PKCS5Padding");
        aes.init(Cipher.ENCRYPT_MODE, k);
        FileOutputStream fs = new FileOutputStream(getClass().getClassLoader().getResource("texto.txt").getFile());
        CipherOutputStream out = new CipherOutputStream(fs, aes);
        out.write("[Hello:Okay]\nOkay".getBytes());
        out.close();

        Cipher aes2 = Cipher.getInstance("AES/ECB/PKCS5Padding");
        aes2.init(Cipher.DECRYPT_MODE, k);

        byte[] arr = new byte[100];
        FileInputStream fis = new FileInputStream(getClass().getClassLoader().getResource("texto.txt").getFile());
        CipherInputStream in = new CipherInputStream(fis, aes2);
        in.read(arr, 0, 10);

        Assertions.expectingNonEmptySetOfErrors();
    }
}
