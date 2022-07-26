#!/bin/bash

#docker run -it --rm --name test-mop pamunb/mop:0.0.1 /bin/bash
#docker run -it --rm -v $(pwd)/example:/projects/mop -v $(pwd):/projects/output --name test-mop pamunb/mop:0.0.1 /bin/bash
docker run -it --rm -v $(pwd)/example:/projects/mop -v $(pwd):/projects/output --name test-mop pamunb/mop:0.0.1
