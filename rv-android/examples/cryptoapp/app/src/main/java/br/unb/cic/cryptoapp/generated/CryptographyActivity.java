package br.unb.cic.cryptoapp.generated;

import android.os.Bundle;
import android.text.TextUtils;
import android.util.Base64;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.tabs.TabLayout;
import com.google.android.material.textfield.TextInputLayout;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import br.unb.cic.cryptoapp.R;

public class CryptographyActivity extends AppCompatActivity {

    // UI Components
    private TabLayout cryptoTabLayout;
    private TextInputLayout inputTextLayout;
    private EditText inputEditText;
    private TextInputLayout keyInputLayout;
    private EditText keyEditText;
    private Spinner algorithmSpinner;
    private RadioGroup modeRadioGroup;
    private TextView resultTextView;
    private Button executeButton;
    private TextView publicKeyTextView;
    private TextView privateKeyTextView;
    private TextView ivTextView;

    // Current tab
    private String currentTab = "Secret Key";

    // Generated keys
    private SecretKey secretKey;
    private KeyPair keyPair;
    private byte[] iv;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_cryptography);

        // Initialize UI components
        initializeViews();
        setupTabLayout();
        setupInputFields();
        setupModeRadioGroup();
        setupExecuteButton();
    }

    private void initializeViews() {
        cryptoTabLayout = findViewById(R.id.cryptoTabLayout);
        inputTextLayout = findViewById(R.id.inputTextLayout);
        inputEditText = findViewById(R.id.inputEditText);
        keyInputLayout = findViewById(R.id.keyInputLayout);
        keyEditText = findViewById(R.id.keyEditText);
        algorithmSpinner = findViewById(R.id.algorithmSpinner);
        modeRadioGroup = findViewById(R.id.modeRadioGroup);
        resultTextView = findViewById(R.id.resultTextView);
        executeButton = findViewById(R.id.executeButton);
        publicKeyTextView = findViewById(R.id.publicKeyTextView);
        privateKeyTextView = findViewById(R.id.privateKeyTextView);
        ivTextView = findViewById(R.id.ivTextView);
    }

    private void setupTabLayout() {
        // Add tabs
        cryptoTabLayout.addTab(cryptoTabLayout.newTab().setText("Secret Key"));
        cryptoTabLayout.addTab(cryptoTabLayout.newTab().setText("Key Pair"));
        cryptoTabLayout.addTab(cryptoTabLayout.newTab().setText("Hash"));
        cryptoTabLayout.addTab(cryptoTabLayout.newTab().setText("HMAC"));

        // Add tab selected listener
        cryptoTabLayout.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override
            public void onTabSelected(TabLayout.Tab tab) {
                currentTab = tab.getText().toString();
                updateUIForTab();
            }

            @Override
            public void onTabUnselected(TabLayout.Tab tab) {
                // Not needed
            }

            @Override
            public void onTabReselected(TabLayout.Tab tab) {
                // Not needed
            }
        });
    }

    private void updateUIForTab() {
        // Clear previous results
        resultTextView.setText("");
        publicKeyTextView.setText("");
        privateKeyTextView.setText("");
        ivTextView.setText("");

        // Update UI based on selected tab
        switch (currentTab) {
            case "Secret Key":
                setupSecretKeyUI();
                break;
            case "Key Pair":
                setupKeyPairUI();
                break;
            case "Hash":
                setupHashUI();
                break;
            case "HMAC":
                setupHmacUI();
                break;
        }
    }

    private void setupSecretKeyUI() {
        // Set visibility
        inputTextLayout.setVisibility(View.VISIBLE);
        keyInputLayout.setVisibility(View.VISIBLE);
        modeRadioGroup.setVisibility(View.VISIBLE);

        // Update labels
        inputTextLayout.setHint("Text to Encrypt/Decrypt");
        keyInputLayout.setHint("Secret Key (leave empty to generate)");

        // Update algorithm spinner
        setupAlgorithmSpinner(new String[]{
                "AES", "DES", "TripleDES", "Blowfish", "RC4"
        });

        // Update mode radio group
        RadioButton encryptRadio = findViewById(R.id.encryptRadioButton);
        RadioButton decryptRadio = findViewById(R.id.decryptRadioButton);
        RadioButton generateRadio = findViewById(R.id.generateRadioButton);

        encryptRadio.setText("Encrypt");
        decryptRadio.setText("Decrypt");
        generateRadio.setText("Generate Secret Key");

        encryptRadio.setVisibility(View.VISIBLE);
        decryptRadio.setVisibility(View.VISIBLE);
        generateRadio.setVisibility(View.VISIBLE);
    }

    private void setupKeyPairUI() {
        // Set visibility
        inputTextLayout.setVisibility(View.VISIBLE);
        keyInputLayout.setVisibility(View.GONE);
        modeRadioGroup.setVisibility(View.VISIBLE);

        // Update labels
        inputTextLayout.setHint("Text to Encrypt/Decrypt/Sign");

        // Update algorithm spinner
        setupAlgorithmSpinner(new String[]{
                "RSA", "DSA", "EC", "DiffieHellman"
        });

        // Update mode radio group
        RadioButton encryptRadio = findViewById(R.id.encryptRadioButton);
        RadioButton decryptRadio = findViewById(R.id.decryptRadioButton);
        RadioButton generateRadio = findViewById(R.id.generateRadioButton);

        encryptRadio.setText("Encrypt/Sign");
        decryptRadio.setText("Decrypt/Verify");
        generateRadio.setText("Generate Key Pair");

        encryptRadio.setVisibility(View.VISIBLE);
        decryptRadio.setVisibility(View.VISIBLE);
        generateRadio.setVisibility(View.VISIBLE);
    }

    private void setupHashUI() {
        // Set visibility
        inputTextLayout.setVisibility(View.VISIBLE);
        keyInputLayout.setVisibility(View.GONE);
        modeRadioGroup.setVisibility(View.GONE);

        // Update labels
        inputTextLayout.setHint("Text to Hash");

        // Update algorithm spinner
        setupAlgorithmSpinner(new String[]{
                "MD5", "SHA-1", "SHA-256", "SHA-384", "SHA-512"
        });
    }

    private void setupHmacUI() {
        // Set visibility
        inputTextLayout.setVisibility(View.VISIBLE);
        keyInputLayout.setVisibility(View.VISIBLE);
        modeRadioGroup.setVisibility(View.GONE);

        // Update labels
        inputTextLayout.setHint("Text to Generate HMAC");
        keyInputLayout.setHint("Secret Key (leave empty to generate)");

        // Update algorithm spinner
        setupAlgorithmSpinner(new String[]{
                "HmacMD5", "HmacSHA1", "HmacSHA256", "HmacSHA384", "HmacSHA512"
        });
    }

    private void setupAlgorithmSpinner(String[] algorithms) {
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_item, algorithms);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        algorithmSpinner.setAdapter(adapter);
    }

    private void setupInputFields() {
        // Default setup
        updateUIForTab();
    }

    private void setupModeRadioGroup() {
        // Set default selection
        modeRadioGroup.check(R.id.encryptRadioButton);
    }

    private void setupExecuteButton() {
        executeButton.setOnClickListener(v -> {
            if (validateInputs()) {
                executeOperation();
            }
        });
    }

    private boolean validateInputs() {
        boolean isValid = true;

        // Validate based on tab and operation
        if (currentTab.equals("Secret Key")) {
            int selectedRadioId = modeRadioGroup.getCheckedRadioButtonId();
            if (selectedRadioId == R.id.encryptRadioButton || selectedRadioId == R.id.decryptRadioButton) {
                // For encryption/decryption, input is required
                if (TextUtils.isEmpty(inputEditText.getText())) {
                    inputTextLayout.setError("Input text is required");
                    isValid = false;
                } else {
                    inputTextLayout.setError(null);
                }

                // For decryption, key is required
                if (selectedRadioId == R.id.decryptRadioButton && TextUtils.isEmpty(keyEditText.getText()) && secretKey == null) {
                    keyInputLayout.setError("Secret key is required for decryption");
                    isValid = false;
                } else {
                    keyInputLayout.setError(null);
                }
            }
        } else if (currentTab.equals("Key Pair")) {
            int selectedRadioId = modeRadioGroup.getCheckedRadioButtonId();
            if (selectedRadioId == R.id.encryptRadioButton || selectedRadioId == R.id.decryptRadioButton) {
                // For encryption/decryption, input is required
                if (TextUtils.isEmpty(inputEditText.getText())) {
                    inputTextLayout.setError("Input text is required");
                    isValid = false;
                } else {
                    inputTextLayout.setError(null);
                }

                // Key pair must exist
                if (keyPair == null) {
                    Toast.makeText(this, "Generate a key pair first", Toast.LENGTH_SHORT).show();
                    isValid = false;
                }
            }
        } else if (currentTab.equals("Hash")) {
            // For hash, input is required
            if (TextUtils.isEmpty(inputEditText.getText())) {
                inputTextLayout.setError("Input text is required");
                isValid = false;
            } else {
                inputTextLayout.setError(null);
            }
        } else if (currentTab.equals("HMAC")) {
            // For HMAC, input is required
            if (TextUtils.isEmpty(inputEditText.getText())) {
                inputTextLayout.setError("Input text is required");
                isValid = false;
            } else {
                inputTextLayout.setError(null);
            }
        }

        return isValid;
    }

    private void executeOperation() {
        try {
            switch (currentTab) {
                case "Secret Key":
                    executeSecretKeyOperation();
                    break;
                case "Key Pair":
                    executeKeyPairOperation();
                    break;
                case "Hash":
                    executeHashOperation();
                    break;
                case "HMAC":
                    executeHmacOperation();
                    break;
            }
        } catch (Exception e) {
            resultTextView.setText("Error: " + e.getMessage());
        }
    }

    private void executeSecretKeyOperation() throws Exception {
        String algorithm = algorithmSpinner.getSelectedItem().toString();
        int selectedRadioId = modeRadioGroup.getCheckedRadioButtonId();

        if (selectedRadioId == R.id.generateRadioButton) {
            // Generate a new secret key
            generateSecretKey(algorithm);
        } else if (selectedRadioId == R.id.encryptRadioButton) {
            // Encrypt the input
            String input = inputEditText.getText().toString();
            String keyString = keyEditText.getText().toString();

            // If key is provided, use it; otherwise use generated key
            if (!TextUtils.isEmpty(keyString)) {
                byte[] keyBytes = keyString.getBytes(StandardCharsets.UTF_8);
                // Use only first 16/24/32 bytes for AES, depending on key size
                if (algorithm.equals("AES")) {
                    keyBytes = Arrays.copyOf(keyBytes, 16); // AES-128
                }
                secretKey = new SecretKeySpec(keyBytes, algorithm);
            } else if (secretKey == null) {
                generateSecretKey(algorithm);
            }

            // Generate IV for algorithms that need it
            if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
                generateIV();
            }

            // Encrypt
            byte[] encrypted = encryptWithSecretKey(input, algorithm);
            String encryptedBase64 = Base64.encodeToString(encrypted, Base64.DEFAULT);
            resultTextView.setText("Encrypted (Base64):\n" + encryptedBase64);

        } else if (selectedRadioId == R.id.decryptRadioButton) {
            // Decrypt the input
            String input = inputEditText.getText().toString();
            String keyString = keyEditText.getText().toString();

            // If key is provided, use it; otherwise use generated key
            if (!TextUtils.isEmpty(keyString)) {
                byte[] keyBytes = keyString.getBytes(StandardCharsets.UTF_8);
                // Use only first 16/24/32 bytes for AES, depending on key size
                if (algorithm.equals("AES")) {
                    keyBytes = Arrays.copyOf(keyBytes, 16); // AES-128
                }
                secretKey = new SecretKeySpec(keyBytes, algorithm);
            } else if (secretKey == null) {
                throw new Exception("No secret key available for decryption");
            }

            // Decrypt
            byte[] inputBytes = Base64.decode(input, Base64.DEFAULT);
            String decrypted = decryptWithSecretKey(inputBytes, algorithm);
            resultTextView.setText("Decrypted:\n" + decrypted);
        }
    }

    private void generateSecretKey(String algorithm) throws Exception {
        int keySize;

        // Determine key size based on algorithm
        switch (algorithm) {
            case "AES":
                keySize = 128; // AES-128
                break;
            case "DES":
                keySize = 56;
                break;
            case "TripleDES":
                keySize = 168;
                break;
            case "Blowfish":
                keySize = 128;
                break;
            case "RC4":
                keySize = 128;
                break;
            default:
                keySize = 128;
        }

        // Generate key
        KeyGenerator keyGen = KeyGenerator.getInstance(algorithm);
        keyGen.init(keySize);
        secretKey = keyGen.generateKey();

        // Generate IV for algorithms that need it
        if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
            generateIV();
        }

        // Display key information
        String keyBase64 = Base64.encodeToString(secretKey.getEncoded(), Base64.DEFAULT);
        resultTextView.setText("Generated Secret Key (Base64):\n" + keyBase64);

        // Display IV if generated
        if (iv != null) {
            String ivBase64 = Base64.encodeToString(iv, Base64.DEFAULT);
            ivTextView.setText("IV (Base64):\n" + ivBase64);
        }
    }

    private void generateIV() {
        // Generate a secure random IV
        SecureRandom random = new SecureRandom();
        iv = new byte[16]; // 16 bytes for AES
        random.nextBytes(iv);
    }

    private byte[] encryptWithSecretKey(String input, String algorithm) throws Exception {
        Cipher cipher;

        // Initialize cipher based on algorithm
        if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
            // Block ciphers that need an IV
            String transformation = algorithm + "/CBC/PKCS5Padding";
            cipher = Cipher.getInstance(transformation);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, new IvParameterSpec(iv));
        } else {
            // Stream ciphers or other block ciphers
            cipher = Cipher.getInstance(algorithm);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        }

        // Encrypt
        return cipher.doFinal(input.getBytes(StandardCharsets.UTF_8));
    }

    private String decryptWithSecretKey(byte[] input, String algorithm) throws Exception {
        Cipher cipher;

        // Initialize cipher based on algorithm
        if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
            // Block ciphers that need an IV
            String transformation = algorithm + "/CBC/PKCS5Padding";
            cipher = Cipher.getInstance(transformation);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, new IvParameterSpec(iv));
        } else {
            // Stream ciphers or other block ciphers
            cipher = Cipher.getInstance(algorithm);
            cipher.init(Cipher.DECRYPT_MODE, secretKey);
        }

        // Decrypt
        byte[] decrypted = cipher.doFinal(input);
        return new String(decrypted, StandardCharsets.UTF_8);
    }

    private void executeKeyPairOperation() throws Exception {
        String algorithm = algorithmSpinner.getSelectedItem().toString();
        int selectedRadioId = modeRadioGroup.getCheckedRadioButtonId();

        if (selectedRadioId == R.id.generateRadioButton) {
            // Generate a new key pair
            generateKeyPair(algorithm);
        } else if (selectedRadioId == R.id.encryptRadioButton) {
            // Encrypt/sign with private key
            String input = inputEditText.getText().toString();

            if (algorithm.equals("RSA")) {
                // Encrypt with public key
                byte[] encrypted = encryptWithPublicKey(input);
                String encryptedBase64 = Base64.encodeToString(encrypted, Base64.DEFAULT);
                resultTextView.setText("Encrypted (Base64):\n" + encryptedBase64);
            } else {
                // Other algorithms would be for signing, but we're keeping it simple
                resultTextView.setText("Signing not implemented for this demo");
            }
        } else if (selectedRadioId == R.id.decryptRadioButton) {
            // Decrypt/verify with public key
            String input = inputEditText.getText().toString();

            if (algorithm.equals("RSA")) {
                // Decrypt with private key
                byte[] inputBytes = Base64.decode(input, Base64.DEFAULT);
                String decrypted = decryptWithPrivateKey(inputBytes);
                resultTextView.setText("Decrypted:\n" + decrypted);
            } else {
                // Other algorithms would be for verification, but we're keeping it simple
                resultTextView.setText("Verification not implemented for this demo");
            }
        }
    }

    private void generateKeyPair(String algorithm) throws Exception {
        int keySize;

        // Determine key size based on algorithm
        switch (algorithm) {
            case "RSA":
                keySize = 2048;
                break;
            case "DSA":
                keySize = 1024;
                break;
            case "EC":
                keySize = 256;
                break;
            case "DiffieHellman":
                keySize = 2048;
                break;
            default:
                keySize = 2048;
        }

        // Generate key pair
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance(algorithm);
        keyGen.initialize(keySize);
        keyPair = keyGen.generateKeyPair();

        // Display key information
        String publicKeyBase64 = Base64.encodeToString(keyPair.getPublic().getEncoded(), Base64.DEFAULT);
        String privateKeyBase64 = Base64.encodeToString(keyPair.getPrivate().getEncoded(), Base64.DEFAULT);

        publicKeyTextView.setText("Public Key (Base64):\n" + publicKeyBase64);
        privateKeyTextView.setText("Private Key (Base64):\n" + privateKeyBase64);
        resultTextView.setText("Key pair generated successfully");
    }

    private byte[] encryptWithPublicKey(String input) throws Exception {
        // Encrypt with the public key (RSA)
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keyPair.getPublic());
        return cipher.doFinal(input.getBytes(StandardCharsets.UTF_8));
    }

    private String decryptWithPrivateKey(byte[] input) throws Exception {
        // Decrypt with the private key (RSA)
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.DECRYPT_MODE, keyPair.getPrivate());
        byte[] decrypted = cipher.doFinal(input);
        return new String(decrypted, StandardCharsets.UTF_8);
    }

    private void executeHashOperation() throws Exception {
        String algorithm = algorithmSpinner.getSelectedItem().toString();
        String input = inputEditText.getText().toString();

        // Create message digest
        MessageDigest md = MessageDigest.getInstance(algorithm);
        byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));

        // Convert to hex string
        StringBuilder hexString = new StringBuilder();
        for (byte b : digest) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }

        resultTextView.setText(algorithm + " Hash:\n" + hexString.toString());
    }

    private void executeHmacOperation() throws Exception {
        String algorithm = algorithmSpinner.getSelectedItem().toString();
        String input = inputEditText.getText().toString();
        String keyString = keyEditText.getText().toString();

        // Get or generate key
        SecretKey hmacKey;
        if (!TextUtils.isEmpty(keyString)) {
            byte[] keyBytes = keyString.getBytes(StandardCharsets.UTF_8);
            hmacKey = new SecretKeySpec(keyBytes, algorithm);
        } else {
            // Generate a random key
            KeyGenerator keyGen = KeyGenerator.getInstance(algorithm);
            hmacKey = keyGen.generateKey();

            // Display the generated key
            String keyBase64 = Base64.encodeToString(hmacKey.getEncoded(), Base64.DEFAULT);
            keyEditText.setText(keyBase64);
        }

        // Initialize Mac
        Mac mac = Mac.getInstance(algorithm);
        mac.init(hmacKey);

        // Compute HMAC
        byte[] hmac = mac.doFinal(input.getBytes(StandardCharsets.UTF_8));

        // Convert to hex string
        StringBuilder hexString = new StringBuilder();
        for (byte b : hmac) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }

        resultTextView.setText(algorithm + " HMAC:\n" + hexString.toString());
    }
}