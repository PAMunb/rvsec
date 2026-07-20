# RVSec

[![CI Pipeline](https://github.com/PAMunb/rvsec/actions/workflows/ci.yml/badge.svg?branch=modules)](https://github.com/PAMunb/rvsec/actions/workflows/ci.yml)

RVSec implements a runtime verification infrastructure 
for identifying crypto API misuses via dynamic analyses. 
The main components in this repository are:

   * rvsec: Contains JavaMOP specifications and suites of tests
   * rv-android: A port of rv-sec for android. 
   * mop-maven-plugin: A maven plugin for automating the build process
   * javamop: A fork of the JavaMOP implementation
   * rv-monitor: A fork of the RV Monitor implementation

## Requirements

   * JDK 21+: install the Java Development Kit (the reference dev/Docker environment uses JDK 25; bytecode target is 21)
   * AspectJ 1.9.25.1: install AspectJ and set the ASPECTJ_HOME variable
   * Maven: install Maven to build rvsec
   * For rv-android: Python >= 3.12 and uv; the Android SDK (emulator + platform-tools) with ANDROID_HOME set; RVSEC_HOME set to the RVSEC workspace root
   
## Building RVSec (Java)

   * Build the RVSec agent
   
```
$ cd rvsec && source ./config.sh          # sets CLASSPATH (needs ASPECTJ_HOME)
$ cd .. && mvn clean install -DskipTests -DskipMopAgent
$ cd rvsec/rvsec-agent && mvn test        # builds + exercises the JSE agent
```

Executing the above commands generates the RVSec agent and executes the 
test suite. The final output should looks like: 

```
[INFO] Tests run: 209, Failures: 0, Errors: 0, Skipped: 0
[INFO] 
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  01:25 min
[INFO] Finished at: 2023-06-05T11:16:21-03:00
[INFO] ------------------------------------------------------------------------
```

## Building and running rv-android

Build all rv-android modules (editable) into a shared virtual environment, then run one
simple execution over the bundled example APK (`rv-android/apks_examples/cryptoapp.apk`):

```
$ cd rv-android && uv sync
$ uv run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeouts 300
```

## MOP specifications 

The MOP specifications for JSE (Java Standard Edition) are available [here](https://github.com/PAMunb/rvsec/tree/master/rvsec/rvsec-agent/src/main/mop). 

## Test Suite

We strongly recommend you to browse our test suite. It contains several test cases 
initially designed to test CogniCrypt and that we port to test RVSEC. 
The test suite is available [here](https://github.com/PAMunb/rvsec/tree/master/rvsec/rvsec-agent/src/test/java/br/unb/cic/mop/bench01). It also serves a good start point for understanding our 
specifications. 

   
