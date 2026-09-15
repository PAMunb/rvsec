import pandas as pd, glob, sys
SP=sys.argv[1]
v=pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f'{SP}/my_verdicts_L*.csv'))])
v=v.rename(columns={'cls':'class'})
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
n=b[b.code.str.contains('-NOBS-',na=False)]
sites=n.drop_duplicates(['class','method','spec','code'])[['class','method','spec','code']]
m=sites.merge(v,on=['class','method','spec','code'],how='left',indicator=True)
print('sites',len(sites),'covered',(m._merge=='both').sum())
print('MISSING:'); print(m[m._merge=='left_only'][['class','method','spec','code']].to_string())
extra=v.merge(sites,on=['class','method','spec','code'],how='left',indicator=True); print('extra verdict rows not in census:',(extra._merge=='left_only').sum()); print(extra[extra._merge=='left_only'][['class','method','spec','code']].to_string())
v.to_csv(f'{SP}/my_verdicts_all.csv',index=False)
# diff vs first pass
fp=pd.read_csv('experimento-estudo02/docs/adjudicacao_nobs/vereditos.csv').rename(columns={'cls':'class'})
d=v.merge(fp[['class','method','spec','code','category','mechanism','confidence']],on=['class','method','spec','code'],how='outer',suffixes=('_mine','_fp'),indicator=True)
print('\nfirst-pass rows',len(fp),'merged',len(d),'unmatched',(d._merge!='both').sum())
dd=d[(d.category_mine!=d.category_fp)]
pd.set_option('display.width',300); pd.set_option('display.max_colwidth',60)
print('\nDISAGREEMENTS',len(dd)); print(dd[['class','method','code','category_mine','category_fp','mechanism_mine','mechanism_fp']].to_string())
