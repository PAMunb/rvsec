# RVSec

RVSec implements a runtime verification infrastructure 
for identifying crypto API misuses via dynamic analyses. 
The main components in this repository are:

   * rvsec: Contains JavaMOP specifications and suites of tests
   * rv-android: A port of rv-sec for android. 
   * mop-maven-plugin: A maven plugin for automating the build process
   * javamop: A fork of the JavaMOP implementation
   * rv-monitor: A fork of the RV Monitor implementation

## Requirements

   * JDK: it is necessary to install the Java Development Kit (tested with Java 11) 
   * AspectJ: it is necessary to install AspectJ and set the ASPECTJ_HOME variable
   * Maven: it is necessary to install maven in order to build rvsec
   
## Building RVSec (Java)

   * Build the RVSec agent
   
```
$ ./configure.sh
$ mvn clean install -DskipTests
$ cd rvsec/rvsec-agent
$ mvn test
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

## MOP specifications 

The MOP specifications for JSE (Java Standard Edition) are available [here](https://github.com/PAMunb/rvsec/tree/master/rvsec/rvsec-agent/src/main/mop). 

## Test Suite

We strongly recommend you to browse our test suite. It contains several test cases 
initially designed to test CogniCrypt and that we port to test RVSEC. 
The test suite is available [here](https://github.com/PAMunb/rvsec/tree/master/rvsec/rvsec-agent/src/test/java/br/unb/cic/mop/bench01). It also serves a good start point for understanding our 
specifications. 

   
