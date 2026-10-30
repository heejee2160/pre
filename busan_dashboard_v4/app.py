"""부산 행정동 위험 조기진단 대시보드 (Streamlit)

실행:  streamlit run app.py
화면:  ① 전체(지도 + 폐업예측 팝업)  ② 행정동·업종 상세  ③ 근거 확인 및 자료 다운
상태는 주소창 쿼리(?page=detail&code=...&month=...)에 담아서, 링크로 화면을 오간다.
"""
from __future__ import annotations

import copy

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

import data as D
import ui as U

st.set_page_config(page_title="부산 상권 위험 조기진단", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")
st.markdown(U.CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------- state (query params)
qp = st.query_params
PAGE = qp.get("page", "overview")
MONTH = qp.get("month", D.MONTHS[-1])
UPJONG = qp.get("upjong", "전체")
GU = qp.get("gu", "전체")
CODE = qp.get("code", "")
HOLD_SHOW = qp.get("hold", "1") == "1"


def setq(**kw):
    for k, v in kw.items():
        if v in (None, ""):
            qp.pop(k, None)
        else:
            qp[k] = v


def base_q() -> dict:
    return {k: qp.get(k) for k in ("month", "upjong", "gu", "code", "hold") if qp.get(k)}


df = D.month_table(MONTH, UPJONG)
BUSAN = D.busan_avg(df)
if not CODE:
    CODE = D.top_n(df, 1).iloc[0]["code"]
row = df[df["code"] == CODE].iloc[0]

step = {"overview": 1, "detail": 2, "evidence": 3}.get(PAGE, 1)
st.markdown(U.header(step, MONTH, base_q()), unsafe_allow_html=True)
st.write("")


# ---------------------------------------------------------------- shared widgets
def filter_card(detail: bool = False):
    with st.container():
        if detail:
            st.markdown(f'<a class="go" href="{U.link(**{**base_q(), "page": "overview", "popup": "0"})}" target="_self">← 전체 지도로</a>', unsafe_allow_html=True)
            names = D.dong_list().assign(label=lambda d: d["gu"] + " · " + d["dong"])
            idx = int(names.index[names["code"] == CODE][0])
            pick = st.selectbox("선택한 행정동", names["label"], index=idx)
            new_code = names.loc[names["label"] == pick, "code"].iloc[0]
            if new_code != CODE:
                setq(code=new_code); st.rerun()
        else:
            st.markdown('<p class="ct">조건 선택</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        m = c1.selectbox("기준월", D.MONTHS[::-1], index=D.MONTHS[::-1].index(MONTH), format_func=lambda s: f"{s[:4]}.{s[4:]}")
        gus = ["전체"] + D.gu_list()
        g = c2.selectbox("구·군", gus, index=gus.index(GU) if GU in gus else 0, format_func=lambda s: "전체 (16개)" if s == "전체" else s)
        h = st.checkbox("판단 보류 동 표시 (영업점포 30곳 미만)", value=HOLD_SHOW)
        st.markdown(f'<div class="lbl" style="margin-top:4px">카드업종 <b style="color:{U.ACC}">11개</b></div>', unsafe_allow_html=True)
        st.markdown(U.upjong_grid_html(UPJONG, D.CARD_UPJONG, base_q(), PAGE), unsafe_allow_html=True)
        if (m, g, h) != (MONTH, GU, HOLD_SHOW):
            setq(month=m, gu=None if g == "전체" else g, hold="1" if h else "0")
            st.rerun()


def build_map(sel_code: str, gu: str | None, height: int, zoom_gu: bool = False):
    geo = copy.deepcopy(D.load_geo())
    info = df.set_index("code")
    feats = []
    for f in geo["features"]:
        c = f["properties"]["adm_cd"]
        if c not in info.index:
            continue
        r = info.loc[c]
        if r["hold"] and not HOLD_SHOW:
            color = "#EEF1F5"
        else:
            color = r["color"]
        dim = gu not in (None, "전체") and r["gu"] != gu
        f["properties"].update(prob=f'{r["prob"]:.1f}%', grade=r["grade"], _c=color, _dim=dim, _sel=(c == sel_code))
        feats.append(f)
    geo["features"] = feats
    sub = [f for f in feats if not f["properties"]["_dim"]] if zoom_gu or gu not in (None, "전체") else feats
    xs = [x for f in sub for x in _coords(f["geometry"], 0)]
    ys = [y for f in sub for y in _coords(f["geometry"], 1)]
    m = folium.Map(location=[35.17, 129.07], zoom_start=11, tiles=None, control_scale=True, zoom_control=True)
    folium.GeoJson(
        geo,
        style_function=lambda f: {"fillColor": f["properties"]["_c"], "color": "#13294D" if f["properties"]["_sel"] else "#FFFFFF",
                                  "weight": 4 if f["properties"]["_sel"] else 0.8,
                                  "fillOpacity": 0.25 if f["properties"]["_dim"] else 0.85},
        highlight_function=lambda f: {"weight": 3, "color": "#13294D"},
        tooltip=folium.GeoJsonTooltip(fields=["adm_nm", "prob", "grade"], aliases=["", "폐업확률", "등급"], sticky=True),
    ).add_to(m)
    if xs:
        m.fit_bounds([[min(ys), min(xs)], [max(ys), max(xs)]])
    out = st_folium(m, height=height, use_container_width=True, returned_objects=["last_active_drawing"], key=f"map_{PAGE}")
    clicked = (out or {}).get("last_active_drawing") or {}
    return clicked.get("properties", {}).get("adm_cd")


def _coords(g, i):
    if g["type"] == "Polygon":
        return [p[i] for p in g["coordinates"][0]]
    return [p[i] for poly in g["coordinates"] for p in poly[0]]


# ---------------------------------------------------------------- ① overview
@st.dialog("폐업예측 한 눈에 보기", width="medium")
def popup():
    top3 = D.top_n(df, 3).to_dict("records")
    sigs = [D.signals(pd.Series(r), df) for r in top3]
    st.caption(f"{MONTH[:4]}.{MONTH[4:]} 기준 · 향후 6개월 폐업확률이 높은 순 · 다른 동에 마우스를 올리면 자세히 보입니다")
    components.html(U.popup_component(top3, BUSAN, sigs), height=320)
    c = st.columns(3)
    for i, r in enumerate(top3):
        if c[i].button(f"{i + 1}순위 {r['dong']} 상세 →", key=f"pp{i}", use_container_width=True):
            setq(page="detail", code=r["code"], popup="0"); st.rerun()
    st.caption('공개자료로 예측한 "폐업위험 신호"로, 보증사고·위험·지원 효과와 다릅니다.')


def overview():
    if qp.get("popup", "1") != "0" and not st.session_state.get("popup_done"):
        st.session_state["popup_done"] = True
        popup()
    rail, left, main = st.columns([0.22, 1, 3.3], gap="small")
    with rail, st.container(key="railpane"):
        st.markdown(U.rail_html("overview", base_q()), unsafe_allow_html=True)
    with left, st.container(key="leftpane"):
        filter_card()
        st.markdown(U.top5_html(D.top_n(df), base_q(), MONTH, UPJONG), unsafe_allow_html=True)
    with main:
        c1, c2, c3 = st.columns([2.2, 1, 0.9])
        names = D.dong_list().assign(label=lambda d: d["gu"] + " " + d["dong"])
        q = c1.selectbox("행정동 검색", ["행정동·상권 검색 (예: 부전동)"] + names["label"].tolist(), label_visibility="collapsed")
        if q != "행정동·상권 검색 (예: 부전동)":
            c = names.loc[names["label"] == q, "code"].iloc[0]
            if c != CODE:
                setq(code=c); st.rerun()
        c2.segmented_control("단위", ["행정동", "상권"], default="행정동", label_visibility="collapsed", key="unit")
        if c3.button("폐업예측 한 눈에 보기", use_container_width=True):
            popup()
        mcol, side = st.columns([2.1, 1], gap="medium")
        with mcol:
            clicked = build_map(CODE, GU, 690)
            if clicked and clicked != CODE:
                setq(code=clicked); st.rerun()
            st.caption('공개자료로 예측한 "폐업위험 신호"로, 보증사고 위험·지원 효과와 다릅니다.')
        with side:
            ut = D.upjong_table(CODE, MONTH)
            top_up = " · ".join(ut[~ut["hold"]].head(2)["upjong"])
            st.markdown(U.info_card_html(row, BUSAN, D.signals(row, df), top_up, base_q()), unsafe_allow_html=True)
            with st.container(key="card_compare"):
                st.markdown('<p class="ct">한 번에 비교하기</p><div class="cs">선택한 동의 핵심 지표</div>', unsafe_allow_html=True)
                labels = (df["gu"] + " " + df["dong"]).tolist()
                default = [f'{row["gu"]} {row["dong"]}'] + [f'{r.gu} {r.dong}' for r in D.top_n(df, 2).itertuples() if r.code != CODE][:1]
                pick = st.multiselect("비교할 행정동 (최대 3곳)", labels, default=default, max_selections=3, label_visibility="collapsed")
                rows = [df[(df["gu"] + " " + df["dong"]) == p].iloc[0] for p in pick]
                st.markdown(U.compare_html(rows), unsafe_allow_html=True)
            st.markdown(U.legend_html(), unsafe_allow_html=True)


# ---------------------------------------------------------------- ② detail
def detail():
    rail, left, main = st.columns([0.22, 1, 4.6], gap="small")
    with rail, st.container(key="railpane"):
        st.markdown(U.rail_html("detail", base_q()), unsafe_allow_html=True)
    with left, st.container(key="leftpane"):
        filter_card(detail=True)
        with st.container(key="primary_go"):
            if st.button("선택 업종 담고 근거 보기 →", use_container_width=True):
                setq(page="evidence"); st.rerun()
    gu_avg = D.gu_avg(df, row["gu"])
    cols = ["close_rate_6m", "young_close_share", "card_yoy", "pop_yoy", "prob"]
    busan_row = {c: D.busan_avg(df, c) for c in cols}
    gu_row = {c: D.gu_avg(df, row["gu"], c) for c in cols}
    with main:
        rank = int((df.loc[~df["hold"], "prob"] > row["prob"]).sum()) + 1
        sig = D.signals(row, df)
        st.markdown(
            f'<div class="row" style="gap:14px;margin-top:4px"><span style="font-size:34px;font-weight:700;color:{U.INK}">{row["dong"]}</span>'
            f'<span class="mut" style="font-size:17px">{row["gu"]}</span><span class="tag" style="background:{U.NAVY};color:#fff">{row["grade"]}</span>'
            f'<span class="mut">{len(df)}개 동 중 {rank}위 · 전월 {row["mom"]:+.1f}%p</span><span class="sp"></span>'
            f'<a class="go" style="font-size:13px" href="{U.link(**{**base_q(), "page": "evidence", "popup": "0"})}" target="_self">리포트 PDF · 원자료 CSV</a></div>'
            f'<div style="color:{U.INK};margin:6px 0 4px">폐업위험이 부산 평균보다 {row["prob"] - BUSAN:+.1f}%p, {" / ".join(sig)}.</div>',
            unsafe_allow_html=True)
        a, b = st.columns([2.38, 1], gap="medium")
        with a:
            h1, h2 = st.columns([1.85, 1], gap="medium")
            h1.markdown(U.hero_html(row, BUSAN, gu_avg), unsafe_allow_html=True)
            h2.markdown(U.stat_html("예상 폐업 점포", f'{round(row["stores"] * row["prob"] / 100)}곳', f'영업 {int(row["stores"])}곳 중'), unsafe_allow_html=True)
            h2.markdown(U.stat_html("위험 순위", f"{rank}위", f"{len(df)}개 동 중 상위 {rank / len(df) * 100:.0f}%"), unsafe_allow_html=True)
            st.markdown(U.field_html(row, busan_row), unsafe_allow_html=True)
        b.markdown(U.guarantee_html(D.sinbo_gu(row["gu"]), row["gu"]), unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.85, 1.3], gap="medium")
        c1.markdown(U.industry_html(D.upjong_table(CODE, MONTH), BUSAN), unsafe_allow_html=True)
        c2.markdown(U.causes_html(D.shap_parts(CODE, MONTH)), unsafe_allow_html=True)
        c3.markdown(U.trend_html(*D.trend_series(CODE)), unsafe_allow_html=True)
        m1, m2 = st.columns([1.4, 2], gap="medium")
        with m1:
            with st.container(key="card_map"):
                st.markdown('<div class="row"><p class="ct">주변 행정동 위험단계</p><span class="sp"></span><span class="cs">굵은 테두리가 선택한 동</span></div>', unsafe_allow_html=True)
                clicked = build_map(CODE, row["gu"], 420, zoom_gu=True)
                if clicked and clicked != CODE:
                    setq(code=clicked); st.rerun()
                st.markdown(U.legend_html().replace('class="card"', 'class=""'), unsafe_allow_html=True)
        with m2:
            st.markdown(U.compare3_html(row, gu_row, busan_row), unsafe_allow_html=True)
            x, y = st.columns(2, gap="medium")
            x.markdown(U.confidence_html(row, MONTH), unsafe_allow_html=True)
            y.markdown(U.netopen_html(row), unsafe_allow_html=True)


# ---------------------------------------------------------------- ③ evidence
def evidence():
    rail, left, main = st.columns([0.22, 1, 4.6], gap="small")
    with rail, st.container(key="railpane"):
        st.markdown(U.rail_html("evidence", base_q()), unsafe_allow_html=True)
    with left, st.container(key="leftpane"):
        filter_card(detail=True)
    with main:
        st.markdown(f'<p class="ct" style="font-size:26px">{row["gu"]} {row["dong"]} · 근거 확인 및 자료 다운</p>', unsafe_allow_html=True)
        with st.container(key="card_ev1"):
            st.markdown('<p class="ct">숫자의 근거</p>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([
                ["폐업위험률", "모델(M) 예측, 향후 6개월 내 폐업 확률", "모델 v0.1", f"{MONTH[:4]}.{MONTH[4:]}"],
                ["최근 6개월 폐업률", "최근 6개월 폐업 수 ÷ 6개월 전 영업 점포 수", "인허가(행정안전부)", f"{MONTH[:4]}.{MONTH[4:]}"],
                ["카드소비 전년비", "월별 일평균 카드 결제 금액, 전년 동월 대비", "카드소비 데이터", "2026.02"],
                ["방문인구 전년비", "방문인구, 전년 동월 대비", "생활인구(부산광역시)", "2026.02"],
                ["재단 보증현황", "2025년 연 사고금액 ÷ 분기 평균 잔액", "재단 보증 실자료(구·군 단위)", "2025.4Q"],
            ], columns=["지표", "계산 방법", "출처", "기준"]), hide_index=True, use_container_width=True)
        with st.container(key="card_ev2"):
            st.markdown('<p class="ct">자료 내려받기</p>', unsafe_allow_html=True)
            sel = df[df["code"] == CODE]
            c1, c2, c3 = st.columns(3)
            c1.download_button("이 동 지표 CSV", sel.to_csv(index=False).encode("utf-8-sig"), f"{row['dong']}_{MONTH}.csv", use_container_width=True)
            c2.download_button("이 동 업종별 위험 CSV", D.upjong_table(CODE, MONTH).to_csv(index=False).encode("utf-8-sig"), f"{row['dong']}_업종_{MONTH}.csv", use_container_width=True)
            c3.download_button("부산 전체 행정동 CSV", df.drop(columns=["color"]).to_csv(index=False).encode("utf-8-sig"), f"부산_행정동_{MONTH}.csv", use_container_width=True)
        st.caption("※ 참고자료입니다. 보증 승인·제한 판단이 아닙니다.")


{"overview": overview, "detail": detail, "evidence": evidence}.get(PAGE, overview)()
