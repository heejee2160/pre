"""부산 상권 위험 조기진단 대시보드 — Streamlit (Figma S-00 · 2페이지 HTML 반영, 1536×864 @125% 기준)

실행:  pip install -r requirements.txt  →  streamlit run app.py
화면:  ① 전체 지도  ② 행정동·업종 상세(스크롤)  ③ 근거 확인 및 자료 다운
상태:  주소창 ?page=&dong=&month=&gu=&ind= 로 관리 (새로고침·링크 공유해도 같은 화면)
※ 1536×864 화면 + 배율 125% 이면 브라우저가 쓰는 실제 폭은 약 1229px, 높이 약 600px 이다. 그 크기에 맞춰 잡았다.
"""
import io
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import logic as L

st.set_page_config(page_title="부산 상권 위험 조기진단", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")
ROOT = Path(__file__).parent
busan_map = components.declare_component("busan_map", path=str(ROOT / "components" / "busan_map"))

NAVY, NAVY2, BLUE, BLUE2, MUT, INK, LINE, BG = "#13294D", "#1C2E57", "#1F5FD6", "#4a86f4", "#6B7280", "#1A1D23", "#E3E8EF", "#E4EBF2"
PAGES = {"map": ("1", "전체"), "detail": ("2", "행정동·업종 상세"), "data": ("3", "근거 확인 및 자료 다운")}
INDS = [("전체", "▦"), ("음식/주점", "🍴"), ("음식료품", "🧺"), ("유통", "🛒"), ("미용", "✂️"), ("의료", "➕"),
        ("교육", "📖"), ("생활", "🏠"), ("여가/문화", "🎭"), ("여행/숙박", "🧳"), ("의류/잡화", "👕"), ("자동차", "🚗")]


def H(html: str):
    """HTML을 한 줄로 붙여서 출력. (들여쓴 줄을 마크다운이 코드 블록으로 바꾸는 문제를 막는다)"""
    st.markdown(" ".join(x.strip() for x in html.splitlines() if x.strip()), unsafe_allow_html=True)


H(f"""<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{display:none !important}}
html, body, [data-testid="stAppViewContainer"], .stApp {{background:{BG};}}
.block-container, [data-testid="stMainBlockContainer"] {{padding:8px 12px 24px !important; max-width:100% !important}}
[data-testid="stVerticalBlock"] {{gap:.55rem}}
[data-testid="stMarkdownContainer"], .stMarkdown, [data-testid="stMarkdown"] {{margin-bottom:0 !important}}
[data-testid="stMarkdownContainer"] > div {{margin-bottom:0}}
[data-testid="stElementContainer"], .element-container {{margin-bottom:0 !important}}
[data-testid="stHorizontalBlock"] {{gap:.6rem}}
p, li, label, .stMarkdown {{font-size:13px}}
[data-testid="stWidgetLabel"] p {{font-size:12px !important; color:{MUT}}}
div[data-baseweb="select"] > div {{min-height:34px; font-size:13px}}
.stButton > button {{border-radius:8px; padding:.3rem .6rem; font-size:13px; min-height:34px}}
[data-testid="stVerticalBlockBorderWrapper"] {{background:#fff; border-radius:12px !important; border:1px solid {LINE} !important}}
[data-testid="stExpander"] details {{background:#fff; border-radius:10px}}
a {{text-decoration:none !important}}
.hd {{background:linear-gradient(90deg,{NAVY} 85%,#2664B9 100%); margin:0 -12px; padding:10px 18px; display:flex; align-items:center; gap:12px}}
.hd .logo {{width:34px; height:34px; border-radius:6px; border:1px solid #6f87a8; color:#fff; font-size:10px; display:flex; align-items:center; justify-content:center}}
.hd .t1 {{color:#fff; font-size:18px; font-weight:700; line-height:1.15}} .hd .t2 {{color:#b9c7da; font-size:11px}}
.steps {{margin-left:auto; display:flex; align-items:center; gap:8px}}
.steps a {{display:flex; align-items:center; gap:8px; border:1px solid #4d6589; border-radius:6px; padding:5px 12px 5px 6px; color:#c9d6e6; font-size:12px; line-height:1.15}}
.steps a i {{font-style:normal; width:20px; height:20px; border:1px solid #9fb2cb; display:flex; align-items:center; justify-content:center; font-size:11px}}
.steps a.on {{background:#fff; color:{NAVY}; font-weight:700; border-color:#fff; padding:6px 22px 6px 8px}}
.steps a.on i {{background:{NAVY}; color:#fff; border-color:{NAVY}}}
.steps a.on small {{display:block; font-size:9px; color:{BLUE}; font-weight:700}}
.strip {{background:#F4F7FB; border-bottom:1px solid #DBE3EE; margin:0 -12px 10px; padding:6px 18px; font-size:11.5px; color:#4A5A70; display:flex; gap:22px; white-space:nowrap; overflow:hidden}}
.strip b {{color:{NAVY}}} .strip .r {{margin-left:auto}}
.rail {{background:{NAVY2}; border-radius:10px; padding:6px 0; min-height:560px}}
.rail a {{display:block; text-align:center; color:#c9d6e6; font-size:10.5px; padding:9px 0; line-height:1.3}}
.rail a b {{display:block; font-size:16px; color:#fff; font-weight:400}}
.rail a.on {{background:{BLUE}; color:#fff}}
.pnl {{background:#fff; border:1px solid {LINE}; border-radius:12px; padding:12px 14px}}
.pnl h5 {{margin:0 0 6px; font-size:15px; color:{INK}}}
.grid4 {{display:grid; grid-template-columns:repeat(4,1fr); gap:5px}}
.grid4 a {{display:flex; flex-direction:column; align-items:center; justify-content:center; height:48px; border-radius:7px; background:#F4F6F9; color:#3b4250; font-size:11px; gap:3px}}
.grid4 a span {{font-size:17px; line-height:1}}
.grid4 a.on {{background:{NAVY2}; color:#fff; font-weight:700}}
.top5 a {{display:flex; align-items:center; gap:6px; padding:6px 0; font-size:12.5px; color:{INK}; border-bottom:1px solid #f0f2f5}}
.top5 .k {{color:#d6342c; font-weight:700; width:12px}} .top5 .p {{margin-left:auto; font-weight:700}} .top5 .u {{color:#d6342c; font-size:11px; width:64px; text-align:right}}
.card, .pnl, .rail {{box-sizing:border-box}}
.card {{background:#fff; border:1px solid {LINE}; border-radius:12px; padding:14px 16px}}
.card h4 {{margin:0 0 8px; font-size:15px; color:{INK}; font-weight:700; display:flow-root}}
.card h4 .n {{color:{MUT}; font-size:11.5px; font-weight:400; float:right}}
.navy {{background:#132F5E; border:0; color:#fff}} .navy h4 {{color:#fff}}
.lblue {{background:#E7EFFB; border-color:#d3e1f7}}
.kv {{font-size:12px; color:{MUT}}} .kv b {{display:block; color:{INK}; font-size:24px; margin-top:2px}}
.chip {{display:inline-block; font-size:11px; font-weight:700; padding:2px 9px; border-radius:4px; vertical-align:middle}}
.bd {{display:inline-block; padding:0 5px; border-radius:3px; font-size:10px; font-weight:700; margin-left:3px; vertical-align:middle}}
.real {{background:#eaf6ec; color:#267337}} .mock {{background:#fff3db; color:#8a5c00}}
.note {{color:{MUT}; font-size:11.5px}}
.rw {{display:flex; justify-content:space-between; align-items:center; padding:5px 0; font-size:12.5px; border-bottom:1px solid #eef1f4}}
.tbl {{width:100%; border-collapse:collapse; font-size:12.5px}}
.tbl th {{color:{MUT}; font-weight:400; font-size:11.5px; text-align:right; padding:5px}}
.tbl td {{text-align:right; padding:7px 5px; border-top:1px solid #f0f2f5}}
.tbl td:first-child, .tbl th:first-child {{text-align:left; color:#3b4250}}
.tbl .sel {{color:{BLUE}; font-weight:700}}
.ib {{display:flex; align-items:center; gap:8px; font-size:12.5px; padding:5px 0}}
.ib .nm {{width:72px; font-weight:700; white-space:nowrap}}
.ib .tr {{flex:1; height:9px; background:#eef1f5; border-radius:3px; position:relative}}
.ib .fl {{display:block; height:100%; border-radius:3px}}
.ib .av {{position:absolute; top:-4px; bottom:-4px; border-left:1.5px dashed {INK}}}
.ib .v {{width:40px; text-align:right; font-weight:700}} .ib .d {{width:34px; text-align:right; font-size:11px}}
</style>""")


def bd(kind):
    return f'<span class="bd {"real" if kind == "실측" else "mock"}">{kind}</span>'


def bars_svg(vals, w=130, h=70, pos="#1F5FD6", neg="#d6342c"):
    """작은 막대 그래프 SVG (0 기준선 위아래)."""
    if not vals:
        return ""
    m = max(abs(v) for v in vals) or 1
    bw, mid = w / len(vals), h / 2
    out = [f'<line x1="0" y1="{mid}" x2="{w}" y2="{mid}" stroke="#9fb6dd" stroke-width="1"/>']
    for i, v in enumerate(vals):
        bh = abs(v) / m * (mid - 4)
        out.append(f'<rect x="{i * bw + bw * .2:.1f}" y="{(mid - bh if v >= 0 else mid):.1f}" width="{bw * .6:.1f}" '
                   f'height="{max(bh, 1):.1f}" fill="{pos if v >= 0 else neg}"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def chip(stage):
    c = L.STAGE_COLOR.get(stage, "#eee")
    return f'<span class="chip" style="background:{c};color:{"#fff" if stage in ("심각", "경계") else INK}">{stage}</span>'


# ======================= 데이터 =======================
@st.cache_data
def load():
    d, problems = L.load_all()
    d["staged"] = L.assign_stage(d["pred_dong_month"])
    return d, problems


D, problems = load()
if problems:
    st.error("데이터 계약과 다른 부분이 있어요: " + " / ".join(problems))
    st.stop()
staged, sig, geo = D["staged"], D["signals_dong_month"], D["geo"]
MONTHS = sorted(staged["기준월"].unique())
PRED = L.SOURCE["pred_dong_month.csv"]
STORE = L.SOURCE["stores_dong_quarter.csv"]

# ======================= 상태 (주소창 쿼리) =======================
qp = st.query_params
page = qp.get("page") if qp.get("page") in PAGES else "map"
_m = str(qp.get("month", ""))
month = int(_m) if _m.isdigit() and int(_m) in MONTHS else MONTHS[-1]
cur = staged[staged["기준월"] == month]
gu = qp.get("gu") if qp.get("gu") in set(cur["구군"]) else "부산 전체"
ind = qp.get("ind") if qp.get("ind") in [x for x, _ in INDS] else "전체"
names = cur.set_index("행정동코드")
codes = list(names.sort_values(["구군", "읍면동"]).index)
dong = qp.get("dong") if qp.get("dong") in names.index else L.top_n(staged, month, 1)["행정동코드"].iloc[0]
pick = [x for x in str(qp.get("pick", "")).split(",") if x in [n for n, _ in INDS[1:]]]


def link(**kw):
    s = dict(page=page, dong=dong, month=month, gu=gu, ind=ind, pick=",".join(pick))
    s.update(kw)
    return "?" + urlencode(s)


def goto(**kw):
    st.query_params.update({k: str(v) for k, v in kw.items()})
    st.rerun()


def label(c):
    return f"{names.loc[c, '구군']} · {names.loc[c, '읍면동']}"


# ======================= 배너 =======================
steps = ""
for i, (k, (n, t)) in enumerate(PAGES.items()):
    on = k == page
    steps += (f'<a class="{"on" if on else ""}" href="{link(page=k)}" target="_self"><i>{n}</i>'
              f'<span>{"<small>STEP " + n + " / 3</small>" if on else ""}{t}</span></a>')
H(f"""<div class="hd"><div class="logo">로고</div><div><div class="t1">부산신용보증재단</div>
<div class="t2">부산 행정동 위험 조기진단 · 정책지원 의사결정 보조</div></div><div class="steps">{steps}</div></div>""")
H(f"""<div class="strip"><span>기준월 <b>{L.month_label(month)}</b></span><span>예측 대상 향후 6개월 내 폐업</span>
<span>학습 기준월 2023.01~2026.01</span><span>데이터 갱신 2026.07.15</span><span>모델 v0.1 ({PRED})</span>
<span class="r">출처: 인허가(행정안전부) · 카드소비·생활인구(부산광역시) · 보증(부산신용보증재단)</span></div>""")


def rail(active):
    items = [("▦", "지도", "map"), ("☰", "조건", "map"), ("◫", "상세", "detail"), ("⇆", "비교", "map"), ("★", "내 목록", "data")]
    H('<div class="rail">' + "".join(
        f'<a class="{"on" if lab == active else ""}" href="{link(page=p)}" target="_self"><b>{ic}</b>{lab}</a>'
        for ic, lab, p in items) + "</div>")


# ======================= ① 전체 지도 =======================
def page_map():
    ind_note = None
    view, tag = staged, PRED
    if ind != "전체":
        if month == MONTHS[-1]:
            alt = L.stage_for_industry(staged, D["pred_dong_industry"], month, ind)
            if alt is not None:
                alt["전월대비"] = float("nan")   # 업종별 예측은 한 달치뿐이라 전월 대비 없음
                view, tag = pd.concat([staged[staged["기준월"] != month], alt]), f"{PRED} · {ind}"
        else:
            ind_note = "업종별 예측은 최신 기준월만 있어 전체 업종으로 보여 줍니다."
    c_rail, c_left, c_map = st.columns([0.42, 2.45, 7.9])
    with c_rail:
        rail("지도")
    with c_left:
        with st.container(border=True):
            a, b = st.columns([3, 1.3])
            a.markdown("**조건 선택**")
            b.markdown(f'<div style="text-align:right"><a href="?page=map" target="_self" class="note">초기화 ⟲</a></div>',
                       unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            mm = m1.selectbox("기준월", MONTHS[::-1], index=MONTHS[::-1].index(month), format_func=L.month_label)
            gus = ["부산 전체"] + sorted(cur["구군"].unique())
            gg = m2.selectbox("구·군", gus, index=gus.index(gu),
                              format_func=lambda g: f"전체 ({cur['구군'].nunique()}개)" if g == "부산 전체" else g)
            hold = st.checkbox("판단 보류 동 표시 (영업점포 30곳 미만)", value=True)
        if (mm, gg) != (month, gu):
            goto(month=mm, gu=gg, page="map")
        grid = "".join(f'<a class="{"on" if nm == ind else ""}" href="{link(page="map", ind=nm)}" target="_self">'
                       f'<span>{ic}</span>{nm}</a>' for nm, ic in INDS)
        H(f'<div class="pnl"><h5>카드업종 <span style="color:{BLUE}">11개</span></h5><div class="grid4">{grid}</div></div>')
        with st.expander("상세조건 · 최소 점포 수 · 예측 폐업률"):
            min_shop = st.slider("영업 점포 최소 수", 0, 300, 0, 10)
            rng = st.slider("예측 폐업률 범위(%)", 0.0, 15.0, (0.0, 15.0), 0.5)
        t = L.top_n(view, month, 5, gu)
        rows = "".join(
            f'<a href="{link(page="detail", dong=x["행정동코드"])}" target="_self"><span class="k">{i + 1}</span>'
            f'<span>{x["구군"]} {x["읍면동"]}</span><span class="p">{x["폐업위험률"]:.1f}%</span>'
            f'<span class="u">{"" if pd.isna(x["전월대비"]) else ("%+.1f%%p " % x["전월대비"]) + ("↑" if x["전월대비"] > 0 else "↓")}</span></a>'
            for i, (_, x) in enumerate(t.iterrows()))
        H(f"""<div class="pnl"><h5>⚠ 위험순위 TOP 5</h5><div class="top5">
<div class="rw note" style="border:0"><span style="color:#d6342c;font-weight:700">{ind if ind != "전체" else "전체 업종"}</span>
<span>{L.month_label(month)} 기준 · 전월 대비</span></div>{rows}</div></div>""")
        if st.button("TOP 5 팝업 다시 열기", use_container_width=True):
            st.session_state["pop_n"] = st.session_state.get("pop_n", 0) + 1

    with c_map:
        if ind_note:
            st.caption(ind_note)
        v = view.copy()
        out = (v["영업점포수"] < min_shop) | (v["폐업위험률"] < rng[0]) | (v["폐업위험률"] > rng[1])
        v.loc[(v["기준월"] == month) & out, "단계"] = "판단 보류"
        payload = L.map_payload(v, sig, D["shap_top"], geo, month, gu, 5, tag, D["pred_dong_industry"],
                                show_hold=hold, popup_nonce=st.session_state.get("pop_n", 0))
        payload["height"] = 590
        ev = busan_map(**payload, key=f"map_{month}_{gu}_{ind}", default=None)
        if ev and ev.get("t") != st.session_state.get("_last_t"):
            st.session_state["_last_t"] = ev.get("t")
            if ev.get("action") == "detail":
                goto(page="detail", dong=ev["dong"])


# ======================= ② 행정동·업종 상세 =======================
def page_detail():
    r = names.loc[dong]
    gu_codes = list(cur[cur["구군"] == r["구군"]]["행정동코드"])
    yo = L.area_yoy(sig, [dong], month)
    byo = L.area_yoy(sig, list(cur["행정동코드"]), month)
    stx = L.store_stats(D["stores_dong_quarter"], [dong])
    pi = D["pred_dong_industry"]
    pi = pi[(pi["행정동코드"] == dong) & (pi["기준월"] == pi["기준월"].max())].sort_values("폐업위험률", ascending=False)
    sh = D["shap_top"]
    sh = sh[(sh["행정동코드"] == dong) & (sh["기준월"] == sh["기준월"].max())].sort_values("순위")
    rank = "-" if pd.isna(r["순위"]) else int(r["순위"])
    n_all = len(cur)

    c_rail, c_left, c_main = st.columns([0.42, 1.7, 8.6])
    with c_rail:
        rail("상세")
    # ---- 왼쪽 패널 ----
    with c_left, st.container(border=True):
        H(f'<a href="{link(page="map")}" target="_self" style="color:{BLUE};font-weight:700;font-size:12.5px">← 전체 지도로</a>')
        nd = st.selectbox("선택한 행정동", codes, index=codes.index(dong), format_func=label)
        nm = st.selectbox("기준월", MONTHS[::-1], index=MONTHS[::-1].index(month), format_func=L.month_label)
        if (nd, nm) != (dong, month):
            goto(dong=nd, month=nm, page="detail")
        H('<div class="rw note" style="border:0"><span>비교 대상</span><span>최대 3곳</span></div>')
        cb = st.checkbox("부산 평균", True)
        cg = st.checkbox(f"{r['구군']} 평균", True)
        extra = st.selectbox("직접 추가", [""] + [c for c in codes if c != dong],
                             format_func=lambda c: "행정동 추가…" if c == "" else label(c))
        picked = st.multiselect("업종", [x for x, _ in INDS[1:]], default=pick or pi["카드업종"].head(2).tolist())
        pick[:] = picked
        if st.button("선택 업종 담고 근거 보기 →", type="primary", use_container_width=True):
            goto(page="data", pick=",".join(picked))

    with c_main:
        # ---- 제목 ----
        trend = " · 3개월 연속 상승" if r["연속상승"] else ""
        s_now = sig[(sig["행정동코드"] == dong) & (sig["기준월"] == month)]
        H(f"""<div style="display:flex;align-items:flex-end;gap:10px;margin-top:2px">
<span style="font-size:26px;font-weight:700;color:{INK};line-height:1.1">{r['읍면동']}</span>
<span style="color:{MUT};font-size:14px">{r['구군']}</span>{chip(r['단계'])}
<span class="note" style="font-size:12.5px">{n_all}개 동 중 {rank}위{trend}</span>
<a href="{link(page='data')}" target="_self" style="margin-left:auto;color:{BLUE};font-size:12px;font-weight:700">리포트 PDF · 원자료 CSV</a></div>
<p style="font-size:13px;color:#3b4250;margin:4px 0 10px">{L.summary_sentence(r, s_now.iloc[0] if len(s_now) else None)}</p>""")

        # ---- 1행 ----
        left, right = st.columns([3.55, 1.6])
        with left:
            k1, k2 = st.columns([1.75, 1])
            risk, d = r["폐업위험률"], r["전월대비"]
            mx = max(12.0, (0 if pd.isna(risk) else risk) * 1.3)
            with k1:
                H(f"""<div class="card navy" style="min-height:212px">
<div style="display:flex;justify-content:space-between;align-items:center">
<span style="font-size:14px;font-weight:700">폐업위험률 <span style="font-weight:400;color:#9fb2cb;font-size:12px">모델 예측 · 향후 6개월</span> {bd(PRED)}</span>
<span style="border:1px solid #6f87a8;padding:2px 8px;font-size:11.5px">↗ 전월 {'-' if pd.isna(d) else f'{d:+.1f}%p'}</span></div>
<div style="font-size:64px;font-weight:700;line-height:1;margin:16px 0 22px">{'판단 보류' if pd.isna(risk) else f'{risk:.1f}%'}</div>
<div style="position:relative;height:8px;background:#28467c">
<div style="width:{0 if pd.isna(risk) else risk / mx * 100:.0f}%;height:100%;background:#8db4f0"></div>
<div style="position:absolute;left:{r['부산평균'] / mx * 100:.0f}%;top:-5px;bottom:-5px;border-left:2px solid #fff"></div></div>
<div style="display:flex;justify-content:space-between;font-size:12px;color:#c9d6e6;margin-top:8px">
<b>부산 평균 {r['부산평균']}% · {r['구군']} {r['구평균']}%</b><span>0 — {mx:.0f}%</span></div></div>""")
            with k2:
                top_pct = "" if rank == "-" else f"상위 {rank / n_all * 100:.0f}%"
                H(f"""<div class="card" style="min-height:101px;margin-bottom:10px"><div class="kv">예상 폐업 점포 {bd(PRED)}<b>{int(r['예상폐업점포'])}곳</b></div>
<div class="note" style="text-align:right;margin-top:-18px">영업 {int(r['영업점포수'])}곳 중</div></div>
<div class="card" style="min-height:101px"><div class="kv">위험 순위<b>{rank}위</b></div>
<div class="note" style="text-align:right;margin-top:-18px">{n_all}개 동 중 {top_pct}</div></div>""")
            sigs = [("최근 6개월 폐업률", "-" if not stx else f"{stx['close6']}%",
                     f"전년 동기 {stx['close6_prev']}%" if stx and stx["close6_prev"] is not None else "", STORE),
                    ("1년 미만 폐업 비중", "-" if not stx else f"{stx['young']:.0f}%", "최근 4개 분기", STORE),
                    ("카드소비 전년비", "-" if yo["카드소비"] is None else f"{yo['카드소비']:+.1f}%", f"부산 {byo['카드소비']:+.1f}%", "실측"),
                    ("방문인구 전년비", "-" if yo["방문인구_월"] is None else f"{yo['방문인구_월']:+.1f}%", f"부산 {byo['방문인구_월']:+.1f}%", "실측")]
            cells = "".join(f'<div style="flex:1;padding-left:{0 if i == 0 else 12}px">'
                            f'<div class="note" style="font-size:12px">{a_} {bd(k)}</div>'
                            f'<div style="font-size:26px;font-weight:700;color:{INK};margin:2px 0">{v}</div>'
                            f'<div class="note">{s_}</div></div>' for i, (a_, v, s_, k) in enumerate(sigs))
            H(f'<div class="card" style="margin-top:10px"><h4>상권 실측 신호 <span class="note" style="font-weight:400">직전 기간</span></h4>'
              f'<div style="display:flex">{cells}</div></div>')
        with right:
            g = L.guarantee_gu(D["guarantee_gu_industry"], r["구군"])
            if g:
                rows = ""
                for nm_, x in g["업종"].head(4).iterrows():
                    short = (nm_.split("(")[0].replace("협회 및 단체, 수리 및 기타 ", "").replace(" 및 ", "·")).strip()[:9]
                    sel_ = "음식점" in nm_
                    rows += (f'<div class="rw"><span style="font-weight:{700 if sel_ else 400}">{short}'
                             f'{" <span style=color:" + BLUE + ";font-size:11px;font-weight:700>선택 업종</span>" if sel_ else ""}</span>'
                             f'<span><b style="color:{BLUE if x["사고율"] > x["부산_사고율"] else INK}">{x["사고율"]:.2f}%</b>'
                             f' <span class="note">{x["보증잔액"] / 100:,.0f}억</span></span></div>')
                H(f"""<div class="card" style="padding:0;min-height:376px">
<div class="lblue" style="padding:12px 14px">
<div style="font-size:14px;font-weight:700">재단 보증현황 <span class="note" style="font-weight:400">{r['구군']}</span> {bd('실측')}</div>
<div class="note" style="margin-top:4px">보증 사고율</div>
<div style="display:flex;align-items:flex-end;justify-content:space-between">
<span style="font-size:36px;font-weight:700;line-height:1.1">{g['사고율']:.2f}%</span>
<span style="border:1px solid #9fb6dd;padding:2px 6px;font-size:10.5px;color:#3b4250">부산 {g['부산사고율']:.2f}%</span></div></div>
<div style="padding:10px 14px">
<div style="display:flex;justify-content:space-between">
<div class="kv">보증 잔액<b style="font-size:17px">{g['잔액억']:,.0f}억</b><span style="font-size:10px">{g['구군수']}개 구·군 중 {g['잔액순위']}위</span></div>
<div class="kv">보증 사고<b style="font-size:17px">{g['사고억']:,.0f}억</b><span style="font-size:10px">{g['사고건수']}건</span></div></div>
<div class="rw" style="font-weight:700;margin-top:6px">업종별 사고율<span class="note" style="font-weight:400">사고율 · 잔액</span></div>
{rows}<div class="note" style="font-size:10px;margin-top:6px">2023.1Q~25.4Q · 구·군 단위(행정동 자료 없음) · 정상화 미반영</div></div></div>""")

        # ---- 2행: 업종별 · 원인 · 추이 ----
        c1, c2, c3 = st.columns([1.5, 1.9, 1.45])
        with c1:
            avg = float(r["부산평균"])
            mx = max(12.0, pi["폐업위험률"].max() * 1.12)
            bars = ""
            for _, x in pi.head(6).iterrows():
                dd = x["폐업위험률"] - avg
                bars += (f'<div class="ib"><span class="nm">{x["카드업종"]}</span><span class="tr">'
                         f'<span class="fl" style="width:{x["폐업위험률"] / mx * 100:.0f}%;background:{BLUE if dd > 0 else "#b1c6ef"}"></span>'
                         f'<span class="av" style="left:{avg / mx * 100:.0f}%"></span></span><span class="v">{x["폐업위험률"]:.1f}%</span>'
                         f'<span class="d" style="color:{"#d6342c" if dd > 0 else MUT}">{dd:+.1f}</span></div>')
            H(f'<div class="card" style="min-height:320px"><h4>업종별 폐업위험 {bd(PRED)}<span class="n">향후 6개월</span></h4>'
              f'<div class="note" style="margin:-4px 0 4px">점선 = 부산 평균 {avg}%</div>{bars}</div>')
        with c2:
            ups = sh[sh["방향"] == "상승"]
            w = ups["기여도"].clip(lower=0)
            vals = (w / w.sum() * 86).round(0).tolist() if w.sum() else []
            vals.append(max(0, 100 - sum(vals)))
            labs = list(ups["설명"]) + ["기타 요인"]
            cols = ["#E8EEF9", "#7EA6EE", "#3D73DC", "#2B4A86"]
            items = "".join(f'<div class="rw" style="border-color:#28467c;color:#fff;align-items:flex-start">'
                            f'<span style="min-width:0"><span style="display:inline-block;width:10px;height:10px;background:{cols[i % 4]};margin-right:6px"></span>{t_}</span>'
                            f'<b style="font-size:15px">{v_:.0f}%</b></div>' for i, (t_, v_) in enumerate(zip(labs, vals)))
            low = sh[sh["방향"] == "하락"]
            H(f"""<div class="card navy" style="min-height:320px"><h4>폐업위험을 높이는 원인 {bd(PRED)}
<span class="n" style="color:#9fb2cb">SHAP 기여 비중 · 인과 아님</span></h4>
<div style="display:flex;gap:12px;align-items:center"><div style="flex:1 1 auto;min-width:0;font-size:12px">{items}</div>
<div style="flex:0 0 118px">{L.donut_svg(vals, cols, 118)}</div></div>
<div style="font-size:11.5px;color:#c9d6e6;margin-top:10px">위험을 낮춘 요인 · {low.iloc[0]["설명"] if len(low) else "-"}</div></div>""")
        with c3, st.container(border=True):
            H('<div style="font-size:15px;font-weight:700;margin-bottom:4px">언제부터 나빠졌나</div>')
            s1, s2 = L.index_series(sig, [dong], "카드소비"), L.index_series(sig, gu_codes, "카드소비")
            q = stx["quarterly"] if stx else pd.Series(dtype=float)
            a_, b_ = st.columns([1.15, 1])
            fig = go.Figure()
            fig.add_scatter(x=[L.month_label(m) for m in s1.index], y=s1.values, name=r["읍면동"], line=dict(color=BLUE, width=2))
            fig.add_scatter(x=[L.month_label(m) for m in s2.index], y=s2.values, name=r["구군"], line=dict(color="#9aa3ad", dash="dot"))
            fig.update_layout(height=190, margin=dict(l=0, r=0, t=24, b=0), title=dict(text="카드소비 지수(23.01=100) 실측", font_size=11),
                              legend=dict(orientation="h", y=-0.25, font_size=9), xaxis=dict(nticks=3, tickfont_size=9),
                              yaxis=dict(tickfont_size=9), plot_bgcolor="#fff")
            a_.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            if len(q):
                fig = go.Figure(go.Bar(x=[x.replace("20", "", 1) for x in q.index], y=q.values,
                                       marker_color=[BLUE if i >= len(q) - 1 else "#a9c2f2" for i in range(len(q))]))
                fig.update_layout(height=190, margin=dict(l=0, r=0, t=24, b=0), title=dict(text=f"분기별 폐업 신고 · {STORE}", font_size=11),
                                  yaxis_visible=False, xaxis=dict(tickfont_size=9, nticks=4), plot_bgcolor="#fff")
                b_.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                H(f'<div style="text-align:right;font-weight:700;font-size:13px;margin-top:-10px">최근 분기 {int(q.iloc[-1])}건</div>')

        # ---- 3행: 주변 지도 | 비교 · 신뢰도 · 점포 순증 ----
        c1, c2 = st.columns([1.05, 1.3])
        with c1, st.container(border=True):
            H(f'<div class="rw" style="border:0;font-size:15px;font-weight:700">주변 행정동 위험단계 {bd(PRED)}'
              f'<span class="note" style="font-weight:400">굵은 테두리 = 선택한 동</span></div>')
            sub = cur[cur["구군"] == r["구군"]]
            fig = px.choropleth(sub, geojson=geo, locations="행정동코드", featureidkey="properties.행정동코드", color="단계",
                                category_orders={"단계": L.STAGES}, color_discrete_map=L.STAGE_COLOR, hover_name="읍면동",
                                hover_data={"폐업위험률": ":.1f", "행정동코드": False, "단계": False})
            fig.update_traces(marker_line_color="#fff", marker_line_width=1)
            sel = sub[sub["행정동코드"] == dong]
            fig.add_trace(go.Choropleth(geojson=geo, locations=sel["행정동코드"], featureidkey="properties.행정동코드", z=[1],
                                        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
                                        marker_line_color=INK, marker_line_width=3.5, hoverinfo="skip"))
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=370, margin=dict(l=0, r=0, t=0, b=0),
                              legend=dict(orientation="h", y=-0.02, title="", font_size=10))
            try:   # Streamlit 1.35+ : 지도에서 다른 동을 누르면 그 동으로
                ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="nbmap")
                pts = ev.selection.points if ev else []
            except Exception:
                st.plotly_chart(fig, use_container_width=True)
                pts = []
            if pts and pts[0].get("location") and pts[0]["location"] != dong:
                goto(dong=pts[0]["location"], page="detail")
            H('<div class="note">상권 위험단계(안): 재단 리스크 5단계 명칭을 빌림 · 재단 KRI 단계와는 별개 지표, 기준은 팀 확정 전</div>')
        with c2:
            t = L.compare_table(staged, sig, month, dong)
            if extra:
                t.insert(1, names.loc[extra, "읍면동"], L.compare_table(staged, sig, month, extra).iloc[:, 0])
            keep = [t.columns[0]] + ([t.columns[1]] if extra else []) + ([r["구군"]] if cg else []) + (["부산"] if cb else [])
            t = t[[c for c in keep if c in t.columns]]
            head = "".join(f'<th class="{"sel" if i == 0 else ""}">{c}</th>' for i, c in enumerate(t.columns))
            body = "".join(f"<tr><td>{idx}</td>" + "".join(f'<td class="{"sel" if i == 0 else ""}">{"-" if pd.isna(v) else f"{v:.1f}"}</td>'
                                                          for i, v in enumerate(row)) + "</tr>" for idx, row in t.iterrows())
            H(f'<div class="card"><h4>주변과 비교 <span class="n">예측 {bd(PRED)} · 전년비 {bd("실측")}</span></h4>'
              f'<table class="tbl"><tr><th></th>{head}</tr>{body}</table></div>')
            k1, k2 = st.columns([1.05, 1])
            with k1:
                H(f"""<div class="card" style="min-height:178px"><h4>예측 신뢰도 {bd(PRED)}</h4>
<div style="display:flex;gap:10px">
<div class="kv" style="flex:1">판단 근거 점포<b style="font-size:21px">{int(r['영업점포수'])}곳</b><span style="font-size:10px">30곳 이상이면 판단</span></div>
<div class="kv" style="flex:1">상위 3요인 비중<b style="font-size:21px">{sum(vals[:-1]):.0f}%</b><span style="font-size:10px">SHAP 합계</span></div></div>
<div class="kv" style="margin-top:8px">자료 최신월 <b style="display:inline;font-size:14px">{L.month_label(month)}</b> <span style="font-size:10px">카드·인구 기준</span></div></div>""")
            with k2:
                if stx:
                    H(f"""<div class="card lblue" style="min-height:178px"><h4>점포 순증 {bd(STORE)}<span class="n">최근 4개 분기</span></h4>
<div style="display:flex;justify-content:space-between;align-items:flex-end">
<div><div style="font-size:30px;font-weight:700;line-height:1">{stx['net']:+d}곳</div>
<div class="note">개업 {stx['opened']} · 폐업 {stx['closed']}</div></div>{bars_svg(stx['net_q'].tolist(), 104, 64)}</div></div>""")
        H(f'<p class="note" style="margin-top:10px">예측·요인·업종 위험·점포 집계는 모델/인허가 연결 전 {PRED}값입니다. '
          '카드 소비·생활인구·재단 보증은 실제 자료입니다. 요인은 예측에 영향을 준 정도이며 원인이 아닙니다.</p>')


# ======================= ③ 근거 확인 및 자료 다운 =======================
FILES = [
    ("pred_dong_month.csv", "행정동×월 폐업위험률 · 예상 폐업 점포", "행정동 205 × 2025.01~2026.07", "모델 v0.1"),
    ("pred_dong_industry.csv", "행정동×카드업종 폐업위험률", "행정동 205 × 11업종 · 최신월", "모델 v0.1"),
    ("shap_top.csv", "행정동별 위험 요인 Top 3 + 낮춘 요인", "행정동 205 · 최신월", "모델 v0.1 (SHAP)"),
    ("stores_dong_quarter.csv", "행정동×분기 개업·폐업·1년 미만 폐업", "행정동 205 × 2024Q3~2026Q2", "인허가(행정안전부) 집계 예정"),
    ("signals_dong_month.csv", "카드 소비·생활인구 월값과 전년비", "행정동 205 × 2023.01~2026.07", "부산광역시 카드·통신"),
    ("card_dong_industry_month.csv", "행정동×카드업종 일평균 결제금액·건수", "행정동 205 × 11업종 × 43개월", "부산광역시 빅데이터담당관"),
    ("guarantee_gu_industry.csv", "구·군×산업 대분류 보증 잔액·사고", "16개 구·군 · 2023.1Q~2025.4Q", "부산신용보증재단"),
]


@st.cache_data
def raw(fname):
    return pd.read_csv(L.DATA / fname, dtype={"행정동코드": str})


def page_data():
    r = names.loc[dong]
    c_rail, c_main = st.columns([0.42, 10.3])
    with c_rail:
        rail("내 목록")
    with c_main:
        H(f'<div style="font-size:24px;font-weight:700;margin:2px 0 4px">근거 확인 및 자료 다운</div>')
        t1, t2 = st.tabs(["선택한 동 근거 확인", "원자료 · CSV 내려받기"])
        with t1:
            picked = pick
            a, b = st.columns([2.2, 1])
            nd = a.selectbox("행정동", codes, index=codes.index(dong), format_func=label)
            if nd != dong:
                goto(dong=nd, page="data")
            with b:
                H(f'<div style="padding-top:28px;text-align:right"><a href="{link(page="detail")}" target="_self" '
                  f'style="color:{BLUE};font-weight:700">← ② 상세로 돌아가기</a></div>')
            H(f'<div style="font-size:18px;font-weight:700;margin:4px 0">{r["구군"]} {r["읍면동"]} {chip(r["단계"])}</div>'
              f'<div class="note" style="font-size:13px">담은 업종: <b style="color:{INK}">{", ".join(picked) if picked else "없음 (② 화면 왼쪽에서 고를 수 있어요)"}</b></div>')
            l, rr = st.columns(2)
            with l, st.container(border=True):
                st.markdown("**현장 확인 질문**")
                qs = {"데이터 확인": ["카드 소비 변화가 특정 대형 점포의 개점·폐점 때문인가요?", "영업 점포 수가 적어 숫자가 흔들리는 동은 아닌가요?"],
                      "지역 상황": ["최근 3개월 사이 개발·공사·휴업 같은 큰 변화가 있었나요?", "같은 구의 다른 동과 비교해 이 동만의 특이점이 있나요?"],
                      "재단 내부자료": ["담은 업종의 보증 업체에서 연체·사고가 늘었나요?", "이 지역 보증 잔액이 최근 빠르게 늘었나요?"]}
                checked = []
                for grp, items in qs.items():
                    st.caption(grp)
                    for q in items:
                        if st.checkbox(q, key=f"q_{dong}_{q}"):
                            checked.append(q)
                memo = st.text_area("담당자 메모", key=f"memo_{dong}", height=90)
            with rr, st.container(border=True):
                st.markdown("**자료 신뢰도와 유의사항**")
                H(f"""<div style="font-size:12.5px;margin-bottom:12px">
<div style="padding:3px 0">· 폐업위험률·요인·업종 위험·점포 집계 {bd(PRED)} 모델·인허가 연결 전</div>
<div style="padding:3px 0">· 카드 소비·생활인구 {bd('실측')} 2023.01~2026.07</div>
<div style="padding:3px 0">· 재단 보증 {bd('실측')} 구·군 단위 (행정동 자료 없음)</div>
<div style="padding:3px 0">· 요인은 SHAP 기여도이며 인과관계가 아닙니다.</div>
<div style="padding:3px 0">· 보증 승인·제한 판단에 쓰지 않습니다.</div></div>""")
                shx = D["shap_top"]
                shx = shx[shx["행정동코드"] == dong].sort_values("순위")
                report = "\n".join([f"# {r['구군']} {r['읍면동']} 근거 확인 리포트", f"- 기준월: {L.month_label(month)}",
                                    f"- 단계: {r['단계']} / 폐업위험률: {r['폐업위험률']}% (부산 평균 {r['부산평균']}%) [{PRED}]",
                                    "## 요인 (SHAP, 인과 아님)", *[f"- {x}" for x in shx["설명"]],
                                    "## 담은 업종", *([f"- {x}" for x in picked] or ["- 없음"]),
                                    "## 확인한 질문", *([f"- [x] {x}" for x in checked] or ["- 없음"]), "## 메모", memo or "-"])
                st.download_button("근거 리포트 내려받기 (.md)", report.encode("utf-8"), file_name=f"{r['읍면동']}_근거리포트.md",
                                   use_container_width=True, type="primary")
                one = staged[staged["행정동코드"] == dong][["기준월", "구군", "읍면동", "폐업위험률", "단계", "부산평균", "구평균", "순위"]]
                one = one.merge(sig[sig["행정동코드"] == dong].drop(columns=["행정동코드"]), on="기준월", how="left")
                st.download_button("이 동의 월별 지표 (.csv)", one.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"{r['읍면동']}_월별지표.csv", use_container_width=True)
                st.caption("PDF가 필요하면 리포트(.md)를 열어 인쇄 → PDF로 저장하세요.")
        with t2:
            H('<p class="note">대시보드가 읽는 파일 그대로입니다. 구·군과 기간으로 걸러서 받을 수 있어요.</p>')
            f1, f2 = st.columns(2)
            fgu = f1.selectbox("구·군 필터", ["전체"] + sorted(cur["구군"].unique()))
            allm = sorted(set(sig["기준월"]))
            fm = f2.select_slider("기간 (월 단위 파일)", options=allm, value=(allm[0], allm[-1]), format_func=L.month_label)
            gcodes = set(cur[cur["구군"] == fgu]["행정동코드"]) if fgu != "전체" else None
            buf = io.BytesIO()
            zf = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
            meta = []
            for fname, desc, unit, src in FILES:
                df = raw(fname)
                if gcodes is not None:
                    if "행정동코드" in df:
                        df = df[df["행정동코드"].isin(gcodes)]
                    elif "구군" in df:
                        df = df[df["구군"] == fgu]
                if "기준월" in df:
                    df = df[(df["기준월"] >= fm[0]) & (df["기준월"] <= fm[1])]
                kind = L.SOURCE[fname]
                meta.append({"파일": fname, "내용": desc, "단위·기간": unit, "출처": src, "구분": kind, "행 수": len(df)})
                zf.writestr(fname, df.to_csv(index=False).encode("utf-8-sig"))
                with st.container(border=True):
                    a, b, c = st.columns([5, 1.1, 1.1])
                    with a:
                        H(f'<b>{fname}</b> {bd(kind)}<br><span class="note">{desc} · {unit} · 출처 {src} · {len(df):,}행</span>')
                    with b.popover("미리보기", use_container_width=True):
                        st.dataframe(df.head(50), hide_index=True)
                    c.download_button("CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name=fname, key=f"dl_{fname}",
                                      use_container_width=True)
            zf.writestr("자료목록.csv", pd.DataFrame(meta).to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("busan_dong.geojson", (L.DATA / "busan_dong.geojson").read_bytes())
            zf.close()
            st.download_button("전체 묶음 내려받기 (.zip)", buf.getvalue(), file_name="부산상권위험_자료.zip", type="primary")


{"map": page_map, "detail": page_detail, "data": page_data}[page]()
st.query_params.update({"page": page, "dong": dong, "month": str(month), "gu": gu, "ind": ind, "pick": ",".join(pick)})
