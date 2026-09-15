import pandas as pd, sys
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
print('lines', len(b))
b['nobs']=b.code.str.contains('-NOBS-',na=False)
n=b[b.nobs]
print('NOBS lines', len(n))
print('points', n.drop_duplicates(['apk','class','method','spec','code']).shape[0])
print('sites', n.drop_duplicates(['class','method','spec','code']).shape[0])
print('methods', n.drop_duplicates(['class','method']).shape[0])
K=['apk','tool','rep','timeout','class','method','spec']
g=b.groupby(K).nobs.all()
print('per-run misuses', len(g), 'NOBS-only', int(g.sum()))
# code families
b['fam']=b.code.str.extract(r'-([A-Z]+)-\d+$')
print(b.fam.value_counts())
print(b[~b.nobs].groupby(['spec','code','event']).size().sort_values(ascending=False).head(40).to_string())
# sites table
s=n.groupby(['class','method','spec','code']).agg(lines=('code','size'), apks=('apk','nunique'), src=('source', lambda x: x.value_counts().index[0]), ev=('event', lambda x: x.value_counts().index[0]), msg=('message', lambda x: x.iloc[0])).reset_index()
s.to_csv(sys.argv[1]+'/sites.csv', index=False)
m=n.groupby(['class','method']).agg(lines=('code','size'), apks=('apk','nunique'), specs=('spec', lambda x: ','.join(sorted(set(x)))), codes=('code', lambda x: ','.join(sorted(set(x)))), src=('source', lambda x: x.value_counts().index[0]), apklist=('apk', lambda x: ','.join(sorted(set(x))[:6]))).reset_index().sort_values('lines', ascending=False)
m.to_csv(sys.argv[1]+'/methods.csv', index=False)
print(m.head(40).to_string())
