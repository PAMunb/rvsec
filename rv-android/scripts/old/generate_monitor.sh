#!/bin/sh

# Script to generate the monitor files

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters!"
    echo "Usage: ./generate_monitor.sh [mop_dir] [mop_out_dir]"
    exit
fi

JAVAMOP_HOME=../javamop
RV_MONITOR_HOME=../rv-monitor

MOP_DIR=$1            # contains de JavaMOP specifications (*.mop)
MOP_OUT_DIR=$2        # where to put the generated artifacts (monitor and aspects)


# Set up output directories, removing old files
rm $MOP_DIR/*.rvm
find $MOP_DIR -name "*Monitor.java" -exec rm -Rvf {} \;
rm -rvf $MOP_OUT_DIR
mkdir -v $MOP_OUT_DIR
cp $MOP_DIR/*.aj $MOP_OUT_DIR

# Use JavaMOP
echo "[+] Executing JavaMOP"
$JAVAMOP_HOME/bin/javamop -d $MOP_OUT_DIR -merge $MOP_DIR/*.mop

# Use RV-Monitor
echo "[+] Executing RV-Monitor"
$RV_MONITOR_HOME/bin/rv-monitor -merge -d $MOP_OUT_DIR $MOP_DIR/*.rvm

# Remove .rvm files 
rm $MOP_DIR/*.rvm

MOP_OUT_DIR_PATH=$(readlink -f $MOP_OUT_DIR)
echo "[+] Done! Monitor generated in $MOP_OUT_DIR_PATH"
