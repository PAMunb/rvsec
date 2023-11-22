#!/bin/sh

# WARNING: This script removes several directories(, including results). Please check before using

OUT_DIR="out"            # out dir (for instrumented apk)
LIB_TMP="lib_tmp"        # libs dir (maven dependencies)
MOP_OUT="mop_out"
TMP_DIR="tmp"
RVM_TMP_DIR="rvm_tmp"
RESULTS_DIR="results"

echo "[+] Cleaning ..."
rm -rf __pycache__ $TMP_DIR $RVM_TMP_DIR $LIB_TMP $OUT_DIR $MOP_OUT #$RESULTS_DIR
rm -v *.dex
rm ajcore*.txt
