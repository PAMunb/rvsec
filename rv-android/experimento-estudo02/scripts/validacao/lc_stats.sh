#!/bin/bash
# One pass per logcat (threadtime format). Emits one TSV row:
# file lines cov rvsec headers_mid chatty fatal anr died maxgap_ms inversions maxinv_ms midnight first_ts last_ts
f="$1"
/usr/bin/awk -v F="$f" '
function tsms(s,  m,d,h,mi,se,ms) {
  # s = "MM-DD HH:MM:SS.mmm"
  m=substr(s,1,2)+0; d=substr(s,4,2)+0; h=substr(s,7,2)+0; mi=substr(s,10,2)+0; se=substr(s,13,2)+0; ms=substr(s,16,3)+0
  return ((((m*31+d)*24+h)*60+mi)*60+se)*1000+ms
}
BEGIN{lines=0;cov=0;rv=0;hdr=0;hdrmid=0;chatty=0;fatal=0;anr=0;died=0;maxgap=0;inv=0;maxinv=0;mid=0;prev=-1;first="";last="";seen=0}
{
  lines++
  if ($0 ~ /^--------- beginning of /) { hdr++; if (seen) hdrmid++; next }
  if ($0 ~ /^[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9] /) {
    seen=1
    t=tsms(substr($0,1,18))
    if (first=="") first=substr($0,1,18)
    last=substr($0,1,18)
    if (prev>=0) { g=t-prev; if (g>maxgap) maxgap=g; if (g<0) { inv++; if (-g>maxinv) maxinv=-g; if (-g>3600000) mid++ } }
    prev=t
  }
  if (index($0,"RVSEC-COV")) cov++
  else if (index($0,"RVSEC")) { if ($0 ~ /RVSEC[ \t]*:/) rv++ }
  if (index($0,"chatty")) chatty++
  if (index($0,"FATAL EXCEPTION")) fatal++
  if (index($0,"ANR in ")) anr++
  if (index($0,"has died")) died++
}
END{printf "%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n",F,lines,cov,rv,hdr,hdrmid,chatty,fatal,anr,died,maxgap,inv,maxinv,mid,first,last}
' "$f"
