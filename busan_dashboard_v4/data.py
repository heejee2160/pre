"""데이터 계층.

실제 파일이 data/ 폴더에 있으면 그것을 읽고, 없으면 같은 형식의 예시 데이터를 만든다.
화면 코드는 이 파일의 함수만 부르므로, 모델 결과가 나오면 아래 '실제 파일 형식'에 맞춰
CSV를 넣기만 하면 화면이 바뀐다.

실제 파일 형식 (모두 UTF-8 CSV, 행정동코드는 10자리 문자열)
- data/model_pred.csv      : 행정동코드, 기준월(YYYYMM), 카드업종, 폐업확률(0~1)
                             카드업종이 '전체'인 행은 동 전체 확률
- data/model_shap.csv      : 행정동코드, 기준월, 카드업종, 요인, 기여(로그오즈 또는 %p)
- data/dong_signals.csv    : 행정동코드, 기준월, 폐업률_6m, 카드소비_전년비, 방문인구_전년비,
                             영업점포수, 1년미만폐업비중, 개업_6m, 폐업_6m
- data/sinbo_gu_upjong_2025.csv : 재단 보증 실자료(구군 × 업종 대분류) — 이미 들어 있음
"""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
DATA = BASE / "data"
ASSETS = BASE / "assets"

CARD_UPJONG = ["음식/주점", "음식료품", "유통", "미용", "의료", "교육", "생활",
               "여가/문화", "여행/숙박", "의류/잡화", "자동차"]
MONTHS = [f"{y}{m:02d}" for y in (2025, 2026) for m in range(1, 13) if f"{y}{m:02d}" <= "202606"]
HOLD_MIN_STORES = 30

# 폐업확률 등급 (피그마 S-00 범례 기준)
GRADES = [  # (이름, 하한 %, 색)
    ("우선 확인", 10.0, "#D9452F"),
    ("높음", 8.0, "#EE7B3A"),
    ("주의", 6.0, "#F5B24F"),
    ("보통", 0.0, "#FADB8E"),
]
HOLD_COLOR = "#C9CED6"


def grade_of(p: float, hold: bool = False) -> tuple[str, str]:
    if hold:
        return "판단 보류", HOLD_COLOR
    for name, lo, color in GRADES:
        if p >= lo:
            return name, color
    return GRADES[-1][0], GRADES[-1][2]


# ---------------------------------------------------------------- geometry
@lru_cache(maxsize=1)
def load_geo() -> dict:
    return json.loads((ASSETS / "busan_hd.geojson").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def dong_list() -> pd.DataFrame:
    rows = [f["properties"] for f in load_geo()["features"]]
    df = pd.DataFrame(rows).rename(columns={"adm_cd": "code", "sgg": "gu", "dong": "dong"})
    return df[["code", "gu", "dong"]].sort_values(["gu", "dong"]).reset_index(drop=True)


def gu_list() -> list[str]:
    return sorted(dong_list()["gu"].unique())


# ---------------------------------------------------------------- example data
# 피그마 시안의 숫자를 일부 그대로 쓴다 (나머지는 동 코드로 고정된 난수)
_DEMO = {
    ("해운대구", "우1동"): 12.4, ("동래구", "온천1동"): 11.8, ("부산진구", "부전1동"): 10.6,
    ("사하구", "하단1동"): 10.2, ("중구", "남포동"): 9.9,
}
_GU_BASE = {"해운대구": 7.6, "동래구": 7.4, "부산진구": 7.5, "중구": 7.3, "사하구": 7.1, "금정구": 7.0,
            "서구": 6.9, "영도구": 6.9, "동구": 6.8, "연제구": 6.8, "수영구": 6.7, "남구": 6.5,
            "북구": 6.3, "사상구": 6.4, "기장군": 6.0, "강서구": 5.8}


def _rng(*keys) -> random.Random:
    return random.Random("|".join(map(str, keys)))


@lru_cache(maxsize=64)
def _example_month(month: str) -> pd.DataFrame:
    d = dong_list().copy()
    mi = MONTHS.index(month) if month in MONTHS else len(MONTHS) - 1
    out = []
    for r in d.itertuples():
        g = _rng(r.code)
        base = _GU_BASE.get(r.gu, 6.5) + g.gauss(0, 1.6)
        drift = (mi - (len(MONTHS) - 1)) * 0.06 * g.uniform(0.3, 1.2)
        p = _DEMO.get((r.gu, r.dong), base + drift)
        stores = int(g.uniform(18, 480))
        prev = p - g.uniform(-0.2, 0.45)
        out.append(dict(code=r.code, gu=r.gu, dong=r.dong, prob=round(max(p, 1.5), 1),
                        prob_prev=round(max(prev, 1.5), 1),
                        close_rate_6m=round(max(p * 0.56 + g.gauss(0, 0.6), 1.0), 1),
                        card_yoy=round(-p * 0.55 + g.gauss(1.5, 2.0), 1),
                        pop_yoy=round(-p * 0.18 + g.gauss(0.6, 1.0), 1),
                        young_close_share=int(min(60, max(10, p * 3 + g.gauss(0, 4)))),
                        stores=stores, open_6m=int(stores * g.uniform(0.04, 0.09)),
                        close_6m=int(stores * g.uniform(0.05, 0.12))))
    df = pd.DataFrame(out)
    df.loc[df["stores"] < HOLD_MIN_STORES, "stores"] = df["stores"]  # 판단 보류 후보 유지
    return df


def _real_month(month: str) -> pd.DataFrame | None:
    pred = DATA / "model_pred.csv"
    sig = DATA / "dong_signals.csv"
    if not (pred.exists() and sig.exists()):
        return None
    p = pd.read_csv(pred, dtype={"행정동코드": str, "기준월": str})
    s = pd.read_csv(sig, dtype={"행정동코드": str, "기준월": str})
    months = sorted(p["기준월"].unique())
    prev_m = months[months.index(month) - 1] if month in months and months.index(month) > 0 else month
    cur = p[(p["기준월"] == month) & (p["카드업종"] == "전체")][["행정동코드", "폐업확률"]]
    prv = p[(p["기준월"] == prev_m) & (p["카드업종"] == "전체")][["행정동코드", "폐업확률"]]
    df = dong_list().merge(cur.rename(columns={"행정동코드": "code", "폐업확률": "prob"}), how="left")
    df = df.merge(prv.rename(columns={"행정동코드": "code", "폐업확률": "prob_prev"}), how="left")
    df[["prob", "prob_prev"]] = df[["prob", "prob_prev"]] * 100
    s = s[s["기준월"] == month].rename(columns={
        "행정동코드": "code", "폐업률_6m": "close_rate_6m", "카드소비_전년비": "card_yoy",
        "방문인구_전년비": "pop_yoy", "영업점포수": "stores", "1년미만폐업비중": "young_close_share",
        "개업_6m": "open_6m", "폐업_6m": "close_6m"})
    return df.merge(s.drop(columns=["기준월"]), how="left")


def month_table(month: str, upjong: str = "전체") -> pd.DataFrame:
    """동 × 지표 표. upjong이 '전체'가 아니면 그 업종 확률로 바꾼다."""
    df = _real_month(month)
    if df is None:
        df = _example_month(month).copy()
        if upjong != "전체":
            k = CARD_UPJONG.index(upjong) if upjong in CARD_UPJONG else 0
            f = [_rng(c, upjong).uniform(0.7, 1.35) for c in df["code"]]
            df["prob"] = [round(max(p * x + (0.6 if k == 0 else 0), 1.0), 1) for p, x in zip(df["prob"], f)]
            df["prob_prev"] = [round(max(p * x + (0.6 if k == 0 else 0), 1.0), 1) for p, x in zip(df["prob_prev"], f)]
    df["hold"] = df["stores"] < HOLD_MIN_STORES
    df["mom"] = (df["prob"] - df["prob_prev"]).round(1)
    gr = [grade_of(p, h) for p, h in zip(df["prob"], df["hold"])]
    df["grade"] = [g[0] for g in gr]
    df["color"] = [g[1] for g in gr]
    return df


def busan_avg(df: pd.DataFrame, col: str = "prob") -> float:
    w = df.loc[~df["hold"], "stores"]
    return round(float((df.loc[~df["hold"], col] * w).sum() / w.sum()), 1)


def gu_avg(df: pd.DataFrame, gu: str, col: str = "prob") -> float:
    return busan_avg(df[df["gu"] == gu], col)


def top_n(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    return df[~df["hold"]].sort_values("prob", ascending=False).head(n).reset_index(drop=True)


# ---------------------------------------------------------------- detail
def signals(row: pd.Series, df: pd.DataFrame) -> list[str]:
    """규칙 기반 위험 신호 문장 (모델이 아닌 실측 데이터로 만든다)."""
    out = []
    g_card = gu_avg(df, row["gu"], "card_yoy")
    if row["card_yoy"] < 0 and row["card_yoy"] < g_card:
        ratio = row["card_yoy"] / g_card if g_card < 0 else None
        out.append(f"카드소비 감소 폭이 {row['gu']} 평균의 {ratio:.1f}배" if ratio and ratio >= 1.3
                   else f"카드소비 전년 대비 {row['card_yoy']:+.1f}% ({row['gu']} {g_card:+.1f}%)")
    if row["close_6m"] > row["open_6m"]:
        out.append(f"최근 6개월 폐업 {row['close_6m']}곳이 개업 {row['open_6m']}곳보다 많음")
    if row["pop_yoy"] < 0:
        out.append(f"방문인구 전년 대비 {row['pop_yoy']:+.1f}%")
    return out[:2] or ["뚜렷한 위험 신호 없음"]


def upjong_table(code: str, month: str) -> pd.DataFrame:
    rows = []
    for u in CARD_UPJONG:
        t = month_table(month, u)
        r = t[t["code"] == code].iloc[0]
        rows.append(dict(upjong=u, prob=r["prob"], mom=r["mom"], stores=max(int(r["stores"] * _rng(code, u, "s").uniform(0.03, 0.4)), 1)))
    df = pd.DataFrame(rows)
    df["hold"] = df["stores"] < 5
    return df.sort_values("prob", ascending=False).reset_index(drop=True)


def shap_parts(code: str, month: str) -> list[tuple[str, int, str]]:
    """원인 비중 (상위 3 + 기타). 실제 SHAP 파일이 있으면 그것을 쓴다."""
    f = DATA / "model_shap.csv"
    if f.exists():
        s = pd.read_csv(f, dtype={"행정동코드": str, "기준월": str})
        s = s[(s["행정동코드"] == code) & (s["기준월"] == month) & (s["카드업종"] == "전체") & (s["기여"] > 0)]
        s = s.sort_values("기여", ascending=False)
        tot = s["기여"].sum()
        top = [(r.요인, round(r.기여 / tot * 100), "") for r in s.head(3).itertuples()]
        rest = 100 - sum(t[1] for t in top)
        return top + [("기타 요인", rest, "나머지 변수 합계")]
    g = _rng(code, month, "shap")
    a = g.uniform(32, 42); b = g.uniform(22, 30); c = g.uniform(14, 22)
    tot = a + b + c + g.uniform(10, 16)
    v = [round(x / tot * 100) for x in (a, b, c)]
    return [("카드소비 감소", v[0], "전년 동월 대비 감소 · 4개월 연속"),
            ("동종 업종 폐업 증가", v[1], "최근 12개월 폐업률 부산 평균 상회"),
            ("저녁 방문인구 감소", v[2], "18~22시 방문인구 전년 대비 감소"),
            ("기타 요인", 100 - sum(v), "나머지 변수 합계")]


def trend_series(code: str) -> tuple[list[str], list[float], list[float], list[str], list[int]]:
    g = _rng(code, "trend")
    months = ["23.01", "26.06"]
    line = [100.0]
    for _ in range(10):
        line.append(round(line[-1] + g.uniform(-3, 4) - (2.5 if len(line) > 6 else 0), 1))
    base = [round(100 + g.uniform(-1, 2), 1) for _ in line]
    qs = ["24Q3", "24Q4", "25Q1", "25Q2", "25Q3", "25Q4", "26Q1", "26Q2"]
    q = [4]
    for _ in range(7):
        q.append(max(1, q[-1] + g.choice([0, 1, 1, 2])))
    return months, line, base, qs, q


@lru_cache(maxsize=1)
def sinbo() -> pd.DataFrame:
    return pd.read_csv(DATA / "sinbo_gu_upjong_2025.csv")


def sinbo_gu(gu: str) -> dict:
    s = sinbo()
    by = s.groupby("구군")[["잔액_평균", "사고금액", "신규금액", "신규업체", "사고건수", "잔액_2025Q4"]].sum()
    by["사고율"] = by["사고금액"] / by["잔액_평균"] * 100
    by["순위"] = by["사고율"].rank(ascending=False).astype(int)
    r = by.loc[gu]
    up = s[s["구군"] == gu].sort_values("잔액_2025Q4", ascending=False).head(4)
    return dict(rate=round(r["사고율"], 2), busan=round(by["사고금액"].sum() / by["잔액_평균"].sum() * 100, 2),
                rank=int(r["순위"]), n=len(by), bal=r["잔액_2025Q4"], bal_rank=int(by["잔액_2025Q4"].rank(ascending=False)[gu]),
                new=r["신규금액"], new_cnt=int(r["신규업체"]), acc=r["사고금액"], acc_cnt=int(r["사고건수"]),
                upjong=[(_short(u.업종), round(u.사고율, 2), u.잔액_2025Q4) for u in up.itertuples()])


def _short(name: str) -> str:
    return {"도매 및 소매업": "도매·소매업", "숙박 및 음식점업": "숙박·음식점업",
            "협회 및 단체, 수리 및 기타 개인 서비스업": "개인 서비스업",
            "사업시설 관리, 사업 지원 및 임대 서비스업": "사업지원 서비스업",
            "전문, 과학 및 기술 서비스업": "전문·과학기술", "예술, 스포츠 및 여가관련 서비스업": "예술·스포츠·여가",
            "보건업 및 사회복지 서비스업": "보건·사회복지", "운수 및 창고업": "운수·창고업"}.get(name, name)
