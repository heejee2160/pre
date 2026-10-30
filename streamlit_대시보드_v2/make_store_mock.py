"""가상 점포 집계 (인허가 행정동×분기 집계가 나오면 같은 컬럼으로 교체)."""
import numpy as np, pandas as pd
rng=np.random.default_rng(11)
pr=pd.read_csv('data/pred_dong_month.csv',dtype={'행정동코드':str})
last=pr[pr.기준월==pr.기준월.max()][['행정동코드','영업점포수','폐업위험률']]
qs=['2024Q3','2024Q4','2025Q1','2025Q2','2025Q3','2025Q4','2026Q1','2026Q2']
rows=[]
for _,r in last.iterrows():
    n=int(r.영업점포수); risk=r.폐업위험률 if r.폐업위험률==r.폐업위험률 else 6.5
    for i,q in enumerate(qs):
        clo=max(0,int(rng.poisson(n*risk/100/2*(0.75+0.07*i))))
        op=max(0,int(rng.poisson(n*0.03)))
        rows.append((q,r.행정동코드,op,clo,int(clo*rng.uniform(0.2,0.45)),n))
pd.DataFrame(rows,columns=['기준분기','행정동코드','개업','폐업','폐업_1년미만','영업점포수']).to_csv('data/stores_dong_quarter.csv',index=False,encoding='utf-8-sig')
print(len(rows))
