"""부산 상권 위험 조기진단 대시보드 — Streamlit (Figma S-00 / 2페이지 구성 반영)

실행:  pip install -r requirements.txt  →  streamlit run app.py
화면:  ① 전체 지도  ② 행정동·업종 상세(스크롤)  ③ 근거 확인 및 자료 다운
상태:  주소창의 ?page=&dong=&month=&gu=&ind= 로 관리 → 배너 단계 버튼·새로고침·공유 링크 모두 같은 화면을 연다.
데이터: data/ 의 CSV (DB 없음). 가상 파일은 logic.SOURCE 참고, 모델 결과가 나오면 같은 이름·컬럼으로 교체.
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

NAVY, NAVY2, BLUE, BLUE2, SKY, MUT, INK, LINE = "#1C2E57", "#1f3a5f", "#256ef4", "#4a86f4", "#00A0E8", "#6B7280", "#1A1D23", "#E3E8EF"
PAGES = {"map": ("1", "전체"), "detail": ("2", "행정동·업종 상세"), "data": ("3", "근거 확인 및 자료 다운")}
INDS = [("전체", "▦"), ("음식/주점", "🍴"), ("음식료품", "🧺"), ("유통", "🛒"), ("미용", "✂"), ("의료", "✚"),
        ("교육", "📖"), ("생활", "🏠"), ("여가/문화", "🎭"), ("여행/숙박", "🧳"), ("의류/잡화", "👕"), ("자동차", "🚗")]

st.markdown(f"""<style>
header[data-testid="stHeader"]{{display:none}}
.block-container{{padding:0 1.2rem 2rem;max-width:1480px}}
section.main > div{{padding-top:0}}
a{{text-decoration:none}}
.hd{{background:{NAVY2};margin:0 -1.2rem;padding:12px 1.6rem;display:flex;align-items:center;gap:14px}}
.hd .logo{{width:38px;height:38px;border-radius:6px;background:#2b5c94;color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}}
.hd .t1{{color:#fff;font-size:19px;font-weight:700;line-height:1.15}} .hd .t2{{color:#b9c7da;font-size:11.5px}}
.steps{{margin-left:auto;display:flex;align-items:center;gap:6px}}
.steps a{{display:flex;align-items:center;gap:8px;border:1px solid #6f87a8;border-radius:22px;padding:5px 14px 5px 6px;color:#c9d6e6;font-size:12.5px}}
.steps a i{{font-style:normal;width:22px;height:22px;border-radius:50%;border:1px solid #9fb2cb;display:flex;align-items:center;justify-content:center;font-size:11px}}
.steps a.on{{background:#fff;color:{NAVY};font-weight:700;border-color:#fff}} .steps a.on i{{background:{NAVY};color:#fff;border-color:{NAVY}}}
.steps a.on small{{display:block;font-size:9px;color:{BLUE};font-weight:700;line-height:1}}
.steps .dots{{color:#6f87a8;letter-spacing:2px}}
.warn{{background:{BLUE};color:#fff;font-size:12.5px;font-weight:700;padding:7px 14px;border-radius:6px;margin-left:14px}}
.strip{{background:#e8eef6;margin:0 -1.2rem 14px;padding:6px 1.6rem;font-size:12px;color:{NAVY2};display:flex;gap:28px;flex-wrap:wrap}}
.rail{{background:{NAVY2};border-radius:10px;padding:8px 0;min-height:760px}}
.rail a{{display:block;text-align:center;color:#c9d6e6;font-size:11px;padding:10px 0}} .rail a b{{display:block;font-size:17px;color:#fff;font-weight:400}}
.rail a.on{{background:{BLUE};color:#fff}}
.card{{background:#fff;border:1px solid {LINE};border-radius:12px;padding:18px 20px;height:100%}}
.card h4{{margin:0 0 10px;font-size:16px;color:{INK}}} .card .n{{color:{MUT};font-size:12px;font-weight:400;float:right}}
.navy{{background:{NAVY};border:0;color:#fff}} .navy h4{{color:#fff}}
.lblue{{background:#eef4fd;border-color:#d9e6fb}}
.big{{font-size:64px;font-weight:700;letter-spacing:1px;line-height:1.05}}
.kv{{font-size:13px;color:{MUT}}} .kv b{{color:{INK};font-size:26px;display:block;margin-top:2px}}
.chip{{display:inline-block;font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:12px;margin-left:6px}}
.badge{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10.5px;font-weight:700;margin-left:4px;vertical-align:middle}}
.real{{background:#eaf6ec;color:#267337}} .mock{{background:#fff3db;color:#8a5c00}}
.note{{color:{MUT};font-size:12.5px}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:13.5px;border-bottom:1px solid #f0f2f5}}
.tbl{{width:100%;border-collapse:collapse;font-size:13.5px}} .tbl th{{color:{MUT};font-weight:400;font-size:12px;text-align:right;padding:6px}}
.tbl td{{text-align:right;padding:9px 6px;border-top:1px solid #f0f2f5}} .tbl td:first-child,.tbl th:first-child{{text-align:left;color:#3b4250}}
.tbl .sel{{background:#eef4fd;color:{BLUE};font-weight:700}}
.ibar{{display:flex;align-items:center;gap:10px;font-size:13.5px;padding:5px 0}} .ibar .nm{{width:86px;font-weight:700}}
.ibar .tr{{flex:1;height:12px;background:#eef1f5;border-radius:3px;position:relative}} .ibar .fl{{height:100%;border-radius:3px}}
.ibar .av{{position:absolute;top:-4px;bottom:-4px;width:0;border-left:1.5px dashed {INK}}}
.ibar .v{{width:44px;text-align:right;font-weight:700}} .ibar .d{{width:52px;text-align:right;font-size:12px}}
.top5 .r{{display:flex;align-items:center;gap:8px;padding:7px 0;font-size:13.5px;border-bottom:1px solid #f0f2f5}}
.top5 .k{{color:{BLUE};font-weight:700;width:14px}} .top5 .p{{margin-left:auto;font-weight:700}} .top5 .u{{color:#d6342c;font-size:12px;width:62px;text-align:right}}
div[data-testid="stVerticalBlockBorderWrapper"]{{border-radius:12px}}
.stButton>button{{border-radius:8px}}
</style>""", unsafe_allow_html=True)


def badge(kind):
    return f'<span class="badge {"real" if kind == "실측" else "mock"}">{kind}</span>'


def stage_chip(stage):
    c = L.STAGE_COLOR.get(stage, "#eee")
    fg = "#fff" if stage in ("심각", "경계") else INK
    return f'<span class="chip" style="background:{c};color:{fg}">{stage}</span>'


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

# ======================= 상태 (주소창 쿼리) =======================
qp = st.query_params
page = qp.get("page", "map") if qp.get("page") in PAGES else "map"
month = int(qp.get("month", MONTHS[-1])) if str(qp.get("month", "")).isdigit() and int(qp.get("month")) in MONTHS else MONTHS[-1]
gu = qp.get("gu", "부산 전체")
ind = qp.get("ind", "전체")
cur = staged[staged["기준월"] == month]
names = cur.set_index("행정동코드")
codes = list(names.sort_values(["구군", "읍면동"]).index)
dong = qp.get("dong") if qp.get("dong") in names.index else L.top_n(staged, month, 1)["행정동코드"].iloc[0]


def link(**kw):
    s = dict(page=page, dong=dong, month=month, gu=gu, ind=ind)
    s.update(kw)
    return "?" + urlencode(s)


def goto(**kw):
    st.query_params.update({k: str(v) for k, v in kw.items()})
    st.rerun()


def label(c):
    return f"{names.loc[c, '구군']} {names.loc[c, '읍면동']}"


# ======================= 배너 =======================
steps = ""
for i, (k, (n, t)) in enumerate(PAGES.items()):
    on = k == page
    steps += (f'<a class="{"on" if on else ""}" href="{link(page=k)}" target="_self"><i>{n}</i>'
              f'<span>{"<small>STEP " + n + " / 3</small>" if on else ""}{t}</span></a>')
    if i < 2:
        steps += '<span class="dots">·····</span>'
st.markdown(f'<div class="hd"><div class="logo">로고</div><div><div class="t1">부산신용보증재단</div>'
            f'<div class="t2">부산 행정동 위험 조기진단 · 정책지원 의사결정 보조</div></div>'
            f'<div class="steps">{steps}</div><div class="warn">참고자료 · 보증 승인·제한 판단 아님</div></div>',
            unsafe_allow_html=True)
st.markdown(f'<div class="strip"><span>기준월 <b>{L.month_label(month)}</b></span><span>예측 대상 향후 6개월 내 폐업</span>'
            f'<span>학습 기준월 2023.01~2026.01</span><span>모델 v0.1 ({PRED})</span>'
            f'<span>출처: 인허가(행정안전부) · 카드소비·생활인구(부산광역시) · 보증(부산신용보증재단)</span></div>',
            unsafe_allow_html=True)


def rail(active):
    items = [("▦", "지도", "map"), ("◉", "지표", "detail"), ("☰", "업종", "detail"), ("⇆", "비교", "map"),
             ("★", "내 목록", "data"), ("?", "도움말", "data")]
    h = "".join(f'<a class="{"on" if lab == active else ""}" href="{link(page=p)}" target="_self"><b>{ic}</b>{lab}</a>'
                for ic, lab, p in items)
    st.markdown(f'<div class="rail">{h}</div>', unsafe_allow_html=True)


# ======================= ① 전체 지도 =======================
def page_map():
    c_rail, c_left, c_map = st.columns([0.42, 2.3, 7.3], gap="small")
    with c_rail:
        rail("지도")
    with c_left:
        with st.container(border=True):
            a, b = st.columns([3, 1.2])
            a.markdown("**조건 선택**")
            if b.button("초기화 ⟲", key="reset"):
                goto(page="map", month=MONTHS[-1], gu="부산 전체", ind="전체")
            m1, m2 = st.columns(2)
            mm = m1.selectbox("기준월", MONTHS[::-1], index=MONTHS[::-1].index(month), format_func=L.month_label)
            gus = ["부산 전체"] + sorted(cur["구군"].unique())
            gg = m2.selectbox("구·군", gus, index=gus.index(gu) if gu in gus else 0,
                              format_func=lambda g: f"전체 ({cur['구군'].nunique()}개)" if g == "부산 전체" else g)
            hold = st.checkbox("판단 보류 동 표시", value=True, help="영업 점포가 적어 숫자가 흔들리는 동")
        with st.container(border=True):
            st.markdown(f"**카드업종** <span style='color:{BLUE};font-weight:700'>11개</span>", unsafe_allow_html=True)
            for row in range(3):
                cols = st.columns(4)
                for col, (nm, ic) in zip(cols, INDS[row * 4:row * 4 + 4]):
                    if col.button(f"{ic}\n\n{nm}", key=f"ind_{nm}", type="primary" if nm == ind else "secondary",
                                  use_container_width=True):
                        goto(ind=nm, page="map")
            with st.expander("상세조건  ·  최소 점포 수 · 예측 폐업률"):
                min_shop = st.slider("영업 점포 최소 수", 0, 300, 0, 10)
                rng = st.slider("예측 폐업률 범위(%)", 0.0, 15.0, (0.0, 15.0), 0.5)
        with st.container(border=True):
            st.markdown(f"**⚠ 위험순위 TOP 5** <span class='note' style='float:right'>{L.month_label(month)} 기준 · 전월 대비</span>",
                        unsafe_allow_html=True)
            t = L.top_n(staged, month, 5, gu)
            rows_ = "".join(
                f'<a class="r" href="{link(page="detail", dong=x["행정동코드"])}" target="_self" style="color:{INK}">'
                f'<span class="k">{i + 1}</span><span>{x["구군"]} {x["읍면동"]}</span><span class="p">{x["폐업위험률"]:.1f}%</span>'
                f'<span class="u">{"" if pd.isna(x["전월대비"]) else ("%+.1f%%p " % x["전월대비"]) + ("↑" if x["전월대비"] > 0 else "↓")}</span></a>'
                for i, (_, x) in enumerate(t.iterrows()))
            st.markdown(f'<div class="top5"><div class="r note" style="border:0"><span>전체 업종</span>'
                        f'<span style="margin-left:auto">폐업위험률 · 전월 대비</span></div>{rows_}</div>', unsafe_allow_html=True)
            if st.button("팝업으로 크게 보기", key="pop", use_container_width=True):
                st.session_state["pop_n"] = st.session_state.get("pop_n", 0) + 1
    if (mm, gg) != (month, gu):
        goto(month=mm, gu=gg)

    with c_map:
        view = staged
        tag = PRED
        if ind != "전체":
            if month == MONTHS[-1]:
                alt = L.stage_for_industry(staged, D["pred_dong_industry"], month, ind)
                view = pd.concat([staged[staged["기준월"] != month], alt]) if alt is not None else staged
                tag = f"{PRED} · {ind}"
            else:
                st.caption("업종별 예측은 최신 기준월만 있어 전체 업종으로 보여 줍니다.")
        v = view.copy()
        out = (v["영업점포수"] < min_shop) | (v["폐업위험률"] < rng[0]) | (v["폐업위험률"] > rng[1])
        v.loc[(v["기준월"] == month) & out, "단계"] = "판단 보류"
        payload = L.map_payload(v, sig, D["shap_top"], geo, month, gg, 5, tag, D["pred_dong_industry"],
                                show_hold=hold, popup_nonce=st.session_state.get("pop_n", 0))
        payload["height"] = 780
        ev = busan_map(**payload, key=f"map_{month}_{gg}_{ind}", default=None)
        if ev and ev.get("t") != st.session_state.get("_last_t"):
            st.session_state["_last_t"] = ev.get("t")
            if ev.get("action") == "detail":
                goto(page="detail", dong=ev["dong"])
        st.markdown('<p class="note">팝업의 다른 순위에 마우스를 올리면 자세히 보입니다 · 팝업을 닫으면 지도 위 행정동에 마우스를 올려 정보를 보고, '
                    '클릭하면 ② 상세로 이동합니다 · ‘한 번에 비교하기’로 여러 동을 같은 지표로 비교합니다.</p>', unsafe_allow_html=True)


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
    rank = "-" if pd.isna(r["순위"]) else f"{int(r['순위'])}"

    c_rail, c_left, c_main = st.columns([0.42, 1.75, 7.8], gap="small")
    with c_rail:
        rail("지표")
    # ---- 왼쪽 패널 ----
    with c_left, st.container(border=True):
        st.markdown(f'<a href="{link(page="map")}" target="_self" style="color:{BLUE};font-weight:700;font-size:13px">← 전체 지도로</a>',
                    unsafe_allow_html=True)
        nd = st.selectbox("선택한 행정동", codes, index=codes.index(dong), format_func=label)
        nm = st.selectbox("기준월", MONTHS[::-1], index=MONTHS[::-1].index(month), format_func=L.month_label)
        if (nd, nm) != (dong, month):
            goto(dong=nd, month=nm, page="detail")
        st.markdown("<span class='note'>비교 대상 · 최대 3곳</span>", unsafe_allow_html=True)
        st.checkbox("부산 평균", True, key="cmp_busan")
        st.checkbox(f"{r['구군']} 평균", True, key="cmp_gu")
        extra = st.multiselect("직접 추가", [c for c in codes if c != dong], max_selections=1, format_func=label,
                               placeholder="행정동 추가")
        st.markdown("<span class='note'>업종</span>", unsafe_allow_html=True)
        picked = st.multiselect("업종", [x for x, _ in INDS[1:]], default=pi["카드업종"].head(2).tolist(),
                                label_visibility="collapsed")
        st.session_state["picked"] = picked
        if st.button("선택 업종 담고 근거 보기 →", type="primary", use_container_width=True):
            st.session_state["picked_for"] = (dong, picked)
            goto(page="data")

    with c_main:
        # ---- 제목 ----
        a, b = st.columns([6, 1.4])
        trend = " · 3개월 연속 상승" if r["연속상승"] else ""
        a.markdown(f"<span style='font-size:30px;font-weight:700;color:{INK}'>{r['읍면동']}</span> "
                   f"<span class='note' style='font-size:14px'>{r['구군']}</span> {stage_chip(r['단계'])} "
                   f"<span class='note'>{len(cur)}개 동 중 {rank}위{trend}</span>", unsafe_allow_html=True)
        b.markdown(f'<div style="text-align:right;padding-top:12px"><a href="{link(page="data")}" target="_self" '
                   f'style="color:{BLUE};font-size:12.5px;font-weight:700">리포트(PDF) · 원자료 CSV</a></div>', unsafe_allow_html=True)
        s_now = sig[(sig["행정동코드"] == dong) & (sig["기준월"] == month)]
        st.markdown(f"<p style='font-size:14px;color:#3b4250;margin-top:-6px'>{L.summary_sentence(r, s_now.iloc[0] if len(s_now) else None)}</p>",
                    unsafe_allow_html=True)

        # ---- 1행: 예측 카드 + 작은 카드 2 + 재단 보증현황 ----
        left, right = st.columns([3.3, 1.7])
        with left:
            k1, k2 = st.columns([2.05, 1])
            with k1:
                risk = r["폐업위험률"]
                mx = max(12.0, (risk or 0) * 1.3)
                d = r["전월대비"]
                st.markdown(f'''<div class="card navy" style="min-height:236px">
                  <div style="display:flex;justify-content:space-between"><span style="font-size:15px;font-weight:700">폐업위험률
                  <span style="font-weight:400;color:#9fb2cb;font-size:12px">모델 예측 · 향후 6개월</span> {badge(PRED)}</span>
                  <span style="border:1px solid #6f87a8;border-radius:12px;padding:2px 10px;font-size:12px">↗ 전월 {'-' if pd.isna(d) else f"{d:+.1f}%p"}</span></div>
                  <div class="big" style="margin:16px 0 18px">{'판단 보류' if pd.isna(risk) else f"{risk:.1f}%"}</div>
                  <div style="position:relative;height:10px;background:#2c3f6b;border-radius:5px">
                    <div style="width:{0 if pd.isna(risk) else risk / mx * 100:.0f}%;height:100%;background:#fff;border-radius:5px"></div>
                    <div style="position:absolute;left:{r['부산평균'] / mx * 100:.0f}%;top:-5px;bottom:-5px;border-left:2px solid #9fb2cb"></div>
                    <div style="position:absolute;left:{r['구평균'] / mx * 100:.0f}%;top:-5px;bottom:-5px;border-left:2px dashed #9fb2cb"></div></div>
                  <div style="display:flex;justify-content:space-between;font-size:12px;color:#c9d6e6;margin-top:8px">
                  <span>부산 평균 {r['부산평균']}% · {r['구군']} {r['구평균']}%</span><span>0 ~ {mx:.0f}%</span></div></div>''',
                            unsafe_allow_html=True)
            with k2:
                st.markdown(f'''<div class="card" style="margin-bottom:10px"><div class="kv">예상 폐업 점포 {badge(PRED)}
                  <b>{int(r['예상폐업점포'])}곳</b></div><div class="note" style="text-align:right">영업 {int(r['영업점포수'])}곳 중</div></div>
                  <div class="card"><div class="kv">위험 순위<b>{rank}위</b></div>
                  <div class="note" style="text-align:right">{len(cur)}개 동 중 상위 {(r['순위'] / len(cur) * 100 if rank != '-' else 0):.0f}%</div></div>''',
                            unsafe_allow_html=True)
            # 상권 실측 신호
            close6 = "-" if not stx else f"{stx['close6']}%"
            young = "-" if not stx else f"{stx['young']:.0f}%"
            sigs = [("최근 6개월 폐업률", close6, f"전년 동기 {stx['close6_prev']}%" if stx and stx['close6_prev'] is not None else "", L.SOURCE["stores_dong_quarter.csv"]),
                    ("1년 미만 폐업 비중", young, "최근 4개 분기", L.SOURCE["stores_dong_quarter.csv"]),
                    ("카드 소비 전년비", "-" if yo["카드소비"] is None else f"{yo['카드소비']:+.1f}%", f"부산 {byo['카드소비']:+.1f}%", "실측"),
                    ("방문인구 전년비", "-" if yo["방문인구_월"] is None else f"{yo['방문인구_월']:+.1f}%", f"부산 {byo['방문인구_월']:+.1f}%", "실측")]
            cells = "".join(f'<div style="flex:1;padding:0 14px;border-left:{"0" if i == 0 else "1px solid #eef0f3"}">'
                            f'<div class="note">{a_} {badge(k)}</div><div style="font-size:28px;font-weight:700;color:{BLUE};margin:4px 0">{v}</div>'
                            f'<div class="note">{s_}</div></div>' for i, (a_, v, s_, k) in enumerate(sigs))
            st.markdown(f'<div class="card" style="margin-top:12px"><h4>상권 실측 신호 <span class="note">직전 기간</span></h4>'
                        f'<div style="display:flex">{cells}</div></div>', unsafe_allow_html=True)
        with right:
            g = L.guarantee_gu(D["guarantee_gu_industry"], r["구군"])
            if g:
                ind_rows = ""
                for nm_, rr_ in g["업종"].head(4).iterrows():
                    short = nm_.split("(")[0].replace(" 및 ", "·").replace("협회 및 단체, 수리 및 기타 ", "")[:9]
                    hi = rr_["사고율"] > rr_["부산_사고율"]
                    tag = ' <span class="chip" style="background:#256ef4;color:#fff;font-size:10px">선택 업종</span>' if "음식점" in nm_ else ""
                    ind_rows += (f'<div class="row"><span style="font-weight:{700 if tag else 400}">{short}{tag}</span>'
                                 f'<span><b style="color:{BLUE if hi else INK}">{rr_["사고율"]:.2f}%</b> '
                                 f'<span class="note">{rr_["보증잔액"] / 100:,.0f}억</span></span></div>')
                st.markdown(f'''<div class="card lblue" style="min-height:420px">
                  <h4>재단 보증현황 <span class="note" style="float:none">{r['구군']}</span> {badge('실측')}</h4>
                  <div class="note">보증 사고율</div>
                  <div style="display:flex;align-items:flex-end;gap:10px"><span style="font-size:44px;font-weight:700;color:{BLUE}">{g['사고율']:.2f}%</span>
                  <span class="chip" style="background:#fff;color:#3b4250;border:1px solid #d9e6fb">부산 {g['부산사고율']:.2f}%</span></div>
                  <div style="display:flex;gap:18px;margin:14px 0 10px">
                    <div class="kv">보증 잔액<b style="font-size:20px">{g['잔액억']:,.0f}억</b><span class="note">{g['구군수']}개 구·군 중 {g['잔액순위']}위</span></div>
                    <div class="kv">보증 사고<b style="font-size:20px">{g['사고억']:,.0f}억</b><span class="note">{g['사고건수']}건</span></div></div>
                  <div style="font-weight:700;font-size:13.5px;margin:8px 0 2px">업종별 사고율 <span class="note" style="float:right">사고율 · 잔액</span></div>
                  {ind_rows}
                  <div class="note" style="margin-top:8px">2023.1Q~25.4Q 누적 · 정상화 금액 미반영(보증사고순증률과 산식 다름) · 구·군=최초 보증 소재지</div></div>''',
                            unsafe_allow_html=True)

        # ---- 2행: 업종별 · 원인 · 추이 ----
        st.write("")
        c1, c2, c3 = st.columns([1.15, 1.25, 1.2])
        with c1:
            avg = float(r["부산평균"])
            mx = max(12.0, pi["폐업위험률"].max() * 1.15)
            bars = ""
            for _, x in pi.head(6).iterrows():
                hi = x["폐업위험률"] > avg
                dd = x["폐업위험률"] - avg
                bars += (f'<div class="ibar"><span class="nm">{x["카드업종"]}</span><span class="tr"><span class="fl" style="display:block;width:'
                         f'{x["폐업위험률"] / mx * 100:.0f}%;background:{BLUE if hi else "#b1c6ef"}"></span>'
                         f'<span class="av" style="left:{avg / mx * 100:.0f}%"></span></span><span class="v">{x["폐업위험률"]:.1f}%</span>'
                         f'<span class="d" style="color:{"#d6342c" if dd > 0 else MUT}">{dd:+.1f}</span></div>')
            st.markdown(f'<div class="card" style="min-height:330px"><h4>업종별 폐업위험 {badge(PRED)} <span class="n">부산 평균 대비</span></h4>'
                        f'{bars}<div class="note" style="text-align:center;margin-top:6px">점선 = 부산 평균 {avg}%</div></div>',
                        unsafe_allow_html=True)
        with c2:
            ups = sh[sh["방향"] == "상승"]
            w = ups["기여도"].clip(lower=0)
            vals = (w / w.sum() * 86).round(0).tolist() if w.sum() else []
            vals.append(max(0, 100 - sum(vals)))
            labs = list(ups["설명"]) + ["기타 요인"]
            st.markdown(f'''<div class="card navy" style="min-height:330px"><h4>폐업위험을 높이는 원인 {badge(PRED)}
              <span class="n" style="color:#9fb2cb">SHAP 기여 비중 · 인과 아님</span></h4>
              <div style="display:flex;gap:14px;align-items:center">{L.donut_svg(vals, ["#1450D2", "#4C8FEA", "#A9C4F2", "#3a4c75"], 150)}
              <div style="flex:1;font-size:12.5px">{"".join(f'<div class="row" style="border-color:#2c3f6b;color:#fff"><span>● {d_}</span><b>{v_:.0f}%</b></div>' for d_, v_ in zip(labs, vals))}</div></div>
              <div style="font-size:12px;color:#c9d6e6;margin-top:10px">위험을 낮춘 요인: {sh[sh["방향"] == "하락"].iloc[0]["설명"] if (sh["방향"] == "하락").any() else "-"}</div></div>''',
                        unsafe_allow_html=True)
        with c3:
            with st.container(border=True):
                st.markdown(f"**언제부터 나빠졌나**", unsafe_allow_html=True)
                s1 = L.index_series(sig, [dong], "카드소비")
                s2 = L.index_series(sig, gu_codes, "카드소비")
                fig = go.Figure()
                fig.add_scatter(x=[L.month_label(m) for m in s1.index], y=s1.values, name=r["읍면동"], line=dict(color=BLUE, width=2.4))
                fig.add_scatter(x=[L.month_label(m) for m in s2.index], y=s2.values, name=r["구군"], line=dict(color="#9aa3ad", dash="dash"))
                fig.update_layout(height=150, margin=dict(l=0, r=0, t=22, b=0), title=dict(text="카드소비 지수 (23.01=100) · 실측", font_size=12),
                                  legend=dict(orientation="h", y=-0.35, font_size=10), xaxis=dict(nticks=4))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                if stx:
                    q = stx["quarterly"]
                    fig = go.Figure(go.Bar(x=list(q.index), y=q.values, marker_color=[BLUE if i >= len(q) - 2 else "#a9c2f2" for i in range(len(q))],
                                           text=q.values, textposition="outside"))
                    fig.update_layout(height=150, margin=dict(l=0, r=0, t=22, b=0), title=dict(text=f"분기별 폐업 신고 · {L.SOURCE['stores_dong_quarter.csv']}", font_size=12),
                                      yaxis_visible=False)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    st.markdown(f"<div style='text-align:right;font-weight:700'>최근 분기 {int(q.iloc[-1])}건</div>", unsafe_allow_html=True)

        # ---- 3행: 주변 지도 · 비교 · 신뢰도 · 점포 순증 ----
        st.write("")
        c1, c2 = st.columns([1.15, 1])
        with c1, st.container(border=True):
            st.markdown(f"**주변 행정동 위험단계** {badge(PRED)} <span class='note' style='float:right'>굵은 테두리 = 선택 동</span>",
                        unsafe_allow_html=True)
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
            fig.update_layout(height=470, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.02, title=""))
            try:   # Streamlit 1.35+ : 지도 클릭으로 동 바꾸기
                ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="nbmap")
                pts = ev.selection.points if ev else []
            except Exception:
                st.plotly_chart(fig, use_container_width=True)
                pts = []
            if pts and pts[0].get("location") and pts[0]["location"] != dong:
                goto(dong=pts[0]["location"], page="detail")
            st.caption("지도에서 다른 동을 클릭하면 그 동의 상세로 바뀝니다.")
        with c2:
            t = L.compare_table(staged, sig, month, dong)
            if extra:
                e = extra[0]
                t2 = L.compare_table(staged, sig, month, e)
                t.insert(1, names.loc[e, "읍면동"], t2.iloc[:, 0])
            show = [t.columns[0]] + ([t.columns[1]] if extra else []) + \
                   ([f"{r['구군']}"] if st.session_state.get("cmp_gu", True) else []) + (["부산"] if st.session_state.get("cmp_busan", True) else [])
            t = t[[c for c in show if c in t.columns]]
            head = "".join(f'<th class="{"sel" if i == 0 else ""}">{c}</th>' for i, c in enumerate(t.columns))
            body = ""
            for idx, row in t.iterrows():
                body += f"<tr><td>{idx}</td>" + "".join(
                    f'<td class="{"sel" if i == 0 else ""}">{"-" if pd.isna(v) else f"{v:.1f}"}</td>' for i, v in enumerate(row)) + "</tr>"
            st.markdown(f'<div class="card"><h4>주변과 비교 <span class="n">예측 {badge(PRED)} · 전년비 {badge("실측")}</span></h4>'
                        f'<table class="tbl"><tr><th></th>{head}</tr>{body}</table></div>', unsafe_allow_html=True)
            st.write("")
            k1, k2 = st.columns(2)
            share_top3 = 86 if len(sh) else 0
            k1.markdown(f'''<div class="card" style="min-height:190px"><h4>예측 신뢰도 {badge(PRED)}</h4>
              <div style="display:flex;gap:14px"><div class="kv">판단 근거 점포<b style="font-size:22px">{int(r['영업점포수'])}곳</b></div>
              <div class="kv">상위 3요인 비중<b style="font-size:22px">{share_top3}%</b></div></div>
              <div class="kv" style="margin-top:8px">최신 데이터<b style="font-size:18px">{L.month_label(month)}</b></div></div>''',
                        unsafe_allow_html=True)
            with k2:
                if stx:
                    nq = stx["net_q"]
                    fig = go.Figure(go.Bar(x=list(nq.index), y=nq.values, marker_color=["#d6342c" if v < 0 else BLUE for v in nq.values]))
                    fig.update_layout(height=110, margin=dict(l=0, r=0, t=0, b=0), yaxis_visible=False, xaxis=dict(tickfont_size=9, nticks=4))
                    st.markdown(f'<div class="card lblue" style="padding-bottom:4px"><h4>점포 순증 {badge(L.SOURCE["stores_dong_quarter.csv"])}'
                                f'<span class="n">최근 4개 분기</span></h4><div style="font-size:34px;font-weight:700;color:{BLUE}">{stx["net"]:+d}곳</div>'
                                f'<div class="note">개업 {stx["opened"]} · 폐업 {stx["closed"]}</div></div>', unsafe_allow_html=True)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<p class="note" style="margin-top:14px">예측·요인·업종 위험·점포 집계는 모델/인허가 연결 전 {PRED}값입니다. '
                    '카드 소비·생활인구·재단 보증은 실제 자료입니다. 요인은 예측에 영향을 준 정도이며 원인이 아닙니다.</p>', unsafe_allow_html=True)


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
    c_rail, c_main = st.columns([0.42, 9.6], gap="small")
    with c_rail:
        rail("내 목록")
    with c_main:
        st.markdown(f"<span style='font-size:26px;font-weight:700'>근거 확인 및 자료 다운</span>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["선택한 동 근거 확인", "원자료 · CSV 내려받기"])
        with t1:
            pf = st.session_state.get("picked_for")
            picked = pf[1] if pf and pf[0] == dong else st.session_state.get("picked", [])
            a, b = st.columns([3, 1])
            nd = a.selectbox("행정동", codes, index=codes.index(dong), format_func=label)
            if nd != dong:
                goto(dong=nd, page="data")
            b.markdown(f'<div style="padding-top:30px"><a href="{link(page="detail")}" target="_self" style="color:{BLUE};font-weight:700">'
                       f'← ② 상세로 돌아가기</a></div>', unsafe_allow_html=True)
            st.markdown(f"#### {r['구군']} {r['읍면동']} {stage_chip(r['단계'])}", unsafe_allow_html=True)
            st.markdown(f"담은 업종: **{', '.join(picked) if picked else '없음 (② 화면 왼쪽에서 고를 수 있어요)'}**")
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
                memo = st.text_area("담당자 메모", key=f"memo_{dong}")
            with rr, st.container(border=True):
                st.markdown("**자료 신뢰도와 유의사항**")
                st.markdown(f"- 폐업위험률·요인·업종 위험·점포 집계 {badge(PRED)} — 모델·인허가 연결 전\n"
                            f"- 카드 소비·생활인구 {badge('실측')} 2023.01~2026.07\n"
                            f"- 재단 보증 {badge('실측')} 구·군 단위 (행정동 자료 없음)\n"
                            "- 요인은 SHAP 기여도이며 인과관계가 아닙니다.\n- 보증 승인·제한 판단에 쓰지 않습니다.", unsafe_allow_html=True)
                sh = D["shap_top"]
                sh = sh[sh["행정동코드"] == dong].sort_values("순위")
                report = "\n".join([f"# {r['구군']} {r['읍면동']} 근거 확인 리포트", f"- 기준월: {L.month_label(month)}",
                                    f"- 단계: {r['단계']} / 폐업위험률: {r['폐업위험률']}% (부산 평균 {r['부산평균']}%) [{PRED}]",
                                    "## 요인 (SHAP, 인과 아님)", *[f"- {x}" for x in sh["설명"]],
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
            st.markdown('<p class="note">대시보드가 읽는 파일 그대로입니다. 구·군과 기간으로 걸러서 받을 수 있어요.</p>', unsafe_allow_html=True)
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
                    a, b, c = st.columns([5, 1.1, 1.3])
                    a.markdown(f"**{fname}** {badge(kind)}<br><span class='note'>{desc} · {unit} · 출처 {src} · {len(df):,}행</span>",
                               unsafe_allow_html=True)
                    with b.popover("미리보기", use_container_width=True):
                        st.dataframe(df.head(50), hide_index=True)
                    c.download_button("CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name=fname, key=f"dl_{fname}",
                                      use_container_width=True)
            zf.writestr("자료목록.csv", pd.DataFrame(meta).to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("busan_dong.geojson", (L.DATA / "busan_dong.geojson").read_bytes())
            zf.close()
            st.download_button("전체 묶음 내려받기 (.zip)", buf.getvalue(), file_name="부산상권위험_자료.zip", type="primary")


{"map": page_map, "detail": page_detail, "data": page_data}[page]()
st.query_params.update({"page": page, "dong": dong, "month": str(month), "gu": gu, "ind": ind})
