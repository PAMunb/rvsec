#!/bin/bash
# Richer scan (scratch only): every getEncoded()[B call outside mop/, with the containing
# class + method, the declared owner, and the exact classification evidence:
#   WRAPPER:<wrapperName>          invoke-static to Lmop/MonitorWrappers;.*_getEncoded
#   INLINE:<EventName>             a MultiSpec_1RuntimeMonitor;.<X>Event within the next 3 instrs
#   none                           neither
apk="$1"; DD="$2"; tmp=$(mktemp -d); unzip -q -o "$apk" 'classes*.dex' -d "$tmp"
for d in "$tmp"/classes*.dex; do "$DD" -d "$d" 2>/dev/null; done | awk -v apk="$(basename "$apk")" '
  /Class descriptor/ { match($0, /\x27[^\x27]*\x27/); cls=substr($0,RSTART+1,RLENGTH-2); inmop = (cls ~ /^Lmop\//); next }
  inmop { next }
  /^ *name *: \x27/ { match($0, /\x27[^\x27]*\x27/); meth=substr($0,RSTART+1,RLENGTH-2); next }
  pend>0 { pend--;
           if ($0 ~ /invoke-static.*Lmop\/MonitorWrappers;\./) { pend=0 }  # a different, wrapped call; stop
           else if ($0 ~ /MultiSpec_1RuntimeMonitor;\.[A-Za-z0-9_]*Event/) { match($0, /MultiSpec_1RuntimeMonitor;\.[A-Za-z0-9_]*Event/); ev=substr($0,RSTART+25,RLENGTH-25); print apk, cls, meth, cur, "INLINE:" ev; pend=0; next }
           if (pend==0) print apk, cls, meth, cur, "none" }
  /invoke-static.*Lmop\/MonitorWrappers;\.[A-Za-z_]*_getEncoded:/ { match($0, /MonitorWrappers;\.[A-Za-z_]*_getEncoded/); print apk, cls, meth, "(wrapped)", "WRAPPER:" substr($0,RSTART+17,RLENGTH-17); next }
  /invoke-(interface|virtual|super|direct)(\/range)?.*\.getEncoded:\(\)\[B/ { match($0, /L[^;]*;\.getEncoded/); cur=substr($0,RSTART,RLENGTH-11); pend=3; next }'
rm -rf "$tmp"
