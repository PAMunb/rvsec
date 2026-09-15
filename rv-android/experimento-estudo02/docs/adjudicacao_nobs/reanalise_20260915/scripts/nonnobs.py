import pandas as pd, re
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
b['nobs']=b.code.str.contains('-NOBS-',na=False)
b['fam']=b.code.str.extract(r'-([A-Z]+)-\d+$')[0]
K=['apk','tool','rep','timeout','class','method','spec']
def parse(msg):
    m=re.search(r"obj=(.*?) val='(.*?)' exp='(.*?)' msg='(.*?)'$", str(msg)); return m.groups() if m else ('','','',str(msg))
nn=b[~b.nobs]
rows=[]
for (s,c,e),h in nn.groupby(['spec','code','event']):
    for (cls,m),hh in h.groupby(['class','method']):
        obj,val,exp,msg=parse(hh.message.iloc[0])
        vals=sorted(set(parse(x)[1] for x in hh.message.unique()))[:5]
        rows.append(dict(spec=s,code=c,event=e,cls=cls,method=m,lines=len(hh),runkeys=hh.drop_duplicates(K).shape[0],apks=hh.apk.nunique(),src=hh.source.value_counts().index[0],vals=vals,exp=exp[:60],msg=msg[:90]))
t=pd.DataFrame(rows).sort_values(['spec','code','runkeys'],ascending=[True,True,False])
pd.set_option('display.width',400); pd.set_option('display.max_colwidth',100); pd.set_option('display.max_rows',500)
t.to_csv(f'{__import__("sys").argv[1]}/nonnobs_sites.csv',index=False)
print(t[['spec','code','event','cls','method','lines','runkeys','apks','src','vals','msg']].to_string())
