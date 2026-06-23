package mop;
import com.runtimeverification.rvmonitor.java.rt.RVMLogging;
import com.runtimeverification.rvmonitor.java.rt.RVMLogging.Level;
import java.awt.TextArea;
import java.util.concurrent.Future;
import java.util.concurrent.ConcurrentMap;
import java.net.InetAddress;
import java.lang.Integer;
import java.util.AbstractMap;
import java.util.Dictionary;
import java.util.EventObject;
import javax.swing.border.Border;
import javax.swing.AbstractButton;
import java.util.Vector;
import java.util.Collection;
import java.util.LinkedList;
import java.util.Hashtable;
import java.util.Enumeration;
import javax.swing.JLabel;
import java.lang.Thread;
import java.lang.ref.Reference;
import java.net.InetSocketAddress;
import java.awt.TextComponent;
import javax.swing.text.JTextComponent;
import javax.swing.text.Document;
import javax.swing.text.AttributeSet;
import javax.swing.JScrollPane;
import java.awt.Component;
import java.util.Iterator;
import java.util.Set;
import java.util.Map.Entry;
import javax.swing.text.AbstractDocument.AbstractElement;
import javax.management.MBeanAttributeInfo;
import java.beans.PropertyChangeEvent;
import java.lang.Boolean;
import java.util.Deque;
import java.net.URL;
import java.util.concurrent.CyclicBarrier;
import javax.swing.text.SimpleAttributeSet;
import java.lang.reflect.Field;
import java.lang.Class;
import java.io.File;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.awt.GradientPaint;
import java.awt.Color;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import javax.swing.JSplitPane;
import java.util.concurrent.locks.Condition;
import javax.swing.JList;
import javax.swing.ListModel;
import java.awt.LayoutManager;
import java.awt.Container;
import javax.swing.JComponent;
import javax.swing.BoxLayout;
import javax.swing.DefaultListModel;
import java.util.HashSet;
import java.lang.Iterable;
import java.util.AbstractCollection;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.Stack;
import java.io.DataInput;
import java.util.concurrent.atomic.AtomicLong;
import javax.swing.ComboBoxEditor;
import java.util.concurrent.CountDownLatch;
import java.awt.Label;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.swing.ButtonGroup;
import java.lang.Number;
import java.util.List;
import java.lang.reflect.AnnotatedElement;
import java.util.AbstractList;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.jar.JarFile;
import java.util.jar.Manifest;
import java.awt.Window;
import java.util.concurrent.ConcurrentHashMap;
import java.net.NetworkInterface;
import java.lang.Runtime;
import java.lang.ClassLoader;
import java.lang.reflect.AccessibleObject;
import java.io.ObjectInput;
import java.lang.Double;
import java.util.logging.Logger;
import javax.swing.JInternalFrame;
import java.lang.Package;
import java.lang.Throwable;
import javax.swing.DefaultComboBoxModel;
import javax.swing.ImageIcon;
import javax.swing.table.TableColumnModel;
import javax.swing.table.TableColumn;
import java.util.StringTokenizer;
import java.net.URLStreamHandler;
import java.io.Closeable;
import java.util.zip.ZipEntry;
import java.util.SortedMap;
import java.util.zip.ZipFile;
import java.util.Random;
import javax.swing.JTextField;
import javax.swing.Icon;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
import java.util.*;

import java.lang.ref.*;
import org.aspectj.lang.*;

aspect BaseAspect {
	pointcut notwithin() :
	!within(sun..*) &&
	!within(java..*) &&
	!within(javax..*) &&
	!within(com.sun..*) &&
	!within(org.dacapo.harness..*) &&
	!within(org.apache.commons..*) &&
	!within(org.apache.geronimo..*) &&
	!within(net.sf.cglib..*) &&
	!within(mop..*) &&
	!within(javamoprt..*) &&
	!within(rvmonitorrt..*) &&
	!within(com.runtimeverification..*);
}

public aspect MultiSpec_1MonitorAspect implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	public MultiSpec_1MonitorAspect(){
	}

	// Declarations for the Lock
	static ReentrantLock MultiSpec_1_MOPLock = new ReentrantLock();
	static Condition MultiSpec_1_MOPLock_cond = MultiSpec_1_MOPLock.newCondition();

	pointcut MOP_CommonPointCut() : !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
	pointcut FSM100_event_1() : (call(TextArea.new())) && MOP_CommonPointCut();
	after () returning (TextArea t) : FSM100_event_1() {
		MultiSpec_1RuntimeMonitor.FSM100_event_1Event(t);
	}

	pointcut FSM100_event_2(TextArea t) : (call(* TextArea.setEditable(boolean)) && target(t)) && MOP_CommonPointCut();
	after (TextArea t) : FSM100_event_2(t) {
		MultiSpec_1RuntimeMonitor.FSM100_event_2Event(t);
	}

	pointcut FSM100_event_3(TextArea t, String s) : (call(* TextArea.append(String)) && target(t) && args(s)) && MOP_CommonPointCut();
	after (TextArea t, String s) : FSM100_event_3(t, s) {
		MultiSpec_1RuntimeMonitor.FSM100_event_3Event(t, s);
	}

	pointcut FSM100_event_4(TextArea t) : (call(* TextArea.setBounds(int, int, int, int)) && target(t)) && MOP_CommonPointCut();
	after (TextArea t) : FSM100_event_4(t) {
		MultiSpec_1RuntimeMonitor.FSM100_event_4Event(t);
	}

	pointcut FSM101_event_1(Future f) : (call(* Future.isDone()) && target(f)) && MOP_CommonPointCut();
	after (Future f) : FSM101_event_1(f) {
		MultiSpec_1RuntimeMonitor.FSM101_event_1Event(f);
	}

	pointcut FSM101_event_2(Future f) : (call(* Future.isCancelled()) && target(f)) && MOP_CommonPointCut();
	after (Future f) : FSM101_event_2(f) {
		MultiSpec_1RuntimeMonitor.FSM101_event_2Event(f);
	}

	pointcut FSM101_event_3(Future f) : (call(* Future.cancel(boolean)) && target(f)) && MOP_CommonPointCut();
	after (Future f) : FSM101_event_3(f) {
		//FSM101_event_3
		MultiSpec_1RuntimeMonitor.FSM101_event_3Event(f);
		//FSM103_event_3
		MultiSpec_1RuntimeMonitor.FSM103_event_3Event(f);
		//FSM195_event_1
		MultiSpec_1RuntimeMonitor.FSM195_event_1Event(f);
		//FSM246_event_7
		MultiSpec_1RuntimeMonitor.FSM246_event_7Event(f);
		//FSM333_event_4
		MultiSpec_1RuntimeMonitor.FSM333_event_4Event(f);
		//FSM360_event_2
		MultiSpec_1RuntimeMonitor.FSM360_event_2Event(f);
	}

	pointcut FSM103_event_1(ConcurrentMap c, Object o, Object o1) : (call(* ConcurrentMap.putIfAbsent(Object, Object)) && target(c) && args(o, o1)) && MOP_CommonPointCut();
	after (ConcurrentMap c, Object o, Object o1) : FSM103_event_1(c, o, o1) {
		//FSM103_event_1
		MultiSpec_1RuntimeMonitor.FSM103_event_1Event(c, o, o1);
		//FSM19_event_4
		MultiSpec_1RuntimeMonitor.FSM19_event_4Event(c, o, o1);
		//FSM226_event_2
		MultiSpec_1RuntimeMonitor.FSM226_event_2Event(c, o, o1);
	}

	pointcut FSM103_event_2(ConcurrentMap c, Object o) : (call(* ConcurrentMap.remove(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (ConcurrentMap c, Object o) : FSM103_event_2(c, o) {
		//FSM103_event_2
		MultiSpec_1RuntimeMonitor.FSM103_event_2Event(c, o);
		//FSM19_event_1
		MultiSpec_1RuntimeMonitor.FSM19_event_1Event(c, o);
		//FSM226_event_4
		MultiSpec_1RuntimeMonitor.FSM226_event_4Event(c, o);
	}

	pointcut FSM105_event_1(InetAddress i) : (call(* InetAddress.getHostAddress()) && target(i)) && MOP_CommonPointCut();
	after (InetAddress i) : FSM105_event_1(i) {
		MultiSpec_1RuntimeMonitor.FSM105_event_1Event(i);
	}

	pointcut FSM105_event_2(InetAddress i) : (call(* InetAddress.isMulticastAddress()) && target(i)) && MOP_CommonPointCut();
	after (InetAddress i) : FSM105_event_2(i) {
		MultiSpec_1RuntimeMonitor.FSM105_event_2Event(i);
	}

	pointcut FSM106_event_1() : (call(Integer.new(int))) && MOP_CommonPointCut();
	after () returning (Integer i) : FSM106_event_1() {
		//FSM106_event_1
		MultiSpec_1RuntimeMonitor.FSM106_event_1Event(i);
		//FSM140_event_1
		MultiSpec_1RuntimeMonitor.FSM140_event_1Event(i);
		//FSM311_event_1
		MultiSpec_1RuntimeMonitor.FSM311_event_1Event(i);
		//FSM323_event_1
		MultiSpec_1RuntimeMonitor.FSM323_event_1Event(i);
	}

	pointcut FSM106_event_2(AbstractMap a, Object o, Object o1) : (call(* AbstractMap.put(Object, Object)) && target(a) && args(o, o1)) && MOP_CommonPointCut();
	after (AbstractMap a, Object o, Object o1) : FSM106_event_2(a, o, o1) {
		//FSM106_event_2
		MultiSpec_1RuntimeMonitor.FSM106_event_2Event(a, o, o1);
		//FSM146_event_2
		MultiSpec_1RuntimeMonitor.FSM146_event_2Event(a, o, o1);
		//FSM17_event_1
		MultiSpec_1RuntimeMonitor.FSM17_event_1Event(a, o, o1);
		//FSM214_event_1
		MultiSpec_1RuntimeMonitor.FSM214_event_1Event(a, o, o1);
		//FSM32_event_1
		MultiSpec_1RuntimeMonitor.FSM32_event_1Event(a, o, o1);
	}

	pointcut FSM106_event_3() : (call(AbstractMap.new())) && MOP_CommonPointCut();
	after () returning (AbstractMap a) : FSM106_event_3() {
		//FSM106_event_3
		MultiSpec_1RuntimeMonitor.FSM106_event_3Event(a);
		//FSM146_event_3
		MultiSpec_1RuntimeMonitor.FSM146_event_3Event(a);
		//FSM17_event_2
		MultiSpec_1RuntimeMonitor.FSM17_event_2Event(a);
		//FSM214_event_5
		MultiSpec_1RuntimeMonitor.FSM214_event_5Event(a);
		//FSM32_event_3
		MultiSpec_1RuntimeMonitor.FSM32_event_3Event(a);
	}

	pointcut FSM108_event_1() : (call(Dictionary.new())) && MOP_CommonPointCut();
	after () returning (Dictionary d) : FSM108_event_1() {
		MultiSpec_1RuntimeMonitor.FSM108_event_1Event(d);
	}

	pointcut FSM108_event_2(Dictionary d, Object o) : (call(* Dictionary.get(Object)) && target(d) && args(o)) && MOP_CommonPointCut();
	after (Dictionary d, Object o) : FSM108_event_2(d, o) {
		//FSM108_event_2
		MultiSpec_1RuntimeMonitor.FSM108_event_2Event(d, o);
		//FSM342_event_3
		MultiSpec_1RuntimeMonitor.FSM342_event_3Event(d, o);
	}

	pointcut FSM108_event_3(Dictionary d, Object o, Object o1) : (call(* Dictionary.put(Object, Object)) && target(d) && args(o, o1)) && MOP_CommonPointCut();
	after (Dictionary d, Object o, Object o1) : FSM108_event_3(d, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM108_event_3Event(d, o, o1);
	}

	pointcut FSM111_event_1(AbstractButton a, Border b) : (call(* AbstractButton.setBorder(Border)) && target(a) && args(b)) && MOP_CommonPointCut();
	after (AbstractButton a, Border b) : FSM111_event_1(a, b) {
		//FSM111_event_1
		MultiSpec_1RuntimeMonitor.FSM111_event_1Event(a, b);
		//FSM97_event_1
		MultiSpec_1RuntimeMonitor.FSM97_event_1Event(a, b);
	}

	pointcut FSM111_event_2(AbstractButton a) : (call(* AbstractButton.isSelected()) && target(a)) && MOP_CommonPointCut();
	after (AbstractButton a) : FSM111_event_2(a) {
		//FSM111_event_2
		MultiSpec_1RuntimeMonitor.FSM111_event_2Event(a);
		//FSM97_event_4
		MultiSpec_1RuntimeMonitor.FSM97_event_4Event(a);
	}

	pointcut FSM111_event_3(EventObject e) : (call(* EventObject.getSource()) && target(e)) && MOP_CommonPointCut();
	after (EventObject e) : FSM111_event_3(e) {
		MultiSpec_1RuntimeMonitor.FSM111_event_3Event(e);
	}

	pointcut FSM111_event_4(AbstractButton a) : (call(* AbstractButton.isEnabled()) && target(a)) && MOP_CommonPointCut();
	after (AbstractButton a) : FSM111_event_4(a) {
		//FSM111_event_4
		MultiSpec_1RuntimeMonitor.FSM111_event_4Event(a);
		//FSM97_event_3
		MultiSpec_1RuntimeMonitor.FSM97_event_3Event(a);
	}

	pointcut FSM112_event_1() : (call(Vector.new(Collection))) && MOP_CommonPointCut();
	after () returning (Vector v) : FSM112_event_1() {
		//FSM112_event_1
		MultiSpec_1RuntimeMonitor.FSM112_event_1Event(v);
		//FSM282_event_2
		MultiSpec_1RuntimeMonitor.FSM282_event_2Event(v);
	}

	pointcut FSM112_event_2(Vector v) : (call(* Vector.size()) && target(v)) && MOP_CommonPointCut();
	after (Vector v) : FSM112_event_2(v) {
		MultiSpec_1RuntimeMonitor.FSM112_event_2Event(v);
	}

	pointcut FSM112_event_3(LinkedList l, Object o) : (call(* LinkedList.contains(Object)) && target(l) && args(o)) && MOP_CommonPointCut();
	after (LinkedList l, Object o) : FSM112_event_3(l, o) {
		MultiSpec_1RuntimeMonitor.FSM112_event_3Event(l, o);
	}

	pointcut FSM112_event_4(LinkedList l) : (call(* LinkedList.iterator()) && target(l)) && MOP_CommonPointCut();
	after (LinkedList l) : FSM112_event_4(l) {
		MultiSpec_1RuntimeMonitor.FSM112_event_4Event(l);
	}

	pointcut FSM112_event_5() : (call(LinkedList.new(Collection))) && MOP_CommonPointCut();
	after () returning (LinkedList l) : FSM112_event_5() {
		MultiSpec_1RuntimeMonitor.FSM112_event_5Event(l);
	}

	pointcut FSM115_event_1(Hashtable h) : (call(* Hashtable.elements()) && target(h)) && MOP_CommonPointCut();
	after (Hashtable h) : FSM115_event_1(h) {
		MultiSpec_1RuntimeMonitor.FSM115_event_1Event(h);
	}

	pointcut FSM115_event_2(Enumeration e) : (call(* Enumeration.nextElement()) && target(e)) && MOP_CommonPointCut();
	after (Enumeration e) : FSM115_event_2(e) {
		//FSM115_event_2
		MultiSpec_1RuntimeMonitor.FSM115_event_2Event(e);
		//FSM152_event_3
		MultiSpec_1RuntimeMonitor.FSM152_event_3Event(e);
		//FSM354_event_1
		MultiSpec_1RuntimeMonitor.FSM354_event_1Event(e);
		//FSM62_event_1
		MultiSpec_1RuntimeMonitor.FSM62_event_1Event(e);
		//FSM68_event_1
		MultiSpec_1RuntimeMonitor.FSM68_event_1Event(e);
	}

	pointcut FSM115_event_3(Enumeration e) : (call(* Enumeration.hasMoreElements()) && target(e)) && MOP_CommonPointCut();
	after (Enumeration e) : FSM115_event_3(e) {
		//FSM115_event_3
		MultiSpec_1RuntimeMonitor.FSM115_event_3Event(e);
		//FSM152_event_7
		MultiSpec_1RuntimeMonitor.FSM152_event_7Event(e);
		//FSM326_event_1
		MultiSpec_1RuntimeMonitor.FSM326_event_1Event(e);
		//FSM354_event_2
		MultiSpec_1RuntimeMonitor.FSM354_event_2Event(e);
		//FSM62_event_2
		MultiSpec_1RuntimeMonitor.FSM62_event_2Event(e);
		//FSM68_event_2
		MultiSpec_1RuntimeMonitor.FSM68_event_2Event(e);
	}

	pointcut FSM115_event_4(Hashtable h, Object o) : (call(* Hashtable.get(Object)) && target(h) && args(o)) && MOP_CommonPointCut();
	after (Hashtable h, Object o) : FSM115_event_4(h, o) {
		MultiSpec_1RuntimeMonitor.FSM115_event_4Event(h, o);
	}

	pointcut FSM115_event_5(Hashtable h, Object o) : (call(* Hashtable.containsKey(Object)) && target(h) && args(o)) && MOP_CommonPointCut();
	after (Hashtable h, Object o) : FSM115_event_5(h, o) {
		MultiSpec_1RuntimeMonitor.FSM115_event_5Event(h, o);
	}

	pointcut FSM117_event_1() : (call(JLabel.new())) && MOP_CommonPointCut();
	after () returning (JLabel j) : FSM117_event_1() {
		MultiSpec_1RuntimeMonitor.FSM117_event_1Event(j);
	}

	pointcut FSM117_event_2(JLabel j, Border b) : (call(* JLabel.setBorder(Border)) && target(j) && args(b)) && MOP_CommonPointCut();
	after (JLabel j, Border b) : FSM117_event_2(j, b) {
		MultiSpec_1RuntimeMonitor.FSM117_event_2Event(j, b);
	}

	pointcut FSM117_event_3(JLabel j, String s) : (call(* JLabel.setText(String)) && target(j) && args(s)) && MOP_CommonPointCut();
	after (JLabel j, String s) : FSM117_event_3(j, s) {
		MultiSpec_1RuntimeMonitor.FSM117_event_3Event(j, s);
	}

	pointcut FSM119_event_1() : (call(Reference.new(Object))) && MOP_CommonPointCut();
	after () returning (Reference r) : FSM119_event_1() {
		//FSM119_event_1
		MultiSpec_1RuntimeMonitor.FSM119_event_1Event(r);
		//FSM242_event_2
		MultiSpec_1RuntimeMonitor.FSM242_event_2Event(r);
		//FSM58_event_1
		MultiSpec_1RuntimeMonitor.FSM58_event_1Event(r);
	}

	pointcut FSM119_event_2(Thread t) : (call(* Thread.getName()) && target(t)) && MOP_CommonPointCut();
	after (Thread t) : FSM119_event_2(t) {
		//FSM119_event_2
		MultiSpec_1RuntimeMonitor.FSM119_event_2Event(t);
		//FSM246_event_4
		MultiSpec_1RuntimeMonitor.FSM246_event_4Event(t);
	}

	pointcut FSM119_event_3(Reference r) : (call(* Reference.get()) && target(r)) && MOP_CommonPointCut();
	after (Reference r) : FSM119_event_3(r) {
		//FSM119_event_3
		MultiSpec_1RuntimeMonitor.FSM119_event_3Event(r);
		//FSM242_event_1
		MultiSpec_1RuntimeMonitor.FSM242_event_1Event(r);
	}

	pointcut FSM119_event_4(Thread t) : (call(* Thread.setDaemon(boolean)) && target(t)) && MOP_CommonPointCut();
	after (Thread t) : FSM119_event_4(t) {
		//FSM119_event_4
		MultiSpec_1RuntimeMonitor.FSM119_event_4Event(t);
		//FSM246_event_2
		MultiSpec_1RuntimeMonitor.FSM246_event_2Event(t);
	}

	pointcut FSM119_event_5(Thread t, String s) : (call(* Thread.setName(String)) && target(t) && args(s)) && MOP_CommonPointCut();
	after (Thread t, String s) : FSM119_event_5(t, s) {
		//FSM119_event_5
		MultiSpec_1RuntimeMonitor.FSM119_event_5Event(t, s);
		//FSM246_event_5
		MultiSpec_1RuntimeMonitor.FSM246_event_5Event(t, s);
	}

	pointcut FSM119_event_6() : (call(Thread.new(ThreadGroup, Runnable, String))) && MOP_CommonPointCut();
	after () returning (Thread t) : FSM119_event_6() {
		//FSM119_event_6
		MultiSpec_1RuntimeMonitor.FSM119_event_6Event(t);
		//FSM246_event_6
		MultiSpec_1RuntimeMonitor.FSM246_event_6Event(t);
	}

	pointcut FSM123_event_1(InetSocketAddress i) : (call(* InetSocketAddress.getPort()) && target(i)) && MOP_CommonPointCut();
	after (InetSocketAddress i) : FSM123_event_1(i) {
		MultiSpec_1RuntimeMonitor.FSM123_event_1Event(i);
	}

	pointcut FSM123_event_2() : (call(InetSocketAddress.new(InetAddress, int))) && MOP_CommonPointCut();
	after () returning (InetSocketAddress i) : FSM123_event_2() {
		MultiSpec_1RuntimeMonitor.FSM123_event_2Event(i);
	}

	pointcut FSM123_event_3(InetSocketAddress i) : (call(* InetSocketAddress.getHostName()) && target(i)) && MOP_CommonPointCut();
	after (InetSocketAddress i) : FSM123_event_3(i) {
		MultiSpec_1RuntimeMonitor.FSM123_event_3Event(i);
	}

	pointcut FSM128_event_1(TextComponent t) : (call(* TextComponent.setEditable(boolean)) && target(t)) && MOP_CommonPointCut();
	after (TextComponent t) : FSM128_event_1(t) {
		MultiSpec_1RuntimeMonitor.FSM128_event_1Event(t);
	}

	pointcut FSM128_event_2(TextComponent t) : (call(* TextComponent.setBounds(int, int, int, int)) && target(t)) && MOP_CommonPointCut();
	after (TextComponent t) : FSM128_event_2(t) {
		MultiSpec_1RuntimeMonitor.FSM128_event_2Event(t);
	}

	pointcut FSM128_event_3() : (call(TextComponent.new())) && MOP_CommonPointCut();
	after () returning (TextComponent t) : FSM128_event_3() {
		MultiSpec_1RuntimeMonitor.FSM128_event_3Event(t);
	}

	pointcut FSM132_event_1(Document d) : (call(* Document.getLength()) && target(d)) && MOP_CommonPointCut();
	after (Document d) : FSM132_event_1(d) {
		MultiSpec_1RuntimeMonitor.FSM132_event_1Event(d);
	}

	pointcut FSM132_event_2(Document d, String s, AttributeSet a) : (call(* Document.insertString(int, String, AttributeSet)) && target(d) && args(s, a)) && MOP_CommonPointCut();
	after (Document d, String s, AttributeSet a) : FSM132_event_2(d, s, a) {
		MultiSpec_1RuntimeMonitor.FSM132_event_2Event(d, s, a);
	}

	pointcut FSM132_event_3(JTextComponent j) : (call(* JTextComponent.setCaretPosition(int)) && target(j)) && MOP_CommonPointCut();
	after (JTextComponent j) : FSM132_event_3(j) {
		MultiSpec_1RuntimeMonitor.FSM132_event_3Event(j);
	}

	pointcut FSM132_event_4(JTextComponent j) : (call(* JTextComponent.getDocument()) && target(j)) && MOP_CommonPointCut();
	after (JTextComponent j) : FSM132_event_4(j) {
		MultiSpec_1RuntimeMonitor.FSM132_event_4Event(j);
	}

	pointcut FSM133_event_1(JTextComponent j) : (call(* JTextComponent.setEditable(boolean)) && target(j)) && MOP_CommonPointCut();
	after (JTextComponent j) : FSM133_event_1(j) {
		//FSM133_event_1
		MultiSpec_1RuntimeMonitor.FSM133_event_1Event(j);
		//FSM320_event_2
		MultiSpec_1RuntimeMonitor.FSM320_event_2Event(j);
	}

	pointcut FSM133_event_2() : (call(JTextComponent.new())) && MOP_CommonPointCut();
	after () returning (JTextComponent j) : FSM133_event_2() {
		//FSM133_event_2
		MultiSpec_1RuntimeMonitor.FSM133_event_2Event(j);
		//FSM320_event_1
		MultiSpec_1RuntimeMonitor.FSM320_event_1Event(j);
	}

	pointcut FSM133_event_3() : (call(JScrollPane.new(Component))) && MOP_CommonPointCut();
	after () returning (JScrollPane j) : FSM133_event_3() {
		//FSM133_event_3
		MultiSpec_1RuntimeMonitor.FSM133_event_3Event(j);
		//FSM197_event_4
		MultiSpec_1RuntimeMonitor.FSM197_event_4Event(j);
		//FSM206_event_2
		MultiSpec_1RuntimeMonitor.FSM206_event_2Event(j);
		//FSM32_event_5
		MultiSpec_1RuntimeMonitor.FSM32_event_5Event(j);
	}

	pointcut FSM140_event_2(Integer i) : (call(* Integer.intValue()) && target(i)) && MOP_CommonPointCut();
	after (Integer i) : FSM140_event_2(i) {
		//FSM140_event_2
		MultiSpec_1RuntimeMonitor.FSM140_event_2Event(i);
		//FSM311_event_3
		MultiSpec_1RuntimeMonitor.FSM311_event_3Event(i);
		//FSM323_event_5
		MultiSpec_1RuntimeMonitor.FSM323_event_5Event(i);
	}

	pointcut FSM140_event_3(Iterator i) : (call(* Iterator.next()) && target(i)) && MOP_CommonPointCut();
	after (Iterator i) : FSM140_event_3(i) {
		//FSM140_event_3
		MultiSpec_1RuntimeMonitor.FSM140_event_3Event(i);
		//FSM162_event_2
		MultiSpec_1RuntimeMonitor.FSM162_event_2Event(i);
		//FSM195_event_2
		MultiSpec_1RuntimeMonitor.FSM195_event_2Event(i);
		//FSM199_event_4
		MultiSpec_1RuntimeMonitor.FSM199_event_4Event(i);
		//FSM242_event_3
		MultiSpec_1RuntimeMonitor.FSM242_event_3Event(i);
		//FSM29_event_7
		MultiSpec_1RuntimeMonitor.FSM29_event_7Event(i);
		//FSM373_event_2
		MultiSpec_1RuntimeMonitor.FSM373_event_2Event(i);
		//FSM52_event_2
		MultiSpec_1RuntimeMonitor.FSM52_event_2Event(i);
	}

	pointcut FSM140_event_4(Iterator i) : (call(* Iterator.hasNext()) && target(i)) && MOP_CommonPointCut();
	after (Iterator i) : FSM140_event_4(i) {
		//FSM140_event_4
		MultiSpec_1RuntimeMonitor.FSM140_event_4Event(i);
		//FSM143_event_3
		MultiSpec_1RuntimeMonitor.FSM143_event_3Event(i);
		//FSM162_event_3
		MultiSpec_1RuntimeMonitor.FSM162_event_3Event(i);
		//FSM195_event_3
		MultiSpec_1RuntimeMonitor.FSM195_event_3Event(i);
		//FSM199_event_5
		MultiSpec_1RuntimeMonitor.FSM199_event_5Event(i);
		//FSM242_event_4
		MultiSpec_1RuntimeMonitor.FSM242_event_4Event(i);
		//FSM29_event_5
		MultiSpec_1RuntimeMonitor.FSM29_event_5Event(i);
		//FSM373_event_3
		MultiSpec_1RuntimeMonitor.FSM373_event_3Event(i);
		//FSM52_event_3
		MultiSpec_1RuntimeMonitor.FSM52_event_3Event(i);
	}

	pointcut FSM143_event_1(Set s) : (call(* Set.iterator()) && target(s)) && MOP_CommonPointCut();
	after (Set s) : FSM143_event_1(s) {
		MultiSpec_1RuntimeMonitor.FSM143_event_1Event(s);
	}

	pointcut FSM143_event_2(Set s) : (call(* Set.isEmpty()) && target(s)) && MOP_CommonPointCut();
	after (Set s) : FSM143_event_2(s) {
		MultiSpec_1RuntimeMonitor.FSM143_event_2Event(s);
	}

	pointcut FSM146_event_1(Set s, Collection c) : (call(* Set.retainAll(Collection)) && target(s) && args(c)) && MOP_CommonPointCut();
	after (Set s, Collection c) : FSM146_event_1(s, c) {
		//FSM146_event_1
		MultiSpec_1RuntimeMonitor.FSM146_event_1Event(s, c);
		//FSM21_event_1
		MultiSpec_1RuntimeMonitor.FSM21_event_1Event(s, c);
		//FSM69_event_1
		MultiSpec_1RuntimeMonitor.FSM69_event_1Event(s, c);
	}

	pointcut FSM146_event_4(AbstractMap a) : (call(* AbstractMap.keySet()) && target(a)) && MOP_CommonPointCut();
	after (AbstractMap a) : FSM146_event_4(a) {
		MultiSpec_1RuntimeMonitor.FSM146_event_4Event(a);
	}

	pointcut FSM147_event_1(Entry e) : (call(* Entry.getValue()) && target(e)) && MOP_CommonPointCut();
	after (Entry e) : FSM147_event_1(e) {
		//FSM147_event_1
		MultiSpec_1RuntimeMonitor.FSM147_event_1Event(e);
		//FSM199_event_2
		MultiSpec_1RuntimeMonitor.FSM199_event_2Event(e);
		//FSM305_event_4
		MultiSpec_1RuntimeMonitor.FSM305_event_4Event(e);
		//FSM63_event_1
		MultiSpec_1RuntimeMonitor.FSM63_event_1Event(e);
	}

	pointcut FSM147_event_2(Entry e) : (call(* Entry.getKey()) && target(e)) && MOP_CommonPointCut();
	after (Entry e) : FSM147_event_2(e) {
		//FSM147_event_2
		MultiSpec_1RuntimeMonitor.FSM147_event_2Event(e);
		//FSM199_event_3
		MultiSpec_1RuntimeMonitor.FSM199_event_3Event(e);
		//FSM305_event_3
		MultiSpec_1RuntimeMonitor.FSM305_event_3Event(e);
		//FSM63_event_2
		MultiSpec_1RuntimeMonitor.FSM63_event_2Event(e);
	}

	pointcut FSM152_event_1(AbstractElement a) : (call(* AbstractElement.getAttributeNames()) && target(a)) && MOP_CommonPointCut();
	after (AbstractElement a) : FSM152_event_1(a) {
		MultiSpec_1RuntimeMonitor.FSM152_event_1Event(a);
	}

	pointcut FSM152_event_2(AbstractElement a, Object o) : (call(* AbstractElement.getAttribute(Object)) && target(a) && args(o)) && MOP_CommonPointCut();
	after (AbstractElement a, Object o) : FSM152_event_2(a, o) {
		//FSM152_event_2
		MultiSpec_1RuntimeMonitor.FSM152_event_2Event(a, o);
		//FSM332_event_2
		MultiSpec_1RuntimeMonitor.FSM332_event_2Event(a, o);
	}

	pointcut FSM152_event_4(AbstractElement a) : (call(* AbstractElement.getDocument()) && target(a)) && MOP_CommonPointCut();
	after (AbstractElement a) : FSM152_event_4(a) {
		//FSM152_event_4
		MultiSpec_1RuntimeMonitor.FSM152_event_4Event(a);
		//FSM332_event_3
		MultiSpec_1RuntimeMonitor.FSM332_event_3Event(a);
	}

	pointcut FSM152_event_5(AbstractElement a) : (call(* AbstractElement.getName()) && target(a)) && MOP_CommonPointCut();
	after (AbstractElement a) : FSM152_event_5(a) {
		//FSM152_event_5
		MultiSpec_1RuntimeMonitor.FSM152_event_5Event(a);
		//FSM332_event_4
		MultiSpec_1RuntimeMonitor.FSM332_event_4Event(a);
	}

	pointcut FSM152_event_6(AbstractElement a) : (call(* AbstractElement.getAttributes()) && target(a)) && MOP_CommonPointCut();
	after (AbstractElement a) : FSM152_event_6(a) {
		//FSM152_event_6
		MultiSpec_1RuntimeMonitor.FSM152_event_6Event(a);
		//FSM332_event_1
		MultiSpec_1RuntimeMonitor.FSM332_event_1Event(a);
	}

	pointcut FSM154_event_1(MBeanAttributeInfo m) : (call(* MBeanAttributeInfo.isWritable()) && target(m)) && MOP_CommonPointCut();
	after (MBeanAttributeInfo m) : FSM154_event_1(m) {
		//FSM154_event_1
		MultiSpec_1RuntimeMonitor.FSM154_event_1Event(m);
		//FSM2_event_1
		MultiSpec_1RuntimeMonitor.FSM2_event_1Event(m);
	}

	pointcut FSM154_event_2(MBeanAttributeInfo m) : (call(* MBeanAttributeInfo.isReadable()) && target(m)) && MOP_CommonPointCut();
	after (MBeanAttributeInfo m) : FSM154_event_2(m) {
		//FSM154_event_2
		MultiSpec_1RuntimeMonitor.FSM154_event_2Event(m);
		//FSM2_event_2
		MultiSpec_1RuntimeMonitor.FSM2_event_2Event(m);
	}

	pointcut FSM154_event_3(MBeanAttributeInfo m) : (call(* MBeanAttributeInfo.getType()) && target(m)) && MOP_CommonPointCut();
	after (MBeanAttributeInfo m) : FSM154_event_3(m) {
		//FSM154_event_3
		MultiSpec_1RuntimeMonitor.FSM154_event_3Event(m);
		//FSM2_event_3
		MultiSpec_1RuntimeMonitor.FSM2_event_3Event(m);
	}

	pointcut FSM154_event_4(MBeanAttributeInfo m) : (call(* MBeanAttributeInfo.getName()) && target(m)) && MOP_CommonPointCut();
	after (MBeanAttributeInfo m) : FSM154_event_4(m) {
		//FSM154_event_4
		MultiSpec_1RuntimeMonitor.FSM154_event_4Event(m);
		//FSM2_event_4
		MultiSpec_1RuntimeMonitor.FSM2_event_4Event(m);
	}

	pointcut FSM154_event_5() : (call(MBeanAttributeInfo.new(String, String, String, boolean, boolean, boolean))) && MOP_CommonPointCut();
	after () returning (MBeanAttributeInfo m) : FSM154_event_5() {
		//FSM154_event_5
		MultiSpec_1RuntimeMonitor.FSM154_event_5Event(m);
		//FSM2_event_5
		MultiSpec_1RuntimeMonitor.FSM2_event_5Event(m);
	}

	pointcut FSM154_event_6(MBeanAttributeInfo m) : (call(* MBeanAttributeInfo.isIs()) && target(m)) && MOP_CommonPointCut();
	after (MBeanAttributeInfo m) : FSM154_event_6(m) {
		//FSM154_event_6
		MultiSpec_1RuntimeMonitor.FSM154_event_6Event(m);
		//FSM2_event_6
		MultiSpec_1RuntimeMonitor.FSM2_event_6Event(m);
	}

	pointcut FSM155_event_1(PropertyChangeEvent p) : (call(* PropertyChangeEvent.getNewValue()) && target(p)) && MOP_CommonPointCut();
	after (PropertyChangeEvent p) : FSM155_event_1(p) {
		//FSM155_event_1
		MultiSpec_1RuntimeMonitor.FSM155_event_1Event(p);
		//FSM244_event_1
		MultiSpec_1RuntimeMonitor.FSM244_event_1Event(p);
		//FSM247_event_2
		MultiSpec_1RuntimeMonitor.FSM247_event_2Event(p);
	}

	pointcut FSM155_event_2(Boolean b) : (call(* Boolean.booleanValue()) && target(b)) && MOP_CommonPointCut();
	after (Boolean b) : FSM155_event_2(b) {
		//FSM155_event_2
		MultiSpec_1RuntimeMonitor.FSM155_event_2Event(b);
		//FSM214_event_6
		MultiSpec_1RuntimeMonitor.FSM214_event_6Event(b);
	}

	pointcut FSM155_event_3(PropertyChangeEvent p) : (call(* PropertyChangeEvent.getPropertyName()) && target(p)) && MOP_CommonPointCut();
	after (PropertyChangeEvent p) : FSM155_event_3(p) {
		//FSM155_event_3
		MultiSpec_1RuntimeMonitor.FSM155_event_3Event(p);
		//FSM244_event_3
		MultiSpec_1RuntimeMonitor.FSM244_event_3Event(p);
		//FSM247_event_3
		MultiSpec_1RuntimeMonitor.FSM247_event_3Event(p);
	}

	pointcut FSM157_event_1(Deque d) : (call(* Deque.removeFirst()) && target(d)) && MOP_CommonPointCut();
	after (Deque d) : FSM157_event_1(d) {
		//FSM157_event_1
		MultiSpec_1RuntimeMonitor.FSM157_event_1Event(d);
		//FSM258_event_1
		MultiSpec_1RuntimeMonitor.FSM258_event_1Event(d);
	}

	pointcut FSM157_event_2(URL u) : (call(* URL.openStream()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM157_event_2(u) {
		//FSM157_event_2
		MultiSpec_1RuntimeMonitor.FSM157_event_2Event(u);
		//FSM60_event_3
		MultiSpec_1RuntimeMonitor.FSM60_event_3Event(u);
	}

	pointcut FSM157_event_3(Deque d) : (call(* Deque.isEmpty()) && target(d)) && MOP_CommonPointCut();
	after (Deque d) : FSM157_event_3(d) {
		//FSM157_event_3
		MultiSpec_1RuntimeMonitor.FSM157_event_3Event(d);
		//FSM258_event_5
		MultiSpec_1RuntimeMonitor.FSM258_event_5Event(d);
	}

	pointcut FSM160_event_1() : (call(CyclicBarrier.new(int))) && MOP_CommonPointCut();
	after () returning (CyclicBarrier c) : FSM160_event_1() {
		MultiSpec_1RuntimeMonitor.FSM160_event_1Event(c);
	}

	pointcut FSM160_event_2(CyclicBarrier c) : (call(* CyclicBarrier.await()) && target(c)) && MOP_CommonPointCut();
	after (CyclicBarrier c) : FSM160_event_2(c) {
		MultiSpec_1RuntimeMonitor.FSM160_event_2Event(c);
	}

	pointcut FSM161_event_1() : (call(SimpleAttributeSet.new())) && MOP_CommonPointCut();
	after () returning (SimpleAttributeSet s) : FSM161_event_1() {
		MultiSpec_1RuntimeMonitor.FSM161_event_1Event(s);
	}

	pointcut FSM161_event_2(SimpleAttributeSet s, Object o, Object o1) : (call(* SimpleAttributeSet.addAttribute(Object, Object)) && target(s) && args(o, o1)) && MOP_CommonPointCut();
	after (SimpleAttributeSet s, Object o, Object o1) : FSM161_event_2(s, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM161_event_2Event(s, o, o1);
	}

	pointcut FSM162_event_1(Iterator i) : (call(* Iterator.remove()) && target(i)) && MOP_CommonPointCut();
	after (Iterator i) : FSM162_event_1(i) {
		MultiSpec_1RuntimeMonitor.FSM162_event_1Event(i);
	}

	pointcut FSM164_event_1(Field f, Class c) : (call(* Field.getAnnotation(Class)) && target(f) && args(c)) && MOP_CommonPointCut();
	after (Field f, Class c) : FSM164_event_1(f, c) {
		MultiSpec_1RuntimeMonitor.FSM164_event_1Event(f, c);
	}

	pointcut FSM164_event_2(Field f) : (call(* Field.getType()) && target(f)) && MOP_CommonPointCut();
	after (Field f) : FSM164_event_2(f) {
		MultiSpec_1RuntimeMonitor.FSM164_event_2Event(f);
	}

	pointcut FSM164_event_3(Field f) : (call(* Field.setAccessible(boolean)) && target(f)) && MOP_CommonPointCut();
	after (Field f) : FSM164_event_3(f) {
		MultiSpec_1RuntimeMonitor.FSM164_event_3Event(f);
	}

	pointcut FSM164_event_4(Class c) : (call(* Class.getCanonicalName()) && target(c)) && MOP_CommonPointCut();
	after (Class c) : FSM164_event_4(c) {
		MultiSpec_1RuntimeMonitor.FSM164_event_4Event(c);
	}

	pointcut FSM164_event_5(Field f) : (call(* Field.isAccessible()) && target(f)) && MOP_CommonPointCut();
	after (Field f) : FSM164_event_5(f) {
		MultiSpec_1RuntimeMonitor.FSM164_event_5Event(f);
	}

	pointcut FSM164_event_6(Field f) : (call(* Field.getName()) && target(f)) && MOP_CommonPointCut();
	after (Field f) : FSM164_event_6(f) {
		MultiSpec_1RuntimeMonitor.FSM164_event_6Event(f);
	}

	pointcut FSM164_event_7(Field f) : (call(* Field.getModifiers()) && target(f)) && MOP_CommonPointCut();
	after (Field f) : FSM164_event_7(f) {
		//FSM164_event_7
		MultiSpec_1RuntimeMonitor.FSM164_event_7Event(f);
		//FSM312_event_2
		MultiSpec_1RuntimeMonitor.FSM312_event_2Event(f);
	}

	pointcut FSM166_event_1(URL u) : (call(* URL.getPath()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM166_event_1(u) {
		MultiSpec_1RuntimeMonitor.FSM166_event_1Event(u);
	}

	pointcut FSM166_event_2(File f) : (call(* File.toURL()) && target(f)) && MOP_CommonPointCut();
	after (File f) : FSM166_event_2(f) {
		MultiSpec_1RuntimeMonitor.FSM166_event_2Event(f);
	}

	pointcut FSM166_event_3(File f) : (call(* File.exists()) && target(f)) && MOP_CommonPointCut();
	after (File f) : FSM166_event_3(f) {
		MultiSpec_1RuntimeMonitor.FSM166_event_3Event(f);
	}

	pointcut FSM166_event_4(URL u) : (call(* URL.getProtocol()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM166_event_4(u) {
		//FSM166_event_4
		MultiSpec_1RuntimeMonitor.FSM166_event_4Event(u);
		//FSM339_event_3
		MultiSpec_1RuntimeMonitor.FSM339_event_3Event(u);
		//FSM73_event_6
		MultiSpec_1RuntimeMonitor.FSM73_event_6Event(u);
	}

	pointcut FSM17_event_3() : (call(TreeMap.new(Map))) && MOP_CommonPointCut();
	after () returning (TreeMap t) : FSM17_event_3() {
		MultiSpec_1RuntimeMonitor.FSM17_event_3Event(t);
	}

	pointcut FSM184_event_1() : (call(Semaphore.new(int, boolean))) && MOP_CommonPointCut();
	after () returning (Semaphore s) : FSM184_event_1() {
		MultiSpec_1RuntimeMonitor.FSM184_event_1Event(s);
	}

	pointcut FSM184_event_2(Semaphore s, TimeUnit t) : (call(* Semaphore.tryAcquire(long, TimeUnit)) && target(s) && args(t)) && MOP_CommonPointCut();
	after (Semaphore s, TimeUnit t) : FSM184_event_2(s, t) {
		MultiSpec_1RuntimeMonitor.FSM184_event_2Event(s, t);
	}

	pointcut FSM187_event_1(Color c) : (call(* Color.getRed()) && target(c)) && MOP_CommonPointCut();
	after (Color c) : FSM187_event_1(c) {
		//FSM187_event_1
		MultiSpec_1RuntimeMonitor.FSM187_event_1Event(c);
		//FSM376_event_1
		MultiSpec_1RuntimeMonitor.FSM376_event_1Event(c);
	}

	pointcut FSM187_event_2() : (call(GradientPaint.new(float, float, Color, float, float, Color))) && MOP_CommonPointCut();
	after () returning (GradientPaint g) : FSM187_event_2() {
		MultiSpec_1RuntimeMonitor.FSM187_event_2Event(g);
	}

	pointcut FSM187_event_3(Color c) : (call(* Color.getBlue()) && target(c)) && MOP_CommonPointCut();
	after (Color c) : FSM187_event_3(c) {
		//FSM187_event_3
		MultiSpec_1RuntimeMonitor.FSM187_event_3Event(c);
		//FSM376_event_2
		MultiSpec_1RuntimeMonitor.FSM376_event_2Event(c);
	}

	pointcut FSM187_event_4(Color c, Object o) : (call(* Color.equals(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (Color c, Object o) : FSM187_event_4(c, o) {
		//FSM187_event_4
		MultiSpec_1RuntimeMonitor.FSM187_event_4Event(c, o);
		//FSM376_event_3
		MultiSpec_1RuntimeMonitor.FSM376_event_3Event(c, o);
	}

	pointcut FSM187_event_5(Color c) : (call(* Color.getGreen()) && target(c)) && MOP_CommonPointCut();
	after (Color c) : FSM187_event_5(c) {
		//FSM187_event_5
		MultiSpec_1RuntimeMonitor.FSM187_event_5Event(c);
		//FSM376_event_4
		MultiSpec_1RuntimeMonitor.FSM376_event_4Event(c);
	}

	pointcut FSM190_event_1(ReentrantLock r) : (call(* ReentrantLock.unlock()) && target(r)) && MOP_CommonPointCut();
	after (ReentrantLock r) : FSM190_event_1(r) {
		//FSM190_event_1
		MultiSpec_1RuntimeMonitor.FSM190_event_1Event(r);
		//FSM1_event_1
		MultiSpec_1RuntimeMonitor.FSM1_event_1Event(r);
	}

	pointcut FSM190_event_2() : (call(ReentrantLock.new(boolean))) && MOP_CommonPointCut();
	after () returning (ReentrantLock r) : FSM190_event_2() {
		//FSM190_event_2
		MultiSpec_1RuntimeMonitor.FSM190_event_2Event(r);
		//FSM1_event_4
		MultiSpec_1RuntimeMonitor.FSM1_event_4Event(r);
	}

	pointcut FSM190_event_3() : (call(ReentrantLock.new())) && MOP_CommonPointCut();
	after () returning (ReentrantLock r) : FSM190_event_3() {
		//FSM190_event_3
		MultiSpec_1RuntimeMonitor.FSM190_event_3Event(r);
		//FSM1_event_5
		MultiSpec_1RuntimeMonitor.FSM1_event_5Event(r);
	}

	pointcut FSM190_event_4(ReentrantLock r) : (call(* ReentrantLock.newCondition()) && target(r)) && MOP_CommonPointCut();
	after (ReentrantLock r) : FSM190_event_4(r) {
		//FSM190_event_4
		MultiSpec_1RuntimeMonitor.FSM190_event_4Event(r);
		//FSM1_event_7
		MultiSpec_1RuntimeMonitor.FSM1_event_7Event(r);
	}

	pointcut FSM190_event_5(ReentrantLock r) : (call(* ReentrantLock.lock()) && target(r)) && MOP_CommonPointCut();
	after (ReentrantLock r) : FSM190_event_5(r) {
		//FSM190_event_5
		MultiSpec_1RuntimeMonitor.FSM190_event_5Event(r);
		//FSM1_event_2
		MultiSpec_1RuntimeMonitor.FSM1_event_2Event(r);
	}

	pointcut FSM194_event_1(ReentrantReadWriteLock r) : (call(* ReentrantReadWriteLock.writeLock()) && target(r)) && MOP_CommonPointCut();
	after (ReentrantReadWriteLock r) : FSM194_event_1(r) {
		MultiSpec_1RuntimeMonitor.FSM194_event_1Event(r);
	}

	pointcut FSM194_event_2(Lock l) : (call(* Lock.lock()) && target(l)) && MOP_CommonPointCut();
	after (Lock l) : FSM194_event_2(l) {
		//FSM194_event_2
		MultiSpec_1RuntimeMonitor.FSM194_event_2Event(l);
		//FSM30_event_3
		MultiSpec_1RuntimeMonitor.FSM30_event_3Event(l);
		//FSM327_event_2
		MultiSpec_1RuntimeMonitor.FSM327_event_2Event(l);
	}

	pointcut FSM194_event_3(ReentrantReadWriteLock r) : (call(* ReentrantReadWriteLock.readLock()) && target(r)) && MOP_CommonPointCut();
	after (ReentrantReadWriteLock r) : FSM194_event_3(r) {
		MultiSpec_1RuntimeMonitor.FSM194_event_3Event(r);
	}

	pointcut FSM194_event_4(Lock l) : (call(* Lock.unlock()) && target(l)) && MOP_CommonPointCut();
	after (Lock l) : FSM194_event_4(l) {
		//FSM194_event_4
		MultiSpec_1RuntimeMonitor.FSM194_event_4Event(l);
		//FSM30_event_2
		MultiSpec_1RuntimeMonitor.FSM30_event_2Event(l);
		//FSM327_event_1
		MultiSpec_1RuntimeMonitor.FSM327_event_1Event(l);
	}

	pointcut FSM194_event_5() : (call(ReentrantReadWriteLock.new())) && MOP_CommonPointCut();
	after () returning (ReentrantReadWriteLock r) : FSM194_event_5() {
		MultiSpec_1RuntimeMonitor.FSM194_event_5Event(r);
	}

	pointcut FSM197_event_1(JSplitPane j, Component c) : (call(* JSplitPane.setLeftComponent(Component)) && target(j) && args(c)) && MOP_CommonPointCut();
	after (JSplitPane j, Component c) : FSM197_event_1(j, c) {
		//FSM197_event_1
		MultiSpec_1RuntimeMonitor.FSM197_event_1Event(j, c);
		//FSM81_event_1
		MultiSpec_1RuntimeMonitor.FSM81_event_1Event(j, c);
	}

	pointcut FSM197_event_2() : (call(JSplitPane.new())) && MOP_CommonPointCut();
	after () returning (JSplitPane j) : FSM197_event_2() {
		//FSM197_event_2
		MultiSpec_1RuntimeMonitor.FSM197_event_2Event(j);
		//FSM81_event_2
		MultiSpec_1RuntimeMonitor.FSM81_event_2Event(j);
	}

	pointcut FSM197_event_3(JSplitPane j) : (call(* JSplitPane.invalidate()) && target(j)) && MOP_CommonPointCut();
	after (JSplitPane j) : FSM197_event_3(j) {
		MultiSpec_1RuntimeMonitor.FSM197_event_3Event(j);
	}

	pointcut FSM197_event_5(JSplitPane j) : (call(* JSplitPane.setOrientation(int)) && target(j)) && MOP_CommonPointCut();
	after (JSplitPane j) : FSM197_event_5(j) {
		MultiSpec_1RuntimeMonitor.FSM197_event_5Event(j);
	}

	pointcut FSM197_event_6(JSplitPane j) : (call(* JSplitPane.setResizeWeight(double)) && target(j)) && MOP_CommonPointCut();
	after (JSplitPane j) : FSM197_event_6(j) {
		MultiSpec_1RuntimeMonitor.FSM197_event_6Event(j);
	}

	pointcut FSM197_event_7(JSplitPane j, Component c) : (call(* JSplitPane.setRightComponent(Component)) && target(j) && args(c)) && MOP_CommonPointCut();
	after (JSplitPane j, Component c) : FSM197_event_7(j, c) {
		//FSM197_event_7
		MultiSpec_1RuntimeMonitor.FSM197_event_7Event(j, c);
		//FSM81_event_3
		MultiSpec_1RuntimeMonitor.FSM81_event_3Event(j, c);
	}

	pointcut FSM199_event_1(Entry e, Object o) : (call(* Entry.setValue(Object)) && target(e) && args(o)) && MOP_CommonPointCut();
	after (Entry e, Object o) : FSM199_event_1(e, o) {
		//FSM199_event_1
		MultiSpec_1RuntimeMonitor.FSM199_event_1Event(e, o);
		//FSM305_event_1
		MultiSpec_1RuntimeMonitor.FSM305_event_1Event(e, o);
	}

	pointcut FSM19_event_2(ConcurrentMap c) : (call(* ConcurrentMap.keySet()) && target(c)) && MOP_CommonPointCut();
	after (ConcurrentMap c) : FSM19_event_2(c) {
		MultiSpec_1RuntimeMonitor.FSM19_event_2Event(c);
	}

	pointcut FSM19_event_3(ConcurrentMap c, Object o, Object o1) : (call(* ConcurrentMap.put(Object, Object)) && target(c) && args(o, o1)) && MOP_CommonPointCut();
	after (ConcurrentMap c, Object o, Object o1) : FSM19_event_3(c, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM19_event_3Event(c, o, o1);
	}

	pointcut FSM19_event_5(ConcurrentMap c, Object o) : (call(* ConcurrentMap.get(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (ConcurrentMap c, Object o) : FSM19_event_5(c, o) {
		MultiSpec_1RuntimeMonitor.FSM19_event_5Event(c, o);
	}

	pointcut FSM19_event_6(ConcurrentMap c) : (call(* ConcurrentMap.clear()) && target(c)) && MOP_CommonPointCut();
	after (ConcurrentMap c) : FSM19_event_6(c) {
		//FSM19_event_6
		MultiSpec_1RuntimeMonitor.FSM19_event_6Event(c);
		//FSM226_event_3
		MultiSpec_1RuntimeMonitor.FSM226_event_3Event(c);
	}

	pointcut FSM1_event_3(Condition c) : (call(* Condition.signalAll()) && target(c)) && MOP_CommonPointCut();
	after (Condition c) : FSM1_event_3(c) {
		//FSM1_event_3
		MultiSpec_1RuntimeMonitor.FSM1_event_3Event(c);
		//FSM56_event_1
		MultiSpec_1RuntimeMonitor.FSM56_event_1Event(c);
	}

	pointcut FSM1_event_6(Condition c, TimeUnit t) : (call(* Condition.await(long, TimeUnit)) && target(c) && args(t)) && MOP_CommonPointCut();
	after (Condition c, TimeUnit t) : FSM1_event_6(c, t) {
		//FSM1_event_6
		MultiSpec_1RuntimeMonitor.FSM1_event_6Event(c, t);
		//FSM56_event_2
		MultiSpec_1RuntimeMonitor.FSM56_event_2Event(c, t);
	}

	pointcut FSM206_event_1() : (call(JList.new(ListModel))) && MOP_CommonPointCut();
	after () returning (JList j) : FSM206_event_1() {
		//FSM206_event_1
		MultiSpec_1RuntimeMonitor.FSM206_event_1Event(j);
		//FSM213_event_2
		MultiSpec_1RuntimeMonitor.FSM213_event_2Event(j);
	}

	pointcut FSM209_event_1(JComponent j, LayoutManager l) : (call(* JComponent.setLayout(LayoutManager)) && target(j) && args(l)) && MOP_CommonPointCut();
	after (JComponent j, LayoutManager l) : FSM209_event_1(j, l) {
		MultiSpec_1RuntimeMonitor.FSM209_event_1Event(j, l);
	}

	pointcut FSM209_event_2(JComponent j, Component c) : (call(* JComponent.add(Component)) && target(j) && args(c)) && MOP_CommonPointCut();
	after (JComponent j, Component c) : FSM209_event_2(j, c) {
		MultiSpec_1RuntimeMonitor.FSM209_event_2Event(j, c);
	}

	pointcut FSM209_event_3(JComponent j, Border b) : (call(* JComponent.setBorder(Border)) && target(j) && args(b)) && MOP_CommonPointCut();
	after (JComponent j, Border b) : FSM209_event_3(j, b) {
		//FSM209_event_3
		MultiSpec_1RuntimeMonitor.FSM209_event_3Event(j, b);
		//FSM284_event_1
		MultiSpec_1RuntimeMonitor.FSM284_event_1Event(j, b);
	}

	pointcut FSM209_event_4() : (call(JComponent.new())) && MOP_CommonPointCut();
	after () returning (JComponent j) : FSM209_event_4() {
		//FSM209_event_4
		MultiSpec_1RuntimeMonitor.FSM209_event_4Event(j);
		//FSM284_event_4
		MultiSpec_1RuntimeMonitor.FSM284_event_4Event(j);
	}

	pointcut FSM209_event_5() : (call(BoxLayout.new(Container, int))) && MOP_CommonPointCut();
	after () returning (BoxLayout b) : FSM209_event_5() {
		MultiSpec_1RuntimeMonitor.FSM209_event_5Event(b);
	}

	pointcut FSM213_event_1(DefaultListModel d, Object o) : (call(* DefaultListModel.addElement(Object)) && target(d) && args(o)) && MOP_CommonPointCut();
	after (DefaultListModel d, Object o) : FSM213_event_1(d, o) {
		//FSM213_event_1
		MultiSpec_1RuntimeMonitor.FSM213_event_1Event(d, o);
		//FSM22_event_1
		MultiSpec_1RuntimeMonitor.FSM22_event_1Event(d, o);
	}

	pointcut FSM213_event_3() : (call(DefaultListModel.new())) && MOP_CommonPointCut();
	after () returning (DefaultListModel d) : FSM213_event_3() {
		//FSM213_event_3
		MultiSpec_1RuntimeMonitor.FSM213_event_3Event(d);
		//FSM22_event_2
		MultiSpec_1RuntimeMonitor.FSM22_event_2Event(d);
	}

	pointcut FSM214_event_2(AbstractMap a, Map m) : (call(* AbstractMap.putAll(Map)) && target(a) && args(m)) && MOP_CommonPointCut();
	after (AbstractMap a, Map m) : FSM214_event_2(a, m) {
		MultiSpec_1RuntimeMonitor.FSM214_event_2Event(a, m);
	}

	pointcut FSM214_event_3(AbstractMap a, Object o) : (call(* AbstractMap.get(Object)) && target(a) && args(o)) && MOP_CommonPointCut();
	after (AbstractMap a, Object o) : FSM214_event_3(a, o) {
		MultiSpec_1RuntimeMonitor.FSM214_event_3Event(a, o);
	}

	pointcut FSM214_event_4(AbstractMap a, Object o) : (call(* AbstractMap.containsKey(Object)) && target(a) && args(o)) && MOP_CommonPointCut();
	after (AbstractMap a, Object o) : FSM214_event_4(a, o) {
		//FSM214_event_4
		MultiSpec_1RuntimeMonitor.FSM214_event_4Event(a, o);
		//FSM32_event_2
		MultiSpec_1RuntimeMonitor.FSM32_event_2Event(a, o);
	}

	pointcut FSM21_event_2() : (call(HashSet.new(Collection))) && MOP_CommonPointCut();
	after () returning (HashSet h) : FSM21_event_2() {
		MultiSpec_1RuntimeMonitor.FSM21_event_2Event(h);
	}

	pointcut FSM21_event_3(HashSet h, Object o) : (call(* HashSet.add(Object)) && target(h) && args(o)) && MOP_CommonPointCut();
	after (HashSet h, Object o) : FSM21_event_3(h, o) {
		MultiSpec_1RuntimeMonitor.FSM21_event_3Event(h, o);
	}

	pointcut FSM221_event_1(AbstractCollection a) : (call(* AbstractCollection.clone()) && target(a)) && MOP_CommonPointCut();
	after (AbstractCollection a) : FSM221_event_1(a) {
		MultiSpec_1RuntimeMonitor.FSM221_event_1Event(a);
	}

	pointcut FSM221_event_2(AbstractCollection a, Object o) : (call(* AbstractCollection.add(Object)) && target(a) && args(o)) && MOP_CommonPointCut();
	after (AbstractCollection a, Object o) : FSM221_event_2(a, o) {
		MultiSpec_1RuntimeMonitor.FSM221_event_2Event(a, o);
	}

	pointcut FSM221_event_3() : (call(AbstractCollection.new())) && MOP_CommonPointCut();
	after () returning (AbstractCollection a) : FSM221_event_3() {
		MultiSpec_1RuntimeMonitor.FSM221_event_3Event(a);
	}

	pointcut FSM221_event_4(Iterable i) : (call(* Iterable.iterator()) && target(i)) && MOP_CommonPointCut();
	after (Iterable i) : FSM221_event_4(i) {
		//FSM221_event_4
		MultiSpec_1RuntimeMonitor.FSM221_event_4Event(i);
		//FSM226_event_5
		MultiSpec_1RuntimeMonitor.FSM226_event_5Event(i);
		//FSM269_event_2
		MultiSpec_1RuntimeMonitor.FSM269_event_2Event(i);
		//FSM300_event_5
		MultiSpec_1RuntimeMonitor.FSM300_event_5Event(i);
	}

	pointcut FSM224_event_1(Socket s) : (call(* Socket.getOutputStream()) && target(s)) && MOP_CommonPointCut();
	after (Socket s) : FSM224_event_1(s) {
		MultiSpec_1RuntimeMonitor.FSM224_event_1Event(s);
	}

	pointcut FSM224_event_2(ServerSocket s) : (call(* ServerSocket.accept()) && target(s)) && MOP_CommonPointCut();
	after (ServerSocket s) : FSM224_event_2(s) {
		MultiSpec_1RuntimeMonitor.FSM224_event_2Event(s);
	}

	pointcut FSM224_event_3(Socket s) : (call(* Socket.close()) && target(s)) && MOP_CommonPointCut();
	after (Socket s) : FSM224_event_3(s) {
		MultiSpec_1RuntimeMonitor.FSM224_event_3Event(s);
	}

	pointcut FSM224_event_4(ServerSocket s) : (call(* ServerSocket.getLocalPort()) && target(s)) && MOP_CommonPointCut();
	after (ServerSocket s) : FSM224_event_4(s) {
		//FSM224_event_4
		MultiSpec_1RuntimeMonitor.FSM224_event_4Event(s);
		//FSM304_event_3
		MultiSpec_1RuntimeMonitor.FSM304_event_3Event(s);
	}

	pointcut FSM224_event_5() : (call(ServerSocket.new(int))) && MOP_CommonPointCut();
	after () returning (ServerSocket s) : FSM224_event_5() {
		//FSM224_event_5
		MultiSpec_1RuntimeMonitor.FSM224_event_5Event(s);
		//FSM304_event_1
		MultiSpec_1RuntimeMonitor.FSM304_event_1Event(s);
	}

	pointcut FSM224_event_6(Socket s) : (call(* Socket.getInputStream()) && target(s)) && MOP_CommonPointCut();
	after (Socket s) : FSM224_event_6(s) {
		MultiSpec_1RuntimeMonitor.FSM224_event_6Event(s);
	}

	pointcut FSM226_event_1(ConcurrentMap c) : (call(* ConcurrentMap.values()) && target(c)) && MOP_CommonPointCut();
	after (ConcurrentMap c) : FSM226_event_1(c) {
		MultiSpec_1RuntimeMonitor.FSM226_event_1Event(c);
	}

	pointcut FSM229_event_1(Matcher m, StringBuffer s2) : (call(* Matcher.appendTail(StringBuffer)) && target(m) && args(s2)) && MOP_CommonPointCut();
	after (Matcher m, StringBuffer s2) : FSM229_event_1(m, s2) {
		MultiSpec_1RuntimeMonitor.FSM229_event_1Event(m, s2);
	}

	pointcut FSM229_event_2(Matcher m) : (call(* Matcher.end()) && target(m)) && MOP_CommonPointCut();
	after (Matcher m) : FSM229_event_2(m) {
		MultiSpec_1RuntimeMonitor.FSM229_event_2Event(m);
	}

	pointcut FSM229_event_3(Pattern p, CharSequence c) : (call(* Pattern.matcher(CharSequence)) && target(p) && args(c)) && MOP_CommonPointCut();
	after (Pattern p, CharSequence c) : FSM229_event_3(p, c) {
		MultiSpec_1RuntimeMonitor.FSM229_event_3Event(p, c);
	}

	pointcut FSM229_event_4(Matcher m) : (call(* Matcher.find()) && target(m)) && MOP_CommonPointCut();
	after (Matcher m) : FSM229_event_4(m) {
		MultiSpec_1RuntimeMonitor.FSM229_event_4Event(m);
	}

	pointcut FSM229_event_5(Matcher m, StringBuffer s2, String s1) : (call(* Matcher.appendReplacement(StringBuffer, String)) && target(m) && args(s2, s1)) && MOP_CommonPointCut();
	after (Matcher m, StringBuffer s2, String s1) : FSM229_event_5(m, s2, s1) {
		MultiSpec_1RuntimeMonitor.FSM229_event_5Event(m, s2, s1);
	}

	pointcut FSM231_event_1() : (call(Stack.new())) && MOP_CommonPointCut();
	after () returning (Stack s) : FSM231_event_1() {
		MultiSpec_1RuntimeMonitor.FSM231_event_1Event(s);
	}

	pointcut FSM231_event_2(Stack s, Object o) : (call(* Stack.push(Object)) && target(s) && args(o)) && MOP_CommonPointCut();
	after (Stack s, Object o) : FSM231_event_2(s, o) {
		MultiSpec_1RuntimeMonitor.FSM231_event_2Event(s, o);
	}

	pointcut FSM241_event_1(DataInput d) : (call(* DataInput.readByte()) && target(d)) && MOP_CommonPointCut();
	after (DataInput d) : FSM241_event_1(d) {
		//FSM241_event_1
		MultiSpec_1RuntimeMonitor.FSM241_event_1Event(d);
		//FSM78_event_1
		MultiSpec_1RuntimeMonitor.FSM78_event_1Event(d);
	}

	pointcut FSM241_event_2(DataInput d) : (call(* DataInput.readInt()) && target(d)) && MOP_CommonPointCut();
	after (DataInput d) : FSM241_event_2(d) {
		//FSM241_event_2
		MultiSpec_1RuntimeMonitor.FSM241_event_2Event(d);
		//FSM78_event_3
		MultiSpec_1RuntimeMonitor.FSM78_event_3Event(d);
	}

	pointcut FSM241_event_3(AtomicLong a) : (call(* AtomicLong.incrementAndGet()) && target(a)) && MOP_CommonPointCut();
	after (AtomicLong a) : FSM241_event_3(a) {
		//FSM241_event_3
		MultiSpec_1RuntimeMonitor.FSM241_event_3Event(a);
		//FSM271_event_3
		MultiSpec_1RuntimeMonitor.FSM271_event_3Event(a);
	}

	pointcut FSM244_event_2(ComboBoxEditor c) : (call(* ComboBoxEditor.getEditorComponent()) && target(c)) && MOP_CommonPointCut();
	after (ComboBoxEditor c) : FSM244_event_2(c) {
		MultiSpec_1RuntimeMonitor.FSM244_event_2Event(c);
	}

	pointcut FSM246_event_1(Thread t) : (call(* Thread.start()) && target(t)) && MOP_CommonPointCut();
	after (Thread t) : FSM246_event_1(t) {
		MultiSpec_1RuntimeMonitor.FSM246_event_1Event(t);
	}

	pointcut FSM246_event_3(Thread t, boolean b) : (call(* Thread.setDaemon(boolean)) && target(t) && args(b)) && MOP_CommonPointCut();
	after (Thread t, boolean b) : FSM246_event_3(t, b) {
		MultiSpec_1RuntimeMonitor.FSM246_event_3Event(t, b);
	}

	pointcut FSM247_event_1(PropertyChangeEvent p) : (call(* PropertyChangeEvent.getSource()) && target(p)) && MOP_CommonPointCut();
	after (PropertyChangeEvent p) : FSM247_event_1(p) {
		MultiSpec_1RuntimeMonitor.FSM247_event_1Event(p);
	}

	pointcut FSM254_event_1(CountDownLatch c, TimeUnit t) : (call(* CountDownLatch.await(long, TimeUnit)) && target(c) && args(t)) && MOP_CommonPointCut();
	after (CountDownLatch c, TimeUnit t) : FSM254_event_1(c, t) {
		MultiSpec_1RuntimeMonitor.FSM254_event_1Event(c, t);
	}

	pointcut FSM254_event_2() : (call(CountDownLatch.new(int))) && MOP_CommonPointCut();
	after () returning (CountDownLatch c) : FSM254_event_2() {
		MultiSpec_1RuntimeMonitor.FSM254_event_2Event(c);
	}

	pointcut FSM256_event_1(Label l) : (call(* Label.setBounds(int, int, int, int)) && target(l)) && MOP_CommonPointCut();
	after (Label l) : FSM256_event_1(l) {
		MultiSpec_1RuntimeMonitor.FSM256_event_1Event(l);
	}

	pointcut FSM256_event_2() : (call(Label.new(String))) && MOP_CommonPointCut();
	after () returning (Label l) : FSM256_event_2() {
		MultiSpec_1RuntimeMonitor.FSM256_event_2Event(l);
	}

	pointcut FSM258_event_2(Deque d) : (call(* Deque.getLast()) && target(d)) && MOP_CommonPointCut();
	after (Deque d) : FSM258_event_2(d) {
		MultiSpec_1RuntimeMonitor.FSM258_event_2Event(d);
	}

	pointcut FSM258_event_3(Deque d) : (call(* Deque.size()) && target(d)) && MOP_CommonPointCut();
	after (Deque d) : FSM258_event_3(d) {
		MultiSpec_1RuntimeMonitor.FSM258_event_3Event(d);
	}

	pointcut FSM258_event_4(Deque d, Object o) : (call(* Deque.add(Object)) && target(d) && args(o)) && MOP_CommonPointCut();
	after (Deque d, Object o) : FSM258_event_4(d, o) {
		MultiSpec_1RuntimeMonitor.FSM258_event_4Event(d, o);
	}

	pointcut FSM269_event_1(AtomicBoolean a) : (call(* AtomicBoolean.get()) && target(a)) && MOP_CommonPointCut();
	after (AtomicBoolean a) : FSM269_event_1(a) {
		//FSM269_event_1
		MultiSpec_1RuntimeMonitor.FSM269_event_1Event(a);
		//FSM349_event_2
		MultiSpec_1RuntimeMonitor.FSM349_event_2Event(a);
	}

	pointcut FSM26_event_1(ButtonGroup b, AbstractButton a) : (call(* ButtonGroup.add(AbstractButton)) && target(b) && args(a)) && MOP_CommonPointCut();
	after (ButtonGroup b, AbstractButton a) : FSM26_event_1(b, a) {
		MultiSpec_1RuntimeMonitor.FSM26_event_1Event(b, a);
	}

	pointcut FSM26_event_2(ButtonGroup b, AbstractButton a) : (call(* ButtonGroup.remove(AbstractButton)) && target(b) && args(a)) && MOP_CommonPointCut();
	after (ButtonGroup b, AbstractButton a) : FSM26_event_2(b, a) {
		MultiSpec_1RuntimeMonitor.FSM26_event_2Event(b, a);
	}

	pointcut FSM271_event_1(AtomicLong a) : (call(* AtomicLong.doubleValue()) && target(a)) && MOP_CommonPointCut();
	after (AtomicLong a) : FSM271_event_1(a) {
		MultiSpec_1RuntimeMonitor.FSM271_event_1Event(a);
	}

	pointcut FSM271_event_2() : (call(AtomicLong.new(long))) && MOP_CommonPointCut();
	after () returning (AtomicLong a) : FSM271_event_2() {
		MultiSpec_1RuntimeMonitor.FSM271_event_2Event(a);
	}

	pointcut FSM271_event_4(AtomicLong a) : (call(* AtomicLong.addAndGet(long)) && target(a)) && MOP_CommonPointCut();
	after (AtomicLong a) : FSM271_event_4(a) {
		MultiSpec_1RuntimeMonitor.FSM271_event_4Event(a);
	}

	pointcut FSM279_event_1(Class c) : (call(* Class.getName()) && target(c)) && MOP_CommonPointCut();
	after (Class c) : FSM279_event_1(c) {
		//FSM279_event_1
		MultiSpec_1RuntimeMonitor.FSM279_event_1Event(c);
		//FSM369_event_1
		MultiSpec_1RuntimeMonitor.FSM369_event_1Event(c);
	}

	pointcut FSM279_event_2(Class c) : (call(* Class.newInstance()) && target(c)) && MOP_CommonPointCut();
	after (Class c) : FSM279_event_2(c) {
		MultiSpec_1RuntimeMonitor.FSM279_event_2Event(c);
	}

	pointcut FSM279_event_3(Map m, Object o) : (call(* Map.get(Object)) && target(m) && args(o)) && MOP_CommonPointCut();
	after (Map m, Object o) : FSM279_event_3(m, o) {
		//FSM279_event_3
		MultiSpec_1RuntimeMonitor.FSM279_event_3Event(m, o);
		//FSM287_event_4
		MultiSpec_1RuntimeMonitor.FSM287_event_4Event(m, o);
		//FSM342_event_4
		MultiSpec_1RuntimeMonitor.FSM342_event_4Event(m, o);
		//FSM88_event_2
		MultiSpec_1RuntimeMonitor.FSM88_event_2Event(m, o);
	}

	pointcut FSM282_event_1(Collection c, Object o) : (call(* Collection.contains(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (Collection c, Object o) : FSM282_event_1(c, o) {
		MultiSpec_1RuntimeMonitor.FSM282_event_1Event(c, o);
	}

	pointcut FSM284_event_2(JComponent j) : (call(* JComponent.setEnabled(boolean)) && target(j)) && MOP_CommonPointCut();
	after (JComponent j) : FSM284_event_2(j) {
		MultiSpec_1RuntimeMonitor.FSM284_event_2Event(j);
	}

	pointcut FSM284_event_3(JComponent j, String s) : (call(* JComponent.setToolTipText(String)) && target(j) && args(s)) && MOP_CommonPointCut();
	after (JComponent j, String s) : FSM284_event_3(j, s) {
		MultiSpec_1RuntimeMonitor.FSM284_event_3Event(j, s);
	}

	pointcut FSM287_event_1(Number n) : (call(* Number.longValue()) && target(n)) && MOP_CommonPointCut();
	after (Number n) : FSM287_event_1(n) {
		//FSM287_event_1
		MultiSpec_1RuntimeMonitor.FSM287_event_1Event(n);
		//FSM305_event_2
		MultiSpec_1RuntimeMonitor.FSM305_event_2Event(n);
		//FSM52_event_1
		MultiSpec_1RuntimeMonitor.FSM52_event_1Event(n);
	}

	pointcut FSM287_event_2(Number n) : (call(* Number.byteValue()) && target(n)) && MOP_CommonPointCut();
	after (Number n) : FSM287_event_2(n) {
		//FSM287_event_2
		MultiSpec_1RuntimeMonitor.FSM287_event_2Event(n);
		//FSM67_event_2
		MultiSpec_1RuntimeMonitor.FSM67_event_2Event(n);
	}

	pointcut FSM287_event_3(Map m, Object o, Object o1) : (call(* Map.put(Object, Object)) && target(m) && args(o, o1)) && MOP_CommonPointCut();
	after (Map m, Object o, Object o1) : FSM287_event_3(m, o, o1) {
		//FSM287_event_3
		MultiSpec_1RuntimeMonitor.FSM287_event_3Event(m, o, o1);
		//FSM325_event_2
		MultiSpec_1RuntimeMonitor.FSM325_event_2Event(m, o, o1);
	}

	pointcut FSM29_event_1(List l, Object o) : (call(* List.add(Object)) && target(l) && args(o)) && MOP_CommonPointCut();
	after (List l, Object o) : FSM29_event_1(l, o) {
		MultiSpec_1RuntimeMonitor.FSM29_event_1Event(l, o);
	}

	pointcut FSM29_event_2(List l) : (call(* List.size()) && target(l)) && MOP_CommonPointCut();
	after (List l) : FSM29_event_2(l) {
		MultiSpec_1RuntimeMonitor.FSM29_event_2Event(l);
	}

	pointcut FSM29_event_3(List l) : (call(* List.iterator()) && target(l)) && MOP_CommonPointCut();
	after (List l) : FSM29_event_3(l) {
		MultiSpec_1RuntimeMonitor.FSM29_event_3Event(l);
	}

	pointcut FSM29_event_4(List l) : (call(* List.get(int)) && target(l)) && MOP_CommonPointCut();
	after (List l) : FSM29_event_4(l) {
		MultiSpec_1RuntimeMonitor.FSM29_event_4Event(l);
	}

	pointcut FSM29_event_6(List l, Object o) : (call(* List.indexOf(Object)) && target(l) && args(o)) && MOP_CommonPointCut();
	after (List l, Object o) : FSM29_event_6(l, o) {
		MultiSpec_1RuntimeMonitor.FSM29_event_6Event(l, o);
	}

	pointcut FSM29_event_8(List l) : (call(* List.remove(int)) && target(l)) && MOP_CommonPointCut();
	after (List l) : FSM29_event_8(l) {
		MultiSpec_1RuntimeMonitor.FSM29_event_8Event(l);
	}

	pointcut FSM29_event_9(List l, Object o) : (call(* List.add(int, Object)) && target(l) && args(o)) && MOP_CommonPointCut();
	after (List l, Object o) : FSM29_event_9(l, o) {
		MultiSpec_1RuntimeMonitor.FSM29_event_9Event(l, o);
	}

	pointcut FSM2_event_7(AnnotatedElement a, Class c) : (call(* AnnotatedElement.getAnnotation(Class)) && target(a) && args(c)) && MOP_CommonPointCut();
	after (AnnotatedElement a, Class c) : FSM2_event_7(a, c) {
		MultiSpec_1RuntimeMonitor.FSM2_event_7Event(a, c);
	}

	pointcut FSM300_event_1(AbstractList a) : (call(* AbstractList.subList(int, int)) && target(a)) && MOP_CommonPointCut();
	after (AbstractList a) : FSM300_event_1(a) {
		MultiSpec_1RuntimeMonitor.FSM300_event_1Event(a);
	}

	pointcut FSM300_event_2(AbstractList a) : (call(* AbstractList.get(int)) && target(a)) && MOP_CommonPointCut();
	after (AbstractList a) : FSM300_event_2(a) {
		MultiSpec_1RuntimeMonitor.FSM300_event_2Event(a);
	}

	pointcut FSM300_event_3() : (call(AbstractList.new())) && MOP_CommonPointCut();
	after () returning (AbstractList a) : FSM300_event_3() {
		MultiSpec_1RuntimeMonitor.FSM300_event_3Event(a);
	}

	pointcut FSM300_event_4(AbstractList a) : (call(* AbstractList.size()) && target(a)) && MOP_CommonPointCut();
	after (AbstractList a) : FSM300_event_4(a) {
		MultiSpec_1RuntimeMonitor.FSM300_event_4Event(a);
	}

	pointcut FSM304_event_2(ServerSocket s) : (call(* ServerSocket.close()) && target(s)) && MOP_CommonPointCut();
	after (ServerSocket s) : FSM304_event_2(s) {
		MultiSpec_1RuntimeMonitor.FSM304_event_2Event(s);
	}

	pointcut FSM305_event_5(Number n) : (call(* Number.intValue()) && target(n)) && MOP_CommonPointCut();
	after (Number n) : FSM305_event_5(n) {
		MultiSpec_1RuntimeMonitor.FSM305_event_5Event(n);
	}

	pointcut FSM30_event_1(ReadWriteLock r) : (call(* ReadWriteLock.readLock()) && target(r)) && MOP_CommonPointCut();
	after (ReadWriteLock r) : FSM30_event_1(r) {
		MultiSpec_1RuntimeMonitor.FSM30_event_1Event(r);
	}

	pointcut FSM30_event_4(ReadWriteLock r) : (call(* ReadWriteLock.writeLock()) && target(r)) && MOP_CommonPointCut();
	after (ReadWriteLock r) : FSM30_event_4(r) {
		MultiSpec_1RuntimeMonitor.FSM30_event_4Event(r);
	}

	pointcut FSM311_event_2() : (call(Integer.new(String))) && MOP_CommonPointCut();
	after () returning (Integer i) : FSM311_event_2() {
		MultiSpec_1RuntimeMonitor.FSM311_event_2Event(i);
	}

	pointcut FSM312_event_1(Field f, Object o, Object o1) : (call(* Field.set(Object, Object)) && target(f) && args(o, o1)) && MOP_CommonPointCut();
	after (Field f, Object o, Object o1) : FSM312_event_1(f, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM312_event_1Event(f, o, o1);
	}

	pointcut FSM319_event_1() : (call(JarFile.new(String))) && MOP_CommonPointCut();
	after () returning (JarFile j) : FSM319_event_1() {
		MultiSpec_1RuntimeMonitor.FSM319_event_1Event(j);
	}

	pointcut FSM319_event_2(JarFile j) : (call(* JarFile.getManifest()) && target(j)) && MOP_CommonPointCut();
	after (JarFile j) : FSM319_event_2(j) {
		MultiSpec_1RuntimeMonitor.FSM319_event_2Event(j);
	}

	pointcut FSM319_event_3() : (call(JarFile.new(File))) && MOP_CommonPointCut();
	after () returning (JarFile j) : FSM319_event_3() {
		MultiSpec_1RuntimeMonitor.FSM319_event_3Event(j);
	}

	pointcut FSM319_event_4(JarFile j) : (call(* JarFile.close()) && target(j)) && MOP_CommonPointCut();
	after (JarFile j) : FSM319_event_4(j) {
		MultiSpec_1RuntimeMonitor.FSM319_event_4Event(j);
	}

	pointcut FSM319_event_5(Manifest m) : (call(* Manifest.getMainAttributes()) && target(m)) && MOP_CommonPointCut();
	after (Manifest m) : FSM319_event_5(m) {
		MultiSpec_1RuntimeMonitor.FSM319_event_5Event(m);
	}

	pointcut FSM323_event_2(Vector v, Object o) : (call(* Vector.addElement(Object)) && target(v) && args(o)) && MOP_CommonPointCut();
	after (Vector v, Object o) : FSM323_event_2(v, o) {
		MultiSpec_1RuntimeMonitor.FSM323_event_2Event(v, o);
	}

	pointcut FSM323_event_3() : (call(Vector.new())) && MOP_CommonPointCut();
	after () returning (Vector v) : FSM323_event_3() {
		MultiSpec_1RuntimeMonitor.FSM323_event_3Event(v);
	}

	pointcut FSM323_event_4() : (call(Vector.new(int))) && MOP_CommonPointCut();
	after () returning (Vector v) : FSM323_event_4() {
		MultiSpec_1RuntimeMonitor.FSM323_event_4Event(v);
	}

	pointcut FSM324_event_1(Window w) : (call(* Window.setVisible(boolean)) && target(w)) && MOP_CommonPointCut();
	after (Window w) : FSM324_event_1(w) {
		MultiSpec_1RuntimeMonitor.FSM324_event_1Event(w);
	}

	pointcut FSM324_event_2(Window w) : (call(* Window.dispose()) && target(w)) && MOP_CommonPointCut();
	after (Window w) : FSM324_event_2(w) {
		MultiSpec_1RuntimeMonitor.FSM324_event_2Event(w);
	}

	pointcut FSM325_event_1() : (call(ConcurrentHashMap.new(Map))) && MOP_CommonPointCut();
	after () returning (ConcurrentHashMap c) : FSM325_event_1() {
		MultiSpec_1RuntimeMonitor.FSM325_event_1Event(c);
	}

	pointcut FSM325_event_3(Map m) : (call(* Map.size()) && target(m)) && MOP_CommonPointCut();
	after (Map m) : FSM325_event_3(m) {
		MultiSpec_1RuntimeMonitor.FSM325_event_3Event(m);
	}

	pointcut FSM326_event_2(NetworkInterface n) : (call(* NetworkInterface.getInetAddresses()) && target(n)) && MOP_CommonPointCut();
	after (NetworkInterface n) : FSM326_event_2(n) {
		//FSM326_event_2
		MultiSpec_1RuntimeMonitor.FSM326_event_2Event(n);
		//FSM373_event_1
		MultiSpec_1RuntimeMonitor.FSM373_event_1Event(n);
	}

	pointcut FSM32_event_4(AbstractMap a) : (call(* AbstractMap.size()) && target(a)) && MOP_CommonPointCut();
	after (AbstractMap a) : FSM32_event_4(a) {
		MultiSpec_1RuntimeMonitor.FSM32_event_4Event(a);
	}

	pointcut FSM332_event_5(AbstractElement a) : (call(* AbstractElement.getStartOffset()) && target(a)) && MOP_CommonPointCut();
	after (AbstractElement a) : FSM332_event_5(a) {
		MultiSpec_1RuntimeMonitor.FSM332_event_5Event(a);
	}

	pointcut FSM333_event_1(ConcurrentHashMap c, Object o) : (call(* ConcurrentHashMap.remove(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (ConcurrentHashMap c, Object o) : FSM333_event_1(c, o) {
		MultiSpec_1RuntimeMonitor.FSM333_event_1Event(c, o);
	}

	pointcut FSM333_event_2() : (call(ConcurrentHashMap.new())) && MOP_CommonPointCut();
	after () returning (ConcurrentHashMap c) : FSM333_event_2() {
		MultiSpec_1RuntimeMonitor.FSM333_event_2Event(c);
	}

	pointcut FSM333_event_3(ConcurrentHashMap c, Object o, Object o1) : (call(* ConcurrentHashMap.putIfAbsent(Object, Object)) && target(c) && args(o, o1)) && MOP_CommonPointCut();
	after (ConcurrentHashMap c, Object o, Object o1) : FSM333_event_3(c, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM333_event_3Event(c, o, o1);
	}

	pointcut FSM337_event_1(Runtime r) : (call(* Runtime.freeMemory()) && target(r)) && MOP_CommonPointCut();
	after (Runtime r) : FSM337_event_1(r) {
		MultiSpec_1RuntimeMonitor.FSM337_event_1Event(r);
	}

	pointcut FSM337_event_2(Runtime r) : (call(* Runtime.availableProcessors()) && target(r)) && MOP_CommonPointCut();
	after (Runtime r) : FSM337_event_2(r) {
		MultiSpec_1RuntimeMonitor.FSM337_event_2Event(r);
	}

	pointcut FSM337_event_3(Runtime r) : (call(* Runtime.totalMemory()) && target(r)) && MOP_CommonPointCut();
	after (Runtime r) : FSM337_event_3(r) {
		MultiSpec_1RuntimeMonitor.FSM337_event_3Event(r);
	}

	pointcut FSM337_event_4(Runtime r) : (call(* Runtime.maxMemory()) && target(r)) && MOP_CommonPointCut();
	after (Runtime r) : FSM337_event_4(r) {
		MultiSpec_1RuntimeMonitor.FSM337_event_4Event(r);
	}

	pointcut FSM339_event_1(ClassLoader c, String s) : (call(* ClassLoader.findResource(String)) && target(c) && args(s)) && MOP_CommonPointCut();
	after (ClassLoader c, String s) : FSM339_event_1(c, s) {
		MultiSpec_1RuntimeMonitor.FSM339_event_1Event(c, s);
	}

	pointcut FSM339_event_2(URL u) : (call(* URL.getFile()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM339_event_2(u) {
		//FSM339_event_2
		MultiSpec_1RuntimeMonitor.FSM339_event_2Event(u);
		//FSM73_event_2
		MultiSpec_1RuntimeMonitor.FSM73_event_2Event(u);
	}

	pointcut FSM342_event_1(Map m, Object o) : (call(* Map.containsKey(Object)) && target(m) && args(o)) && MOP_CommonPointCut();
	after (Map m, Object o) : FSM342_event_1(m, o) {
		MultiSpec_1RuntimeMonitor.FSM342_event_1Event(m, o);
	}

	pointcut FSM342_event_2(Dictionary d) : (call(* Dictionary.keys()) && target(d)) && MOP_CommonPointCut();
	after (Dictionary d) : FSM342_event_2(d) {
		MultiSpec_1RuntimeMonitor.FSM342_event_2Event(d);
	}

	pointcut FSM347_event_1(AccessibleObject a) : (call(* AccessibleObject.setAccessible(boolean)) && target(a)) && MOP_CommonPointCut();
	after (AccessibleObject a) : FSM347_event_1(a) {
		MultiSpec_1RuntimeMonitor.FSM347_event_1Event(a);
	}

	pointcut FSM347_event_2(AccessibleObject a) : (call(* AccessibleObject.isAccessible()) && target(a)) && MOP_CommonPointCut();
	after (AccessibleObject a) : FSM347_event_2(a) {
		MultiSpec_1RuntimeMonitor.FSM347_event_2Event(a);
	}

	pointcut FSM348_event_1(ObjectInput o) : (call(* ObjectInput.readShort()) && target(o)) && MOP_CommonPointCut();
	after (ObjectInput o) : FSM348_event_1(o) {
		MultiSpec_1RuntimeMonitor.FSM348_event_1Event(o);
	}

	pointcut FSM348_event_2(ObjectInput o) : (call(* ObjectInput.readUTF()) && target(o)) && MOP_CommonPointCut();
	after (ObjectInput o) : FSM348_event_2(o) {
		MultiSpec_1RuntimeMonitor.FSM348_event_2Event(o);
	}

	pointcut FSM348_event_3(ObjectInput o) : (call(* ObjectInput.readBoolean()) && target(o)) && MOP_CommonPointCut();
	after (ObjectInput o) : FSM348_event_3(o) {
		MultiSpec_1RuntimeMonitor.FSM348_event_3Event(o);
	}

	pointcut FSM348_event_4(ObjectInput o) : (call(* ObjectInput.readObject()) && target(o)) && MOP_CommonPointCut();
	after (ObjectInput o) : FSM348_event_4(o) {
		MultiSpec_1RuntimeMonitor.FSM348_event_4Event(o);
	}

	pointcut FSM349_event_1() : (call(AtomicBoolean.new(boolean))) && MOP_CommonPointCut();
	after () returning (AtomicBoolean a) : FSM349_event_1() {
		MultiSpec_1RuntimeMonitor.FSM349_event_1Event(a);
	}

	pointcut FSM349_event_3(AtomicBoolean a) : (call(* AtomicBoolean.compareAndSet(boolean, boolean)) && target(a)) && MOP_CommonPointCut();
	after (AtomicBoolean a) : FSM349_event_3(a) {
		MultiSpec_1RuntimeMonitor.FSM349_event_3Event(a);
	}

	pointcut FSM349_event_4(AtomicBoolean a) : (call(* AtomicBoolean.set(boolean)) && target(a)) && MOP_CommonPointCut();
	after (AtomicBoolean a) : FSM349_event_4(a) {
		MultiSpec_1RuntimeMonitor.FSM349_event_4Event(a);
	}

	pointcut FSM352_event_1() : (call(Double.new(String))) && MOP_CommonPointCut();
	after () returning (Double d) : FSM352_event_1() {
		MultiSpec_1RuntimeMonitor.FSM352_event_1Event(d);
	}

	pointcut FSM352_event_2(Double d) : (call(* Double.doubleValue()) && target(d)) && MOP_CommonPointCut();
	after (Double d) : FSM352_event_2(d) {
		MultiSpec_1RuntimeMonitor.FSM352_event_2Event(d);
	}

	pointcut FSM358_event_1(Logger l2, Level l1) : (call(* Logger.isLoggable(Level)) && target(l2) && args(l1)) && MOP_CommonPointCut();
	after (Logger l2, Level l1) : FSM358_event_1(l2, l1) {
		MultiSpec_1RuntimeMonitor.FSM358_event_1Event(l2, l1);
	}

	pointcut FSM358_event_2(Logger l2, Level l1, String s) : (call(* Logger.log(Level, String)) && target(l2) && args(l1, s)) && MOP_CommonPointCut();
	after (Logger l2, Level l1, String s) : FSM358_event_2(l2, l1, s) {
		MultiSpec_1RuntimeMonitor.FSM358_event_2Event(l2, l1, s);
	}

	pointcut FSM360_event_1(Map m, Object o) : (call(* Map.remove(Object)) && target(m) && args(o)) && MOP_CommonPointCut();
	after (Map m, Object o) : FSM360_event_1(m, o) {
		MultiSpec_1RuntimeMonitor.FSM360_event_1Event(m, o);
	}

	pointcut FSM363_event_1(JInternalFrame j, String s) : (call(* JInternalFrame.setTitle(String)) && target(j) && args(s)) && MOP_CommonPointCut();
	after (JInternalFrame j, String s) : FSM363_event_1(j, s) {
		//FSM363_event_1
		MultiSpec_1RuntimeMonitor.FSM363_event_1Event(j, s);
		//FSM88_event_1
		MultiSpec_1RuntimeMonitor.FSM88_event_1Event(j, s);
	}

	pointcut FSM369_event_2(Package p) : (call(* Package.getName()) && target(p)) && MOP_CommonPointCut();
	after (Package p) : FSM369_event_2(p) {
		MultiSpec_1RuntimeMonitor.FSM369_event_2Event(p);
	}

	pointcut FSM369_event_3(Class c) : (call(* Class.getPackage()) && target(c)) && MOP_CommonPointCut();
	after (Class c) : FSM369_event_3(c) {
		MultiSpec_1RuntimeMonitor.FSM369_event_3Event(c);
	}

	pointcut FSM371_event_1(Throwable t) : (call(* Throwable.getLocalizedMessage()) && target(t)) && MOP_CommonPointCut();
	after (Throwable t) : FSM371_event_1(t) {
		MultiSpec_1RuntimeMonitor.FSM371_event_1Event(t);
	}

	pointcut FSM371_event_2() : (call(Throwable.new())) && MOP_CommonPointCut();
	after () returning (Throwable t) : FSM371_event_2() {
		MultiSpec_1RuntimeMonitor.FSM371_event_2Event(t);
	}

	pointcut FSM371_event_3() : (call(Throwable.new(String))) && MOP_CommonPointCut();
	after () returning (Throwable t) : FSM371_event_3() {
		MultiSpec_1RuntimeMonitor.FSM371_event_3Event(t);
	}

	pointcut FSM371_event_4(Throwable t) : (call(* Throwable.getStackTrace()) && target(t)) && MOP_CommonPointCut();
	after (Throwable t) : FSM371_event_4(t) {
		MultiSpec_1RuntimeMonitor.FSM371_event_4Event(t);
	}

	pointcut FSM372_event_1(DefaultComboBoxModel d) : (call(* DefaultComboBoxModel.removeAllElements()) && target(d)) && MOP_CommonPointCut();
	after (DefaultComboBoxModel d) : FSM372_event_1(d) {
		MultiSpec_1RuntimeMonitor.FSM372_event_1Event(d);
	}

	pointcut FSM372_event_2() : (call(DefaultComboBoxModel.new())) && MOP_CommonPointCut();
	after () returning (DefaultComboBoxModel d) : FSM372_event_2() {
		MultiSpec_1RuntimeMonitor.FSM372_event_2Event(d);
	}

	pointcut FSM372_event_3(DefaultComboBoxModel d, Object o) : (call(* DefaultComboBoxModel.addElement(Object)) && target(d) && args(o)) && MOP_CommonPointCut();
	after (DefaultComboBoxModel d, Object o) : FSM372_event_3(d, o) {
		MultiSpec_1RuntimeMonitor.FSM372_event_3Event(d, o);
	}

	pointcut FSM377_event_1(ImageIcon i) : (call(* ImageIcon.getImage()) && target(i)) && MOP_CommonPointCut();
	after (ImageIcon i) : FSM377_event_1(i) {
		MultiSpec_1RuntimeMonitor.FSM377_event_1Event(i);
	}

	pointcut FSM377_event_2() : (call(ImageIcon.new(URL))) && MOP_CommonPointCut();
	after () returning (ImageIcon i) : FSM377_event_2() {
		MultiSpec_1RuntimeMonitor.FSM377_event_2Event(i);
	}

	pointcut FSM377_event_3() : (call(ImageIcon.new(String))) && MOP_CommonPointCut();
	after () returning (ImageIcon i) : FSM377_event_3() {
		MultiSpec_1RuntimeMonitor.FSM377_event_3Event(i);
	}

	pointcut FSM45_event_1(TableColumn t) : (call(* TableColumn.getModelIndex()) && target(t)) && MOP_CommonPointCut();
	after (TableColumn t) : FSM45_event_1(t) {
		MultiSpec_1RuntimeMonitor.FSM45_event_1Event(t);
	}

	pointcut FSM45_event_2(TableColumnModel t) : (call(* TableColumnModel.getColumn(int)) && target(t)) && MOP_CommonPointCut();
	after (TableColumnModel t) : FSM45_event_2(t) {
		MultiSpec_1RuntimeMonitor.FSM45_event_2Event(t);
	}

	pointcut FSM53_event_1() : (call(StringTokenizer.new(String, String))) && MOP_CommonPointCut();
	after () returning (StringTokenizer st) : FSM53_event_1() {
		MultiSpec_1RuntimeMonitor.FSM53_event_1Event(st);
	}

	pointcut FSM53_event_2(StringTokenizer st) : (call(* StringTokenizer.nextToken()) && target(st)) && MOP_CommonPointCut();
	after (StringTokenizer st) : FSM53_event_2(st) {
		MultiSpec_1RuntimeMonitor.FSM53_event_2Event(st);
	}

	pointcut FSM53_event_3() : (call(StringTokenizer.new(String, String, boolean))) && MOP_CommonPointCut();
	after () returning (StringTokenizer st) : FSM53_event_3() {
		MultiSpec_1RuntimeMonitor.FSM53_event_3Event(st);
	}

	pointcut FSM53_event_4(StringTokenizer st) : (call(* StringTokenizer.countTokens()) && target(st)) && MOP_CommonPointCut();
	after (StringTokenizer st) : FSM53_event_4(st) {
		MultiSpec_1RuntimeMonitor.FSM53_event_4Event(st);
	}

	pointcut FSM53_event_5(StringTokenizer st) : (call(* StringTokenizer.hasMoreTokens()) && target(st)) && MOP_CommonPointCut();
	after (StringTokenizer st) : FSM53_event_5(st) {
		MultiSpec_1RuntimeMonitor.FSM53_event_5Event(st);
	}

	pointcut FSM58_event_2(Collection c, Object o) : (call(* Collection.add(Object)) && target(c) && args(o)) && MOP_CommonPointCut();
	after (Collection c, Object o) : FSM58_event_2(c, o) {
		MultiSpec_1RuntimeMonitor.FSM58_event_2Event(c, o);
	}

	pointcut FSM60_event_1() : (call(URL.new(String, String, int, String, URLStreamHandler))) && MOP_CommonPointCut();
	after () returning (URL u) : FSM60_event_1() {
		MultiSpec_1RuntimeMonitor.FSM60_event_1Event(u);
	}

	pointcut FSM60_event_2(Closeable c) : (call(* Closeable.close()) && target(c)) && MOP_CommonPointCut();
	after (Closeable c) : FSM60_event_2(c) {
		MultiSpec_1RuntimeMonitor.FSM60_event_2Event(c);
	}

	pointcut FSM62_event_3(ZipEntry z) : (call(* ZipEntry.getName()) && target(z)) && MOP_CommonPointCut();
	after (ZipEntry z) : FSM62_event_3(z) {
		//FSM62_event_3
		MultiSpec_1RuntimeMonitor.FSM62_event_3Event(z);
		//FSM91_event_3
		MultiSpec_1RuntimeMonitor.FSM91_event_3Event(z);
	}

	pointcut FSM63_event_3(Collection c) : (call(* Collection.isEmpty()) && target(c)) && MOP_CommonPointCut();
	after (Collection c) : FSM63_event_3(c) {
		MultiSpec_1RuntimeMonitor.FSM63_event_3Event(c);
	}

	pointcut FSM67_event_1(SortedMap s) : (call(* SortedMap.lastKey()) && target(s)) && MOP_CommonPointCut();
	after (SortedMap s) : FSM67_event_1(s) {
		MultiSpec_1RuntimeMonitor.FSM67_event_1Event(s);
	}

	pointcut FSM67_event_3(SortedMap s, Object o) : (call(* SortedMap.get(Object)) && target(s) && args(o)) && MOP_CommonPointCut();
	after (SortedMap s, Object o) : FSM67_event_3(s, o) {
		MultiSpec_1RuntimeMonitor.FSM67_event_3Event(s, o);
	}

	pointcut FSM68_event_3() : (call(ZipFile.new(File))) && MOP_CommonPointCut();
	after () returning (ZipFile z) : FSM68_event_3() {
		MultiSpec_1RuntimeMonitor.FSM68_event_3Event(z);
	}

	pointcut FSM68_event_4(ZipFile z) : (call(* ZipFile.close()) && target(z)) && MOP_CommonPointCut();
	after (ZipFile z) : FSM68_event_4(z) {
		MultiSpec_1RuntimeMonitor.FSM68_event_4Event(z);
	}

	pointcut FSM68_event_5(ZipFile z) : (call(* ZipFile.entries()) && target(z)) && MOP_CommonPointCut();
	after (ZipFile z) : FSM68_event_5(z) {
		MultiSpec_1RuntimeMonitor.FSM68_event_5Event(z);
	}

	pointcut FSM69_event_2() : (call(ConcurrentHashMap.new(int))) && MOP_CommonPointCut();
	after () returning (ConcurrentHashMap c) : FSM69_event_2() {
		MultiSpec_1RuntimeMonitor.FSM69_event_2Event(c);
	}

	pointcut FSM69_event_3(ConcurrentHashMap c) : (call(* ConcurrentHashMap.keySet()) && target(c)) && MOP_CommonPointCut();
	after (ConcurrentHashMap c) : FSM69_event_3(c) {
		MultiSpec_1RuntimeMonitor.FSM69_event_3Event(c);
	}

	pointcut FSM73_event_1(URL u) : (call(* URL.getHost()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM73_event_1(u) {
		MultiSpec_1RuntimeMonitor.FSM73_event_1Event(u);
	}

	pointcut FSM73_event_3(Document d, Object o, Object o1) : (call(* Document.putProperty(Object, Object)) && target(d) && args(o, o1)) && MOP_CommonPointCut();
	after (Document d, Object o, Object o1) : FSM73_event_3(d, o, o1) {
		MultiSpec_1RuntimeMonitor.FSM73_event_3Event(d, o, o1);
	}

	pointcut FSM73_event_4(URL u) : (call(* URL.openConnection()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM73_event_4(u) {
		MultiSpec_1RuntimeMonitor.FSM73_event_4Event(u);
	}

	pointcut FSM73_event_5(URL u) : (call(* URL.toString()) && target(u)) && MOP_CommonPointCut();
	after (URL u) : FSM73_event_5(u) {
		MultiSpec_1RuntimeMonitor.FSM73_event_5Event(u);
	}

	pointcut FSM73_event_7(Document d, Object o) : (call(* Document.getProperty(Object)) && target(d) && args(o)) && MOP_CommonPointCut();
	after (Document d, Object o) : FSM73_event_7(d, o) {
		MultiSpec_1RuntimeMonitor.FSM73_event_7Event(d, o);
	}

	pointcut FSM78_event_2(DataInput d) : (call(* DataInput.readShort()) && target(d)) && MOP_CommonPointCut();
	after (DataInput d) : FSM78_event_2(d) {
		MultiSpec_1RuntimeMonitor.FSM78_event_2Event(d);
	}

	pointcut FSM78_event_4(DataInput d) : (call(* DataInput.readBoolean()) && target(d)) && MOP_CommonPointCut();
	after (DataInput d) : FSM78_event_4(d) {
		MultiSpec_1RuntimeMonitor.FSM78_event_4Event(d);
	}

	pointcut FSM78_event_5(DataInput d) : (call(* DataInput.readLong()) && target(d)) && MOP_CommonPointCut();
	after (DataInput d) : FSM78_event_5(d) {
		MultiSpec_1RuntimeMonitor.FSM78_event_5Event(d);
	}

	pointcut FSM8_event_1() : (call(Random.new(long))) && MOP_CommonPointCut();
	after () returning (Random r) : FSM8_event_1() {
		MultiSpec_1RuntimeMonitor.FSM8_event_1Event(r);
	}

	pointcut FSM8_event_2() : (call(Random.new())) && MOP_CommonPointCut();
	after () returning (Random r) : FSM8_event_2() {
		MultiSpec_1RuntimeMonitor.FSM8_event_2Event(r);
	}

	pointcut FSM8_event_3(Random r) : (call(* Random.nextInt()) && target(r)) && MOP_CommonPointCut();
	after (Random r) : FSM8_event_3(r) {
		MultiSpec_1RuntimeMonitor.FSM8_event_3Event(r);
	}

	pointcut FSM91_event_1(ZipEntry z) : (call(* ZipEntry.getSize()) && target(z)) && MOP_CommonPointCut();
	after (ZipEntry z) : FSM91_event_1(z) {
		MultiSpec_1RuntimeMonitor.FSM91_event_1Event(z);
	}

	pointcut FSM91_event_2(ZipEntry z) : (call(* ZipEntry.getTime()) && target(z)) && MOP_CommonPointCut();
	after (ZipEntry z) : FSM91_event_2(z) {
		MultiSpec_1RuntimeMonitor.FSM91_event_2Event(z);
	}

	pointcut FSM91_event_4(ZipEntry z) : (call(* ZipEntry.isDirectory()) && target(z)) && MOP_CommonPointCut();
	after (ZipEntry z) : FSM91_event_4(z) {
		MultiSpec_1RuntimeMonitor.FSM91_event_4Event(z);
	}

	pointcut FSM95_event_1(JTextField j) : (call(* JTextField.setColumns(int)) && target(j)) && MOP_CommonPointCut();
	after (JTextField j) : FSM95_event_1(j) {
		MultiSpec_1RuntimeMonitor.FSM95_event_1Event(j);
	}

	pointcut FSM95_event_2() : (call(JTextField.new(String))) && MOP_CommonPointCut();
	after () returning (JTextField j) : FSM95_event_2() {
		MultiSpec_1RuntimeMonitor.FSM95_event_2Event(j);
	}

	pointcut FSM95_event_3(JTextField j) : (call(* JTextField.getText()) && target(j)) && MOP_CommonPointCut();
	after (JTextField j) : FSM95_event_3(j) {
		MultiSpec_1RuntimeMonitor.FSM95_event_3Event(j);
	}

	pointcut FSM97_event_2(AbstractButton a, Icon i) : (call(* AbstractButton.setIcon(Icon)) && target(a) && args(i)) && MOP_CommonPointCut();
	after (AbstractButton a, Icon i) : FSM97_event_2(a, i) {
		MultiSpec_1RuntimeMonitor.FSM97_event_2Event(a, i);
	}

	pointcut FSM97_event_5(AbstractButton a) : (call(* AbstractButton.setSelected(boolean)) && target(a)) && MOP_CommonPointCut();
	after (AbstractButton a) : FSM97_event_5(a) {
		MultiSpec_1RuntimeMonitor.FSM97_event_5Event(a);
	}

	pointcut FSM97_event_6(AbstractButton a, String s) : (call(* AbstractButton.setToolTipText(String)) && target(a) && args(s)) && MOP_CommonPointCut();
	after (AbstractButton a, String s) : FSM97_event_6(a, s) {
		MultiSpec_1RuntimeMonitor.FSM97_event_6Event(a, s);
	}

	pointcut FSM97_event_7(AbstractButton a) : (call(* AbstractButton.setEnabled(boolean)) && target(a)) && MOP_CommonPointCut();
	after (AbstractButton a) : FSM97_event_7(a) {
		MultiSpec_1RuntimeMonitor.FSM97_event_7Event(a);
	}

}
