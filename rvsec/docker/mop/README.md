# MoniTests


   * Create the docker image

```{shell}
$ ./build.sh
```

   * Execute

```{shell}
$ docker run -it --rm -v <PATH_TO_MOP_FILES>:/projects/mop -v <OUTPUT_DIR>:/projects/output pamunb/mop:0.0.1
```

   * Example

```{shell}
$ docker run -it --rm -v $(pwd)/example:/projects/mop -v $(pwd):/projects/output --name test-mop pamunb/mop:0.0.1
```