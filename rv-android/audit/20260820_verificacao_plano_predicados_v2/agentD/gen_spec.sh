#!/bin/bash
NAME=$1; TYPE=$2
cat <<SPEC
package mop;

import java.io.*;
import java.util.*;

T(Object a, ${TYPE} b, Object c) {
	event e1 before(Object a, ${TYPE} b) :
		call(* OutputStream+.write(..)) && target(a) && args(b) {
	}
	event e2 before(Object a, Object c) :
		call(* Map+.put(..)) && target(a) && args(c, ..) {
	}

	ere : e1 e2

	@match {
		System.out.println("matched");
	}
}
SPEC
