import pandas as pd
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
b['nobs']=b.code.str.contains('-NOBS-',na=False)
b['fam']=b.code.str.extract(r'-([A-Z]+)-\d+$')[0]
K=['apk','tool','rep','timeout','class','method','spec']
b['kid']=b.groupby(K).ngroup()
# artifact A: TMF/KMF ORDER-00 all events; SR ORDER-00 only on g2 (variant B adds next2)
tk=b.spec.isin(['TrustManagerFactorySpec','KeyManagerFactorySpec'])&(b.fam=='ORDER')
sr=(b.spec=='SecureRandomSpec')&(b.fam=='ORDER')
for name,srset in [('A: SR g2 only',{'g2'}),('B: SR g2+next2',{'g2','next2'})]:
    art=tk|(sr&b.event.isin(srset))
    other=~b.nobs&~art
    g=b.assign(art=art,other=other).groupby('kid').agg(nobs=('nobs','any'),art=('art','any'),other=('other','any'))
    print(name,'| keys',len(g),'| sustained by other',int(g.other.sum()),'| NOBS-decided (no other)',int((g.nobs&~g.other).sum()),'| only artifact',int((~g.nobs&~g.other).sum()),'| art lines',int(art.sum()))
# lines that are ORDER-00 in keys that also have ALG/KEYSIZE/CONSTR in same spec (cascade of a value failure)
val=b.fam.isin(['ALG','KEYSIZE','CONSTR','PROTO','FORB'])
kv=set(b[val].kid)
casc=b[(b.fam=='ORDER')&b.kid.isin(kv)&~tk&~sr]
print('ORDER lines in keys with a value failure (same key):',len(casc)); print(casc.groupby('spec').size())
ordo=b[(b.fam=='ORDER')&~b.kid.isin(kv)&~tk&~sr]
print('ORDER lines in keys WITHOUT value failure:',len(ordo)); print(ordo.groupby(['spec','event']).size())
print('per-run keys with only ORDER (no value fail, not TMF/KMF/SR) :', ordo.kid.nunique(), ordo.drop_duplicates('kid').groupby('spec').size().to_dict())
# lines per family overall
print(b.fam.value_counts())
print('TMF/KMF ORDER lines',int(tk.sum()),'SR ORDER lines by event',b[sr].groupby('event').size().to_dict())
