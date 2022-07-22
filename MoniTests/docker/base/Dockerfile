FROM maven:3.8.4-jdk-8-slim

ENV MAVEN_REPO "/root/.m2/repository"
ENV JAVAMOP_HOME "/projects/javamop"
ENV ASPECTJ_HOME "/projects/aspectj"	
ENV RV_MONITOR_HOME "/projects/rv-monitor/target/release/rv-monitor"
ENV PATH "${RV_MONITOR_HOME}/bin:${ASPECTJ_HOME}/bin:${JAVAMOP_HOME}/bin:${PATH}"	

WORKDIR /projects

RUN DEBIAN_FRONTEND="noninteractive" apt-get update && \
    apt-get install -q -y --no-install-recommends git && \
	apt-get clean && apt-get --purge -y autoremove && \
	rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
	
RUN git clone https://github.com/PAMunb/rv-monitor.git && \
    cd rv-monitor && \
    git checkout statistics-1.4 && \
	mvn clean install -DskipTests && \
	cd ..
COPY rv-monitor /projects/rv-monitor/target/release/rv-monitor/bin/
RUN chmod +x /projects/rv-monitor/target/release/rv-monitor/bin/rv-monitor

COPY aspectj-1.8.14.jar /projects
RUN mkdir aspectj && \
	java -jar aspectj-1.8.14.jar -to /projects/aspectj && \
	rm /projects/aspectj-1.8.14.jar
		
RUN git clone https://github.com/PAMunb/javamop.git && \
    cd javamop && \
    git checkout statistics-4.0 && \
	mvn clean install -DskipTests && \
	cd ..		
