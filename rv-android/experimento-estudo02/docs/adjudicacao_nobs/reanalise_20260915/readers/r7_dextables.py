import re,sys,struct
txt=sys.argv[1]; dex=sys.argv[2]; cls=sys.argv[3]
lines=open(txt,errors='replace').read().split('\n')
s=[i for i,l in enumerate(lines) if "Class descriptor  : 'L"+cls+";'" in l][0]
# find <clinit> after s
i=s
while "name          : '<clinit>'" not in lines[i]: i+=1
fills={}; labels={}; pending=None
j=i
while 'positions' not in lines[j]:
    l=lines[j]
    m=re.search(r'\|([0-9a-f]{4}): fill-array-data v\d+, ([0-9a-f]{8})',l)
    if m: pending=m.group(2)[-4:]
    m2=re.search(r'sput-object v\d+, L[^;]+;\.(Prop_1_transition_\w+):\[I',l)
    if m2: fills[m2.group(1)]=pending
    m3=re.match(r'([0-9a-f]{6}):.*\|([0-9a-f]{4}): array-data',l)
    if m3: labels[m3.group(2)]=int(m3.group(1),16)
    j+=1
data=open(dex,'rb').read()
for name,lab in fills.items():
    off=labels[lab]
    ident,width,size=struct.unpack_from('<HHI',data,off)
    vals=list(struct.unpack_from('<%di'%size,data,off+8))
    print(name,vals)
