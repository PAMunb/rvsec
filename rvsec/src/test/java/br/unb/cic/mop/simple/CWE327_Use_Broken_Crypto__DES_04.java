/* TEMPLATE GENERATED TESTCASE FILE
Filename: CWE327_Use_Broken_Crypto__DES_04.java
Label Definition File: CWE327_Use_Broken_Crypto.label.xml
Template File: point-flaw-04.tmpl.java
*/
/*
* @description
* CWE: 327 Use of Broken or Risky Cryptographic Algorithm
* Sinks: DES
*    GoodSink: use AES
*    BadSink : use DES
* Flow Variant: 04 Control flow: if(PRIVATE_STATIC_FINAL_TRUE) and if(PRIVATE_STATIC_FINAL_FALSE)
*
* */

package br.unb.cic.mop.simple;


import br.unb.cic.misc.Assertions;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.eh.ErrorCollector;
import org.junit.Before;
import org.junit.Test;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

public class CWE327_Use_Broken_Crypto__DES_04
{
    /* The two variables below are declared "final", so a tool should
     * be able to identify that reads of these will always return their
     * initialized values.
     */
    private static final boolean PRIVATE_STATIC_FINAL_TRUE = true;
    private static final boolean PRIVATE_STATIC_FINAL_FALSE = false;

    @Before
    public void setup() {
        ErrorCollector.instance().reset();
    }

    @Test
    public void bad() throws Throwable
    {
        if (PRIVATE_STATIC_FINAL_TRUE)
        {
            final String CIPHER_INPUT = "ABCDEFG123456";
            KeyGenerator keyGenerator = KeyGenerator.getInstance("DES");
            /* Perform initialization of KeyGenerator */
            keyGenerator.init(56);
            SecretKey secretKey = keyGenerator.generateKey();
            byte[] byteKey = secretKey.getEncoded();
            /* FLAW: Use a weak crypto algorithm, DES */
            SecretKeySpec secretKeySpec = new SecretKeySpec(byteKey, "DES");
            Cipher desCipher = Cipher.getInstance("DES");
            desCipher.init(Cipher.ENCRYPT_MODE, secretKeySpec);
            byte[] encrypted = desCipher.doFinal(CIPHER_INPUT.getBytes("UTF-8"));
            Assertions.expectingNonEmptySetOfErrors();
        }
    }

    /* good1() changes PRIVATE_STATIC_FINAL_TRUE to PRIVATE_STATIC_FINAL_FALSE */
    @Test
    public void good1() throws Throwable {
        if (PRIVATE_STATIC_FINAL_FALSE)
        {
            /* INCIDENTAL: CWE 561 Dead Code, the code below will never run */
            // IO.writeLine("Benign, fixed string");
        }
        else
        {

            final String CIPHER_INPUT = "ABCDEFG123456";

            KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");

            /* Perform initialization of KeyGenerator */
            keyGenerator.init(128);

            SecretKey secretKey = keyGenerator.generateKey();
            byte[] byteKey = secretKey.getEncoded();


            /* FIX: Use a stronger crypto algorithm, AES */
            SecretKeySpec secretKeySpec = new SecretKeySpec(byteKey, "AES");

            Cipher aesCipher = Cipher.getInstance("AES/GCM/NoPadding");
            aesCipher.init(Cipher.ENCRYPT_MODE, secretKeySpec);

            byte[] encrypted = aesCipher.doFinal(CIPHER_INPUT.getBytes("UTF-8"));

            Assertions.expectingEmptySetOfErrors();
        }
    }

    /* good2() reverses the bodies in the if statement */
    @Test
    public void good2() throws Throwable {
        if (PRIVATE_STATIC_FINAL_TRUE)
        {
            final String CIPHER_INPUT = "ABCDEFG123456";

            KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
            Assertions.expectingEmptySetOfErrors();

            /* Perform initialization of KeyGenerator */
            keyGenerator.init(128);
            Assertions.expectingEmptySetOfErrors();

            SecretKey secretKey = keyGenerator.generateKey();
            Assertions.expectingEmptySetOfErrors();

            byte[] byteKey = secretKey.getEncoded();
            Assertions.expectingEmptySetOfErrors();
            Assertions.assertTrue(ExecutionContext.instance().validate(ExecutionContext.Property.RANDOMIZED, byteKey));

            /* FIX: Use a stronger crypto algorithm, AES */
            SecretKeySpec secretKeySpec = new SecretKeySpec(byteKey, "AES");
            Cipher aesCipher = Cipher.getInstance("AES/GCM/NoPadding");
            aesCipher.init(Cipher.ENCRYPT_MODE, secretKeySpec);
            byte[] encrypted = aesCipher.doFinal(CIPHER_INPUT.getBytes("UTF-8"));

            Assertions.expectingEmptySetOfErrors();
        }
    }
}
