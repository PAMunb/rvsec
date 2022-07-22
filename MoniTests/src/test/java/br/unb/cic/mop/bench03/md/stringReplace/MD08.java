package br.unb.cic.mop.bench03.md.stringReplace;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD08 {
    public static void main(String[] args) {
        MessageDigest cryptoDigest;
        try {
            cryptoDigest = MessageDigest.getInstance("MD$5".replace("$", ""));
            byte[] out = cryptoDigest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            System.out.println("Error");
        }
    }
}

