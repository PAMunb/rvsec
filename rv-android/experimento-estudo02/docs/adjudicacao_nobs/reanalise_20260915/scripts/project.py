"""Project site verdicts (class,method,spec,code -> category) onto per-run misuse keys.
usage: uv run python project.py verdicts.csv [colname_cls colname_method colname_cat]
Artifact definition (independent of verdicts): ORDER-00 lines of TrustManagerFactorySpec /
KeyManagerFactorySpec / SecureRandomSpec whose double-fire trigger (ORDER-00 on event g2) is visible
in the same per-run key, in another method of the same run and spec (g2 fired in a constructor or
helper), or at the same site in other runs (record lost from logcat)."""
import pandas as pd, sys
v=pd.read_csv(sys.argv[1]); c_cls,c_m,c_cat=(sys.argv[2:5] if len(sys.argv)>4 else ('cls','method','category'))
v=v.rename(columns={c_cls:'class',c_m:'method',c_cat:'category'})[['class','method','spec','code','category']].drop_duplicates()
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
b['nobs']=b.code.str.contains('-NOBS-',na=False)
K=['apk','tool','rep','timeout','class','method','spec']
b['kid']=b.groupby(K).ngroup()
ord3=b.spec.isin(['TrustManagerFactorySpec','KeyManagerFactorySpec','SecureRandomSpec'])&b.code.str.contains('-ORDER-',na=False)
g2=ord3&(b.event=='g2')
b['rid']=b.groupby(['apk','tool','rep','timeout','spec']).ngroup()
site=b[['class','method','spec']].apply(tuple,axis=1)
b['art']=ord3&(b.kid.isin(set(b[g2].kid))|b.rid.isin(set(b[g2].rid))|site.isin(set(site[g2])))
b['other']=~b.nobs&~b.art
b=b.merge(v,on=['class','method','spec','code'],how='left')
rank={'MISUSE':6,'WEAVER_GAP':5,'SPEC_DEFECT':4,'WEAVER_ARTIFACT':3,'RULE_DECISION':2,'LEGIT_UNOBSERVABLE':1,'UNDETERMINED':0}
b['r']=b.category.map(rank)
g=b.groupby('kid').agg(nobs=('nobs','any'),art=('art','any'),other=('other','any'),r=('r','max'),tool=('tool','first'),timeout=('timeout','first'),apk=('apk','first'))
inv={v:k for k,v in rank.items()}
def status(row):
    if row.other: return 'sustained_other'
    if row.nobs: return 'NOBS:'+inv.get(row.r,'UNCLASSIFIED')
    return 'only_artifact'
g['status']=g.apply(status,axis=1)
print(g.status.value_counts().to_string()); print('total',len(g))
print('unclassified NOBS lines:', int((b.nobs&b.category.isna()).sum()))
g['sustained']=g.status.isin(['sustained_other','NOBS:MISUSE'])
print('sustained',int(g.sustained.sum()), round(g.sustained.mean(),3))
print(g.groupby('tool').sustained.mean().round(3).to_string()); print(g.groupby('timeout').sustained.mean().round(3).to_string())
print('apks with keys',g.apk.nunique(),'apks with sustained',g[g.sustained].apk.nunique())
g.to_csv(sys.argv[1].replace('.csv','_keys.csv'))
