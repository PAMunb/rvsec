#!/bin/sh

# WARNING: This script removes several directories, including results. Please check before using

OUT_DIR="out"            # out dir (for instrumented apk)
LIB_TMP="lib_tmp"        # libs dir (maven dependencies)
TMP_DIR="tmp"
RVM_TMP_DIR="rvm_tmp"
RESULTS_DIR="results"

echo "[+] Cleaning ..."
rm -rf $TMP_DIR $RVM_TMP_DIR $LIB_TMP $OUT_DIR #$RESULTS_DIR
rm -v *.dex
rm ajcore*.txt
