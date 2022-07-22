package br.unb.cic.mop.bench03.md.differentCase;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD04 {
    public static void main(String[] args) {
        MessageDigest cryptoDigest;
        try {
            cryptoDigest = MessageDigest.getInstance("md5");
            byte[] out = cryptoDigest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            System.out.println("Error");
        }
    }
}
