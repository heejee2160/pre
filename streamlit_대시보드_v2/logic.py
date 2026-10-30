"""화면과 상관없는 계산만 모아 둔 파일 (Streamlit 없이도 테스트 가능).

데이터 계약(data contract): data/ 폴더의 파일과 컬럼 이름이 아래와 같으면
가상 데이터든 실제 모델 결과든 앱은 그대로 동작한다.
"""
import json
from pathlib import Path
import pandas as pd

DATA = Path(__file__).parent / "data"

# 파일별 필수 컬럼. 모델 결과를 연결할 때 이 이름만 맞추면 된다.
CONTRACT = {
    "pred_dong_month.csv": ["기준월", "행정동코드", "구군", "읍면동", "폐업위험률", "영업점포수", "예상폐업점포"],
    "pred_dong_industry.csv": ["기준월", "행정동코드", "카드업종", "폐업위험률", "영업점포수"],
    "shap_top.csv": ["기준월", "행정동코드", "순위", "요인코드", "설명", "기여도", "방향"],
    "signals_dong_month.csv": ["기준월", "행정동코드", "카드소비_전년비", "음식주점소비_전년비", "방문인구_전년비", "직장인구_전년비"],
    "card_dong_industry_month.csv": ["기준월", "행정동코드", "카드업종", "평균금액"],
    "guarantee_gu_industry.csv": ["구군", "업종대분류", "보증잔액", "사고건수", "사고금액"],
    "stores_dong_quarter.csv": ["기준분기", "행정동코드", "개업", "폐업", "폐업_1년미만", "영업점포수"],
}
# 어떤 파일이 실제 자료인지 표시 (화면 배지에 사용)
SOURCE = {
    "pred_dong_month.csv": "가상", "pred_dong_industry.csv": "가상", "shap_top.csv": "가상",
    "signals_dong_month.csv": "실측", "card_dong_industry_month.csv": "실측", "guarantee_gu_industry.csv": "실측",
    "stores_dong_quarter.csv": "가상",
}

STAGES = ["심각", "경계", "주의", "관심", "정상", "판단 보류"]
STAGE_COLOR = {"심각": "#ff4040", "경계": "#ff833a", "주의": "#ffef99", "관심": "#d1ebed",
               "정상": "#c2dfa6", "판단 보류": "#f4f5f6"}


def load_all():
    """data/ 의 파일을 읽고 계약을 검사한다. 빠진 컬럼이 있으면 바로 알려 준다."""
    out, problems = {}, []
    for fname, cols in CONTRACT.items():
        f = DATA / fname
        if not f.exists():
            problems.append(f"{fname} 파일 없음")
            continue
        df = pd.read_csv(f, dtype={"행정동코드": str})
        miss = [c for c in cols if c not in df.columns]
        if miss:
            problems.append(f"{fname}: 컬럼 없음 {miss}")
        out[fname.replace(".csv", "")] = df
    out["geo"] = json.load(open(DATA / "busan_dong.geojson", encoding="utf-8"))
    return out, problems


def assign_stage(pred: pd.DataFrame) -> pd.DataFrame:
    """기준월마다 폐업위험률 순위로 상권 위험단계(안)를 붙인다.
    심각 = 상위 10% 이면서 3개월 연속 상승 / 경계 = 상위 10% / 주의 = 10~30% / 관심 = 30~50% / 정상 = 하위 50%
    """
    p = pred.sort_values(["행정동코드", "기준월"]).copy()
    p["순위비율"] = p.groupby("기준월")["폐업위험률"].rank(ascending=False, pct=True)
    up = p.groupby("행정동코드")["폐업위험률"].diff() > 0
    p["연속상승"] = up.groupby(p["행정동코드"]).transform(lambda s: s.rolling(3).sum()) == 3

    def stage(r):
        if pd.isna(r["폐업위험률"]):
            return "판단 보류"
        q = r["순위비율"]
        if q <= 0.10:
            return "심각" if r["연속상승"] else "경계"
        if q <= 0.30:
            return "주의"
        if q <= 0.50:
            return "관심"
        return "정상"

    p["단계"] = p.apply(stage, axis=1)
    p["부산평균"] = p.groupby("기준월")["폐업위험률"].transform("mean").round(1)
    p["구평균"] = p.groupby(["기준월", "구군"])["폐업위험률"].transform("mean").round(1)
    p["전월대비"] = p.groupby("행정동코드")["폐업위험률"].diff().round(1)
    p["순위"] = p.groupby("기준월")["폐업위험률"].rank(ascending=False, method="min")
    return p


def top_n(staged: pd.DataFrame, month: int, n=5, gu=None) -> pd.DataFrame:
    d = staged[staged["기준월"] == month]
    if gu and gu != "부산 전체":
        d = d[d["구군"] == gu]
    return d.dropna(subset=["폐업위험률"]).nlargest(n, "폐업위험률")


def summary_sentence(row, sig) -> str:
    """숫자만으로 만드는 한 줄 요약 (해석·인과 표현 없음)."""
    diff = row["폐업위험률"] - row["부산평균"]
    s = f"폐업위험 {row['폐업위험률']:.1f}%로 부산 평균 {row['부산평균']:.1f}%보다 {abs(diff):.1f}%p {'높습니다' if diff >= 0 else '낮습니다'}."
    if sig is not None and pd.notna(sig.get("카드소비_전년비")):
        v = sig["카드소비_전년비"]
        s += f" 카드 소비는 전년 같은 달보다 {abs(v):.1f}% {'늘었습니다' if v >= 0 else '줄었습니다'}."
    return s


def guarantee_gu(gtable: pd.DataFrame, gu: str):
    t = gtable.groupby("구군")[["보증잔액", "사고건수", "사고금액"]].sum()
    t["사고율"] = t["사고금액"] / t["보증잔액"] * 100
    busan = t["사고금액"].sum() / t["보증잔액"].sum() * 100
    if gu not in t.index:
        return None
    r = t.loc[gu]
    rank = int(t["보증잔액"].rank(ascending=False)[gu])
    ind = gtable[gtable["구군"] == gu].groupby("업종대분류")[["보증잔액", "사고금액"]].sum()
    ind["사고율"] = ind["사고금액"] / ind["보증잔액"] * 100
    bi = gtable.groupby("업종대분류")[["보증잔액", "사고금액"]].sum()
    ind["부산_사고율"] = bi["사고금액"] / bi["보증잔액"] * 100
    return dict(잔액억=r["보증잔액"] / 100, 사고억=r["사고금액"] / 100, 사고건수=int(r["사고건수"]),
                사고율=r["사고율"], 부산사고율=busan, 잔액순위=rank, 구군수=len(t),
                업종=ind.sort_values("보증잔액", ascending=False).head(6))


def month_label(m) -> str:
    s = str(m)
    return f"{s[:4]}.{s[4:]}"


def map_payload(staged, sig, shap, geo, month, gu="부산 전체", n_top=5, pred_tag="가상",
                pred_ind=None, show_hold=True, popup_nonce=0):
    """지도 컴포넌트(components/busan_map)에 넘길 값. JSON으로 바뀔 수 있는 값만 담는다."""
    cur = staged[staged["기준월"] == month]
    s = sig[sig["기준월"] == month].set_index("행정동코드")
    fac = shap[shap["방향"] == "상승"].sort_values("순위").groupby("행정동코드")["설명"].apply(list)
    ind = None
    if pred_ind is not None:
        pi = pred_ind[pred_ind["기준월"] == pred_ind["기준월"].max()].sort_values("폐업위험률", ascending=False)
        ind = pi.groupby("행정동코드")["카드업종"].apply(lambda x: list(x)[:2])
    avg = float(cur["폐업위험률"].mean())

    def g(c, col):
        return None if c not in s.index or pd.isna(s.loc[c, col]) else float(s.loc[c, col])

    rows = {}
    for _, r in cur.iterrows():
        c = r["행정동코드"]
        risk = None if pd.isna(r["폐업위험률"]) else float(r["폐업위험률"])
        sigs = [(lab, g(c, col)) for col, lab in [("카드소비_전년비", "카드 소비"), ("음식주점소비_전년비", "음식/주점 소비"),
                                                  ("방문인구_전년비", "방문인구"), ("직장인구_전년비", "직장인구")]]
        neg = sorted([x for x in sigs if x[1] is not None and x[1] < 0], key=lambda x: x[1])
        rows[c] = dict(
            gu=r["구군"], dong=r["읍면동"], stage=r["단계"], risk=risk,
            diff=None if risk is None else round(risk - avg, 1),
            rank=None if pd.isna(r["순위"]) else int(r["순위"]),
            expect=None if pd.isna(r["예상폐업점포"]) else float(r["예상폐업점포"]),
            shops=None if pd.isna(r["영업점포수"]) else float(r["영업점포수"]),
            card=g(c, "카드소비_전년비"), food=g(c, "음식주점소비_전년비"),
            visit=g(c, "방문인구_전년비"), work=g(c, "직장인구_전년비"),
            signal=dict(label=neg[0][0], v=neg[0][1]) if neg else None,
            factors=fac.get(c, [])[:2], ind=ind.get(c, []) if ind is not None else [],
        )
    top = top_n(staged, month, n_top, gu)["행정동코드"].tolist()
    return dict(geo=geo, rows=rows, top=top, avg=round(avg, 1), n=int(cur["폐업위험률"].notna().sum()),
                stages=STAGES, colors=STAGE_COLOR, month_label=month_label(month), gu=gu, pred_tag=pred_tag,
                compare_default=top[:2], show_hold=show_hold, popup_nonce=popup_nonce)


SIG_COLS = [("카드소비", "카드 소비"), ("음식주점소비", "음식/주점 소비"), ("방문인구_월", "방문인구"), ("직장인구_월", "직장인구")]


def area_yoy(sig, codes, month):
    """여러 동을 합친 값의 전년 같은 달 대비 증감률(%). 동별 증감률의 단순 평균이 아니라 합계 기준."""
    s = sig[sig["행정동코드"].isin(codes)].groupby("기준월")[[c for c, _ in SIG_COLS]].sum()
    prev = month - 100
    if month not in s.index or prev not in s.index:
        return {c: None for c, _ in SIG_COLS}
    return {c: round((s.loc[month, c] / s.loc[prev, c] - 1) * 100, 1) for c, _ in SIG_COLS}


def compare_table(staged, sig, month, code):
    cur = staged[staged["기준월"] == month]
    r = cur[cur["행정동코드"] == code].iloc[0]
    gu_codes = cur[cur["구군"] == r["구군"]]["행정동코드"]
    cols = {f"{r['읍면동']}": [code], f"{r['구군']}": list(gu_codes), "부산": list(cur["행정동코드"])}
    out = {"폐업위험률 (예측, %)": [r["폐업위험률"], r["구평균"], r["부산평균"]]}
    yo = {k: area_yoy(sig, v, month) for k, v in cols.items()}
    for c, lab in SIG_COLS:
        out[f"{lab} 전년비 (%)"] = [yo[k][c] for k in cols]
    return pd.DataFrame(out, index=list(cols)).T


def index_series(sig, codes, col="음식주점소비"):
    s = sig[sig["행정동코드"].isin(codes)].groupby("기준월")[col].sum().sort_index()
    return (s / s.iloc[0] * 100).round(1)



def store_stats(stores, codes):
    """인허가 분기 집계 → 최근 6개월 폐업률, 1년 미만 폐업 비중, 최근 1년 점포 순증, 분기별 폐업."""
    d = stores[stores["행정동코드"].isin(codes)].groupby("기준분기")[["개업", "폐업", "폐업_1년미만", "영업점포수"]].sum().sort_index()
    if d.empty:
        return None
    last2, last4 = d.tail(2), d.tail(4)
    return dict(
        close6=round(last2["폐업"].sum() / d["영업점포수"].iloc[-1] * 100, 1),
        close6_prev=round(d.iloc[-6:-4]["폐업"].sum() / d["영업점포수"].iloc[-1] * 100, 1) if len(d) >= 6 else None,
        young=round(last4["폐업_1년미만"].sum() / max(1, last4["폐업"].sum()) * 100, 0),
        net=int((last4["개업"] - last4["폐업"]).sum()), opened=int(last4["개업"].sum()), closed=int(last4["폐업"].sum()),
        quarterly=d["폐업"], net_q=(d["개업"] - d["폐업"]),
    )


def stage_for_industry(staged, pred_ind, month, ind):
    """카드업종 하나만 볼 때: 그 업종의 폐업위험률로 단계를 다시 매긴다 (최신월만 있음)."""
    cur = staged[staged["기준월"] == month].copy()
    pi = pred_ind[(pred_ind["기준월"] == month) & (pred_ind["카드업종"] == ind)].set_index("행정동코드")
    if pi.empty:
        return None
    cur["폐업위험률"] = cur["행정동코드"].map(pi["폐업위험률"])
    cur["영업점포수"] = cur["행정동코드"].map(pi["영업점포수"])
    cur.loc[cur["영업점포수"] < 5, "폐업위험률"] = float("nan")
    q = cur["폐업위험률"].rank(ascending=False, pct=True)
    cur["단계"] = ["판단 보류" if pd.isna(v) else "경계" if p <= .1 else "주의" if p <= .3 else "관심" if p <= .5 else "정상"
                 for v, p in zip(cur["폐업위험률"], q)]
    cur["부산평균"] = round(cur["폐업위험률"].mean(), 1)
    cur["순위"] = cur["폐업위험률"].rank(ascending=False, method="min")
    return cur


def donut_svg(vals, colors, size=150, hole=0.56):
    """기여 비중 도넛을 SVG 문자열로 (HTML 카드 안에 바로 넣기 위해)."""
    import math
    tot = sum(vals) or 1
    R, r, c = size / 2, size / 2 * hole, size / 2
    a0, out = -math.pi / 2, []
    for v, col in zip(vals, colors):
        a1 = a0 + 2 * math.pi * v / tot
        big = 1 if a1 - a0 > math.pi else 0
        p = [(c + R * math.cos(a0), c + R * math.sin(a0)), (c + R * math.cos(a1), c + R * math.sin(a1)),
             (c + r * math.cos(a1), c + r * math.sin(a1)), (c + r * math.cos(a0), c + r * math.sin(a0))]
        out.append(f'<path d="M{p[0][0]:.1f} {p[0][1]:.1f} A{R} {R} 0 {big} 1 {p[1][0]:.1f} {p[1][1]:.1f} '
                   f'L{p[2][0]:.1f} {p[2][1]:.1f} A{r} {r} 0 {big} 0 {p[3][0]:.1f} {p[3][1]:.1f}Z" fill="{col}" stroke="#1C2E57" stroke-width="2"/>')
        a0 = a1
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(out)}</svg>'
