"""앱에 들어갈 데이터 파일을 만든다.
- 실측(real): 카드 소비·생활인구 전년비, 보증(구·군×업종)  -> 팀 전처리 파일에서 계산
- 예측(mock): 폐업위험률·SHAP 요인 -> 모델 결과가 나오면 같은 컬럼으로 교체
"""
import json, numpy as np, pandas as pd
rng=np.random.default_rng(7)
# 1) 행정동 경계 (205개, 신호동->녹산동 합산)
g=json.load(open('/home/claude/geo/admdongkor/ver20261001/HangJeongDong_ver20261001.geojson'))
feats=[]
for f in g['features']:
    p=f['properties']
    if p['sidonm']!='부산광역시': continue
    code=p['adm_cd2'][:10]; name=p['adm_nm'].split()[-1]; gu=p['sggnm']
    if code=='2644059000': code,name='2644056000','녹산동'
    gm=f['geometry']; polys=gm['coordinates'] if gm['type']=='MultiPolygon' else [gm['coordinates']]
    # 좌표 간소화(소수 4자리, 3점마다 1개)로 용량 축소
    polys=[[ [ [round(x,4),round(y,4)] for x,y in ring[::2]]+[ [round(ring[0][0],4),round(ring[0][1],4)] ] for ring in poly] for poly in polys]
    ex=[x for x in feats if x['id']==code]
    if ex: ex[0]['geometry']['coordinates']+=polys; continue
    feats.append({'type':'Feature','id':code,'properties':{'행정동코드':code,'구군':gu,'읍면동':name},'geometry':{'type':'MultiPolygon','coordinates':polys}})
json.dump({'type':'FeatureCollection','features':feats},open('data/busan_dong.geojson','w'),ensure_ascii=False)
dongs=pd.DataFrame([f['properties'] for f in feats]); print('dongs',len(dongs))

# 2) 실측 신호 (카드·생활인구) — 실제 값
c=pd.read_csv('/home/claude/sg/data/card.csv',dtype={'행정동코드':str})
p=pd.read_csv('/home/claude/sg/data/pop.csv',dtype={'행정동코드':str})
tot=c.groupby(['행정동코드','기준월']).평균금액.sum().rename('카드소비').reset_index()
food=c[c.카드업종=='음식/주점'].groupby(['행정동코드','기준월']).평균금액.sum().rename('음식주점소비').reset_index()
s=tot.merge(food,on=['행정동코드','기준월']).merge(p[['행정동코드','기준월','방문인구_월','직장인구_월','거주인구_월']],on=['행정동코드','기준월'],how='left')
s=s.sort_values(['행정동코드','기준월'])
for col,new in [('카드소비','카드소비_전년비'),('음식주점소비','음식주점소비_전년비'),('방문인구_월','방문인구_전년비'),('직장인구_월','직장인구_전년비')]:
    s[new]=(s.groupby('행정동코드')[col].pct_change(12)*100).round(1)
s.to_csv('data/signals_dong_month.csv',index=False,encoding='utf-8-sig')
cind=c.copy(); cind=cind.sort_values(['행정동코드','카드업종','기준월'])
cind['소비_전년비']=(cind.groupby(['행정동코드','카드업종']).평균금액.pct_change(12)*100).round(1)
cind[['기준월','행정동코드','카드업종','평균금액','평균건수','소비_전년비']].to_csv('data/card_dong_industry_month.csv',index=False,encoding='utf-8-sig')

# 3) 보증 — 실제 값 (구·군 × 표준산업 대분류)
b=pd.read_excel('/mnt/user-data/attachments/f14f9ab8-347b-586e-ba8d-f1b2192aa217/bf603c99-25_4__.xlsx',header=2)
b.columns=['시도','구군','업종대분류','신규보증금액','신규보증업체수','보증잔액','사고건수','사고금액']
b[['시도','구군']]=b[['시도','구군']].ffill(); b=b[b.시도=='부산'].drop(columns='시도')
b.to_csv('data/guarantee_gu_industry.csv',index=False,encoding='utf-8-sig')

# 4) 예측 — 가상 (모델 결과로 교체할 자리)
months=sorted(s.기준월.unique()); months=[m for m in months if m>=202501]
gu_eff={'부산진구':1.15,'해운대구':1.1,'사하구':1.08,'중구':1.12,'동구':1.05,'금정구':1.0,'수영구':1.02,'강서구':0.85,'기장군':0.88}
rows=[]
base=dongs.assign(b=lambda d:d.구군.map(gu_eff).fillna(0.97)*rng.normal(6.9,1.1,len(d)).clip(3.5,12))
for i,m in enumerate(months):
    for _,r in base.iterrows():
        v=max(2.0,r.b+rng.normal(0,0.25)+0.02*i*(1 if r.b>7.5 else -0.5))
        n=int(rng.integers(60,900))
        rows.append((m,r.행정동코드,r.구군,r.읍면동,round(v,1),n,round(n*v/100)))
pr=pd.DataFrame(rows,columns=['기준월','행정동코드','구군','읍면동','폐업위험률','영업점포수','예상폐업점포'])
pr.loc[pr.영업점포수<80,'폐업위험률']=np.nan   # 30곳 미만 판단 보류 흉내 (가상)
pr.to_csv('data/pred_dong_month.csv',index=False,encoding='utf-8-sig')
inds=['음식/주점','음식료품','유통','미용','의료','교육','생활','여가/문화','여행/숙박','의류/잡화','자동차']
last=pr[pr.기준월==months[-1]]
ri=[(months[-1],r.행정동코드,k,round(max(1.5,(r.폐업위험률 if r.폐업위험률==r.폐업위험률 else 6)+rng.normal(0,1.6)),1),int(rng.integers(3,120))) for _,r in last.iterrows() for k in inds]
pd.DataFrame(ri,columns=['기준월','행정동코드','카드업종','폐업위험률','영업점포수']).to_csv('data/pred_dong_industry.csv',index=False,encoding='utf-8-sig')
facs=[('카드소비_감소','카드 소비가 전년 같은 달보다 줄었습니다'),('업종폐업률','같은 업종의 최근 12개월 폐업률이 높습니다'),('저녁방문_감소','저녁 시간 방문인구가 줄었습니다'),('신규개업_과다','최근 6개월 개업이 폐업보다 빠르게 늘었습니다'),('업력_짧음','1년 미만 점포 비중이 높습니다'),('업력_김','오래 영업한 점포가 많습니다')]
sh=[]
for _,r in last.iterrows():
    pick=rng.choice(5,3,replace=False); w=sorted(rng.uniform(0.2,1,3),reverse=True)
    for k,(j,v) in enumerate(zip(pick,w)): sh.append((months[-1],r.행정동코드,k+1,facs[j][0],facs[j][1],round(v,2),'상승'))
    sh.append((months[-1],r.행정동코드,4,facs[5][0],facs[5][1],round(-rng.uniform(0.1,0.4),2),'하락'))
pd.DataFrame(sh,columns=['기준월','행정동코드','순위','요인코드','설명','기여도','방향']).to_csv('data/shap_top.csv',index=False,encoding='utf-8-sig')
print('done', months[0], months[-1])
