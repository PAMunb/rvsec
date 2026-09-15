#!/bin/bash
# One instrumented APK: every call of getEncoded()[B on a key-typed owner outside the mop/ package,
# classified as woven inline (Event within 3 instructions), woven via MonitorWrappers, or unwoven.
apk="$1"; DD="$2"; tmp=$(mktemp -d); unzip -q -o "$apk" 'classes*.dex' -d "$tmp"
for d in "$tmp"/classes*.dex; do "$DD" -d "$d" 2>/dev/null; done | awk -v apk="$(basename "$apk")" '
  /Class descriptor/ { inmop = ($0 ~ /\x27Lmop\//) ; next }
  inmop { next }
  /invoke-static.*Lmop\/MonitorWrappers;\.[A-Za-z_]*_getEncoded:/ { match($0, /MonitorWrappers;\.[A-Za-z_]*_getEncoded/); print apk, substr($0,RSTART+17,RLENGTH-17), "WRAPPER"; next }
  /invoke-(interface|virtual).*\.getEncoded:\(\)\[B/ { match($0, /L[^;]*;\.getEncoded/); cur=substr($0,RSTART,RLENGTH-11); pend=3; next }
  pend>0 { if ($0 ~ /Event:/) { print apk, cur, "INLINE"; pend=0; next } pend--; if (pend==0) print apk, cur, "none" }'
rm -rf "$tmp"
