import pandas as pd, re
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
b['nobs']=b.code.str.contains('-NOBS-',na=False)
b['fam']=b.code.str.extract(r'-([A-Z]+)-\d+$')[0]
K=['apk','tool','rep','timeout','class','method','spec']
# per-run key: set of (spec,code,event)
g=b.groupby(K)
n_keys=g.ngroups
allnobs=g.nobs.all()
print('keys',n_keys,'nobs-only',int(allnobs.sum()))
# artifact hypothesis: ORDER-00 in TMF/KMF/SR specs
art=b.spec.isin(['TrustManagerFactorySpec','KeyManagerFactorySpec','SecureRandomSpec']) & (b.fam=='ORDER')
b['art']=art
b['other']=~b.nobs & ~b.art
o=g.other.any(); a=g.art.any(); nn=g.nobs.any()
print('sustained by non-NOBS non-artifact', int(o.sum()))
print('has NOBS & no other', int((nn & ~o).sum()))
print('only artifact (no NOBS, no other)', int((~nn & ~o & a).sum()))
print('no NOBS, has other', int((~nn & o).sum()), ' NOBS & other', int((nn&o).sum()))
# which specs/codes sustain the 'other' keys
oo=b[b.other]
print(oo.groupby(K).ngroups, 'keys with other codes; by spec:')
print(oo.drop_duplicates(K+['spec']).groupby('spec').size().sort_values(ascending=False).head(15))
# per (spec,code,event): number of per-run keys, distinct (class,method), distinct apks
t=oo.groupby(['spec','code','event']).agg(keys=('apk', lambda x: 0), lines=('code','size'), sites=('class', lambda x: 0)).reset_index()
rows=[]
for (s,c,e),h in oo.groupby(['spec','code','event']):
    rows.append((s,c,e,len(h),h.drop_duplicates(K).shape[0],h.drop_duplicates(['class','method']).shape[0],h.apk.nunique()))
t=pd.DataFrame(rows,columns=['spec','code','event','lines','runkeys','methods','apks']).sort_values('runkeys',ascending=False)
pd.set_option('display.width',300)
print(t.to_string())
# per-tool / per-budget: fraction of keys that have 'other'
kk=pd.DataFrame({'other':o,'art':a,'nobs':nn}).reset_index()
print(kk.groupby('tool').other.mean().round(3))
print(kk.groupby('timeout').other.mean().round(3))
print('apks with any key', kk.apk.nunique(), 'apks with an other-sustained key', kk[kk.other].apk.nunique())
