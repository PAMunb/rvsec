# MoniTests

This project aims to apply JavaMop, a Java implementation of Monitoring-Oriented Programming, to verify the correct usage of cryptographic libraries
## Status 

   * [x] Cipher
   * [x] HMACParameterSpec
   * [x] Mac
   * [x] MessageDigest
   * [x] KeyGenerator
   * [x] KeyManagerFactory
   * [x] KeyStore 
   * [x] KeyPair
   * [x] KeyPairGenerator
   * [x] SecretKey
   * [x] SecretKeySpec
   * [x] SecureRandom
   * [x] Signature
   * [x] SSLContext
   * [x] TrustManagerFactory

## Configuration

   * Install AspectJ locally

```
$ 
```
   * create a directory to hold the projects

```{shell}
$ mkdir projects
$ cd projects
```

   * clone and build the rv-monitor and java-mop projects
   
```{shell}
$ git clone https://github.com/PAMunb/rv-monitor.git
$ cd rv-monitor
$ git checkout statistics-1.4
$ mvn clean install -DskipTests
$ cd ..

$ git clone https://github.com/PAMunb/javamop.git
$ cd javamop
$ git checkout statistics-4.0
$ mvn clean install
$ cd ..
````

   * clone the maven plugin and build it

```{shell}
$ git clone https://github.com/PAMunb/mop-maven-plugin.git
$ cd mop-maven-plugin
$ mvn clean install
```

   * clone this repository and execute the test cases

```{shell}
$ mvn test
```

   * setup the classpath

```{shell}
$ source ./config.sh		  
```
