"""가상 SHAP 요인 — 실측 신호의 방향과 어긋나지 않게 문장을 만든다 (모델 연결 시 삭제)."""
import numpy as np, pandas as pd
rng=np.random.default_rng(3)
pr=pd.read_csv('data/pred_dong_month.csv',dtype={'행정동코드':str}); sig=pd.read_csv('data/signals_dong_month.csv',dtype={'행정동코드':str})
m=pr.기준월.max(); s=sig[sig.기준월==m].set_index('행정동코드')
rows=[]
for code in pr[pr.기준월==m].행정동코드:
    c=[]; up=[]
    if code in s.index:
        r=s.loc[code]
        for col,neg,pos in [('카드소비_전년비','카드 소비가 전년 같은 달보다 {:.1f}% 줄었습니다','카드 소비가 전년 같은 달보다 {:.1f}% 늘었습니다'),
                            ('음식주점소비_전년비','음식/주점 소비가 전년보다 {:.1f}% 줄었습니다','음식/주점 소비가 전년보다 {:.1f}% 늘었습니다'),
                            ('방문인구_전년비','방문인구가 전년 같은 달보다 {:.1f}% 줄었습니다','방문인구가 전년 같은 달보다 {:.1f}% 늘었습니다'),
                            ('직장인구_전년비','직장인구가 전년보다 {:.1f}% 줄었습니다','직장인구가 전년보다 {:.1f}% 늘었습니다')]:
            v=r[col]
            if pd.isna(v): continue
            (c if v<0 else up).append((abs(v),col,(neg if v<0 else pos).format(abs(v))))
    c.sort(reverse=True); up.sort(reverse=True)
    extra=[(0,'업종폐업률','같은 업종의 최근 12개월 폐업률이 부산 평균보다 높습니다'),(0,'단기점포','1년 미만 점포 비중이 높습니다')]
    picks=(c+extra)[:3]
    w=sorted(rng.uniform(0.25,1,3),reverse=True)
    for k,((_,col,txt),v) in enumerate(zip(picks,w)): rows.append((m,code,k+1,col,txt,round(v,2),'상승'))
    if up: rows.append((m,code,4,up[0][1],up[0][2],round(-rng.uniform(0.1,0.3),2),'하락'))
    else: rows.append((m,code,4,'업력','오래 영업한 점포가 많습니다',round(-rng.uniform(0.1,0.3),2),'하락'))
pd.DataFrame(rows,columns=['기준월','행정동코드','순위','요인코드','설명','기여도','방향']).to_csv('data/shap_top.csv',index=False,encoding='utf-8-sig')
print(len(rows))
