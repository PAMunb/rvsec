#!/bin/bash
# inversions restricted to the app's own RVSEC/RVSEC-COV lines (same emitter), plus per-pid check
f="$1"
/usr/bin/awk -v F="$f" '
function tsms(s){return (((( (substr(s,1,2)+0)*31+substr(s,4,2)+0)*24+substr(s,7,2)+0)*60+substr(s,10,2)+0)*60+substr(s,13,2)+0)*1000+substr(s,16,3)+0}
BEGIN{inv=0;maxinv=0;prev=-1;pinv=0}
/RVSEC/ && /^[0-9][0-9]-[0-9][0-9] / {
  t=tsms(substr($0,1,18)); pid=$3
  if (prev>=0 && t<prev) { inv++; if (prev-t>maxinv) maxinv=prev-t }
  if ((pid in pp) && t<pp[pid]) pinv++
  prev=t; pp[pid]=t
}
END{printf "%s\t%d\t%d\t%d\n",F,inv,maxinv,pinv}' "$f"
