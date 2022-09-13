package mop;
import javax.crypto.CipherInputStream;
import java.io.InputStream;
import javax.crypto.Cipher;
import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import javax.crypto.CipherOutputStream;
import java.io.OutputStream;
import java.security.Provider;
import java.security.Key;
import java.security.SecureRandom;
import java.security.spec.AlgorithmParameterSpec;
import java.nio.ByteBuffer;
import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*;
import javax.crypto.spec.DHGenParameterSpec;
import javax.crypto.spec.GCMParameterSpec;
import javax.xml.crypto.dsig.spec.HMACParameterSpec;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.ManagerFactoryParameters;
import javax.net.ssl.KeyManager;
import java.security.KeyStore;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.KeyStore.ProtectionParameter;
import java.security.KeyStore.Entry;
import javax.crypto.Mac;
import java.security.MessageDigest;
import java.util.List;
import br.unb.cic.mop.ExecutionContext.Property;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.PBEParameterSpec;
import java.util.stream.IntStream;
import javax.crypto.spec.SecretKeySpec;
import java.security.Signature;
import java.security.cert.Certificate;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
import java.util.*;
import java.lang.ref.*;
import com.runtimeverification.rvmonitor.java.rt.*;
import com.runtimeverification.rvmonitor.java.rt.ref.*;
import com.runtimeverification.rvmonitor.java.rt.table.*;
import com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractIndexingTree;
import com.runtimeverification.rvmonitor.java.rt.tablebase.SetEventDelegator;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TableAdopter.Tuple2;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TableAdopter.Tuple3;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IDisableHolder;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IMonitor;
import com.runtimeverification.rvmonitor.java.rt.tablebase.DisableHolder;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TerminatedMonitorCleaner;
import java.util.concurrent.atomic.AtomicInteger;

final class CipherInputStreamSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<CipherInputStreamSpecMonitor> {

	CipherInputStreamSpecMonitor_Set(){
		this.size = 0;
		this.elements = new CipherInputStreamSpecMonitor[4];
	}
	final void event_c1() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherInputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherInputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1();
				if(monitorfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_r1() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherInputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherInputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_r1();
				if(monitorfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_r2(byte[] arr, int offset, int len) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherInputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherInputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_r2(arr, offset, len);
				if(monitorfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_cl1() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherInputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherInputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_cl1();
				if(monitorfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class CipherOutputStreamSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<CipherOutputStreamSpecMonitor> {

	CipherOutputStreamSpecMonitor_Set(){
		this.size = 0;
		this.elements = new CipherOutputStreamSpecMonitor[4];
	}
	final void event_c1() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherOutputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherOutputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1();
				if(monitorfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_w1() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherOutputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherOutputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_w1();
				if(monitorfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_w2(byte[] b, int off, int len) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherOutputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherOutputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_w2(b, off, len);
				if(monitorfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_fl() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherOutputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherOutputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_fl();
				if(monitorfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_cl() {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherOutputStreamSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherOutputStreamSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_cl();
				if(monitorfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class CipherSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<CipherSpecMonitor> {

	CipherSpecMonitor_Set(){
		this.size = 0;
		this.elements = new CipherSpecMonitor[4];
	}
	final void event_g1(String transformation, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(transformation, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String transformation, Object provider, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(transformation, provider, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String transformation, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(transformation, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i1(int mode, Certificate cert, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i1(mode, cert, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i2(int mode, Key key, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i2(mode, key, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_u1(byte[] plainText, Cipher c, byte[] cipherText) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_u1(plainText, c, cipherText);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_u2(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, Cipher c, byte[] cipherText) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_u2(plainText, prePlainTextOffset, prePlainTextLen, c, cipherText);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_u3(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_u3(plainText, prePlainTextOffset, prePlainTextLen, cipherText, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_u4(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, int outputOffset, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_u4(plainText, prePlainTextOffset, prePlainTextLen, cipherText, outputOffset, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_u5(ByteBuffer plainBuffer, ByteBuffer cipherBuffer, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_u5(plainBuffer, cipherBuffer, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_wkb1(Cipher c, byte[] wrappedKeyBytes) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_wkb1(c, wrappedKeyBytes);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f1(Cipher c, byte[] cipherText) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f1(c, cipherText);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f2(Cipher c, byte[] cipherText) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f2(c, cipherText);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f3(byte[] cipherText, int offset, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f3(cipherText, offset, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f5(byte[] plainText, int offset, int len, byte[] cipherText, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f5(plainText, offset, len, cipherText, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f6(byte[] plainText, int offset, int len, byte[] cipherText, int cipherOffset, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f6(plainText, offset, len, cipherText, cipherOffset, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f7(ByteBuffer plainTextBuffer, ByteBuffer cipherTextBuffer, Cipher c) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			CipherSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final CipherSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f7(plainTextBuffer, cipherTextBuffer, c);
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class DHGenParameterSpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<DHGenParameterSpecSpecMonitor> {

	DHGenParameterSpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new DHGenParameterSpecSpecMonitor[4];
	}
	final void event_c1(int primeSize, int exponentSize, DHGenParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			DHGenParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final DHGenParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(primeSize, exponentSize, s);
				if(monitorfinalMonitor.DHGenParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.DHGenParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class GCMParameterSpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<GCMParameterSpecSpecMonitor> {

	GCMParameterSpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new GCMParameterSpecSpecMonitor[4];
	}
	final void event_c1(int tagLen, byte[] src, GCMParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			GCMParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final GCMParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(tagLen, src, s);
				if(monitorfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c1(int tagLen, byte[] src, int offset, int len, GCMParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			GCMParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final GCMParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(tagLen, src, offset, len, s);
				if(monitorfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class HMACParameterSpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<HMACParameterSpecSpecMonitor> {

	HMACParameterSpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new HMACParameterSpecSpecMonitor[4];
	}
	final void event_c(HMACParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			HMACParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final HMACParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c(s);
				if(monitorfinalMonitor.HMACParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.HMACParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class IvParameterSpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<IvParameterSpecSpecMonitor> {

	IvParameterSpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new IvParameterSpecSpecMonitor[4];
	}
	final void event_c1(byte[] iv, IvParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			IvParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final IvParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(iv, s);
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c2(byte[] iv, int offset, int len, IvParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			IvParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final IvParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c2(iv, offset, len, s);
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c3(byte[] iv, IvParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			IvParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final IvParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c3(iv, s);
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c4(byte[] iv, int offset, int len, IvParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			IvParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final IvParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c4(iv, offset, len, s);
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class KeyGeneratorSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyGeneratorSpecMonitor> {

	KeyGeneratorSpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyGeneratorSpecMonitor[4];
	}
	final void event_g1(String alg, KeyGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, k);
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, Object provider, KeyGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, k);
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, KeyGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, k);
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init(KeyGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init(k);
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gk1(KeyGenerator k, SecretKey key) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gk1(k, key);
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class KeyManagerFactorySpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyManagerFactorySpecMonitor> {

	KeyManagerFactorySpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyManagerFactorySpecMonitor[4];
	}
	final void event_g1(String alg, KeyManagerFactory k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, k);
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, KeyManagerFactory k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, k);
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, KeyManagerFactory k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, k);
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init(KeyManagerFactory k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init(k);
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gkm1(KeyManagerFactory k, KeyManager[] keyManager) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gkm1(k, keyManager);
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class KeyPairGeneratorSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyPairGeneratorSpecMonitor> {

	KeyPairGeneratorSpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyPairGeneratorSpecMonitor[4];
	}
	final void event_g1(String alg, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init1(int keySize, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init1(keySize, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init2(int keySize, SecureRandom random, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init2(keySize, random, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init3(AlgorithmParameterSpec params, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init3(params, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init4(params, random, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_initError(int keySize, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_initError(keySize, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gen(KeyPairGenerator k, KeyPair keyPair) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gen(k, keyPair);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class KeyPairSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyPairSpecMonitor> {

	KeyPairSpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyPairSpecMonitor[4];
	}
	final void event_c1(PublicKey publicKey, PrivateKey privateKey, KeyPair kp) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(publicKey, privateKey, kp);
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gpu(KeyPair keyPair, PublicKey publicKey) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gpu(keyPair, publicKey);
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gpr(KeyPair keyPair, PrivateKey privateKey) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gpr(keyPair, privateKey);
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class KeyStoreSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyStoreSpecMonitor> {

	KeyStoreSpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyStoreSpecMonitor[4];
	}
	final void event_g1(String ksType, KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(ksType, k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String ksType, KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(ksType, k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_load(KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_load(k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_store(KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_store(k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_ge1(KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_ge1(k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_se1(KeyStore k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_se1(k);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gk1(KeyStore k, Key key) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyStoreSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyStoreSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gk1(k, key);
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyStoreSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class MacSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<MacSpecMonitor> {

	MacSpecMonitor_Set(){
		this.size = 0;
		this.elements = new MacSpecMonitor[4];
	}
	final void event_g1(String alg, Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i1(java.security.Key key, Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i1(key, m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i2(java.security.Key key, java.security.spec.AlgorithmParameterSpec params, Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i2(key, params, m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_update(Mac m) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_update(m);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f1(Mac m, byte[] output) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f1(m, output);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f2(byte[] output, int outOffset) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MacSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MacSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f2(output, outOffset);
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class MessageDigestSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<MessageDigestSpecMonitor> {

	MessageDigestSpecMonitor_Set(){
		this.size = 0;
		this.elements = new MessageDigestSpecMonitor[4];
	}
	final void event_g1(String alg, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, Provider provider, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, provider, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g4(String alg, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g4(alg, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_update(MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_update(digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_reset(MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_reset(digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d1(MessageDigest digest, byte[] out) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d1(digest, out);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d2(MessageDigest digest, byte[] out) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d2(digest, out);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d3(byte[] out, int offset, int len, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d3(out, offset, len, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class PBEKeySpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<PBEKeySpecSpecMonitor> {

	PBEKeySpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new PBEKeySpecSpecMonitor[4];
	}
	final void event_f1(char[] password) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f1(password);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_f2(char[] password, byte[] salt, int keyLength) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_f2(password, salt, keyLength);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c1(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(password, salt, iterationCount, keyLength, s);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_err1(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_err1(password, salt, iterationCount, keyLength, s);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_err2(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_err2(password, salt, iterationCount, keyLength, s);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_err3(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_err3(password, salt, iterationCount, keyLength, s);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c2(PBEKeySpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c2(s);
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class PBEParameterSpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<PBEParameterSpecSpecMonitor> {

	PBEParameterSpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new PBEParameterSpecSpecMonitor[4];
	}
	final void event_c1(byte[] salt, int iterationCount, PBEParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(salt, iterationCount, s);
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c2(byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec, PBEParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c2(salt, iterationCount, paramSpec, s);
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c3(byte[] salt, int iterationCount, PBEParameterSpec s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			PBEParameterSpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final PBEParameterSpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c3(salt, iterationCount, s);
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class RandomStringPasswordSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<RandomStringPasswordSpecMonitor> {

	RandomStringPasswordSpecMonitor_Set(){
		this.size = 0;
		this.elements = new RandomStringPasswordSpecMonitor[4];
	}
	final void event_vo(Object obj, String s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			RandomStringPasswordSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final RandomStringPasswordSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_vo(obj, s);
				if(monitorfinalMonitor.RandomStringPasswordSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gb(String s, char[] chars) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			RandomStringPasswordSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final RandomStringPasswordSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gb(s, chars);
				if(monitorfinalMonitor.RandomStringPasswordSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class SSLContextSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SSLContextSpecMonitor> {

	SSLContextSpecMonitor_Set(){
		this.size = 0;
		this.elements = new SSLContextSpecMonitor[4];
	}
	final void event_g1(String protocol, SSLContext ctx) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SSLContextSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SSLContextSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(protocol, ctx);
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String protocol, String provider, SSLContext ctx) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SSLContextSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SSLContextSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(protocol, provider, ctx);
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_unsafe_protocol(String protocol) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SSLContextSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SSLContextSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_unsafe_protocol(protocol);
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init(SSLContext ctx) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SSLContextSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SSLContextSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init(ctx);
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_engine(SSLContext ctx, SSLEngine eng) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SSLContextSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SSLContextSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_engine(ctx, eng);
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class SecretKeySpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SecretKeySpecMonitor> {

	SecretKeySpecMonitor_Set(){
		this.size = 0;
		this.elements = new SecretKeySpecMonitor[4];
	}
	final void event_e1(SecretKey secretKey, byte[] key) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecretKeySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecretKeySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_e1(secretKey, key);
				if(monitorfinalMonitor.SecretKeySpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class SecretKeySpecSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SecretKeySpecSpecMonitor> {

	SecretKeySpecSpecMonitor_Set(){
		this.size = 0;
		this.elements = new SecretKeySpecSpecMonitor[4];
	}
	final void event_c1(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecretKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecretKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(keyMaterial, keyAlgorithm, secretKeySpec);
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c2(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecretKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecretKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c2(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c3(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecretKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecretKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c3(keyMaterial, keyAlgorithm, secretKeySpec);
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c4(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecretKeySpecSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecretKeySpecSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c4(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class SecureRandomSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SecureRandomSpecMonitor> {

	SecureRandomSpecMonitor_Set(){
		this.size = 0;
		this.elements = new SecureRandomSpecMonitor[4];
	}
	final void event_c1(SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c1(r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c2(byte[] seed, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c2(seed, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_c3(byte[] seed, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_c3(seed, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g1(String alg, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g4(String alg, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g4(alg, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_setSeed1(SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_setSeed1(r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_setSeed2(byte[] seed, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_setSeed2(seed, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_setSeed3(byte[] seed, SecureRandom r) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_setSeed3(seed, r);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_genSeed(SecureRandom r, byte[] seed) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_genSeed(r, seed);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_next1(SecureRandom r, int randIntInRange) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_next1(r, randIntInRange);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_next2(SecureRandom r, byte[] bytes) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_next2(r, bytes);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_next3(SecureRandom r, int randInt) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_next3(r, randInt);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_ints(SecureRandom r, IntStream stream) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SecureRandomSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SecureRandomSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_ints(r, stream);
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class SignatureSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SignatureSpecMonitor> {

	SignatureSpecMonitor_Set(){
		this.size = 0;
		this.elements = new SignatureSpecMonitor[4];
	}
	final void event_g1(String alg, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i1(PrivateKey privateKey, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i1(privateKey, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i2(PrivateKey privateKey, SecureRandom random, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i2(privateKey, random, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i3(Certificate cert, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i3(cert, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_i4(PublicKey key, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_i4(key, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_update(Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_update(s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_s1(Signature s, byte[] output) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_s1(s, output);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_s2(byte[] output, int offset, int len, Signature s) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_s2(output, offset, len, s);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_v1(byte[] sign, Signature s, boolean signed) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_v1(sign, s, signed);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_v2(byte[] sign, int offset, int len, Signature s, boolean signed) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			SignatureSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final SignatureSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_v2(sign, offset, len, s, signed);
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}
final class TrustManagerFactorySpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<TrustManagerFactorySpecMonitor> {

	TrustManagerFactorySpecMonitor_Set(){
		this.size = 0;
		this.elements = new TrustManagerFactorySpecMonitor[4];
	}
	final void event_g1(String alg, TrustManagerFactory mf) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			TrustManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final TrustManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, mf);
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, TrustManagerFactory mf) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			TrustManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final TrustManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, mf);
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, TrustManagerFactory k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			TrustManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final TrustManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, k);
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init(TrustManagerFactory mf) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			TrustManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final TrustManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init(mf);
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gtm1(TrustManagerFactory k, TrustManager[][] trustManager) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			TrustManagerFactorySpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final TrustManagerFactorySpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gtm1(k, trustManager);
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
					monitorfinalMonitor.Prop_1_handler_match1();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}

class CipherInputStreamSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		CipherInputStreamSpec_Monitor_num++;
		try {
			CipherInputStreamSpecMonitor ret = (CipherInputStreamSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	protected static long CipherInputStreamSpec_Monitor_num = 0;
	protected static long CipherInputStreamSpec_CollectedMonitor_num = 0;
	protected static long CipherInputStreamSpec_TerminatedMonitor_num = 0;
	protected static long CipherInputStreamSpec_r2_num = 0;
	protected static long CipherInputStreamSpec_cl1_num = 0;
	protected static long CipherInputStreamSpec_c1_num = 0;
	protected static long CipherInputStreamSpec_r1_num = 0;
	protected static long CipherInputStreamSpec_1_fail_num = 0;

	static final int Prop_1_transition_c1[] = {1, 4, 4, 4, 4};;
	static final int Prop_1_transition_r1[] = {4, 3, 4, 3, 4};;
	static final int Prop_1_transition_r2[] = {4, 3, 4, 3, 4};;
	static final int Prop_1_transition_cl1[] = {4, 4, 4, 2, 4};;

	volatile boolean CipherInputStreamSpecMonitor_Prop_1_Category_fail = false;

	private AtomicInteger pairValue;

	CipherInputStreamSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		CipherInputStreamSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return CipherInputStreamSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return CipherInputStreamSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return CipherInputStreamSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("r2", CipherInputStreamSpec_r2_num);
		eventCounters.put("cl1", CipherInputStreamSpec_cl1_num);
		eventCounters.put("c1", CipherInputStreamSpec_c1_num);
		eventCounters.put("r1", CipherInputStreamSpec_r1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", CipherInputStreamSpec_1_fail_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1() {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.CipherInputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_r1() {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_r1) ;
		this.CipherInputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_r2(byte[] arr, int offset, int len) {
		{
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_r2) ;
		this.CipherInputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_cl1() {
		{
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_cl1) ;
		this.CipherInputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
			CipherInputStreamSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherInputStreamSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		CipherInputStreamSpecMonitor_Prop_1_Category_fail = false;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			return;
			case 1:
			//r1
			return;
			case 2:
			//r2
			return;
			case 3:
			//cl1
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			CipherInputStreamSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 4;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
class CipherOutputStreamSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		CipherOutputStreamSpec_Monitor_num++;
		try {
			CipherOutputStreamSpecMonitor ret = (CipherOutputStreamSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	protected static long CipherOutputStreamSpec_Monitor_num = 0;
	protected static long CipherOutputStreamSpec_CollectedMonitor_num = 0;
	protected static long CipherOutputStreamSpec_TerminatedMonitor_num = 0;
	protected static long CipherOutputStreamSpec_fl_num = 0;
	protected static long CipherOutputStreamSpec_cl_num = 0;
	protected static long CipherOutputStreamSpec_w1_num = 0;
	protected static long CipherOutputStreamSpec_w2_num = 0;
	protected static long CipherOutputStreamSpec_c1_num = 0;
	protected static long CipherOutputStreamSpec_1_fail_num = 0;

	static final int Prop_1_transition_c1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_w1[] = {4, 4, 3, 3, 4};;
	static final int Prop_1_transition_w2[] = {4, 4, 3, 3, 4};;
	static final int Prop_1_transition_fl[] = {4, 4, 3, 3, 4};;
	static final int Prop_1_transition_cl[] = {4, 4, 4, 1, 4};;

	volatile boolean CipherOutputStreamSpecMonitor_Prop_1_Category_fail = false;

	private AtomicInteger pairValue;

	CipherOutputStreamSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		CipherOutputStreamSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return CipherOutputStreamSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return CipherOutputStreamSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return CipherOutputStreamSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("fl", CipherOutputStreamSpec_fl_num);
		eventCounters.put("cl", CipherOutputStreamSpec_cl_num);
		eventCounters.put("w1", CipherOutputStreamSpec_w1_num);
		eventCounters.put("w2", CipherOutputStreamSpec_w2_num);
		eventCounters.put("c1", CipherOutputStreamSpec_c1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", CipherOutputStreamSpec_1_fail_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1() {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.CipherOutputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_w1() {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_w1) ;
		this.CipherOutputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_w2(byte[] b, int off, int len) {
		{
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_w2) ;
		this.CipherOutputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_fl() {
		{
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_fl) ;
		this.CipherOutputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_cl() {
		{
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_cl) ;
		this.CipherOutputStreamSpecMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			CipherOutputStreamSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherOutputStreamSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		CipherOutputStreamSpecMonitor_Prop_1_Category_fail = false;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			return;
			case 1:
			//w1
			return;
			case 2:
			//w2
			return;
			case 3:
			//fl
			return;
			case 4:
			//cl
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			CipherOutputStreamSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
class CipherSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		CipherSpec_Monitor_num++;
		try {
			CipherSpecMonitor ret = (CipherSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Cipher cipher = null;

	String currentTransformation = "";

	protected static long CipherSpec_Monitor_num = 0;
	protected static long CipherSpec_CollectedMonitor_num = 0;
	protected static long CipherSpec_TerminatedMonitor_num = 0;
	protected static long CipherSpec_u5_num = 0;
	protected static long CipherSpec_i1_num = 0;
	protected static long CipherSpec_i2_num = 0;
	protected static long CipherSpec_g1_num = 0;
	protected static long CipherSpec_g2_num = 0;
	protected static long CipherSpec_f1_num = 0;
	protected static long CipherSpec_g3_num = 0;
	protected static long CipherSpec_f2_num = 0;
	protected static long CipherSpec_f3_num = 0;
	protected static long CipherSpec_f5_num = 0;
	protected static long CipherSpec_f6_num = 0;
	protected static long CipherSpec_f7_num = 0;
	protected static long CipherSpec_wkb1_num = 0;
	protected static long CipherSpec_u1_num = 0;
	protected static long CipherSpec_u2_num = 0;
	protected static long CipherSpec_u3_num = 0;
	protected static long CipherSpec_u4_num = 0;
	protected static long CipherSpec_1_fail_num = 0;
	protected static long CipherSpec_1_match1_num = 0;

	static final int Prop_1_transition_g1[] = {4, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_g2[] = {4, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_g3[] = {0, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_i1[] = {5, 5, 5, 5, 1, 5};;
	static final int Prop_1_transition_i2[] = {5, 5, 5, 5, 1, 5};;
	static final int Prop_1_transition_u1[] = {5, 2, 5, 2, 5, 5};;
	static final int Prop_1_transition_u2[] = {5, 2, 5, 2, 5, 5};;
	static final int Prop_1_transition_u3[] = {5, 2, 5, 2, 5, 5};;
	static final int Prop_1_transition_u4[] = {5, 2, 5, 2, 5, 5};;
	static final int Prop_1_transition_u5[] = {5, 2, 5, 2, 5, 5};;
	static final int Prop_1_transition_wkb1[] = {5, 3, 5, 3, 5, 5};;
	static final int Prop_1_transition_f1[] = {5, 5, 3, 5, 5, 5};;
	static final int Prop_1_transition_f2[] = {5, 3, 3, 3, 5, 5};;
	static final int Prop_1_transition_f3[] = {5, 5, 3, 5, 5, 5};;
	static final int Prop_1_transition_f5[] = {5, 3, 3, 3, 5, 5};;
	static final int Prop_1_transition_f6[] = {5, 3, 3, 3, 5, 5};;
	static final int Prop_1_transition_f7[] = {5, 3, 3, 3, 5, 5};;

	volatile boolean CipherSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean CipherSpecMonitor_Prop_1_Category_match1 = false;

	private AtomicInteger pairValue;

	CipherSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		CipherSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return CipherSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return CipherSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return CipherSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("u5", CipherSpec_u5_num);
		eventCounters.put("i1", CipherSpec_i1_num);
		eventCounters.put("i2", CipherSpec_i2_num);
		eventCounters.put("g1", CipherSpec_g1_num);
		eventCounters.put("g2", CipherSpec_g2_num);
		eventCounters.put("f1", CipherSpec_f1_num);
		eventCounters.put("g3", CipherSpec_g3_num);
		eventCounters.put("f2", CipherSpec_f2_num);
		eventCounters.put("f3", CipherSpec_f3_num);
		eventCounters.put("f5", CipherSpec_f5_num);
		eventCounters.put("f6", CipherSpec_f6_num);
		eventCounters.put("f7", CipherSpec_f7_num);
		eventCounters.put("wkb1", CipherSpec_wkb1_num);
		eventCounters.put("u1", CipherSpec_u1_num);
		eventCounters.put("u2", CipherSpec_u2_num);
		eventCounters.put("u3", CipherSpec_u3_num);
		eventCounters.put("u4", CipherSpec_u4_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", CipherSpec_1_fail_num);
		categoryCounters.put("match1", CipherSpec_1_match1_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String transformation, Cipher c) {
		{
			if ( ! (isValid(transformation)) ) {
				return false;
			}
			{
				currentTransformation = transformation;
				cipher = c;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g2(String transformation, Object provider, Cipher c) {
		{
			if ( ! (isValid(transformation)) ) {
				return false;
			}
			{
				currentTransformation = transformation;
				cipher = c;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g3(String transformation, Cipher c) {
		{
			if ( ! (!isValid(transformation)) ) {
				return false;
			}
			{
				currentTransformation = transformation;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_i1(int mode, Certificate cert, Cipher c) {
		{
			if (!isValid(currentTransformation)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "CipherSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found " + currentTransformation + "."));
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_i1) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_i2(int mode, Key key, Cipher c) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.GENERATED_KEY, key) || ExecutionContext.instance().validate(Property.GENERATED_PUBLIC_KEY, key) || ExecutionContext.instance().validate(Property.GENERATED_PRIVATE_KEY, key)) ) {
				return false;
			}
			{
				if (!isValid(currentTransformation)) {
					ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "CipherSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found " + currentTransformation + "."));
				}
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_i2) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_u1(byte[] plainText, Cipher c, byte[] cipherText) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_u1) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_u2(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, Cipher c, byte[] cipherText) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_u2) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_u3(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_u3) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_u4(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, int outputOffset, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_u4) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_u5(ByteBuffer plainBuffer, ByteBuffer cipherBuffer, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherBuffer);
		}

		int nextstate = this.handleEvent(9, Prop_1_transition_u5) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_wkb1(Cipher c, byte[] wrappedKeyBytes) {
		{
			ExecutionContext.instance().setProperty(Property.WRAPPED_KEY, wrappedKeyBytes);
		}

		int nextstate = this.handleEvent(10, Prop_1_transition_wkb1) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f1(Cipher c, byte[] cipherText) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(11, Prop_1_transition_f1) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f2(Cipher c, byte[] cipherText) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(12, Prop_1_transition_f2) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f3(byte[] cipherText, int offset, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(13, Prop_1_transition_f3) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f5(byte[] plainText, int offset, int len, byte[] cipherText, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(14, Prop_1_transition_f5) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f6(byte[] plainText, int offset, int len, byte[] cipherText, int cipherOffset, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherText);
		}

		int nextstate = this.handleEvent(15, Prop_1_transition_f6) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_f7(ByteBuffer plainTextBuffer, ByteBuffer cipherTextBuffer, Cipher c) {
		{
			ExecutionContext.instance().setProperty(Property.ENCRYPTED, cipherTextBuffer);
		}

		int nextstate = this.handleEvent(16, Prop_1_transition_f7) ;
		this.CipherSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.CipherSpecMonitor_Prop_1_Category_match1 = nextstate == 3;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(CipherSpecMonitor_Prop_1_Category_fail) {
			CipherSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match1 (){
		if(CipherSpecMonitor_Prop_1_Category_match1) {
			CipherSpec_1_match1_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(cipher);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		CipherSpecMonitor_Prop_1_Category_fail = false;
		CipherSpecMonitor_Prop_1_Category_match1 = false;
	}

	// RVMRef_c was suppressed to reduce memory overhead

	//alive_parameters_0 = [Cipher c]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//i1
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//i2
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//u1
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//u2
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//u3
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//u4
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 9:
			//u5
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 10:
			//wkb1
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 11:
			//f1
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 12:
			//f2
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 13:
			//f3
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 14:
			//f5
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 15:
			//f6
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 16:
			//f7
			//alive_c
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				CipherSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			CipherSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 17;
	}

	public static int getNumberOfStates() {
		return 6;
	}

}
class DHGenParameterSpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		DHGenParameterSpecSpec_Monitor_num++;
		try {
			DHGenParameterSpecSpecMonitor ret = (DHGenParameterSpecSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	DHGenParameterSpec spec;

	protected static long DHGenParameterSpecSpec_Monitor_num = 0;
	protected static long DHGenParameterSpecSpec_CollectedMonitor_num = 0;
	protected static long DHGenParameterSpecSpec_TerminatedMonitor_num = 0;
	protected static long DHGenParameterSpecSpec_c1_num = 0;
	protected static long DHGenParameterSpecSpec_1_fail_num = 0;
	protected static long DHGenParameterSpecSpec_1_match_num = 0;

	static final int Prop_1_transition_c1[] = {1, 2, 2};;

	volatile boolean DHGenParameterSpecSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean DHGenParameterSpecSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	DHGenParameterSpecSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		DHGenParameterSpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return DHGenParameterSpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return DHGenParameterSpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return DHGenParameterSpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c1", DHGenParameterSpecSpec_c1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", DHGenParameterSpecSpec_1_fail_num);
		categoryCounters.put("match", DHGenParameterSpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(int primeSize, int exponentSize, DHGenParameterSpec s) {
		{
			if ( ! (exponentSize < primeSize) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.DHGenParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.DHGenParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(DHGenParameterSpecSpecMonitor_Prop_1_Category_fail) {
			DHGenParameterSpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "DHGenParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(DHGenParameterSpecSpecMonitor_Prop_1_Category_match) {
			DHGenParameterSpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.PREPARED_DH, spec);
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		DHGenParameterSpecSpecMonitor_Prop_1_Category_fail = false;
		DHGenParameterSpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [DHGenParameterSpec s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				DHGenParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			DHGenParameterSpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 1;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
class GCMParameterSpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		GCMParameterSpecSpec_Monitor_num++;
		try {
			GCMParameterSpecSpecMonitor ret = (GCMParameterSpecSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	GCMParameterSpec spec;

	List<Integer> validLengths = Arrays.asList(96, 104, 112, 120, 128);

	protected static long GCMParameterSpecSpec_Monitor_num = 0;
	protected static long GCMParameterSpecSpec_CollectedMonitor_num = 0;
	protected static long GCMParameterSpecSpec_TerminatedMonitor_num = 0;
	protected static long GCMParameterSpecSpec_c1_num = 0;
	protected static long GCMParameterSpecSpec_1_fail_num = 0;
	protected static long GCMParameterSpecSpec_1_match_num = 0;

	static final int Prop_1_transition_c1[] = {1, 2, 2};;

	volatile boolean GCMParameterSpecSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean GCMParameterSpecSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	GCMParameterSpecSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		GCMParameterSpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return GCMParameterSpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return GCMParameterSpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return GCMParameterSpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c1", GCMParameterSpecSpec_c1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", GCMParameterSpecSpec_1_fail_num);
		categoryCounters.put("match", GCMParameterSpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(int tagLen, byte[] src, GCMParameterSpec s) {
		{
			if ( ! (validLengths.contains(tagLen) && ExecutionContext.instance().validate(Property.RANDOMIZED, src)) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.GCMParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.GCMParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c1(int tagLen, byte[] src, int offset, int len, GCMParameterSpec s) {
		{
			if ( ! (validLengths.contains(tagLen) && ExecutionContext.instance().validate(Property.RANDOMIZED, src) && offset >= 0 && len >= 0 && src.length >= offset + len) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_c1) ;
		this.GCMParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.GCMParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(GCMParameterSpecSpecMonitor_Prop_1_Category_fail) {
			GCMParameterSpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "GCMParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(GCMParameterSpecSpecMonitor_Prop_1_Category_match) {
			GCMParameterSpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.PREPARED_GCM, spec);
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		GCMParameterSpecSpecMonitor_Prop_1_Category_fail = false;
		GCMParameterSpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [GCMParameterSpec s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				GCMParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//c1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				GCMParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			GCMParameterSpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
interface IHMACParameterSpecSpecMonitor extends IMonitor, IDisableHolder {
}

class HMACParameterSpecSpecDisableHolder extends DisableHolder implements IHMACParameterSpecSpecMonitor {
	HMACParameterSpecSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class HMACParameterSpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IHMACParameterSpecSpecMonitor {
	protected Object clone() {
		HMACParameterSpecSpec_Monitor_num++;
		try {
			HMACParameterSpecSpecMonitor ret = (HMACParameterSpecSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	HMACParameterSpec spec;

	protected static long HMACParameterSpecSpec_Monitor_num = 0;
	protected static long HMACParameterSpecSpec_CollectedMonitor_num = 0;
	protected static long HMACParameterSpecSpec_TerminatedMonitor_num = 0;
	protected static long HMACParameterSpecSpec_c_num = 0;
	protected static long HMACParameterSpecSpec_1_fail_num = 0;
	protected static long HMACParameterSpecSpec_1_match_num = 0;

	WeakReference Ref_hmacParameterSpec = null;
	int Prop_1_state;
	static final int Prop_1_transition_c[] = {1, 2, 2};;

	boolean HMACParameterSpecSpecMonitor_Prop_1_Category_fail = false;
	boolean HMACParameterSpecSpecMonitor_Prop_1_Category_match = false;

	HMACParameterSpecSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		HMACParameterSpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return HMACParameterSpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return HMACParameterSpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return HMACParameterSpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c", HMACParameterSpecSpec_c_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", HMACParameterSpecSpec_1_fail_num);
		categoryCounters.put("match", HMACParameterSpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_c(HMACParameterSpec s) {
		HMACParameterSpec hmacParameterSpec = null;
		if(Ref_hmacParameterSpec != null){
			hmacParameterSpec = (HMACParameterSpec)Ref_hmacParameterSpec.get();
		}
		{
			spec = s;
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_c[Prop_1_state];
		HMACParameterSpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 2;
		HMACParameterSpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(HMACParameterSpecSpecMonitor_Prop_1_Category_fail) {
			HMACParameterSpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "HMACParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(HMACParameterSpecSpecMonitor_Prop_1_Category_match) {
			HMACParameterSpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
			ExecutionContext.instance().setProperty(ExecutionContext.Property.PREPARED_HMAC, spec);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		HMACParameterSpecSpecMonitor_Prop_1_Category_fail = false;
		HMACParameterSpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_hmacParameterSpec was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//c
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			HMACParameterSpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 1;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
class IvParameterSpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		IvParameterSpecSpec_Monitor_num++;
		try {
			IvParameterSpecSpecMonitor ret = (IvParameterSpecSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	IvParameterSpec spec;

	protected static long IvParameterSpecSpec_Monitor_num = 0;
	protected static long IvParameterSpecSpec_CollectedMonitor_num = 0;
	protected static long IvParameterSpecSpec_TerminatedMonitor_num = 0;
	protected static long IvParameterSpecSpec_c3_num = 0;
	protected static long IvParameterSpecSpec_c4_num = 0;
	protected static long IvParameterSpecSpec_c1_num = 0;
	protected static long IvParameterSpecSpec_c2_num = 0;
	protected static long IvParameterSpecSpec_1_fail_num = 0;
	protected static long IvParameterSpecSpec_1_match_num = 0;

	static final int Prop_1_transition_c1[] = {1, 2, 2};;
	static final int Prop_1_transition_c2[] = {1, 2, 2};;
	static final int Prop_1_transition_c3[] = {2, 2, 2};;
	static final int Prop_1_transition_c4[] = {2, 2, 2};;

	volatile boolean IvParameterSpecSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean IvParameterSpecSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	IvParameterSpecSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		IvParameterSpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return IvParameterSpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return IvParameterSpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return IvParameterSpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c3", IvParameterSpecSpec_c3_num);
		eventCounters.put("c4", IvParameterSpecSpec_c4_num);
		eventCounters.put("c1", IvParameterSpecSpec_c1_num);
		eventCounters.put("c2", IvParameterSpecSpec_c2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", IvParameterSpecSpec_1_fail_num);
		categoryCounters.put("match", IvParameterSpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(byte[] iv, IvParameterSpec s) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, iv)) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c2(byte[] iv, int offset, int len, IvParameterSpec s) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, iv) && offset >= 0 && len >= 0 && iv.length >= offset + len) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_c2) ;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c3(byte[] iv, IvParameterSpec s) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, iv)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "IvParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_c3) ;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c4(byte[] iv, int offset, int len, IvParameterSpec s) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, iv)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "IvParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_c4) ;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.IvParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
			IvParameterSpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "IvParameterSpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(IvParameterSpecSpecMonitor_Prop_1_Category_match) {
			IvParameterSpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.PREPARED_IV, spec);
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		IvParameterSpecSpecMonitor_Prop_1_Category_fail = false;
		IvParameterSpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [IvParameterSpec s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				IvParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//c2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				IvParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//c3
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				IvParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//c4
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				IvParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			IvParameterSpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 4;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
class KeyGeneratorSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		KeyGeneratorSpec_Monitor_num++;
		try {
			KeyGeneratorSpecMonitor ret = (KeyGeneratorSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> safeAlgorithms = Arrays.asList("AES", "HmacSHA256", "HmacSHA384", "HmacSHA512");

	String currentAlgorithmInstance = "";

	KeyGenerator keyGenerator = null;

	Key generatedKey;

	protected static long KeyGeneratorSpec_Monitor_num = 0;
	protected static long KeyGeneratorSpec_CollectedMonitor_num = 0;
	protected static long KeyGeneratorSpec_TerminatedMonitor_num = 0;
	protected static long KeyGeneratorSpec_init_num = 0;
	protected static long KeyGeneratorSpec_g1_num = 0;
	protected static long KeyGeneratorSpec_g2_num = 0;
	protected static long KeyGeneratorSpec_g3_num = 0;
	protected static long KeyGeneratorSpec_gk1_num = 0;
	protected static long KeyGeneratorSpec_1_fail_num = 0;
	protected static long KeyGeneratorSpec_1_match_num = 0;

	static final int Prop_1_transition_g1[] = {3, 5, 5, 3, 5, 5};;
	static final int Prop_1_transition_g2[] = {4, 5, 5, 5, 4, 5};;
	static final int Prop_1_transition_g3[] = {0, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_init[] = {5, 5, 5, 2, 2, 5};;
	static final int Prop_1_transition_gk1[] = {5, 5, 1, 1, 1, 5};;

	volatile boolean KeyGeneratorSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean KeyGeneratorSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	KeyGeneratorSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		KeyGeneratorSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return KeyGeneratorSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return KeyGeneratorSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return KeyGeneratorSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("init", KeyGeneratorSpec_init_num);
		eventCounters.put("g1", KeyGeneratorSpec_g1_num);
		eventCounters.put("g2", KeyGeneratorSpec_g2_num);
		eventCounters.put("g3", KeyGeneratorSpec_g3_num);
		eventCounters.put("gk1", KeyGeneratorSpec_gk1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", KeyGeneratorSpec_1_fail_num);
		categoryCounters.put("match", KeyGeneratorSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, KeyGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				keyGenerator = k;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, Object provider, KeyGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				keyGenerator = k;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, KeyGenerator k) {
		{
			if ( ! (!safeAlgorithms.contains(currentAlgorithmInstance)) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_init(KeyGenerator k) {
		{
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_init) ;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_gk1(KeyGenerator k, SecretKey key) {
		{
			if (!safeAlgorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "KeyGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of" + String.join(",", safeAlgorithms) + " but found " + currentAlgorithmInstance + "."));
			}
			generatedKey = key;
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_KEY, generatedKey);
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_gk1) ;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 5;
		this.KeyGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			KeyGeneratorSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(keyGenerator);
			ExecutionContext.instance().remove(ExecutionContext.Property.GENERATED_KEY, generatedKey);
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			KeyGeneratorSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(keyGenerator);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		KeyGeneratorSpecMonitor_Prop_1_Category_fail = false;
		KeyGeneratorSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_k was suppressed to reduce memory overhead

	//alive_parameters_0 = [KeyGenerator k]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//init
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//gk1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			KeyGeneratorSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 6;
	}

}
class KeyManagerFactorySpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		KeyManagerFactorySpec_Monitor_num++;
		try {
			KeyManagerFactorySpecMonitor ret = (KeyManagerFactorySpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> safeAlgorithms = Arrays.asList("PKIX", "SunX509");

	String currentAlgorithmInstance = "";

	KeyManagerFactory keyManagerFactory = null;

	protected static long KeyManagerFactorySpec_Monitor_num = 0;
	protected static long KeyManagerFactorySpec_CollectedMonitor_num = 0;
	protected static long KeyManagerFactorySpec_TerminatedMonitor_num = 0;
	protected static long KeyManagerFactorySpec_init_num = 0;
	protected static long KeyManagerFactorySpec_gkm1_num = 0;
	protected static long KeyManagerFactorySpec_g1_num = 0;
	protected static long KeyManagerFactorySpec_g2_num = 0;
	protected static long KeyManagerFactorySpec_g3_num = 0;
	protected static long KeyManagerFactorySpec_1_fail_num = 0;
	protected static long KeyManagerFactorySpec_1_match1_num = 0;

	static final int Prop_1_transition_g1[] = {1, 3, 1, 3};;
	static final int Prop_1_transition_g2[] = {1, 3, 1, 3};;
	static final int Prop_1_transition_g3[] = {0, 3, 3, 3};;
	static final int Prop_1_transition_init[] = {3, 2, 3, 3};;
	static final int Prop_1_transition_gkm1[] = {3, 3, 0, 3};;

	volatile boolean KeyManagerFactorySpecMonitor_Prop_1_Category_fail = false;
	volatile boolean KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = false;

	private AtomicInteger pairValue;

	KeyManagerFactorySpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		KeyManagerFactorySpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return KeyManagerFactorySpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return KeyManagerFactorySpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return KeyManagerFactorySpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("init", KeyManagerFactorySpec_init_num);
		eventCounters.put("gkm1", KeyManagerFactorySpec_gkm1_num);
		eventCounters.put("g1", KeyManagerFactorySpec_g1_num);
		eventCounters.put("g2", KeyManagerFactorySpec_g2_num);
		eventCounters.put("g3", KeyManagerFactorySpec_g3_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", KeyManagerFactorySpec_1_fail_num);
		categoryCounters.put("match1", KeyManagerFactorySpec_1_match1_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, KeyManagerFactory k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				keyManagerFactory = k;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, KeyManagerFactory k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				keyManagerFactory = k;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, KeyManagerFactory k) {
		{
			if ( ! (!safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_init(KeyManagerFactory k) {
		{
			if (safeAlgorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "KeyManagerFactorySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " expecting one of " + String.join(",", safeAlgorithms) + " but found " + currentAlgorithmInstance + "."));
			}
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_KEY_MANAGERS, keyManagerFactory);
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_init) ;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_gkm1(KeyManagerFactory k, KeyManager[] keyManager) {
		{
			ExecutionContext.instance().setProperty(Property.GENERATED_KEY_MANAGERS, keyManager);
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_gkm1) ;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			KeyManagerFactorySpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyManagerFactorySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(keyManagerFactory);
			ExecutionContext.instance().remove(Property.GENERATED_KEY_MANAGERS);
			this.reset();
		}

	}

	final void Prop_1_handler_match1 (){
		if(KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			KeyManagerFactorySpec_1_match1_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(keyManagerFactory);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		KeyManagerFactorySpecMonitor_Prop_1_Category_fail = false;
		KeyManagerFactorySpecMonitor_Prop_1_Category_match1 = false;
	}

	// RVMRef_k was suppressed to reduce memory overhead

	//alive_parameters_0 = [KeyManagerFactory k]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyManagerFactorySpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyManagerFactorySpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyManagerFactorySpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//init
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyManagerFactorySpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//gkm1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyManagerFactorySpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			KeyManagerFactorySpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class KeyPairGeneratorSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		KeyPairGeneratorSpec_Monitor_num++;
		try {
			KeyPairGeneratorSpecMonitor ret = (KeyPairGeneratorSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> safeAlgorithms = Arrays.asList("RSA", "EC", "DSA", "DiffieHellman", "DH");

	KeyPairGenerator kpg = null;

	KeyPair kp;

	String algorithm;

	private boolean validate(int keySize) {
		switch(algorithm) {
			case "RSA":
			return Arrays.asList(4096, 3072, 2048).contains(keySize);
			case "DSA":
			return keySize == 2048;
			case "DiffieHellman":
			return keySize == 2048;
			case "DH":
			return keySize == 2048;
			case "EC":
			return keySize == 256;
		}
		return false;
	}

	protected static long KeyPairGeneratorSpec_Monitor_num = 0;
	protected static long KeyPairGeneratorSpec_CollectedMonitor_num = 0;
	protected static long KeyPairGeneratorSpec_TerminatedMonitor_num = 0;
	protected static long KeyPairGeneratorSpec_gen_num = 0;
	protected static long KeyPairGeneratorSpec_init3_num = 0;
	protected static long KeyPairGeneratorSpec_init2_num = 0;
	protected static long KeyPairGeneratorSpec_g1_num = 0;
	protected static long KeyPairGeneratorSpec_init1_num = 0;
	protected static long KeyPairGeneratorSpec_g2_num = 0;
	protected static long KeyPairGeneratorSpec_g3_num = 0;
	protected static long KeyPairGeneratorSpec_initError_num = 0;
	protected static long KeyPairGeneratorSpec_init4_num = 0;
	protected static long KeyPairGeneratorSpec_1_fail_num = 0;
	protected static long KeyPairGeneratorSpec_1_match_num = 0;

	static final int Prop_1_transition_g1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g2[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g3[] = {0, 4, 4, 4, 4};;
	static final int Prop_1_transition_init1[] = {4, 4, 1, 4, 4};;
	static final int Prop_1_transition_init2[] = {4, 4, 1, 4, 4};;
	static final int Prop_1_transition_init3[] = {4, 4, 1, 4, 4};;
	static final int Prop_1_transition_init4[] = {4, 4, 1, 4, 4};;
	static final int Prop_1_transition_initError[] = {4, 4, 4, 4, 4};;
	static final int Prop_1_transition_gen[] = {4, 3, 4, 4, 4};;

	volatile boolean KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean KeyPairGeneratorSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	KeyPairGeneratorSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		KeyPairGeneratorSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return KeyPairGeneratorSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return KeyPairGeneratorSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return KeyPairGeneratorSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("gen", KeyPairGeneratorSpec_gen_num);
		eventCounters.put("init3", KeyPairGeneratorSpec_init3_num);
		eventCounters.put("init2", KeyPairGeneratorSpec_init2_num);
		eventCounters.put("g1", KeyPairGeneratorSpec_g1_num);
		eventCounters.put("init1", KeyPairGeneratorSpec_init1_num);
		eventCounters.put("g2", KeyPairGeneratorSpec_g2_num);
		eventCounters.put("g3", KeyPairGeneratorSpec_g3_num);
		eventCounters.put("initError", KeyPairGeneratorSpec_initError_num);
		eventCounters.put("init4", KeyPairGeneratorSpec_init4_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", KeyPairGeneratorSpec_1_fail_num);
		categoryCounters.put("match", KeyPairGeneratorSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, KeyPairGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				kpg = k;
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, KeyPairGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				kpg = k;
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, KeyPairGenerator k) {
		{
			if ( ! (!safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_init1(int keySize, KeyPairGenerator k) {
		{
			if ( ! (validate(keySize)) ) {
				return false;
			}
			{
				if (!safeAlgorithms.contains(algorithm)) {
					ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " expecting one of " + String.join(",", safeAlgorithms) + " but found " + algorithm + "."));
				}
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_init1) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_init2(int keySize, SecureRandom random, KeyPairGenerator k) {
		{
			if ( ! (validate(keySize)) ) {
				return false;
			}
			{
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_init2) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_init3(AlgorithmParameterSpec params, KeyPairGenerator k) {
		{
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_init3) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		{
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_init4) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_initError(int keySize, KeyPairGenerator k) {
		{
			if ( ! (!validate(keySize)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidKeySize, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "invalid key size for algorithm " + algorithm + "."));
			}
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_initError) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_gen(KeyPairGenerator k, KeyPair keyPair) {
		{
			kp = keyPair;
			ExecutionContext.instance().setProperty(Property.GENERATED_KEY_PAIR, kp);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_gen) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			KeyPairGeneratorSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().remove(Property.GENERATED_KEY_PAIR, kp);
		}

	}

	final void Prop_1_handler_match (){
		if(KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			KeyPairGeneratorSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(kpg);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = false;
		KeyPairGeneratorSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_k was suppressed to reduce memory overhead

	//alive_parameters_0 = [KeyPairGenerator k]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//init1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//init2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//init3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//init4
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//initError
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//gen
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				KeyPairGeneratorSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			KeyPairGeneratorSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 9;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
interface IKeyPairSpecMonitor extends IMonitor, IDisableHolder {
}

class KeyPairSpecDisableHolder extends DisableHolder implements IKeyPairSpecMonitor {
	KeyPairSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class KeyPairSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IKeyPairSpecMonitor {
	protected Object clone() {
		KeyPairSpec_Monitor_num++;
		try {
			KeyPairSpecMonitor ret = (KeyPairSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	KeyPair keyPair = null;

	protected static long KeyPairSpec_Monitor_num = 0;
	protected static long KeyPairSpec_CollectedMonitor_num = 0;
	protected static long KeyPairSpec_TerminatedMonitor_num = 0;
	protected static long KeyPairSpec_gpr_num = 0;
	protected static long KeyPairSpec_gpu_num = 0;
	protected static long KeyPairSpec_c1_num = 0;
	protected static long KeyPairSpec_1_fail_num = 0;
	protected static long KeyPairSpec_1_match_num = 0;

	WeakReference Ref_keyPair = null;
	int Prop_1_state;
	static final int Prop_1_transition_c1[] = {1, 2, 2};;
	static final int Prop_1_transition_gpu[] = {2, 1, 2};;
	static final int Prop_1_transition_gpr[] = {2, 1, 2};;

	boolean KeyPairSpecMonitor_Prop_1_Category_fail = false;
	boolean KeyPairSpecMonitor_Prop_1_Category_match = false;

	KeyPairSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		KeyPairSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return KeyPairSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return KeyPairSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return KeyPairSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("gpr", KeyPairSpec_gpr_num);
		eventCounters.put("gpu", KeyPairSpec_gpu_num);
		eventCounters.put("c1", KeyPairSpec_c1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", KeyPairSpec_1_fail_num);
		categoryCounters.put("match", KeyPairSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_c1(PublicKey publicKey, PrivateKey privateKey, KeyPair kp) {
		KeyPair keyPair = null;
		if(Ref_keyPair != null){
			keyPair = (KeyPair)Ref_keyPair.get();
		}
		{
			keyPair = kp;
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_c1[Prop_1_state];
		KeyPairSpecMonitor_Prop_1_Category_fail = Prop_1_state == 2;
		KeyPairSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_gpu(KeyPair keyPair, PublicKey publicKey) {
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_PUBLIC_KEY, publicKey);
		}
		if(Ref_keyPair == null){
			Ref_keyPair = new WeakReference(keyPair);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_gpu[Prop_1_state];
		KeyPairSpecMonitor_Prop_1_Category_fail = Prop_1_state == 2;
		KeyPairSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_gpr(KeyPair keyPair, PrivateKey privateKey) {
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_PUBLIC_KEY, privateKey);
		}
		if(Ref_keyPair == null){
			Ref_keyPair = new WeakReference(keyPair);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_gpr[Prop_1_state];
		KeyPairSpecMonitor_Prop_1_Category_fail = Prop_1_state == 2;
		KeyPairSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(KeyPairSpecMonitor_Prop_1_Category_fail) {
			KeyPairSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyPairSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(KeyPairSpecMonitor_Prop_1_Category_match) {
			KeyPairSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(keyPair);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		KeyPairSpecMonitor_Prop_1_Category_fail = false;
		KeyPairSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_keyPair was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//c1
			return;
			case 1:
			//gpu
			return;
			case 2:
			//gpr
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			KeyPairSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 3;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
interface IKeyStoreSpecMonitor extends IMonitor, IDisableHolder {
}

class KeyStoreSpecDisableHolder extends DisableHolder implements IKeyStoreSpecMonitor {
	KeyStoreSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class KeyStoreSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IKeyStoreSpecMonitor {
	protected Object clone() {
		KeyStoreSpec_Monitor_num++;
		try {
			KeyStoreSpecMonitor ret = (KeyStoreSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> types = Arrays.asList("JCEKS", "JKS", "DKS", "PKCS11", "PKCS12");

	String currentKSType = "";

	KeyStore keyStore = null;

	Key generatedKey = null;

	protected static long KeyStoreSpec_Monitor_num = 0;
	protected static long KeyStoreSpec_CollectedMonitor_num = 0;
	protected static long KeyStoreSpec_TerminatedMonitor_num = 0;
	protected static long KeyStoreSpec_ge1_num = 0;
	protected static long KeyStoreSpec_load_num = 0;
	protected static long KeyStoreSpec_g1_num = 0;
	protected static long KeyStoreSpec_g2_num = 0;
	protected static long KeyStoreSpec_store_num = 0;
	protected static long KeyStoreSpec_gk1_num = 0;
	protected static long KeyStoreSpec_se1_num = 0;
	protected static long KeyStoreSpec_1_fail_num = 0;
	protected static long KeyStoreSpec_1_match_num = 0;

	WeakReference Ref_ks = null;
	int Prop_1_state;
	static final int Prop_1_transition_g1[] = {4, 4, 5, 5, 5, 5};;
	static final int Prop_1_transition_g2[] = {0, 0, 5, 5, 5, 5};;
	static final int Prop_1_transition_load[] = {5, 5, 5, 5, 1, 5};;
	static final int Prop_1_transition_store[] = {5, 5, 5, 1, 5, 5};;
	static final int Prop_1_transition_ge1[] = {5, 2, 5, 5, 5, 5};;
	static final int Prop_1_transition_se1[] = {5, 3, 5, 5, 5, 5};;
	static final int Prop_1_transition_gk1[] = {5, 1, 1, 5, 5, 5};;

	boolean KeyStoreSpecMonitor_Prop_1_Category_fail = false;
	boolean KeyStoreSpecMonitor_Prop_1_Category_match = false;

	KeyStoreSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		KeyStoreSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return KeyStoreSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return KeyStoreSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return KeyStoreSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("ge1", KeyStoreSpec_ge1_num);
		eventCounters.put("load", KeyStoreSpec_load_num);
		eventCounters.put("g1", KeyStoreSpec_g1_num);
		eventCounters.put("g2", KeyStoreSpec_g2_num);
		eventCounters.put("store", KeyStoreSpec_store_num);
		eventCounters.put("gk1", KeyStoreSpec_gk1_num);
		eventCounters.put("se1", KeyStoreSpec_se1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", KeyStoreSpec_1_fail_num);
		categoryCounters.put("match", KeyStoreSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_g1(String ksType, KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
			if ( ! (types.contains(ksType)) ) {
				return false;
			}
			{
				keyStore = k;
				currentKSType = ksType;
			}
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_g1[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_g2(String ksType, KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
			if ( ! (!types.contains(ksType)) ) {
				return false;
			}
			{
				currentKSType = ksType;
			}
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_g2[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_load(KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_KEY_STORE, keyStore);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_load[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_store(KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_store[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_ge1(KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_ge1[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_se1(KeyStore k) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
		}
		RVM_lastevent = 5;

		Prop_1_state = Prop_1_transition_se1[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_gk1(KeyStore k, Key key) {
		KeyStore ks = null;
		if(Ref_ks != null){
			ks = (KeyStore)Ref_ks.get();
		}
		{
			if (!types.contains(currentKSType)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidKeyStoreType, "KeyStoreSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of" + String.join(",", types) + " but found " + currentKSType + "."));
			}
			generatedKey = key;
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_KEY, generatedKey);
		}
		RVM_lastevent = 6;

		Prop_1_state = Prop_1_transition_gk1[Prop_1_state];
		KeyStoreSpecMonitor_Prop_1_Category_fail = Prop_1_state == 5;
		KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(KeyStoreSpecMonitor_Prop_1_Category_fail) {
			KeyStoreSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyStoreSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(keyStore);
			ExecutionContext.instance().remove(Property.GENERATED_KEY, generatedKey);
			ExecutionContext.instance().remove(Property.GENERATED_KEY_STORE, keyStore);
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(KeyStoreSpecMonitor_Prop_1_Category_match) {
			KeyStoreSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(keyStore);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		KeyStoreSpecMonitor_Prop_1_Category_fail = false;
		KeyStoreSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_ks was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//g1
			return;
			case 1:
			//g2
			return;
			case 2:
			//load
			return;
			case 3:
			//store
			return;
			case 4:
			//ge1
			return;
			case 5:
			//se1
			return;
			case 6:
			//gk1
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			KeyStoreSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 7;
	}

	public static int getNumberOfStates() {
		return 6;
	}

}
interface IMacSpecMonitor extends IMonitor, IDisableHolder {
}

class MacSpecDisableHolder extends DisableHolder implements IMacSpecMonitor {
	MacSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class MacSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IMacSpecMonitor {
	protected Object clone() {
		MacSpec_Monitor_num++;
		try {
			MacSpecMonitor ret = (MacSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> safeAlgorithms = Arrays.asList("HmacSHA256", "HmacSHA384", "HmacSHA512", "HmacPBESHA1", "PBEWithHmacSHA1", "PBEWithHmacSHA224", "PBEWithHmacSHA256", "PBEWithHmacSHA384", "PBEWithHmacSHA512");

	String currentAlgorithmInstance = "";

	Mac mac = null;

	protected static long MacSpec_Monitor_num = 0;
	protected static long MacSpec_CollectedMonitor_num = 0;
	protected static long MacSpec_TerminatedMonitor_num = 0;
	protected static long MacSpec_i1_num = 0;
	protected static long MacSpec_i2_num = 0;
	protected static long MacSpec_update_num = 0;
	protected static long MacSpec_g1_num = 0;
	protected static long MacSpec_g2_num = 0;
	protected static long MacSpec_f1_num = 0;
	protected static long MacSpec_g3_num = 0;
	protected static long MacSpec_f2_num = 0;
	protected static long MacSpec_1_fail_num = 0;
	protected static long MacSpec_1_match_num = 0;

	WeakReference Ref_m = null;
	int Prop_1_state;
	static final int Prop_1_transition_g1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g2[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g3[] = {0, 4, 4, 4, 4};;
	static final int Prop_1_transition_i1[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_i2[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_update[] = {4, 4, 4, 3, 4};;
	static final int Prop_1_transition_f1[] = {4, 4, 4, 1, 4};;
	static final int Prop_1_transition_f2[] = {4, 4, 4, 1, 4};;

	boolean MacSpecMonitor_Prop_1_Category_fail = false;
	boolean MacSpecMonitor_Prop_1_Category_match = false;

	MacSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		MacSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return MacSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return MacSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return MacSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("i1", MacSpec_i1_num);
		eventCounters.put("i2", MacSpec_i2_num);
		eventCounters.put("update", MacSpec_update_num);
		eventCounters.put("g1", MacSpec_g1_num);
		eventCounters.put("g2", MacSpec_g2_num);
		eventCounters.put("f1", MacSpec_f1_num);
		eventCounters.put("g3", MacSpec_g3_num);
		eventCounters.put("f2", MacSpec_f2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", MacSpec_1_fail_num);
		categoryCounters.put("match", MacSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_g1(String alg, Mac m) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				mac = m;
				currentAlgorithmInstance = alg;
			}
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_g1[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, Mac m) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				mac = m;
				currentAlgorithmInstance = alg;
			}
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_g2[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_g3(String alg, Mac m) {
		{
			if ( ! (!safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_g3[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_i1(java.security.Key key, Mac m) {
		{
			if ( ! (ExecutionContext.instance().validate(ExecutionContext.Property.GENERATED_KEY, key)) ) {
				return false;
			}
			{
				if (!safeAlgorithms.contains(currentAlgorithmInstance)) {
					ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MacSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " expecting one of " + String.join(",", safeAlgorithms) + " but found " + currentAlgorithmInstance + "."));
				}
			}
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_i1[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_i2(java.security.Key key, java.security.spec.AlgorithmParameterSpec params, Mac m) {
		{
			if ( ! (ExecutionContext.instance().validate(ExecutionContext.Property.GENERATED_KEY, key)) ) {
				return false;
			}
			{
				if (!safeAlgorithms.contains(currentAlgorithmInstance)) {
					ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MacSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "one of " + String.join(",", safeAlgorithms) + " but found " + currentAlgorithmInstance + "."));
				}
			}
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_i2[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_update(Mac m) {
		{
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 5;

		Prop_1_state = Prop_1_transition_update[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_f1(Mac m, byte[] output) {
		{
			ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output);
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 6;

		Prop_1_state = Prop_1_transition_f1[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_f2(byte[] output, int outOffset) {
		Mac m = null;
		if(Ref_m != null){
			m = (Mac)Ref_m.get();
		}
		{
			ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output);
		}
		RVM_lastevent = 7;

		Prop_1_state = Prop_1_transition_f2[Prop_1_state];
		MacSpecMonitor_Prop_1_Category_fail = Prop_1_state == 4;
		MacSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(MacSpecMonitor_Prop_1_Category_fail) {
			MacSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "MacSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().remove(Property.GENERATED_MAC);
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(MacSpecMonitor_Prop_1_Category_match) {
			MacSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(mac);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		MacSpecMonitor_Prop_1_Category_fail = false;
		MacSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_m was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//g1
			return;
			case 1:
			//g2
			return;
			case 2:
			//g3
			return;
			case 3:
			//i1
			return;
			case 4:
			//i2
			return;
			case 5:
			//update
			return;
			case 6:
			//f1
			return;
			case 7:
			//f2
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			MacSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 8;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
class MessageDigestSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		MessageDigestSpec_Monitor_num++;
		try {
			MessageDigestSpecMonitor ret = (MessageDigestSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> algorithms = Arrays.asList("SHA-256", "SHA-384", "SHA-512");

	MessageDigest md = null;

	String currentAlgorithmInstance = "";

	protected static long MessageDigestSpec_Monitor_num = 0;
	protected static long MessageDigestSpec_CollectedMonitor_num = 0;
	protected static long MessageDigestSpec_TerminatedMonitor_num = 0;
	protected static long MessageDigestSpec_update_num = 0;
	protected static long MessageDigestSpec_reset_num = 0;
	protected static long MessageDigestSpec_g1_num = 0;
	protected static long MessageDigestSpec_g2_num = 0;
	protected static long MessageDigestSpec_g3_num = 0;
	protected static long MessageDigestSpec_g4_num = 0;
	protected static long MessageDigestSpec_d1_num = 0;
	protected static long MessageDigestSpec_d2_num = 0;
	protected static long MessageDigestSpec_d3_num = 0;
	protected static long MessageDigestSpec_1_fail_num = 0;
	protected static long MessageDigestSpec_1_match_num = 0;

	static final int Prop_1_transition_g1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g2[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g3[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g4[] = {0, 4, 4, 4, 4};;
	static final int Prop_1_transition_update[] = {4, 1, 1, 1, 4};;
	static final int Prop_1_transition_reset[] = {4, 4, 4, 4, 4};;
	static final int Prop_1_transition_d1[] = {4, 3, 4, 4, 4};;
	static final int Prop_1_transition_d2[] = {4, 3, 3, 3, 4};;
	static final int Prop_1_transition_d3[] = {4, 3, 4, 4, 4};;

	volatile boolean MessageDigestSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean MessageDigestSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	MessageDigestSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		MessageDigestSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return MessageDigestSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return MessageDigestSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return MessageDigestSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("update", MessageDigestSpec_update_num);
		eventCounters.put("reset", MessageDigestSpec_reset_num);
		eventCounters.put("g1", MessageDigestSpec_g1_num);
		eventCounters.put("g2", MessageDigestSpec_g2_num);
		eventCounters.put("g3", MessageDigestSpec_g3_num);
		eventCounters.put("g4", MessageDigestSpec_g4_num);
		eventCounters.put("d1", MessageDigestSpec_d1_num);
		eventCounters.put("d2", MessageDigestSpec_d2_num);
		eventCounters.put("d3", MessageDigestSpec_d3_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", MessageDigestSpec_1_fail_num);
		categoryCounters.put("match", MessageDigestSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, Provider provider, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g4(String alg, MessageDigest digest) {
		{
			if ( ! (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_g4) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_update(MessageDigest digest) {
		{
			if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_update) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_reset(MessageDigest digest) {
		{
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_reset) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d1(MessageDigest digest, byte[] out) {
		{
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_d1) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d2(MessageDigest digest, byte[] out) {
		{
			if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
			}
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_d2) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d3(byte[] out, int offset, int len, MessageDigest digest) {
		{
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_d3) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(MessageDigestSpecMonitor_Prop_1_Category_fail) {
			MessageDigestSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(md);
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(MessageDigestSpecMonitor_Prop_1_Category_match) {
			MessageDigestSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(md);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		MessageDigestSpecMonitor_Prop_1_Category_fail = false;
		MessageDigestSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_digest was suppressed to reduce memory overhead

	//alive_parameters_0 = [MessageDigest digest]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//g4
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//update
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//reset
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//d1
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//d2
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//d3
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			MessageDigestSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 9;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
interface IPBEKeySpecSpecMonitor extends IMonitor, IDisableHolder {
}

class PBEKeySpecSpecDisableHolder extends DisableHolder implements IPBEKeySpecSpecMonitor {
	PBEKeySpecSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class PBEKeySpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IPBEKeySpecSpecMonitor {
	protected Object clone() {
		PBEKeySpecSpec_Monitor_num++;
		try {
			PBEKeySpecSpecMonitor ret = (PBEKeySpecSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	PBEKeySpec spec;

	protected static long PBEKeySpecSpec_Monitor_num = 0;
	protected static long PBEKeySpecSpec_CollectedMonitor_num = 0;
	protected static long PBEKeySpecSpec_TerminatedMonitor_num = 0;
	protected static long PBEKeySpecSpec_err3_num = 0;
	protected static long PBEKeySpecSpec_err2_num = 0;
	protected static long PBEKeySpecSpec_err1_num = 0;
	protected static long PBEKeySpecSpec_f1_num = 0;
	protected static long PBEKeySpecSpec_f2_num = 0;
	protected static long PBEKeySpecSpec_c1_num = 0;
	protected static long PBEKeySpecSpec_c2_num = 0;
	protected static long PBEKeySpecSpec_1_fail_num = 0;
	protected static long PBEKeySpecSpec_1_match_num = 0;

	WeakReference Ref_s = null;
	int Prop_1_state;
	static final int Prop_1_transition_f1[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_f2[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_c1[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_err1[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_err2[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_err3[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_c2[] = {3, 3, 1, 3};;

	boolean PBEKeySpecSpecMonitor_Prop_1_Category_fail = false;
	boolean PBEKeySpecSpecMonitor_Prop_1_Category_match = false;

	PBEKeySpecSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		PBEKeySpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return PBEKeySpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return PBEKeySpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return PBEKeySpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("err3", PBEKeySpecSpec_err3_num);
		eventCounters.put("err2", PBEKeySpecSpec_err2_num);
		eventCounters.put("err1", PBEKeySpecSpec_err1_num);
		eventCounters.put("f1", PBEKeySpecSpec_f1_num);
		eventCounters.put("f2", PBEKeySpecSpec_f2_num);
		eventCounters.put("c1", PBEKeySpecSpec_c1_num);
		eventCounters.put("c2", PBEKeySpecSpec_c2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", PBEKeySpecSpec_1_fail_num);
		categoryCounters.put("match", PBEKeySpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_f1(char[] password) {
		PBEKeySpec s = null;
		if(Ref_s != null){
			s = (PBEKeySpec)Ref_s.get();
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "PBEKeySpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_f1[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_f2(char[] password, byte[] salt, int keyLength) {
		PBEKeySpec s = null;
		if(Ref_s != null){
			s = (PBEKeySpec)Ref_s.get();
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "PBEKeySpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_f2[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_c1(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		{
			if ( ! (iterationCount >= 10000 && ExecutionContext.instance().validate(Property.RANDOMIZED, password) && ExecutionContext.instance().validate(Property.RANDOMIZED, salt)) ) {
				return false;
			}
			{
				spec = s;
				ExecutionContext.instance().setProperty(Property.SPECCED_KEY, spec);
			}
		}
		if(Ref_s == null){
			Ref_s = new WeakReference(s);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_c1[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_err1(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		{
			if ( ! (iterationCount < 10000) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "PBEKeySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "third argument should be >= 1000"));
			}
		}
		if(Ref_s == null){
			Ref_s = new WeakReference(s);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_err1[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_err2(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, password)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "PBEKeySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "first argument should have been randomized"));
			}
		}
		if(Ref_s == null){
			Ref_s = new WeakReference(s);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_err2[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_err3(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, salt)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "PBEKeySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "second argument should have been randomized"));
			}
		}
		if(Ref_s == null){
			Ref_s = new WeakReference(s);
		}
		RVM_lastevent = 5;

		Prop_1_state = Prop_1_transition_err3[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_c2(PBEKeySpec s) {
		{
			ExecutionContext.instance().remove(Property.SPECCED_KEY, s);
		}
		if(Ref_s == null){
			Ref_s = new WeakReference(s);
		}
		RVM_lastevent = 6;

		Prop_1_state = Prop_1_transition_c2[Prop_1_state];
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			PBEKeySpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "PBEKeySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			PBEKeySpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		PBEKeySpecSpecMonitor_Prop_1_Category_fail = false;
		PBEKeySpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//f1
			return;
			case 1:
			//f2
			return;
			case 2:
			//c1
			return;
			case 3:
			//err1
			return;
			case 4:
			//err2
			return;
			case 5:
			//err3
			return;
			case 6:
			//c2
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			PBEKeySpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 7;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class PBEParameterSpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		PBEParameterSpecSpec_Monitor_num++;
		try {
			PBEParameterSpecSpecMonitor ret = (PBEParameterSpecSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	PBEParameterSpec spec;

	protected static long PBEParameterSpecSpec_Monitor_num = 0;
	protected static long PBEParameterSpecSpec_CollectedMonitor_num = 0;
	protected static long PBEParameterSpecSpec_TerminatedMonitor_num = 0;
	protected static long PBEParameterSpecSpec_c3_num = 0;
	protected static long PBEParameterSpecSpec_c1_num = 0;
	protected static long PBEParameterSpecSpec_c2_num = 0;
	protected static long PBEParameterSpecSpec_1_fail_num = 0;
	protected static long PBEParameterSpecSpec_1_match_num = 0;

	static final int Prop_1_transition_c1[] = {1, 2, 2};;
	static final int Prop_1_transition_c2[] = {1, 2, 2};;
	static final int Prop_1_transition_c3[] = {2, 2, 2};;

	volatile boolean PBEParameterSpecSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean PBEParameterSpecSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	PBEParameterSpecSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		PBEParameterSpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return PBEParameterSpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return PBEParameterSpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return PBEParameterSpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c3", PBEParameterSpecSpec_c3_num);
		eventCounters.put("c1", PBEParameterSpecSpec_c1_num);
		eventCounters.put("c2", PBEParameterSpecSpec_c2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", PBEParameterSpecSpec_1_fail_num);
		categoryCounters.put("match", PBEParameterSpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(byte[] salt, int iterationCount, PBEParameterSpec s) {
		{
			if ( ! (iterationCount >= 10000 && ExecutionContext.instance().validate(Property.RANDOMIZED, salt)) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c2(byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec, PBEParameterSpec s) {
		{
			if ( ! (iterationCount >= 10000 && ExecutionContext.instance().validate(Property.RANDOMIZED, salt)) ) {
				return false;
			}
			{
				spec = s;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_c2) ;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c3(byte[] salt, int iterationCount, PBEParameterSpec s) {
		{
			if ( ! (iterationCount < 10000 || !(ExecutionContext.instance().validate(Property.RANDOMIZED, salt))) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "PBEParameterSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting at least 1000 iterations and a randomized salt."));
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_c3) ;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.PBEParameterSpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
			PBEParameterSpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "PBEParameterSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
			PBEParameterSpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setProperty(ExecutionContext.Property.PREPARED_PBE, spec);
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		PBEParameterSpecSpecMonitor_Prop_1_Category_fail = false;
		PBEParameterSpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [PBEParameterSpec s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				PBEParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//c2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				PBEParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//c3
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				PBEParameterSpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			PBEParameterSpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 3;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
interface IRandomStringPasswordSpecMonitor extends IMonitor, IDisableHolder {
}

class RandomStringPasswordSpecDisableHolder extends DisableHolder implements IRandomStringPasswordSpecMonitor {
	RandomStringPasswordSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class RandomStringPasswordSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IRandomStringPasswordSpecMonitor {
	protected Object clone() {
		RandomStringPasswordSpec_Monitor_num++;
		try {
			RandomStringPasswordSpecMonitor ret = (RandomStringPasswordSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	protected static long RandomStringPasswordSpec_Monitor_num = 0;
	protected static long RandomStringPasswordSpec_CollectedMonitor_num = 0;
	protected static long RandomStringPasswordSpec_TerminatedMonitor_num = 0;
	protected static long RandomStringPasswordSpec_vo_num = 0;
	protected static long RandomStringPasswordSpec_gb_num = 0;
	protected static long RandomStringPasswordSpec_1_match_num = 0;

	WeakReference Ref_str = null;
	int Prop_1_state;
	static final int Prop_1_transition_vo[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_gb[] = {3, 3, 1, 3};;

	boolean RandomStringPasswordSpecMonitor_Prop_1_Category_match = false;

	RandomStringPasswordSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		RandomStringPasswordSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return RandomStringPasswordSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return RandomStringPasswordSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return RandomStringPasswordSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("vo", RandomStringPasswordSpec_vo_num);
		eventCounters.put("gb", RandomStringPasswordSpec_gb_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("match", RandomStringPasswordSpec_1_match_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_vo(Object obj, String s) {
		String str = null;
		if(Ref_str != null){
			str = (String)Ref_str.get();
		}
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, obj)) ) {
				return false;
			}
			{
				ExecutionContext.instance().setProperty(Property.RANDOMIZED, s);
			}
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_vo[Prop_1_state];
		RandomStringPasswordSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final boolean Prop_1_event_gb(String s, char[] chars) {
		String str = null;
		if(Ref_str != null){
			str = (String)Ref_str.get();
		}
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, s)) ) {
				return false;
			}
			{
				ExecutionContext.instance().setProperty(Property.RANDOMIZED, chars);
			}
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_gb[Prop_1_state];
		RandomStringPasswordSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;
		return true;
	}

	final void Prop_1_handler_match (){
		if(RandomStringPasswordSpecMonitor_Prop_1_Category_match) {
			RandomStringPasswordSpec_1_match_num++;
		}
		{
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		RandomStringPasswordSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_str was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//vo
			return;
			case 1:
			//gb
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			RandomStringPasswordSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
interface ISSLContextSpecMonitor extends IMonitor, IDisableHolder {
}

class SSLContextSpecDisableHolder extends DisableHolder implements ISSLContextSpecMonitor {
	SSLContextSpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class SSLContextSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, ISSLContextSpecMonitor {
	protected Object clone() {
		SSLContextSpec_Monitor_num++;
		try {
			SSLContextSpecMonitor ret = (SSLContextSpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> protocols = Arrays.asList("TLSV1.2", "TLSV1.3");

	String currentProtocol = "";

	SSLContext context;

	SSLEngine engine;

	protected static long SSLContextSpec_Monitor_num = 0;
	protected static long SSLContextSpec_CollectedMonitor_num = 0;
	protected static long SSLContextSpec_TerminatedMonitor_num = 0;
	protected static long SSLContextSpec_init_num = 0;
	protected static long SSLContextSpec_engine_num = 0;
	protected static long SSLContextSpec_unsafe_protocol_num = 0;
	protected static long SSLContextSpec_g1_num = 0;
	protected static long SSLContextSpec_g2_num = 0;
	protected static long SSLContextSpec_1_fail_num = 0;
	protected static long SSLContextSpec_1_match1_num = 0;

	WeakReference Ref_ctx = null;
	int Prop_1_state;
	static final int Prop_1_transition_g1[] = {1, 3, 3, 3};;
	static final int Prop_1_transition_g2[] = {1, 3, 3, 3};;
	static final int Prop_1_transition_unsafe_protocol[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_init[] = {3, 2, 3, 3};;
	static final int Prop_1_transition_engine[] = {3, 3, 2, 3};;

	boolean SSLContextSpecMonitor_Prop_1_Category_fail = false;
	boolean SSLContextSpecMonitor_Prop_1_Category_match1 = false;

	SSLContextSpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		SSLContextSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return SSLContextSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return SSLContextSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return SSLContextSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("init", SSLContextSpec_init_num);
		eventCounters.put("engine", SSLContextSpec_engine_num);
		eventCounters.put("unsafe_protocol", SSLContextSpec_unsafe_protocol_num);
		eventCounters.put("g1", SSLContextSpec_g1_num);
		eventCounters.put("g2", SSLContextSpec_g2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", SSLContextSpec_1_fail_num);
		categoryCounters.put("match1", SSLContextSpec_1_match1_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_g1(String protocol, SSLContext ctx) {
		{
			if ( ! (protocols.contains(protocol.toUpperCase())) ) {
				return false;
			}
			{
				context = ctx;
				currentProtocol = protocol;
			}
		}
		if(Ref_ctx == null){
			Ref_ctx = new WeakReference(ctx);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_g1[Prop_1_state];
		SSLContextSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		SSLContextSpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_g2(String protocol, String provider, SSLContext ctx) {
		{
			if ( ! (protocols.contains(protocol.toUpperCase())) ) {
				return false;
			}
			{
				context = ctx;
				currentProtocol = protocol;
			}
		}
		if(Ref_ctx == null){
			Ref_ctx = new WeakReference(ctx);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_g2[Prop_1_state];
		SSLContextSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		SSLContextSpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_unsafe_protocol(String protocol) {
		SSLContext ctx = null;
		if(Ref_ctx != null){
			ctx = (SSLContext)Ref_ctx.get();
		}
		{
			if ( ! (!protocols.contains(protocol.toUpperCase())) ) {
				return false;
			}
			{
				currentProtocol = protocol;
			}
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_unsafe_protocol[Prop_1_state];
		SSLContextSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		SSLContextSpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_init(SSLContext ctx) {
		{
			if (!protocols.contains(currentProtocol.toUpperCase())) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeProtocol, "SSLContextSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {TLSv1.2, TLSv1.3} but found " + currentProtocol + "."));
			}
			ExecutionContext.instance().setProperty(Property.GENERATE_SSL_CONTEXT, context);
		}
		if(Ref_ctx == null){
			Ref_ctx = new WeakReference(ctx);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_init[Prop_1_state];
		SSLContextSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		SSLContextSpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_engine(SSLContext ctx, SSLEngine eng) {
		{
			ExecutionContext.instance().setProperty(Property.GENERATE_SSL_ENGINE, eng);
		}
		if(Ref_ctx == null){
			Ref_ctx = new WeakReference(ctx);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_engine[Prop_1_state];
		SSLContextSpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		SSLContextSpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(SSLContextSpecMonitor_Prop_1_Category_fail) {
			SSLContextSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "SSLContextSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(context);
			this.reset();
		}

	}

	final void Prop_1_handler_match1 (){
		if(SSLContextSpecMonitor_Prop_1_Category_match1) {
			SSLContextSpec_1_match1_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(context);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		SSLContextSpecMonitor_Prop_1_Category_fail = false;
		SSLContextSpecMonitor_Prop_1_Category_match1 = false;
	}

	// RVMRef_ctx was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//g1
			return;
			case 1:
			//g2
			return;
			case 2:
			//unsafe_protocol
			return;
			case 3:
			//init
			return;
			case 4:
			//engine
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			SSLContextSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class SecretKeySpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		SecretKeySpec_Monitor_num++;
		try {
			SecretKeySpecMonitor ret = (SecretKeySpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	protected static long SecretKeySpec_Monitor_num = 0;
	protected static long SecretKeySpec_CollectedMonitor_num = 0;
	protected static long SecretKeySpec_TerminatedMonitor_num = 0;
	protected static long SecretKeySpec_e1_num = 0;
	protected static long SecretKeySpec_1_match_num = 0;

	static final int Prop_1_transition_e1[] = {0, 1};;

	volatile boolean SecretKeySpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	SecretKeySpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		SecretKeySpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return SecretKeySpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return SecretKeySpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return SecretKeySpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("e1", SecretKeySpec_e1_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("match", SecretKeySpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 1) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 1) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 1) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_e1(SecretKey secretKey, byte[] key) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.GENERATED_KEY, secretKey)) ) {
				return false;
			}
			{
				ExecutionContext.instance().setProperty(Property.RANDOMIZED, key);
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_e1) ;
		this.SecretKeySpecMonitor_Prop_1_Category_match = nextstate == 0;

		return true;
	}

	final void Prop_1_handler_match (){
		if(SecretKeySpecMonitor_Prop_1_Category_match) {
			SecretKeySpec_1_match_num++;
		}
		{
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		SecretKeySpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_secretKey was suppressed to reduce memory overhead

	//alive_parameters_0 = [SecretKey secretKey]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//e1
			//alive_secretKey
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecretKeySpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			SecretKeySpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 1;
	}

	public static int getNumberOfStates() {
		return 2;
	}

}
class SecretKeySpecSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		SecretKeySpecSpec_Monitor_num++;
		try {
			SecretKeySpecSpecMonitor ret = (SecretKeySpecSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> algorithms = Arrays.asList("AES", "HMACSHA256", "HMACSHA384", "HMACSHA512");

	SecretKeySpec spec;

	protected static long SecretKeySpecSpec_Monitor_num = 0;
	protected static long SecretKeySpecSpec_CollectedMonitor_num = 0;
	protected static long SecretKeySpecSpec_TerminatedMonitor_num = 0;
	protected static long SecretKeySpecSpec_c3_num = 0;
	protected static long SecretKeySpecSpec_c4_num = 0;
	protected static long SecretKeySpecSpec_c1_num = 0;
	protected static long SecretKeySpecSpec_c2_num = 0;
	protected static long SecretKeySpecSpec_1_fail_num = 0;
	protected static long SecretKeySpecSpec_1_match_num = 0;

	static final int Prop_1_transition_c1[] = {1, 2, 2};;
	static final int Prop_1_transition_c2[] = {1, 2, 2};;
	static final int Prop_1_transition_c3[] = {2, 2, 2};;
	static final int Prop_1_transition_c4[] = {2, 2, 2};;

	volatile boolean SecretKeySpecSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean SecretKeySpecSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	SecretKeySpecSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		SecretKeySpecSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return SecretKeySpecSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return SecretKeySpecSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return SecretKeySpecSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("c3", SecretKeySpecSpec_c3_num);
		eventCounters.put("c4", SecretKeySpecSpec_c4_num);
		eventCounters.put("c1", SecretKeySpecSpec_c1_num);
		eventCounters.put("c2", SecretKeySpecSpec_c2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", SecretKeySpecSpec_1_fail_num);
		categoryCounters.put("match", SecretKeySpecSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		{
			if ( ! (algorithms.contains(keyAlgorithm.toUpperCase()) && ExecutionContext.instance().validate(ExecutionContext.Property.RANDOMIZED, keyMaterial)) ) {
				return false;
			}
			{
				spec = secretKeySpec;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c2(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		{
			if ( ! (algorithms.contains(keyAlgorithm.toUpperCase()) && keyMaterial.length >= offset + len) ) {
				return false;
			}
			{
				spec = secretKeySpec;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_c2) ;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c3(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		{
			if ( ! (!(algorithms.contains(keyAlgorithm.toUpperCase()) && ExecutionContext.instance().validate(ExecutionContext.Property.RANDOMIZED, keyMaterial))) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "SecretKeySpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " Using either an invalid algorithm or keyMaterial.length is not randomized."));
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_c3) ;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_c4(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		{
			if ( ! (!algorithms.contains(keyAlgorithm.toUpperCase()) || keyMaterial.length < offset + len) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "SecretKeySpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " Using either an invalid algorithm or keyMaterial.length < offset + len "));
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_c4) ;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_fail = nextstate == 2;
		this.SecretKeySpecSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
			SecretKeySpecSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "SecretKeySpecSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(SecretKeySpecSpecMonitor_Prop_1_Category_match) {
			SecretKeySpecSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(spec);
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_KEY, spec);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		SecretKeySpecSpecMonitor_Prop_1_Category_fail = false;
		SecretKeySpecSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_secretKeySpec was suppressed to reduce memory overhead

	//alive_parameters_0 = [SecretKeySpec secretKeySpec]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_secretKeySpec
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecretKeySpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//c2
			//alive_secretKeySpec
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecretKeySpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//c3
			//alive_secretKeySpec
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecretKeySpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//c4
			//alive_secretKeySpec
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecretKeySpecSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			SecretKeySpecSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 4;
	}

	public static int getNumberOfStates() {
		return 3;
	}

}
class SecureRandomSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		SecureRandomSpec_Monitor_num++;
		try {
			SecureRandomSpecMonitor ret = (SecureRandomSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	SecureRandom sr;

	List<String> algorithms = Arrays.asList("SHA1PRNG", "Windows-PRNG", "NativePRNG", "NativePRNGBlocking", "NativePRNGNonBlocking", "PKCS11");

	protected static long SecureRandomSpec_Monitor_num = 0;
	protected static long SecureRandomSpec_CollectedMonitor_num = 0;
	protected static long SecureRandomSpec_TerminatedMonitor_num = 0;
	protected static long SecureRandomSpec_next2_num = 0;
	protected static long SecureRandomSpec_next1_num = 0;
	protected static long SecureRandomSpec_g1_num = 0;
	protected static long SecureRandomSpec_g2_num = 0;
	protected static long SecureRandomSpec_g3_num = 0;
	protected static long SecureRandomSpec_g4_num = 0;
	protected static long SecureRandomSpec_c1_num = 0;
	protected static long SecureRandomSpec_c2_num = 0;
	protected static long SecureRandomSpec_setSeed3_num = 0;
	protected static long SecureRandomSpec_c3_num = 0;
	protected static long SecureRandomSpec_setSeed2_num = 0;
	protected static long SecureRandomSpec_setSeed1_num = 0;
	protected static long SecureRandomSpec_genSeed_num = 0;
	protected static long SecureRandomSpec_ints_num = 0;
	protected static long SecureRandomSpec_next3_num = 0;
	protected static long SecureRandomSpec_1_fail_num = 0;
	protected static long SecureRandomSpec_1_match1_num = 0;

	static final int Prop_1_transition_c1[] = {2, 3, 2, 3};;
	static final int Prop_1_transition_c2[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_c3[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_g1[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_g2[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_g3[] = {2, 3, 3, 3};;
	static final int Prop_1_transition_g4[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_setSeed1[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_setSeed2[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_setSeed3[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_genSeed[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_next1[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_next2[] = {3, 3, 1, 3};;
	static final int Prop_1_transition_next3[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_ints[] = {3, 1, 1, 3};;

	volatile boolean SecureRandomSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean SecureRandomSpecMonitor_Prop_1_Category_match1 = false;

	private AtomicInteger pairValue;

	SecureRandomSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		SecureRandomSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return SecureRandomSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return SecureRandomSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return SecureRandomSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("next2", SecureRandomSpec_next2_num);
		eventCounters.put("next1", SecureRandomSpec_next1_num);
		eventCounters.put("g1", SecureRandomSpec_g1_num);
		eventCounters.put("g2", SecureRandomSpec_g2_num);
		eventCounters.put("g3", SecureRandomSpec_g3_num);
		eventCounters.put("g4", SecureRandomSpec_g4_num);
		eventCounters.put("c1", SecureRandomSpec_c1_num);
		eventCounters.put("c2", SecureRandomSpec_c2_num);
		eventCounters.put("setSeed3", SecureRandomSpec_setSeed3_num);
		eventCounters.put("c3", SecureRandomSpec_c3_num);
		eventCounters.put("setSeed2", SecureRandomSpec_setSeed2_num);
		eventCounters.put("setSeed1", SecureRandomSpec_setSeed1_num);
		eventCounters.put("genSeed", SecureRandomSpec_genSeed_num);
		eventCounters.put("ints", SecureRandomSpec_ints_num);
		eventCounters.put("next3", SecureRandomSpec_next3_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", SecureRandomSpec_1_fail_num);
		categoryCounters.put("match1", SecureRandomSpec_1_match1_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_c1(SecureRandom r) {
		{
			sr = r;
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_c1) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_c2(byte[] seed, SecureRandom r) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, seed)) ) {
				return false;
			}
			{
				sr = r;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_c2) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_c3(byte[] seed, SecureRandom r) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, seed)) ) {
				return false;
			}
			{
				sr = r;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_c3) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g1(String alg, SecureRandom r) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				sr = r;
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_g1) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, SecureRandom r) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				sr = r;
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_g2) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g3(SecureRandom r) {
		{
			sr = r;
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_g3) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_g4(String alg, SecureRandom r) {
		{
			if ( ! (!algorithms.contains(alg)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SecureRandomSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(" or ", algorithms) + " but found " + alg + "."));
			}
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_g4) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_setSeed1(SecureRandom r) {
		{
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_setSeed1) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_setSeed2(byte[] seed, SecureRandom r) {
		{
			if ( ! (ExecutionContext.instance().validate(Property.RANDOMIZED, seed)) ) {
				return false;
			}
			{
			}
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_setSeed2) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_setSeed3(byte[] seed, SecureRandom r) {
		{
			if ( ! (!ExecutionContext.instance().validate(Property.RANDOMIZED, seed)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "SecureRandomSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "setSeed() expects a randomized byte array."));
			}
		}

		int nextstate = this.handleEvent(9, Prop_1_transition_setSeed3) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_genSeed(SecureRandom r, byte[] seed) {
		{
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, seed);
		}

		int nextstate = this.handleEvent(10, Prop_1_transition_genSeed) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_next1(SecureRandom r, int randIntInRange) {
		{
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, randIntInRange);
		}

		int nextstate = this.handleEvent(11, Prop_1_transition_next1) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_next2(SecureRandom r, byte[] bytes) {
		{
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, bytes);
		}

		int nextstate = this.handleEvent(12, Prop_1_transition_next2) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_next3(SecureRandom r, int randInt) {
		{
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, randInt);
		}

		int nextstate = this.handleEvent(13, Prop_1_transition_next3) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_ints(SecureRandom r, IntStream stream) {
		{
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, stream);
		}

		int nextstate = this.handleEvent(14, Prop_1_transition_ints) ;
		this.SecureRandomSpecMonitor_Prop_1_Category_fail = nextstate == 3;
		this.SecureRandomSpecMonitor_Prop_1_Category_match1 = nextstate == 2;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(SecureRandomSpecMonitor_Prop_1_Category_fail) {
			SecureRandomSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "SecureRandomSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match1 (){
		if(SecureRandomSpecMonitor_Prop_1_Category_match1) {
			SecureRandomSpec_1_match1_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(sr);
			ExecutionContext.instance().setProperty(Property.RANDOMIZED, sr);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		SecureRandomSpecMonitor_Prop_1_Category_fail = false;
		SecureRandomSpecMonitor_Prop_1_Category_match1 = false;
	}

	// RVMRef_r was suppressed to reduce memory overhead

	//alive_parameters_0 = [SecureRandom r]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//c1
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//c2
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//c3
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//g1
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//g2
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//g3
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//g4
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//setSeed1
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//setSeed2
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 9:
			//setSeed3
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 10:
			//genSeed
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 11:
			//next1
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 12:
			//next2
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 13:
			//next3
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 14:
			//ints
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SecureRandomSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			SecureRandomSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 15;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class SignatureSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		SignatureSpec_Monitor_num++;
		try {
			SignatureSpecMonitor ret = (SignatureSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> algorithms = Arrays.asList("SHA256withRSA", "SHA256withECDSA", "SHA256withDSA", "SHA384withRSA", "SHA512withRSA", "SHA384withECDSA", "SHA512withECDSA");

	String currentAlgorithmInstance = "";

	Signature signature = null;

	protected static long SignatureSpec_Monitor_num = 0;
	protected static long SignatureSpec_CollectedMonitor_num = 0;
	protected static long SignatureSpec_TerminatedMonitor_num = 0;
	protected static long SignatureSpec_i1_num = 0;
	protected static long SignatureSpec_i2_num = 0;
	protected static long SignatureSpec_update_num = 0;
	protected static long SignatureSpec_g1_num = 0;
	protected static long SignatureSpec_i3_num = 0;
	protected static long SignatureSpec_g2_num = 0;
	protected static long SignatureSpec_i4_num = 0;
	protected static long SignatureSpec_v1_num = 0;
	protected static long SignatureSpec_g3_num = 0;
	protected static long SignatureSpec_v2_num = 0;
	protected static long SignatureSpec_s1_num = 0;
	protected static long SignatureSpec_s2_num = 0;
	protected static long SignatureSpec_1_fail_num = 0;
	protected static long SignatureSpec_1_match_num = 0;

	static final int Prop_1_transition_g1[] = {4, 8, 8, 8, 8, 8, 8, 8, 8};;
	static final int Prop_1_transition_g2[] = {4, 8, 8, 8, 8, 8, 8, 8, 8};;
	static final int Prop_1_transition_g3[] = {8, 8, 8, 8, 8, 8, 8, 8, 8};;
	static final int Prop_1_transition_i1[] = {8, 8, 2, 2, 2, 8, 8, 8, 8};;
	static final int Prop_1_transition_i2[] = {8, 8, 2, 2, 2, 8, 8, 8, 8};;
	static final int Prop_1_transition_i3[] = {8, 1, 8, 8, 1, 8, 8, 1, 8};;
	static final int Prop_1_transition_i4[] = {8, 1, 8, 8, 1, 8, 8, 1, 8};;
	static final int Prop_1_transition_update[] = {8, 5, 6, 6, 8, 5, 6, 5, 8};;
	static final int Prop_1_transition_s1[] = {8, 8, 8, 3, 8, 8, 3, 8, 8};;
	static final int Prop_1_transition_s2[] = {8, 8, 8, 3, 8, 8, 3, 8, 8};;
	static final int Prop_1_transition_v1[] = {8, 7, 8, 8, 8, 7, 8, 7, 8};;
	static final int Prop_1_transition_v2[] = {8, 7, 8, 8, 8, 7, 8, 7, 8};;

	volatile boolean SignatureSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean SignatureSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	SignatureSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		SignatureSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return SignatureSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return SignatureSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return SignatureSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("i1", SignatureSpec_i1_num);
		eventCounters.put("i2", SignatureSpec_i2_num);
		eventCounters.put("update", SignatureSpec_update_num);
		eventCounters.put("g1", SignatureSpec_g1_num);
		eventCounters.put("i3", SignatureSpec_i3_num);
		eventCounters.put("g2", SignatureSpec_g2_num);
		eventCounters.put("i4", SignatureSpec_i4_num);
		eventCounters.put("v1", SignatureSpec_v1_num);
		eventCounters.put("g3", SignatureSpec_g3_num);
		eventCounters.put("v2", SignatureSpec_v2_num);
		eventCounters.put("s1", SignatureSpec_s1_num);
		eventCounters.put("s2", SignatureSpec_s2_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", SignatureSpec_1_fail_num);
		categoryCounters.put("match", SignatureSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 15) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 4) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 4) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, Signature s) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				signature = s;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, Signature s) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				signature = s;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, Signature s) {
		{
			if ( ! (!algorithms.contains(alg)) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_i1(PrivateKey privateKey, Signature s) {
		{
			if (!algorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SignatureSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(",", algorithms) + " but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_i1) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_i2(PrivateKey privateKey, SecureRandom random, Signature s) {
		{
			if (!algorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SignatureSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(",", algorithms) + " but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_i2) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_i3(Certificate cert, Signature s) {
		{
			if (!algorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SignatureSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(",", algorithms) + " but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_i3) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_i4(PublicKey key, Signature s) {
		{
			if (!algorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SignatureSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(",", algorithms) + " but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_i4) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_update(Signature s) {
		{
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_update) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_s1(Signature s, byte[] output) {
		{
			ExecutionContext.instance().setProperty(Property.SIGNED, output);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_s1) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_s2(byte[] output, int offset, int len, Signature s) {
		{
			ExecutionContext.instance().setProperty(Property.SIGNED, output);
		}

		int nextstate = this.handleEvent(9, Prop_1_transition_s2) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_v1(byte[] sign, Signature s, boolean signed) {
		{
			ExecutionContext.instance().setProperty(Property.VERIFIED, signed);
		}

		int nextstate = this.handleEvent(10, Prop_1_transition_v1) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final boolean Prop_1_event_v2(byte[] sign, int offset, int len, Signature s, boolean signed) {
		{
			ExecutionContext.instance().setProperty(Property.VERIFIED, signed);
		}

		int nextstate = this.handleEvent(11, Prop_1_transition_v2) ;
		this.SignatureSpecMonitor_Prop_1_Category_fail = nextstate == 8;
		this.SignatureSpecMonitor_Prop_1_Category_match = nextstate == 3|| nextstate == 7;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(SignatureSpecMonitor_Prop_1_Category_fail) {
			SignatureSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "SignatureSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(SignatureSpecMonitor_Prop_1_Category_match) {
			SignatureSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(signature);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		SignatureSpecMonitor_Prop_1_Category_fail = false;
		SignatureSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [Signature s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//i1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//i2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//i3
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//i4
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//update
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//s1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 9:
			//s2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 10:
			//v1
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 11:
			//v2
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				SignatureSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			SignatureSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 12;
	}

	public static int getNumberOfStates() {
		return 9;
	}

}
interface ITrustManagerFactorySpecMonitor extends IMonitor, IDisableHolder {
}

class TrustManagerFactorySpecDisableHolder extends DisableHolder implements ITrustManagerFactorySpecMonitor {
	TrustManagerFactorySpecDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class TrustManagerFactorySpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, ITrustManagerFactorySpecMonitor {
	protected Object clone() {
		TrustManagerFactorySpec_Monitor_num++;
		try {
			TrustManagerFactorySpecMonitor ret = (TrustManagerFactorySpecMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> algorithms = Arrays.asList("PKIX", "SunX509");

	String currentAlgorithmInstance = "";

	TrustManagerFactory trustManagerFactory = null;

	protected static long TrustManagerFactorySpec_Monitor_num = 0;
	protected static long TrustManagerFactorySpec_CollectedMonitor_num = 0;
	protected static long TrustManagerFactorySpec_TerminatedMonitor_num = 0;
	protected static long TrustManagerFactorySpec_init_num = 0;
	protected static long TrustManagerFactorySpec_gtm1_num = 0;
	protected static long TrustManagerFactorySpec_g1_num = 0;
	protected static long TrustManagerFactorySpec_g2_num = 0;
	protected static long TrustManagerFactorySpec_g3_num = 0;
	protected static long TrustManagerFactorySpec_1_fail_num = 0;
	protected static long TrustManagerFactorySpec_1_match1_num = 0;

	WeakReference Ref_mf = null;
	int Prop_1_state;
	static final int Prop_1_transition_g1[] = {1, 3, 1, 3};;
	static final int Prop_1_transition_g2[] = {1, 3, 1, 3};;
	static final int Prop_1_transition_g3[] = {3, 3, 3, 3};;
	static final int Prop_1_transition_init[] = {3, 2, 3, 3};;
	static final int Prop_1_transition_gtm1[] = {3, 3, 0, 3};;

	boolean TrustManagerFactorySpecMonitor_Prop_1_Category_fail = false;
	boolean TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = false;

	TrustManagerFactorySpecMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

		TrustManagerFactorySpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return TrustManagerFactorySpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return TrustManagerFactorySpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return TrustManagerFactorySpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("init", TrustManagerFactorySpec_init_num);
		eventCounters.put("gtm1", TrustManagerFactorySpec_gtm1_num);
		eventCounters.put("g1", TrustManagerFactorySpec_g1_num);
		eventCounters.put("g2", TrustManagerFactorySpec_g2_num);
		eventCounters.put("g3", TrustManagerFactorySpec_g3_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", TrustManagerFactorySpec_1_fail_num);
		categoryCounters.put("match1", TrustManagerFactorySpec_1_match1_num);
		return categoryCounters;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_g1(String alg, TrustManagerFactory mf) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				trustManagerFactory = mf;
				currentAlgorithmInstance = alg;
			}
		}
		if(Ref_mf == null){
			Ref_mf = new WeakReference(mf);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_g1[Prop_1_state];
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_g2(String alg, TrustManagerFactory mf) {
		{
			if ( ! (algorithms.contains(alg)) ) {
				return false;
			}
			{
				trustManagerFactory = mf;
				currentAlgorithmInstance = alg;
			}
		}
		if(Ref_mf == null){
			Ref_mf = new WeakReference(mf);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_g2[Prop_1_state];
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_g3(String alg, TrustManagerFactory k) {
		TrustManagerFactory mf = null;
		if(Ref_mf != null){
			mf = (TrustManagerFactory)Ref_mf.get();
		}
		{
			if ( ! (!algorithms.contains(alg)) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_g3[Prop_1_state];
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_init(TrustManagerFactory mf) {
		{
			if (!algorithms.contains(currentAlgorithmInstance)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "TrustManagerFactorySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of " + String.join(",", algorithms) + " but found " + currentAlgorithmInstance + "."));
			}
			ExecutionContext.instance().setProperty(ExecutionContext.Property.GENERATED_TRUST_MANAGER, trustManagerFactory);
		}
		if(Ref_mf == null){
			Ref_mf = new WeakReference(mf);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_init[Prop_1_state];
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final boolean Prop_1_event_gtm1(TrustManagerFactory k, TrustManager[][] trustManager) {
		TrustManagerFactory mf = null;
		if(Ref_mf != null){
			mf = (TrustManagerFactory)Ref_mf.get();
		}
		{
			ExecutionContext.instance().setProperty(Property.GENERATED_KEY_MANAGERS, trustManager);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_gtm1[Prop_1_state];
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = Prop_1_state == 3;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = Prop_1_state == 2;
		return true;
	}

	final void Prop_1_handler_fail (){
		if(TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
			TrustManagerFactorySpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "TrustManagerFactorySpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(trustManagerFactory);
			ExecutionContext.instance().remove(Property.GENERATED_TRUST_MANAGER);
			ExecutionContext.instance().remove(Property.GENERATED_TRUST_MANAGERS);
			this.reset();
		}

	}

	final void Prop_1_handler_match1 (){
		if(TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
			TrustManagerFactorySpec_1_match1_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(trustManagerFactory);
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		TrustManagerFactorySpecMonitor_Prop_1_Category_fail = false;
		TrustManagerFactorySpecMonitor_Prop_1_Category_match1 = false;
	}

	// RVMRef_mf was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//g1
			return;
			case 1:
			//g2
			return;
			case 2:
			//g3
			return;
			case 3:
			//init
			return;
			case 4:
			//gtm1
			return;
		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			TrustManagerFactorySpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}

public final class MultiSpec_1RuntimeMonitor implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	private static com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager MultiSpec_1MapManager;
	static {
		MultiSpec_1MapManager = new com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager();
		MultiSpec_1MapManager.start();
	}

	// Declarations for the Lock
	static final ReentrantLock MultiSpec_1_RVMLock = new ReentrantLock();
	static final Condition MultiSpec_1_RVMLock_cond = MultiSpec_1_RVMLock.newCondition();

	// Declarations for Timestamps
	private static long PBEKeySpecSpec_timestamp = 1;
	private static long SSLContextSpec_timestamp = 1;
	private static long KeyPairSpec_timestamp = 1;
	private static long MacSpec_timestamp = 1;
	private static long HMACParameterSpecSpec_timestamp = 1;
	private static long KeyStoreSpec_timestamp = 1;
	private static long TrustManagerFactorySpec_timestamp = 1;
	private static long RandomStringPasswordSpec_timestamp = 1;

	private static boolean CipherInputStreamSpec_activated = false;
	private static boolean CipherOutputStreamSpec_activated = false;
	private static boolean CipherSpec_activated = false;
	private static boolean DHGenParameterSpecSpec_activated = false;
	private static boolean GCMParameterSpecSpec_activated = false;
	private static boolean HMACParameterSpecSpec_activated = false;
	private static boolean IvParameterSpecSpec_activated = false;
	private static boolean KeyGeneratorSpec_activated = false;
	private static boolean KeyManagerFactorySpec_activated = false;
	private static boolean KeyPairGeneratorSpec_activated = false;
	private static boolean KeyPairSpec_activated = false;
	private static boolean KeyStoreSpec_activated = false;
	private static boolean MacSpec_activated = false;
	private static boolean MessageDigestSpec_activated = false;
	private static boolean PBEKeySpecSpec_activated = false;
	private static boolean PBEParameterSpecSpec_activated = false;
	private static boolean RandomStringPasswordSpec_activated = false;
	private static boolean SSLContextSpec_activated = false;
	private static boolean SecretKeySpec_activated = false;
	private static boolean SecretKeySpecSpec_activated = false;
	private static boolean SecureRandomSpec_activated = false;
	private static boolean SignatureSpec_activated = false;
	private static boolean TrustManagerFactorySpec_activated = false;

	// Declarations for Indexing Trees
	private static final CipherInputStreamSpecMonitor CipherInputStreamSpec__Map = new CipherInputStreamSpecMonitor() ;

	private static final CipherOutputStreamSpecMonitor CipherOutputStreamSpec__Map = new CipherOutputStreamSpecMonitor() ;

	private static Object CipherSpec_c_Map_cachekey_c;
	private static CipherSpecMonitor CipherSpec_c_Map_cachevalue;
	private static final MapOfMonitor<CipherSpecMonitor> CipherSpec_c_Map = new MapOfMonitor<CipherSpecMonitor>(0) ;

	private static Object DHGenParameterSpecSpec_s_Map_cachekey_s;
	private static DHGenParameterSpecSpecMonitor DHGenParameterSpecSpec_s_Map_cachevalue;
	private static final MapOfMonitor<DHGenParameterSpecSpecMonitor> DHGenParameterSpecSpec_s_Map = new MapOfMonitor<DHGenParameterSpecSpecMonitor>(0) ;

	private static Object GCMParameterSpecSpec_s_Map_cachekey_s;
	private static GCMParameterSpecSpecMonitor GCMParameterSpecSpec_s_Map_cachevalue;
	private static final MapOfMonitor<GCMParameterSpecSpecMonitor> GCMParameterSpecSpec_s_Map = new MapOfMonitor<GCMParameterSpecSpecMonitor>(0) ;

	private static final Tuple2<HMACParameterSpecSpecMonitor_Set, HMACParameterSpecSpecMonitor> HMACParameterSpecSpec__Map = new Tuple2<HMACParameterSpecSpecMonitor_Set, HMACParameterSpecSpecMonitor>(new HMACParameterSpecSpecMonitor_Set() , null) ;

	private static Object IvParameterSpecSpec_s_Map_cachekey_s;
	private static IvParameterSpecSpecMonitor IvParameterSpecSpec_s_Map_cachevalue;
	private static final MapOfMonitor<IvParameterSpecSpecMonitor> IvParameterSpecSpec_s_Map = new MapOfMonitor<IvParameterSpecSpecMonitor>(0) ;

	private static Object KeyGeneratorSpec_k_Map_cachekey_k;
	private static KeyGeneratorSpecMonitor KeyGeneratorSpec_k_Map_cachevalue;
	private static final MapOfMonitor<KeyGeneratorSpecMonitor> KeyGeneratorSpec_k_Map = new MapOfMonitor<KeyGeneratorSpecMonitor>(0) ;

	private static Object KeyManagerFactorySpec_k_Map_cachekey_k;
	private static KeyManagerFactorySpecMonitor KeyManagerFactorySpec_k_Map_cachevalue;
	private static final MapOfMonitor<KeyManagerFactorySpecMonitor> KeyManagerFactorySpec_k_Map = new MapOfMonitor<KeyManagerFactorySpecMonitor>(0) ;

	private static Object KeyPairGeneratorSpec_k_Map_cachekey_k;
	private static KeyPairGeneratorSpecMonitor KeyPairGeneratorSpec_k_Map_cachevalue;
	private static final MapOfMonitor<KeyPairGeneratorSpecMonitor> KeyPairGeneratorSpec_k_Map = new MapOfMonitor<KeyPairGeneratorSpecMonitor>(0) ;

	private static Object KeyPairSpec_keyPair_Map_cachekey_keyPair;
	private static KeyPairSpecMonitor KeyPairSpec_keyPair_Map_cachevalue;
	private static final Tuple2<KeyPairSpecMonitor_Set, KeyPairSpecMonitor> KeyPairSpec__Map = new Tuple2<KeyPairSpecMonitor_Set, KeyPairSpecMonitor>(new KeyPairSpecMonitor_Set() , null) ;
	private static final MapOfMonitor<KeyPairSpecMonitor> KeyPairSpec_keyPair_Map = new MapOfMonitor<KeyPairSpecMonitor>(0) ;

	private static final Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> KeyStoreSpec__Map = new Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor>(new KeyStoreSpecMonitor_Set() , null) ;

	private static Object MacSpec_m_Map_cachekey_m;
	private static MacSpecMonitor MacSpec_m_Map_cachevalue;
	private static final MapOfMonitor<MacSpecMonitor> MacSpec_m_Map = new MapOfMonitor<MacSpecMonitor>(0) ;
	private static final Tuple2<MacSpecMonitor_Set, MacSpecMonitor> MacSpec__Map = new Tuple2<MacSpecMonitor_Set, MacSpecMonitor>(new MacSpecMonitor_Set() , null) ;

	private static Object MessageDigestSpec_digest_Map_cachekey_digest;
	private static MessageDigestSpecMonitor MessageDigestSpec_digest_Map_cachevalue;
	private static final MapOfMonitor<MessageDigestSpecMonitor> MessageDigestSpec_digest_Map = new MapOfMonitor<MessageDigestSpecMonitor>(0) ;

	private static Object PBEKeySpecSpec_s_Map_cachekey_s;
	private static PBEKeySpecSpecMonitor PBEKeySpecSpec_s_Map_cachevalue;
	private static final MapOfMonitor<PBEKeySpecSpecMonitor> PBEKeySpecSpec_s_Map = new MapOfMonitor<PBEKeySpecSpecMonitor>(0) ;
	private static final Tuple2<PBEKeySpecSpecMonitor_Set, PBEKeySpecSpecMonitor> PBEKeySpecSpec__Map = new Tuple2<PBEKeySpecSpecMonitor_Set, PBEKeySpecSpecMonitor>(new PBEKeySpecSpecMonitor_Set() , null) ;

	private static Object PBEParameterSpecSpec_s_Map_cachekey_s;
	private static PBEParameterSpecSpecMonitor PBEParameterSpecSpec_s_Map_cachevalue;
	private static final MapOfMonitor<PBEParameterSpecSpecMonitor> PBEParameterSpecSpec_s_Map = new MapOfMonitor<PBEParameterSpecSpecMonitor>(0) ;

	private static final Tuple2<RandomStringPasswordSpecMonitor_Set, RandomStringPasswordSpecMonitor> RandomStringPasswordSpec__Map = new Tuple2<RandomStringPasswordSpecMonitor_Set, RandomStringPasswordSpecMonitor>(new RandomStringPasswordSpecMonitor_Set() , null) ;

	private static Object SSLContextSpec_ctx_Map_cachekey_ctx;
	private static SSLContextSpecMonitor SSLContextSpec_ctx_Map_cachevalue;
	private static final MapOfMonitor<SSLContextSpecMonitor> SSLContextSpec_ctx_Map = new MapOfMonitor<SSLContextSpecMonitor>(0) ;
	private static final Tuple2<SSLContextSpecMonitor_Set, SSLContextSpecMonitor> SSLContextSpec__Map = new Tuple2<SSLContextSpecMonitor_Set, SSLContextSpecMonitor>(new SSLContextSpecMonitor_Set() , null) ;

	private static Object SecretKeySpec_secretKey_Map_cachekey_secretKey;
	private static SecretKeySpecMonitor SecretKeySpec_secretKey_Map_cachevalue;
	private static final MapOfMonitor<SecretKeySpecMonitor> SecretKeySpec_secretKey_Map = new MapOfMonitor<SecretKeySpecMonitor>(0) ;

	private static Object SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec;
	private static SecretKeySpecSpecMonitor SecretKeySpecSpec_secretKeySpec_Map_cachevalue;
	private static final MapOfMonitor<SecretKeySpecSpecMonitor> SecretKeySpecSpec_secretKeySpec_Map = new MapOfMonitor<SecretKeySpecSpecMonitor>(0) ;

	private static Object SecureRandomSpec_r_Map_cachekey_r;
	private static SecureRandomSpecMonitor SecureRandomSpec_r_Map_cachevalue;
	private static final MapOfMonitor<SecureRandomSpecMonitor> SecureRandomSpec_r_Map = new MapOfMonitor<SecureRandomSpecMonitor>(0) ;

	private static Object SignatureSpec_s_Map_cachekey_s;
	private static SignatureSpecMonitor SignatureSpec_s_Map_cachevalue;
	private static final MapOfMonitor<SignatureSpecMonitor> SignatureSpec_s_Map = new MapOfMonitor<SignatureSpecMonitor>(0) ;

	private static Object TrustManagerFactorySpec_mf_Map_cachekey_mf;
	private static TrustManagerFactorySpecMonitor TrustManagerFactorySpec_mf_Map_cachevalue;
	private static final MapOfMonitor<TrustManagerFactorySpecMonitor> TrustManagerFactorySpec_mf_Map = new MapOfMonitor<TrustManagerFactorySpecMonitor>(0) ;
	private static final Tuple2<TrustManagerFactorySpecMonitor_Set, TrustManagerFactorySpecMonitor> TrustManagerFactorySpec__Map = new Tuple2<TrustManagerFactorySpecMonitor_Set, TrustManagerFactorySpecMonitor>(new TrustManagerFactorySpecMonitor_Set() , null) ;

	public static int cleanUp() {
		int collected = 0;
		// indexing trees
		collected += CipherSpec_c_Map.cleanUpUnnecessaryMappings();
		collected += DHGenParameterSpecSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += GCMParameterSpecSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += IvParameterSpecSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += KeyGeneratorSpec_k_Map.cleanUpUnnecessaryMappings();
		collected += KeyManagerFactorySpec_k_Map.cleanUpUnnecessaryMappings();
		collected += KeyPairGeneratorSpec_k_Map.cleanUpUnnecessaryMappings();
		collected += KeyPairSpec_keyPair_Map.cleanUpUnnecessaryMappings();
		collected += MacSpec_m_Map.cleanUpUnnecessaryMappings();
		collected += MessageDigestSpec_digest_Map.cleanUpUnnecessaryMappings();
		collected += PBEKeySpecSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += PBEParameterSpecSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += SSLContextSpec_ctx_Map.cleanUpUnnecessaryMappings();
		collected += SecretKeySpec_secretKey_Map.cleanUpUnnecessaryMappings();
		collected += SecretKeySpecSpec_secretKeySpec_Map.cleanUpUnnecessaryMappings();
		collected += SecureRandomSpec_r_Map.cleanUpUnnecessaryMappings();
		collected += SignatureSpec_s_Map.cleanUpUnnecessaryMappings();
		collected += TrustManagerFactorySpec_mf_Map.cleanUpUnnecessaryMappings();
		return collected;
	}

	// Removing terminated monitors from partitioned sets
	static {
		TerminatedMonitorCleaner.start() ;
	}
	// Setting the behavior of the runtime library according to the compile-time option
	static {
		RuntimeOption.enableFineGrainedLock(false) ;
	}

	public static final void CipherInputStreamSpec_c1Event() {
		CipherInputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherInputStreamSpecMonitor.CipherInputStreamSpec_c1_num++;

		CipherInputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherInputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherInputStreamSpecMonitor created = new CipherInputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherInputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1();
		if(matchedEntryfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherInputStreamSpec_r1Event() {
		CipherInputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherInputStreamSpecMonitor.CipherInputStreamSpec_r1_num++;

		CipherInputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherInputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherInputStreamSpecMonitor created = new CipherInputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherInputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_r1();
		if(matchedEntryfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherInputStreamSpec_r2Event(byte[] arr, int offset, int len) {
		CipherInputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherInputStreamSpecMonitor.CipherInputStreamSpec_r2_num++;

		CipherInputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherInputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherInputStreamSpecMonitor created = new CipherInputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherInputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_r2(arr, offset, len);
		if(matchedEntryfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherInputStreamSpec_cl1Event() {
		CipherInputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherInputStreamSpecMonitor.CipherInputStreamSpec_cl1_num++;

		CipherInputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherInputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherInputStreamSpecMonitor created = new CipherInputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherInputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_cl1();
		if(matchedEntryfinalMonitor.CipherInputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherOutputStreamSpec_c1Event() {
		CipherOutputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherOutputStreamSpecMonitor.CipherOutputStreamSpec_c1_num++;

		CipherOutputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherOutputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherOutputStreamSpecMonitor created = new CipherOutputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherOutputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1();
		if(matchedEntryfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherOutputStreamSpec_w1Event() {
		CipherOutputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherOutputStreamSpecMonitor.CipherOutputStreamSpec_w1_num++;

		CipherOutputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherOutputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherOutputStreamSpecMonitor created = new CipherOutputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherOutputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_w1();
		if(matchedEntryfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherOutputStreamSpec_w2Event(byte[] b, int off, int len) {
		CipherOutputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherOutputStreamSpecMonitor.CipherOutputStreamSpec_w2_num++;

		CipherOutputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherOutputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherOutputStreamSpecMonitor created = new CipherOutputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherOutputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_w2(b, off, len);
		if(matchedEntryfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherOutputStreamSpec_flEvent() {
		CipherOutputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherOutputStreamSpecMonitor.CipherOutputStreamSpec_fl_num++;

		CipherOutputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherOutputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherOutputStreamSpecMonitor created = new CipherOutputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherOutputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_fl();
		if(matchedEntryfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherOutputStreamSpec_clEvent() {
		CipherOutputStreamSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherOutputStreamSpecMonitor.CipherOutputStreamSpec_cl_num++;

		CipherOutputStreamSpecMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CipherOutputStreamSpec__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CipherOutputStreamSpecMonitor created = new CipherOutputStreamSpecMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		final CipherOutputStreamSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_cl();
		if(matchedEntryfinalMonitor.CipherOutputStreamSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_g1Event(String transformation, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_g1_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(transformation, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_g2Event(String transformation, Object provider, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_g2_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(transformation, provider, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_g3Event(String transformation, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_g3_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(transformation, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_i1Event(int mode, Certificate cert, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_i1_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i1(mode, cert, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_i2Event(int mode, Key key, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_i2_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i2(mode, key, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_u1Event(byte[] plainText, Cipher c, byte[] cipherText) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_u1_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_u1(plainText, c, cipherText);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_u2Event(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, Cipher c, byte[] cipherText) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_u2_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_u2(plainText, prePlainTextOffset, prePlainTextLen, c, cipherText);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_u3Event(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_u3_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_u3(plainText, prePlainTextOffset, prePlainTextLen, cipherText, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_u4Event(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, int outputOffset, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_u4_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_u4(plainText, prePlainTextOffset, prePlainTextLen, cipherText, outputOffset, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_u5Event(ByteBuffer plainBuffer, ByteBuffer cipherBuffer, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_u5_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_u5(plainBuffer, cipherBuffer, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_wkb1Event(Cipher c, byte[] wrappedKeyBytes) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_wkb1_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_wkb1(c, wrappedKeyBytes);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f1Event(Cipher c, byte[] cipherText) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f1_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f1(c, cipherText);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f2Event(Cipher c, byte[] cipherText) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f2_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f2(c, cipherText);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f3Event(byte[] cipherText, int offset, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f3_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f3(cipherText, offset, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f5Event(byte[] plainText, int offset, int len, byte[] cipherText, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f5_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f5(plainText, offset, len, cipherText, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f6Event(byte[] plainText, int offset, int len, byte[] cipherText, int cipherOffset, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f6_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f6(plainText, offset, len, cipherText, cipherOffset, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CipherSpec_f7Event(ByteBuffer plainTextBuffer, ByteBuffer cipherTextBuffer, Cipher c) {
		CipherSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CipherSpecMonitor.CipherSpec_f7_num++;

		CachedWeakReference wr_c = null;
		MapOfMonitor<CipherSpecMonitor> matchedLastMap = null;
		CipherSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((c == CipherSpec_c_Map_cachekey_c) ) {
			matchedEntry = CipherSpec_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<CipherSpecMonitor> itmdMap = CipherSpec_c_Map;
				matchedLastMap = itmdMap;
				CipherSpecMonitor node_c = CipherSpec_c_Map.getNodeEquivalent(wr_c) ;
				matchedEntry = node_c;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			// D(X) main:4
			CipherSpecMonitor created = new CipherSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_c, created) ;
		}
		// D(X) main:8--9
		final CipherSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f7(plainTextBuffer, cipherTextBuffer, c);
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.CipherSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			CipherSpec_c_Map_cachekey_c = c;
			CipherSpec_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void DHGenParameterSpecSpec_c1Event(int primeSize, int exponentSize, DHGenParameterSpec s) {
		DHGenParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		DHGenParameterSpecSpecMonitor.DHGenParameterSpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<DHGenParameterSpecSpecMonitor> matchedLastMap = null;
		DHGenParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == DHGenParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = DHGenParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<DHGenParameterSpecSpecMonitor> itmdMap = DHGenParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				DHGenParameterSpecSpecMonitor node_s = DHGenParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			DHGenParameterSpecSpecMonitor created = new DHGenParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final DHGenParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(primeSize, exponentSize, s);
		if(matchedEntryfinalMonitor.DHGenParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.DHGenParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			DHGenParameterSpecSpec_s_Map_cachekey_s = s;
			DHGenParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void GCMParameterSpecSpec_c1Event(int tagLen, byte[] src, GCMParameterSpec s) {
		GCMParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		GCMParameterSpecSpecMonitor.GCMParameterSpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<GCMParameterSpecSpecMonitor> matchedLastMap = null;
		GCMParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == GCMParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = GCMParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<GCMParameterSpecSpecMonitor> itmdMap = GCMParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				GCMParameterSpecSpecMonitor node_s = GCMParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			GCMParameterSpecSpecMonitor created = new GCMParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final GCMParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(tagLen, src, s);
		if(matchedEntryfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			GCMParameterSpecSpec_s_Map_cachekey_s = s;
			GCMParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void GCMParameterSpecSpec_c1Event(int tagLen, byte[] src, int offset, int len, GCMParameterSpec s) {
		GCMParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		GCMParameterSpecSpecMonitor.GCMParameterSpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<GCMParameterSpecSpecMonitor> matchedLastMap = null;
		GCMParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == GCMParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = GCMParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<GCMParameterSpecSpecMonitor> itmdMap = GCMParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				GCMParameterSpecSpecMonitor node_s = GCMParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			GCMParameterSpecSpecMonitor created = new GCMParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final GCMParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(tagLen, src, offset, len, s);
		if(matchedEntryfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.GCMParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			GCMParameterSpecSpec_s_Map_cachekey_s = s;
			GCMParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void HMACParameterSpecSpec_cEvent(HMACParameterSpec s) {
		HMACParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		HMACParameterSpecSpecMonitor.HMACParameterSpecSpec_c_num++;

		Tuple2<HMACParameterSpecSpecMonitor_Set, HMACParameterSpecSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = HMACParameterSpecSpec__Map;
		}
		// D(X) main:1
		HMACParameterSpecSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				HMACParameterSpecSpecMonitor created = new HMACParameterSpecSpecMonitor(HMACParameterSpecSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				HMACParameterSpecSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			HMACParameterSpecSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(HMACParameterSpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		HMACParameterSpecSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_c(s);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void IvParameterSpecSpec_c1Event(byte[] iv, IvParameterSpec s) {
		IvParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		IvParameterSpecSpecMonitor.IvParameterSpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<IvParameterSpecSpecMonitor> matchedLastMap = null;
		IvParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == IvParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = IvParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<IvParameterSpecSpecMonitor> itmdMap = IvParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				IvParameterSpecSpecMonitor node_s = IvParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			IvParameterSpecSpecMonitor created = new IvParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final IvParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(iv, s);
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			IvParameterSpecSpec_s_Map_cachekey_s = s;
			IvParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void IvParameterSpecSpec_c2Event(byte[] iv, int offset, int len, IvParameterSpec s) {
		IvParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		IvParameterSpecSpecMonitor.IvParameterSpecSpec_c2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<IvParameterSpecSpecMonitor> matchedLastMap = null;
		IvParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == IvParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = IvParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<IvParameterSpecSpecMonitor> itmdMap = IvParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				IvParameterSpecSpecMonitor node_s = IvParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			IvParameterSpecSpecMonitor created = new IvParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final IvParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c2(iv, offset, len, s);
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			IvParameterSpecSpec_s_Map_cachekey_s = s;
			IvParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void IvParameterSpecSpec_c3Event(byte[] iv, IvParameterSpec s) {
		IvParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		IvParameterSpecSpecMonitor.IvParameterSpecSpec_c3_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<IvParameterSpecSpecMonitor> matchedLastMap = null;
		IvParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == IvParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = IvParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<IvParameterSpecSpecMonitor> itmdMap = IvParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				IvParameterSpecSpecMonitor node_s = IvParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			IvParameterSpecSpecMonitor created = new IvParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final IvParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c3(iv, s);
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			IvParameterSpecSpec_s_Map_cachekey_s = s;
			IvParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void IvParameterSpecSpec_c4Event(byte[] iv, int offset, int len, IvParameterSpec s) {
		IvParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		IvParameterSpecSpecMonitor.IvParameterSpecSpec_c4_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<IvParameterSpecSpecMonitor> matchedLastMap = null;
		IvParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == IvParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = IvParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<IvParameterSpecSpecMonitor> itmdMap = IvParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				IvParameterSpecSpecMonitor node_s = IvParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			IvParameterSpecSpecMonitor created = new IvParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final IvParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c4(iv, offset, len, s);
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.IvParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			IvParameterSpecSpec_s_Map_cachekey_s = s;
			IvParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyGeneratorSpec_g1Event(String alg, KeyGenerator k) {
		KeyGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyGeneratorSpecMonitor.KeyGeneratorSpec_g1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyGeneratorSpecMonitor> matchedLastMap = null;
		KeyGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyGeneratorSpecMonitor> itmdMap = KeyGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyGeneratorSpecMonitor node_k = KeyGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyGeneratorSpecMonitor created = new KeyGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, k);
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyGeneratorSpec_k_Map_cachekey_k = k;
			KeyGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyGeneratorSpec_g2Event(String alg, Object provider, KeyGenerator k) {
		KeyGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyGeneratorSpecMonitor.KeyGeneratorSpec_g2_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyGeneratorSpecMonitor> matchedLastMap = null;
		KeyGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyGeneratorSpecMonitor> itmdMap = KeyGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyGeneratorSpecMonitor node_k = KeyGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyGeneratorSpecMonitor created = new KeyGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, k);
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyGeneratorSpec_k_Map_cachekey_k = k;
			KeyGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyGeneratorSpec_g3Event(String alg, KeyGenerator k) {
		KeyGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyGeneratorSpecMonitor.KeyGeneratorSpec_g3_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyGeneratorSpecMonitor> matchedLastMap = null;
		KeyGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyGeneratorSpecMonitor> itmdMap = KeyGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyGeneratorSpecMonitor node_k = KeyGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyGeneratorSpecMonitor created = new KeyGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, k);
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyGeneratorSpec_k_Map_cachekey_k = k;
			KeyGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyGeneratorSpec_initEvent(KeyGenerator k) {
		KeyGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyGeneratorSpecMonitor.KeyGeneratorSpec_init_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyGeneratorSpecMonitor> matchedLastMap = null;
		KeyGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyGeneratorSpecMonitor> itmdMap = KeyGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyGeneratorSpecMonitor node_k = KeyGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyGeneratorSpecMonitor created = new KeyGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init(k);
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyGeneratorSpec_k_Map_cachekey_k = k;
			KeyGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyGeneratorSpec_gk1Event(KeyGenerator k, SecretKey key) {
		KeyGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyGeneratorSpecMonitor.KeyGeneratorSpec_gk1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyGeneratorSpecMonitor> matchedLastMap = null;
		KeyGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyGeneratorSpecMonitor> itmdMap = KeyGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyGeneratorSpecMonitor node_k = KeyGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyGeneratorSpecMonitor created = new KeyGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gk1(k, key);
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyGeneratorSpec_k_Map_cachekey_k = k;
			KeyGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyManagerFactorySpec_g1Event(String alg, KeyManagerFactory k) {
		KeyManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyManagerFactorySpecMonitor.KeyManagerFactorySpec_g1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyManagerFactorySpecMonitor> matchedLastMap = null;
		KeyManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyManagerFactorySpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyManagerFactorySpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyManagerFactorySpecMonitor> itmdMap = KeyManagerFactorySpec_k_Map;
				matchedLastMap = itmdMap;
				KeyManagerFactorySpecMonitor node_k = KeyManagerFactorySpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyManagerFactorySpecMonitor created = new KeyManagerFactorySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, k);
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			KeyManagerFactorySpec_k_Map_cachekey_k = k;
			KeyManagerFactorySpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyManagerFactorySpec_g2Event(String alg, KeyManagerFactory k) {
		KeyManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyManagerFactorySpecMonitor.KeyManagerFactorySpec_g2_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyManagerFactorySpecMonitor> matchedLastMap = null;
		KeyManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyManagerFactorySpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyManagerFactorySpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyManagerFactorySpecMonitor> itmdMap = KeyManagerFactorySpec_k_Map;
				matchedLastMap = itmdMap;
				KeyManagerFactorySpecMonitor node_k = KeyManagerFactorySpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyManagerFactorySpecMonitor created = new KeyManagerFactorySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, k);
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			KeyManagerFactorySpec_k_Map_cachekey_k = k;
			KeyManagerFactorySpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyManagerFactorySpec_g3Event(String alg, KeyManagerFactory k) {
		KeyManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyManagerFactorySpecMonitor.KeyManagerFactorySpec_g3_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyManagerFactorySpecMonitor> matchedLastMap = null;
		KeyManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyManagerFactorySpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyManagerFactorySpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyManagerFactorySpecMonitor> itmdMap = KeyManagerFactorySpec_k_Map;
				matchedLastMap = itmdMap;
				KeyManagerFactorySpecMonitor node_k = KeyManagerFactorySpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyManagerFactorySpecMonitor created = new KeyManagerFactorySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, k);
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			KeyManagerFactorySpec_k_Map_cachekey_k = k;
			KeyManagerFactorySpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyManagerFactorySpec_initEvent(KeyManagerFactory k) {
		KeyManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyManagerFactorySpecMonitor.KeyManagerFactorySpec_init_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyManagerFactorySpecMonitor> matchedLastMap = null;
		KeyManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyManagerFactorySpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyManagerFactorySpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyManagerFactorySpecMonitor> itmdMap = KeyManagerFactorySpec_k_Map;
				matchedLastMap = itmdMap;
				KeyManagerFactorySpecMonitor node_k = KeyManagerFactorySpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyManagerFactorySpecMonitor created = new KeyManagerFactorySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init(k);
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			KeyManagerFactorySpec_k_Map_cachekey_k = k;
			KeyManagerFactorySpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyManagerFactorySpec_gkm1Event(KeyManagerFactory k, KeyManager[] keyManager) {
		KeyManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyManagerFactorySpecMonitor.KeyManagerFactorySpec_gkm1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyManagerFactorySpecMonitor> matchedLastMap = null;
		KeyManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyManagerFactorySpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyManagerFactorySpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyManagerFactorySpecMonitor> itmdMap = KeyManagerFactorySpec_k_Map;
				matchedLastMap = itmdMap;
				KeyManagerFactorySpecMonitor node_k = KeyManagerFactorySpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyManagerFactorySpecMonitor created = new KeyManagerFactorySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gkm1(k, keyManager);
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			KeyManagerFactorySpec_k_Map_cachekey_k = k;
			KeyManagerFactorySpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_g1Event(String alg, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_g1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_g2Event(String alg, String provider, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_g2_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_g3Event(String alg, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_g3_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init1Event(int keySize, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_init1_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init1(keySize, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init2Event(int keySize, SecureRandom random, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_init2_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init2(keySize, random, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init3Event(AlgorithmParameterSpec params, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_init3_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init3(params, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init4Event(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_init4_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init4(params, random, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_initErrorEvent(int keySize, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_initError_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_initError(keySize, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_genEvent(KeyPairGenerator k, KeyPair keyPair) {
		KeyPairGeneratorSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairGeneratorSpecMonitor.KeyPairGeneratorSpec_gen_num++;

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gen(k, keyPair);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairSpec_c1Event(PublicKey publicKey, PrivateKey privateKey, KeyPair kp) {
		KeyPairSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairSpecMonitor.KeyPairSpec_c1_num++;

		Tuple2<KeyPairSpecMonitor_Set, KeyPairSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyPairSpec__Map;
		}
		// D(X) main:1
		KeyPairSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyPairSpecMonitor created = new KeyPairSpecMonitor(KeyPairSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyPairSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyPairSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyPairSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyPairSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_c1(publicKey, privateKey, kp);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairSpec_gpuEvent(KeyPair keyPair, PublicKey publicKey) {
		KeyPairSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairSpecMonitor.KeyPairSpec_gpu_num++;

		CachedWeakReference wr_keyPair = null;
		MapOfMonitor<KeyPairSpecMonitor> matchedLastMap = null;
		KeyPairSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((keyPair == KeyPairSpec_keyPair_Map_cachekey_keyPair) ) {
			matchedEntry = KeyPairSpec_keyPair_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_keyPair = new CachedWeakReference(keyPair) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairSpecMonitor> itmdMap = KeyPairSpec_keyPair_Map;
				matchedLastMap = itmdMap;
				KeyPairSpecMonitor node_keyPair = KeyPairSpec_keyPair_Map.getNodeEquivalent(wr_keyPair) ;
				matchedEntry = node_keyPair;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_keyPair == null) ) {
				wr_keyPair = new CachedWeakReference(keyPair) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				KeyPairSpecMonitor sourceLeaf = null;
				{
					// FindCode
					KeyPairSpecMonitor itmdLeaf = KeyPairSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <keyPair>
					if (definable) {
						// FindCode
						KeyPairSpecMonitor node_keyPair = KeyPairSpec_keyPair_Map.getNodeEquivalent(wr_keyPair) ;
						if ((node_keyPair != null) ) {
							if (((node_keyPair.getDisable() > sourceLeaf.getTau() ) || ((node_keyPair.getTau() > 0) && (node_keyPair.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						KeyPairSpecMonitor created = (KeyPairSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_keyPair, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							KeyPairSpecMonitor_Set targetSet = KeyPairSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				KeyPairSpecMonitor created = new KeyPairSpecMonitor(KeyPairSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_keyPair, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					KeyPairSpecMonitor_Set targetSet = KeyPairSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(KeyPairSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final KeyPairSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gpu(keyPair, publicKey);
		if(matchedEntryfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairSpec_keyPair_Map_cachekey_keyPair = keyPair;
			KeyPairSpec_keyPair_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyPairSpec_gprEvent(KeyPair keyPair, PrivateKey privateKey) {
		KeyPairSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyPairSpecMonitor.KeyPairSpec_gpr_num++;

		CachedWeakReference wr_keyPair = null;
		MapOfMonitor<KeyPairSpecMonitor> matchedLastMap = null;
		KeyPairSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((keyPair == KeyPairSpec_keyPair_Map_cachekey_keyPair) ) {
			matchedEntry = KeyPairSpec_keyPair_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_keyPair = new CachedWeakReference(keyPair) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairSpecMonitor> itmdMap = KeyPairSpec_keyPair_Map;
				matchedLastMap = itmdMap;
				KeyPairSpecMonitor node_keyPair = KeyPairSpec_keyPair_Map.getNodeEquivalent(wr_keyPair) ;
				matchedEntry = node_keyPair;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_keyPair == null) ) {
				wr_keyPair = new CachedWeakReference(keyPair) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				KeyPairSpecMonitor sourceLeaf = null;
				{
					// FindCode
					KeyPairSpecMonitor itmdLeaf = KeyPairSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <keyPair>
					if (definable) {
						// FindCode
						KeyPairSpecMonitor node_keyPair = KeyPairSpec_keyPair_Map.getNodeEquivalent(wr_keyPair) ;
						if ((node_keyPair != null) ) {
							if (((node_keyPair.getDisable() > sourceLeaf.getTau() ) || ((node_keyPair.getTau() > 0) && (node_keyPair.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						KeyPairSpecMonitor created = (KeyPairSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_keyPair, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							KeyPairSpecMonitor_Set targetSet = KeyPairSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				KeyPairSpecMonitor created = new KeyPairSpecMonitor(KeyPairSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_keyPair, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					KeyPairSpecMonitor_Set targetSet = KeyPairSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(KeyPairSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final KeyPairSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gpr(keyPair, privateKey);
		if(matchedEntryfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairSpec_keyPair_Map_cachekey_keyPair = keyPair;
			KeyPairSpec_keyPair_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_g1Event(String ksType, KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_g1_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_g1(ksType, k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_g2Event(String ksType, KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_g2_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_g2(ksType, k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_loadEvent(KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_load_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_load(k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_storeEvent(KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_store_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_store(k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_ge1Event(KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_ge1_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_ge1(k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_se1Event(KeyStore k) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_se1_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_se1(k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void KeyStoreSpec_gk1Event(KeyStore k, Key key) {
		KeyStoreSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		KeyStoreSpecMonitor.KeyStoreSpec_gk1_num++;

		Tuple2<KeyStoreSpecMonitor_Set, KeyStoreSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = KeyStoreSpec__Map;
		}
		// D(X) main:1
		KeyStoreSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				KeyStoreSpecMonitor created = new KeyStoreSpecMonitor(KeyStoreSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				KeyStoreSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			KeyStoreSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(KeyStoreSpec_timestamp++) ;
		}
		// D(X) main:8--9
		KeyStoreSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_gk1(k, key);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_g1Event(String alg, Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_g1_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_g2Event(String alg, String provider, Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_g2_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_g3Event(String alg, Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_g3_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_i1Event(java.security.Key key, Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_i1_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i1(key, m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_i2Event(java.security.Key key, java.security.spec.AlgorithmParameterSpec params, Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_i2_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i2(key, params, m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_updateEvent(Mac m) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_update_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_update(m);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_f1Event(Mac m, byte[] output) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_f1_num++;

		CachedWeakReference wr_m = null;
		MapOfMonitor<MacSpecMonitor> matchedLastMap = null;
		MacSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((m == MacSpec_m_Map_cachekey_m) ) {
			matchedEntry = MacSpec_m_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MacSpecMonitor> itmdMap = MacSpec_m_Map;
				matchedLastMap = itmdMap;
				MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
				matchedEntry = node_m;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				MacSpecMonitor sourceLeaf = null;
				{
					// FindCode
					MacSpecMonitor itmdLeaf = MacSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <m>
					if (definable) {
						// FindCode
						MacSpecMonitor node_m = MacSpec_m_Map.getNodeEquivalent(wr_m) ;
						if ((node_m != null) ) {
							if (((node_m.getDisable() > sourceLeaf.getTau() ) || ((node_m.getTau() > 0) && (node_m.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						MacSpecMonitor created = (MacSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_m, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_m, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					MacSpecMonitor_Set targetSet = MacSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final MacSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_f1(m, output);
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MacSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MacSpec_m_Map_cachekey_m = m;
			MacSpec_m_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MacSpec_f2Event(byte[] output, int outOffset) {
		MacSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MacSpecMonitor.MacSpec_f2_num++;

		Tuple2<MacSpecMonitor_Set, MacSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = MacSpec__Map;
		}
		// D(X) main:1
		MacSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				MacSpecMonitor created = new MacSpecMonitor(MacSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				MacSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			MacSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(MacSpec_timestamp++) ;
		}
		// D(X) main:8--9
		MacSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_f2(output, outOffset);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g1Event(String alg, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g1_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g2Event(String alg, String provider, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g2_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g3Event(String alg, Provider provider, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g3_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, provider, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g4Event(String alg, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g4_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g4(alg, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_updateEvent(MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_update_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_update(digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_resetEvent(MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_reset_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_reset(digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d1Event(MessageDigest digest, byte[] out) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d1_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d1(digest, out);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d2Event(MessageDigest digest, byte[] out) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d2_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d2(digest, out);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d3Event(byte[] out, int offset, int len, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d3_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d3(out, offset, len, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_f1Event(char[] password) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_f1_num++;

		Tuple2<PBEKeySpecSpecMonitor_Set, PBEKeySpecSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = PBEKeySpecSpec__Map;
		}
		// D(X) main:1
		PBEKeySpecSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				PBEKeySpecSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			PBEKeySpecSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		PBEKeySpecSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_f1(password);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_f2Event(char[] password, byte[] salt, int keyLength) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_f2_num++;

		Tuple2<PBEKeySpecSpecMonitor_Set, PBEKeySpecSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = PBEKeySpecSpec__Map;
		}
		// D(X) main:1
		PBEKeySpecSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				PBEKeySpecSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			PBEKeySpecSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		PBEKeySpecSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_f2(password, salt, keyLength);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_c1Event(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEKeySpecSpecMonitor> matchedLastMap = null;
		PBEKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEKeySpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEKeySpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEKeySpecSpecMonitor> itmdMap = PBEKeySpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				PBEKeySpecSpecMonitor sourceLeaf = null;
				{
					// FindCode
					PBEKeySpecSpecMonitor itmdLeaf = PBEKeySpecSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <s>
					if (definable) {
						// FindCode
						PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
						if ((node_s != null) ) {
							if (((node_s.getDisable() > sourceLeaf.getTau() ) || ((node_s.getTau() > 0) && (node_s.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						PBEKeySpecSpecMonitor created = (PBEKeySpecSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_s, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_s, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final PBEKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(password, salt, iterationCount, keyLength, s);
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEKeySpecSpec_s_Map_cachekey_s = s;
			PBEKeySpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_err1Event(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_err1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEKeySpecSpecMonitor> matchedLastMap = null;
		PBEKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEKeySpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEKeySpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEKeySpecSpecMonitor> itmdMap = PBEKeySpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				PBEKeySpecSpecMonitor sourceLeaf = null;
				{
					// FindCode
					PBEKeySpecSpecMonitor itmdLeaf = PBEKeySpecSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <s>
					if (definable) {
						// FindCode
						PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
						if ((node_s != null) ) {
							if (((node_s.getDisable() > sourceLeaf.getTau() ) || ((node_s.getTau() > 0) && (node_s.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						PBEKeySpecSpecMonitor created = (PBEKeySpecSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_s, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_s, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final PBEKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_err1(password, salt, iterationCount, keyLength, s);
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEKeySpecSpec_s_Map_cachekey_s = s;
			PBEKeySpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_err2Event(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_err2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEKeySpecSpecMonitor> matchedLastMap = null;
		PBEKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEKeySpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEKeySpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEKeySpecSpecMonitor> itmdMap = PBEKeySpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				PBEKeySpecSpecMonitor sourceLeaf = null;
				{
					// FindCode
					PBEKeySpecSpecMonitor itmdLeaf = PBEKeySpecSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <s>
					if (definable) {
						// FindCode
						PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
						if ((node_s != null) ) {
							if (((node_s.getDisable() > sourceLeaf.getTau() ) || ((node_s.getTau() > 0) && (node_s.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						PBEKeySpecSpecMonitor created = (PBEKeySpecSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_s, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_s, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final PBEKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_err2(password, salt, iterationCount, keyLength, s);
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEKeySpecSpec_s_Map_cachekey_s = s;
			PBEKeySpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_err3Event(char[] password, byte[] salt, int iterationCount, int keyLength, PBEKeySpec s) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_err3_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEKeySpecSpecMonitor> matchedLastMap = null;
		PBEKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEKeySpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEKeySpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEKeySpecSpecMonitor> itmdMap = PBEKeySpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				PBEKeySpecSpecMonitor sourceLeaf = null;
				{
					// FindCode
					PBEKeySpecSpecMonitor itmdLeaf = PBEKeySpecSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <s>
					if (definable) {
						// FindCode
						PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
						if ((node_s != null) ) {
							if (((node_s.getDisable() > sourceLeaf.getTau() ) || ((node_s.getTau() > 0) && (node_s.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						PBEKeySpecSpecMonitor created = (PBEKeySpecSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_s, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_s, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final PBEKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_err3(password, salt, iterationCount, keyLength, s);
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEKeySpecSpec_s_Map_cachekey_s = s;
			PBEKeySpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEKeySpecSpec_c2Event(PBEKeySpec s) {
		PBEKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEKeySpecSpecMonitor.PBEKeySpecSpec_c2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEKeySpecSpecMonitor> matchedLastMap = null;
		PBEKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEKeySpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEKeySpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEKeySpecSpecMonitor> itmdMap = PBEKeySpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				PBEKeySpecSpecMonitor sourceLeaf = null;
				{
					// FindCode
					PBEKeySpecSpecMonitor itmdLeaf = PBEKeySpecSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <s>
					if (definable) {
						// FindCode
						PBEKeySpecSpecMonitor node_s = PBEKeySpecSpec_s_Map.getNodeEquivalent(wr_s) ;
						if ((node_s != null) ) {
							if (((node_s.getDisable() > sourceLeaf.getTau() ) || ((node_s.getTau() > 0) && (node_s.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						PBEKeySpecSpecMonitor created = (PBEKeySpecSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_s, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				PBEKeySpecSpecMonitor created = new PBEKeySpecSpecMonitor(PBEKeySpecSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_s, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					PBEKeySpecSpecMonitor_Set targetSet = PBEKeySpecSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(PBEKeySpecSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final PBEKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c2(s);
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEKeySpecSpec_s_Map_cachekey_s = s;
			PBEKeySpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEParameterSpecSpec_c1Event(byte[] salt, int iterationCount, PBEParameterSpec s) {
		PBEParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEParameterSpecSpecMonitor.PBEParameterSpecSpec_c1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEParameterSpecSpecMonitor> matchedLastMap = null;
		PBEParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEParameterSpecSpecMonitor> itmdMap = PBEParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEParameterSpecSpecMonitor node_s = PBEParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			PBEParameterSpecSpecMonitor created = new PBEParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final PBEParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(salt, iterationCount, s);
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEParameterSpecSpec_s_Map_cachekey_s = s;
			PBEParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEParameterSpecSpec_c2Event(byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec, PBEParameterSpec s) {
		PBEParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEParameterSpecSpecMonitor.PBEParameterSpecSpec_c2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEParameterSpecSpecMonitor> matchedLastMap = null;
		PBEParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEParameterSpecSpecMonitor> itmdMap = PBEParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEParameterSpecSpecMonitor node_s = PBEParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			PBEParameterSpecSpecMonitor created = new PBEParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final PBEParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c2(salt, iterationCount, paramSpec, s);
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEParameterSpecSpec_s_Map_cachekey_s = s;
			PBEParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void PBEParameterSpecSpec_c3Event(byte[] salt, int iterationCount, PBEParameterSpec s) {
		PBEParameterSpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		PBEParameterSpecSpecMonitor.PBEParameterSpecSpec_c3_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<PBEParameterSpecSpecMonitor> matchedLastMap = null;
		PBEParameterSpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == PBEParameterSpecSpec_s_Map_cachekey_s) ) {
			matchedEntry = PBEParameterSpecSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<PBEParameterSpecSpecMonitor> itmdMap = PBEParameterSpecSpec_s_Map;
				matchedLastMap = itmdMap;
				PBEParameterSpecSpecMonitor node_s = PBEParameterSpecSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			PBEParameterSpecSpecMonitor created = new PBEParameterSpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final PBEParameterSpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c3(salt, iterationCount, s);
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.PBEParameterSpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			PBEParameterSpecSpec_s_Map_cachekey_s = s;
			PBEParameterSpecSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void RandomStringPasswordSpec_voEvent(Object obj, String s) {
		RandomStringPasswordSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		RandomStringPasswordSpecMonitor.RandomStringPasswordSpec_vo_num++;

		Tuple2<RandomStringPasswordSpecMonitor_Set, RandomStringPasswordSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = RandomStringPasswordSpec__Map;
		}
		// D(X) main:1
		RandomStringPasswordSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				RandomStringPasswordSpecMonitor created = new RandomStringPasswordSpecMonitor(RandomStringPasswordSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				RandomStringPasswordSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			RandomStringPasswordSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(RandomStringPasswordSpec_timestamp++) ;
		}
		// D(X) main:8--9
		RandomStringPasswordSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_vo(obj, s);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void RandomStringPasswordSpec_gbEvent(String s, char[] chars) {
		RandomStringPasswordSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		RandomStringPasswordSpecMonitor.RandomStringPasswordSpec_gb_num++;

		Tuple2<RandomStringPasswordSpecMonitor_Set, RandomStringPasswordSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = RandomStringPasswordSpec__Map;
		}
		// D(X) main:1
		RandomStringPasswordSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				RandomStringPasswordSpecMonitor created = new RandomStringPasswordSpecMonitor(RandomStringPasswordSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				RandomStringPasswordSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			RandomStringPasswordSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(RandomStringPasswordSpec_timestamp++) ;
		}
		// D(X) main:8--9
		RandomStringPasswordSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_gb(s, chars);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecretKeySpec_e1Event(SecretKey secretKey, byte[] key) {
		SecretKeySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecretKeySpecMonitor.SecretKeySpec_e1_num++;

		CachedWeakReference wr_secretKey = null;
		MapOfMonitor<SecretKeySpecMonitor> matchedLastMap = null;
		SecretKeySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((secretKey == SecretKeySpec_secretKey_Map_cachekey_secretKey) ) {
			matchedEntry = SecretKeySpec_secretKey_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_secretKey = new CachedWeakReference(secretKey) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecretKeySpecMonitor> itmdMap = SecretKeySpec_secretKey_Map;
				matchedLastMap = itmdMap;
				SecretKeySpecMonitor node_secretKey = SecretKeySpec_secretKey_Map.getNodeEquivalent(wr_secretKey) ;
				matchedEntry = node_secretKey;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_secretKey == null) ) {
				wr_secretKey = new CachedWeakReference(secretKey) ;
			}
			// D(X) main:4
			SecretKeySpecMonitor created = new SecretKeySpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_secretKey, created) ;
		}
		// D(X) main:8--9
		final SecretKeySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_e1(secretKey, key);
		if(matchedEntryfinalMonitor.SecretKeySpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SecretKeySpec_secretKey_Map_cachekey_secretKey = secretKey;
			SecretKeySpec_secretKey_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecretKeySpecSpec_c1Event(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		SecretKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecretKeySpecSpecMonitor.SecretKeySpecSpec_c1_num++;

		CachedWeakReference wr_secretKeySpec = null;
		MapOfMonitor<SecretKeySpecSpecMonitor> matchedLastMap = null;
		SecretKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((secretKeySpec == SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec) ) {
			matchedEntry = SecretKeySpecSpec_secretKeySpec_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecretKeySpecSpecMonitor> itmdMap = SecretKeySpecSpec_secretKeySpec_Map;
				matchedLastMap = itmdMap;
				SecretKeySpecSpecMonitor node_secretKeySpec = SecretKeySpecSpec_secretKeySpec_Map.getNodeEquivalent(wr_secretKeySpec) ;
				matchedEntry = node_secretKeySpec;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_secretKeySpec == null) ) {
				wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			}
			// D(X) main:4
			SecretKeySpecSpecMonitor created = new SecretKeySpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_secretKeySpec, created) ;
		}
		// D(X) main:8--9
		final SecretKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(keyMaterial, keyAlgorithm, secretKeySpec);
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec = secretKeySpec;
			SecretKeySpecSpec_secretKeySpec_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecretKeySpecSpec_c2Event(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		SecretKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecretKeySpecSpecMonitor.SecretKeySpecSpec_c2_num++;

		CachedWeakReference wr_secretKeySpec = null;
		MapOfMonitor<SecretKeySpecSpecMonitor> matchedLastMap = null;
		SecretKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((secretKeySpec == SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec) ) {
			matchedEntry = SecretKeySpecSpec_secretKeySpec_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecretKeySpecSpecMonitor> itmdMap = SecretKeySpecSpec_secretKeySpec_Map;
				matchedLastMap = itmdMap;
				SecretKeySpecSpecMonitor node_secretKeySpec = SecretKeySpecSpec_secretKeySpec_Map.getNodeEquivalent(wr_secretKeySpec) ;
				matchedEntry = node_secretKeySpec;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_secretKeySpec == null) ) {
				wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			}
			// D(X) main:4
			SecretKeySpecSpecMonitor created = new SecretKeySpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_secretKeySpec, created) ;
		}
		// D(X) main:8--9
		final SecretKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c2(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec = secretKeySpec;
			SecretKeySpecSpec_secretKeySpec_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecretKeySpecSpec_c3Event(byte[] keyMaterial, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		SecretKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecretKeySpecSpecMonitor.SecretKeySpecSpec_c3_num++;

		CachedWeakReference wr_secretKeySpec = null;
		MapOfMonitor<SecretKeySpecSpecMonitor> matchedLastMap = null;
		SecretKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((secretKeySpec == SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec) ) {
			matchedEntry = SecretKeySpecSpec_secretKeySpec_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecretKeySpecSpecMonitor> itmdMap = SecretKeySpecSpec_secretKeySpec_Map;
				matchedLastMap = itmdMap;
				SecretKeySpecSpecMonitor node_secretKeySpec = SecretKeySpecSpec_secretKeySpec_Map.getNodeEquivalent(wr_secretKeySpec) ;
				matchedEntry = node_secretKeySpec;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_secretKeySpec == null) ) {
				wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			}
			// D(X) main:4
			SecretKeySpecSpecMonitor created = new SecretKeySpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_secretKeySpec, created) ;
		}
		// D(X) main:8--9
		final SecretKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c3(keyMaterial, keyAlgorithm, secretKeySpec);
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec = secretKeySpec;
			SecretKeySpecSpec_secretKeySpec_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecretKeySpecSpec_c4Event(byte[] keyMaterial, int offset, int len, String keyAlgorithm, SecretKeySpec secretKeySpec) {
		SecretKeySpecSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecretKeySpecSpecMonitor.SecretKeySpecSpec_c4_num++;

		CachedWeakReference wr_secretKeySpec = null;
		MapOfMonitor<SecretKeySpecSpecMonitor> matchedLastMap = null;
		SecretKeySpecSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((secretKeySpec == SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec) ) {
			matchedEntry = SecretKeySpecSpec_secretKeySpec_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecretKeySpecSpecMonitor> itmdMap = SecretKeySpecSpec_secretKeySpec_Map;
				matchedLastMap = itmdMap;
				SecretKeySpecSpecMonitor node_secretKeySpec = SecretKeySpecSpec_secretKeySpec_Map.getNodeEquivalent(wr_secretKeySpec) ;
				matchedEntry = node_secretKeySpec;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_secretKeySpec == null) ) {
				wr_secretKeySpec = new CachedWeakReference(secretKeySpec) ;
			}
			// D(X) main:4
			SecretKeySpecSpecMonitor created = new SecretKeySpecSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_secretKeySpec, created) ;
		}
		// D(X) main:8--9
		final SecretKeySpecSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c4(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecretKeySpecSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SecretKeySpecSpec_secretKeySpec_Map_cachekey_secretKeySpec = secretKeySpec;
			SecretKeySpecSpec_secretKeySpec_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_c1Event(SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_c1_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c1(r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_c2Event(byte[] seed, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_c2_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c2(seed, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_c3Event(byte[] seed, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_c3_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_c3(seed, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_g1Event(String alg, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_g1_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_g2Event(String alg, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_g2_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_g3Event(SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_g3_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_g4Event(String alg, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_g4_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g4(alg, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_setSeed1Event(SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_setSeed1_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_setSeed1(r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_setSeed2Event(byte[] seed, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_setSeed2_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_setSeed2(seed, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_setSeed3Event(byte[] seed, SecureRandom r) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_setSeed3_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_setSeed3(seed, r);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_genSeedEvent(SecureRandom r, byte[] seed) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_genSeed_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_genSeed(r, seed);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_next1Event(SecureRandom r, int randIntInRange) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_next1_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_next1(r, randIntInRange);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_next2Event(SecureRandom r, byte[] bytes) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_next2_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_next2(r, bytes);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_next3Event(SecureRandom r, int randInt) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_next3_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_next3(r, randInt);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SecureRandomSpec_intsEvent(SecureRandom r, IntStream stream) {
		SecureRandomSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SecureRandomSpecMonitor.SecureRandomSpec_ints_num++;

		CachedWeakReference wr_r = null;
		MapOfMonitor<SecureRandomSpecMonitor> matchedLastMap = null;
		SecureRandomSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == SecureRandomSpec_r_Map_cachekey_r) ) {
			matchedEntry = SecureRandomSpec_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SecureRandomSpecMonitor> itmdMap = SecureRandomSpec_r_Map;
				matchedLastMap = itmdMap;
				SecureRandomSpecMonitor node_r = SecureRandomSpec_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			SecureRandomSpecMonitor created = new SecureRandomSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final SecureRandomSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_ints(r, stream);
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SecureRandomSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SecureRandomSpec_r_Map_cachekey_r = r;
			SecureRandomSpec_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_g1Event(String alg, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_g1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_g2Event(String alg, String provider, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_g2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_g3Event(String alg, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_g3_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_i1Event(PrivateKey privateKey, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_i1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i1(privateKey, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_i2Event(PrivateKey privateKey, SecureRandom random, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_i2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i2(privateKey, random, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_i3Event(Certificate cert, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_i3_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i3(cert, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_i4Event(PublicKey key, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_i4_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_i4(key, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_updateEvent(Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_update_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_update(s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_s1Event(Signature s, byte[] output) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_s1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_s1(s, output);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_s2Event(byte[] output, int offset, int len, Signature s) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_s2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_s2(output, offset, len, s);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_v1Event(byte[] sign, Signature s, boolean signed) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_v1_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_v1(sign, s, signed);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SignatureSpec_v2Event(byte[] sign, int offset, int len, Signature s, boolean signed) {
		SignatureSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SignatureSpecMonitor.SignatureSpec_v2_num++;

		CachedWeakReference wr_s = null;
		MapOfMonitor<SignatureSpecMonitor> matchedLastMap = null;
		SignatureSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SignatureSpec_s_Map_cachekey_s) ) {
			matchedEntry = SignatureSpec_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SignatureSpecMonitor> itmdMap = SignatureSpec_s_Map;
				matchedLastMap = itmdMap;
				SignatureSpecMonitor node_s = SignatureSpec_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SignatureSpecMonitor created = new SignatureSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		final SignatureSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_v2(sign, offset, len, s, signed);
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SignatureSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			SignatureSpec_s_Map_cachekey_s = s;
			SignatureSpec_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SSLContextSpec_g1Event(String protocol, SSLContext ctx) {
		SSLContextSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SSLContextSpecMonitor.SSLContextSpec_g1_num++;

		CachedWeakReference wr_ctx = null;
		MapOfMonitor<SSLContextSpecMonitor> matchedLastMap = null;
		SSLContextSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((ctx == SSLContextSpec_ctx_Map_cachekey_ctx) ) {
			matchedEntry = SSLContextSpec_ctx_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_ctx = new CachedWeakReference(ctx) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SSLContextSpecMonitor> itmdMap = SSLContextSpec_ctx_Map;
				matchedLastMap = itmdMap;
				SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
				matchedEntry = node_ctx;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_ctx == null) ) {
				wr_ctx = new CachedWeakReference(ctx) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				SSLContextSpecMonitor sourceLeaf = null;
				{
					// FindCode
					SSLContextSpecMonitor itmdLeaf = SSLContextSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <ctx>
					if (definable) {
						// FindCode
						SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
						if ((node_ctx != null) ) {
							if (((node_ctx.getDisable() > sourceLeaf.getTau() ) || ((node_ctx.getTau() > 0) && (node_ctx.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						SSLContextSpecMonitor created = (SSLContextSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_ctx, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				SSLContextSpecMonitor created = new SSLContextSpecMonitor(SSLContextSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_ctx, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(SSLContextSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final SSLContextSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(protocol, ctx);
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SSLContextSpec_ctx_Map_cachekey_ctx = ctx;
			SSLContextSpec_ctx_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SSLContextSpec_g2Event(String protocol, String provider, SSLContext ctx) {
		SSLContextSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SSLContextSpecMonitor.SSLContextSpec_g2_num++;

		CachedWeakReference wr_ctx = null;
		MapOfMonitor<SSLContextSpecMonitor> matchedLastMap = null;
		SSLContextSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((ctx == SSLContextSpec_ctx_Map_cachekey_ctx) ) {
			matchedEntry = SSLContextSpec_ctx_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_ctx = new CachedWeakReference(ctx) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SSLContextSpecMonitor> itmdMap = SSLContextSpec_ctx_Map;
				matchedLastMap = itmdMap;
				SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
				matchedEntry = node_ctx;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_ctx == null) ) {
				wr_ctx = new CachedWeakReference(ctx) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				SSLContextSpecMonitor sourceLeaf = null;
				{
					// FindCode
					SSLContextSpecMonitor itmdLeaf = SSLContextSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <ctx>
					if (definable) {
						// FindCode
						SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
						if ((node_ctx != null) ) {
							if (((node_ctx.getDisable() > sourceLeaf.getTau() ) || ((node_ctx.getTau() > 0) && (node_ctx.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						SSLContextSpecMonitor created = (SSLContextSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_ctx, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				SSLContextSpecMonitor created = new SSLContextSpecMonitor(SSLContextSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_ctx, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(SSLContextSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final SSLContextSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(protocol, provider, ctx);
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SSLContextSpec_ctx_Map_cachekey_ctx = ctx;
			SSLContextSpec_ctx_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SSLContextSpec_unsafe_protocolEvent(String protocol) {
		SSLContextSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SSLContextSpecMonitor.SSLContextSpec_unsafe_protocol_num++;

		Tuple2<SSLContextSpecMonitor_Set, SSLContextSpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = SSLContextSpec__Map;
		}
		// D(X) main:1
		SSLContextSpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				SSLContextSpecMonitor created = new SSLContextSpecMonitor(SSLContextSpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				SSLContextSpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			SSLContextSpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(SSLContextSpec_timestamp++) ;
		}
		// D(X) main:8--9
		SSLContextSpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_unsafe_protocol(protocol);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SSLContextSpec_initEvent(SSLContext ctx) {
		SSLContextSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SSLContextSpecMonitor.SSLContextSpec_init_num++;

		CachedWeakReference wr_ctx = null;
		MapOfMonitor<SSLContextSpecMonitor> matchedLastMap = null;
		SSLContextSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((ctx == SSLContextSpec_ctx_Map_cachekey_ctx) ) {
			matchedEntry = SSLContextSpec_ctx_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_ctx = new CachedWeakReference(ctx) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SSLContextSpecMonitor> itmdMap = SSLContextSpec_ctx_Map;
				matchedLastMap = itmdMap;
				SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
				matchedEntry = node_ctx;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_ctx == null) ) {
				wr_ctx = new CachedWeakReference(ctx) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				SSLContextSpecMonitor sourceLeaf = null;
				{
					// FindCode
					SSLContextSpecMonitor itmdLeaf = SSLContextSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <ctx>
					if (definable) {
						// FindCode
						SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
						if ((node_ctx != null) ) {
							if (((node_ctx.getDisable() > sourceLeaf.getTau() ) || ((node_ctx.getTau() > 0) && (node_ctx.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						SSLContextSpecMonitor created = (SSLContextSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_ctx, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				SSLContextSpecMonitor created = new SSLContextSpecMonitor(SSLContextSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_ctx, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(SSLContextSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final SSLContextSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init(ctx);
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SSLContextSpec_ctx_Map_cachekey_ctx = ctx;
			SSLContextSpec_ctx_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SSLContextSpec_engineEvent(SSLContext ctx, SSLEngine eng) {
		SSLContextSpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		SSLContextSpecMonitor.SSLContextSpec_engine_num++;

		CachedWeakReference wr_ctx = null;
		MapOfMonitor<SSLContextSpecMonitor> matchedLastMap = null;
		SSLContextSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((ctx == SSLContextSpec_ctx_Map_cachekey_ctx) ) {
			matchedEntry = SSLContextSpec_ctx_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_ctx = new CachedWeakReference(ctx) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SSLContextSpecMonitor> itmdMap = SSLContextSpec_ctx_Map;
				matchedLastMap = itmdMap;
				SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
				matchedEntry = node_ctx;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_ctx == null) ) {
				wr_ctx = new CachedWeakReference(ctx) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				SSLContextSpecMonitor sourceLeaf = null;
				{
					// FindCode
					SSLContextSpecMonitor itmdLeaf = SSLContextSpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <ctx>
					if (definable) {
						// FindCode
						SSLContextSpecMonitor node_ctx = SSLContextSpec_ctx_Map.getNodeEquivalent(wr_ctx) ;
						if ((node_ctx != null) ) {
							if (((node_ctx.getDisable() > sourceLeaf.getTau() ) || ((node_ctx.getTau() > 0) && (node_ctx.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						SSLContextSpecMonitor created = (SSLContextSpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_ctx, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				SSLContextSpecMonitor created = new SSLContextSpecMonitor(SSLContextSpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_ctx, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					SSLContextSpecMonitor_Set targetSet = SSLContextSpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(SSLContextSpec_timestamp++) ;
		}
		// D(X) main:8--9
		final SSLContextSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_engine(ctx, eng);
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.SSLContextSpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			SSLContextSpec_ctx_Map_cachekey_ctx = ctx;
			SSLContextSpec_ctx_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TrustManagerFactorySpec_g1Event(String alg, TrustManagerFactory mf) {
		TrustManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TrustManagerFactorySpecMonitor.TrustManagerFactorySpec_g1_num++;

		CachedWeakReference wr_mf = null;
		MapOfMonitor<TrustManagerFactorySpecMonitor> matchedLastMap = null;
		TrustManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((mf == TrustManagerFactorySpec_mf_Map_cachekey_mf) ) {
			matchedEntry = TrustManagerFactorySpec_mf_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_mf = new CachedWeakReference(mf) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<TrustManagerFactorySpecMonitor> itmdMap = TrustManagerFactorySpec_mf_Map;
				matchedLastMap = itmdMap;
				TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
				matchedEntry = node_mf;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_mf == null) ) {
				wr_mf = new CachedWeakReference(mf) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				TrustManagerFactorySpecMonitor sourceLeaf = null;
				{
					// FindCode
					TrustManagerFactorySpecMonitor itmdLeaf = TrustManagerFactorySpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <mf>
					if (definable) {
						// FindCode
						TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
						if ((node_mf != null) ) {
							if (((node_mf.getDisable() > sourceLeaf.getTau() ) || ((node_mf.getTau() > 0) && (node_mf.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						TrustManagerFactorySpecMonitor created = (TrustManagerFactorySpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_mf, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(TrustManagerFactorySpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_mf, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(TrustManagerFactorySpec_timestamp++) ;
		}
		// D(X) main:8--9
		final TrustManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, mf);
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			TrustManagerFactorySpec_mf_Map_cachekey_mf = mf;
			TrustManagerFactorySpec_mf_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TrustManagerFactorySpec_g2Event(String alg, TrustManagerFactory mf) {
		TrustManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TrustManagerFactorySpecMonitor.TrustManagerFactorySpec_g2_num++;

		CachedWeakReference wr_mf = null;
		MapOfMonitor<TrustManagerFactorySpecMonitor> matchedLastMap = null;
		TrustManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((mf == TrustManagerFactorySpec_mf_Map_cachekey_mf) ) {
			matchedEntry = TrustManagerFactorySpec_mf_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_mf = new CachedWeakReference(mf) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<TrustManagerFactorySpecMonitor> itmdMap = TrustManagerFactorySpec_mf_Map;
				matchedLastMap = itmdMap;
				TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
				matchedEntry = node_mf;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_mf == null) ) {
				wr_mf = new CachedWeakReference(mf) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				TrustManagerFactorySpecMonitor sourceLeaf = null;
				{
					// FindCode
					TrustManagerFactorySpecMonitor itmdLeaf = TrustManagerFactorySpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <mf>
					if (definable) {
						// FindCode
						TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
						if ((node_mf != null) ) {
							if (((node_mf.getDisable() > sourceLeaf.getTau() ) || ((node_mf.getTau() > 0) && (node_mf.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						TrustManagerFactorySpecMonitor created = (TrustManagerFactorySpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_mf, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(TrustManagerFactorySpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_mf, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(TrustManagerFactorySpec_timestamp++) ;
		}
		// D(X) main:8--9
		final TrustManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, mf);
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			TrustManagerFactorySpec_mf_Map_cachekey_mf = mf;
			TrustManagerFactorySpec_mf_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TrustManagerFactorySpec_g3Event(String alg, TrustManagerFactory k) {
		TrustManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TrustManagerFactorySpecMonitor.TrustManagerFactorySpec_g3_num++;

		Tuple2<TrustManagerFactorySpecMonitor_Set, TrustManagerFactorySpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TrustManagerFactorySpec__Map;
		}
		// D(X) main:1
		TrustManagerFactorySpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(TrustManagerFactorySpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				TrustManagerFactorySpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			TrustManagerFactorySpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(TrustManagerFactorySpec_timestamp++) ;
		}
		// D(X) main:8--9
		TrustManagerFactorySpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_g3(alg, k);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TrustManagerFactorySpec_initEvent(TrustManagerFactory mf) {
		TrustManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TrustManagerFactorySpecMonitor.TrustManagerFactorySpec_init_num++;

		CachedWeakReference wr_mf = null;
		MapOfMonitor<TrustManagerFactorySpecMonitor> matchedLastMap = null;
		TrustManagerFactorySpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((mf == TrustManagerFactorySpec_mf_Map_cachekey_mf) ) {
			matchedEntry = TrustManagerFactorySpec_mf_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_mf = new CachedWeakReference(mf) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<TrustManagerFactorySpecMonitor> itmdMap = TrustManagerFactorySpec_mf_Map;
				matchedLastMap = itmdMap;
				TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
				matchedEntry = node_mf;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_mf == null) ) {
				wr_mf = new CachedWeakReference(mf) ;
			}
			{
				// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
				TrustManagerFactorySpecMonitor sourceLeaf = null;
				{
					// FindCode
					TrustManagerFactorySpecMonitor itmdLeaf = TrustManagerFactorySpec__Map.getValue2() ;
					sourceLeaf = itmdLeaf;
				}
				if ((sourceLeaf != null) ) {
					boolean definable = true;
					// D(X) defineTo:1--5 for <mf>
					if (definable) {
						// FindCode
						TrustManagerFactorySpecMonitor node_mf = TrustManagerFactorySpec_mf_Map.getNodeEquivalent(wr_mf) ;
						if ((node_mf != null) ) {
							if (((node_mf.getDisable() > sourceLeaf.getTau() ) || ((node_mf.getTau() > 0) && (node_mf.getTau() < sourceLeaf.getTau() ) ) ) ) {
								definable = false;
							}
						}
					}
					if (definable) {
						// D(X) defineTo:6
						TrustManagerFactorySpecMonitor created = (TrustManagerFactorySpecMonitor)sourceLeaf.clone() ;
						matchedEntry = created;
						matchedLastMap.putNode(wr_mf, created) ;
						// D(X) defineTo:7 for <>
						{
							// InsertMonitor
							TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
							targetSet.add(created) ;
						}
					}
				}
			}
			if ((matchedEntry == null) ) {
				// D(X) main:4
				TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(TrustManagerFactorySpec_timestamp++) ;
				matchedEntry = created;
				matchedLastMap.putNode(wr_mf, created) ;
				// D(X) defineNew:5 for <>
				{
					// InsertMonitor
					TrustManagerFactorySpecMonitor_Set targetSet = TrustManagerFactorySpec__Map.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			matchedEntry.setDisable(TrustManagerFactorySpec_timestamp++) ;
		}
		// D(X) main:8--9
		final TrustManagerFactorySpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init(mf);
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.TrustManagerFactorySpecMonitor_Prop_1_Category_match1) {
			matchedEntryfinalMonitor.Prop_1_handler_match1();
		}

		if ((cachehit == false) ) {
			TrustManagerFactorySpec_mf_Map_cachekey_mf = mf;
			TrustManagerFactorySpec_mf_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TrustManagerFactorySpec_gtm1Event(TrustManagerFactory k, TrustManager[][] trustManager) {
		TrustManagerFactorySpec_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TrustManagerFactorySpecMonitor.TrustManagerFactorySpec_gtm1_num++;

		Tuple2<TrustManagerFactorySpecMonitor_Set, TrustManagerFactorySpecMonitor> matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TrustManagerFactorySpec__Map;
		}
		// D(X) main:1
		TrustManagerFactorySpecMonitor matchedLeaf = matchedEntry.getValue2() ;
		if ((matchedLeaf == null) ) {
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(TrustManagerFactorySpec_timestamp++) ;
				matchedEntry.setValue2(created) ;
				TrustManagerFactorySpecMonitor_Set enclosingSet = matchedEntry.getValue1() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			TrustManagerFactorySpecMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
			disableUpdatedLeaf.setDisable(TrustManagerFactorySpec_timestamp++) ;
		}
		// D(X) main:8--9
		TrustManagerFactorySpecMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
		stateTransitionedSet.event_gtm1(k, trustManager);

		MultiSpec_1_RVMLock.unlock();
	}

}
