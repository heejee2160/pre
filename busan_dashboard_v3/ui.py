"""화면 조각(HTML/SVG). Streamlit 위젯이 아닌 '보여주기' 부분은 모두 여기서 만든다."""
from __future__ import annotations

import base64
import math
from pathlib import Path
from urllib.parse import urlencode

from data import GRADES, HOLD_COLOR

ASSETS = Path(__file__).parent / "assets"

# ---------------------------------------------------------------- tokens
NAVY, NAVY2, ACC, LBAR, PALE = "#004098", "#2A62B8", "#0A7FC8", "#8ED2F4", "#DDF0FB"
SKY, LIME = "#00A0E8", "#C2D94D"
INK, MUT, FNT, DIV, BG = "#13212F", "#66788C", "#9AA7B5", "#E6ECF2", "#E4EBF2"
ONDK2 = "#BFD9F3"
RED = "#D9452F"

CSS = f"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
html, body, [class*="css"], .stApp, .stMarkdown, button, input, select, textarea {{
  font-family: Pretendard, 'Noto Sans KR', sans-serif !important; }}
.stApp {{ background: {BG}; }}
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"] {{ display: none !important; }}
.block-container {{ padding: 0 24px 40px 24px !important; max-width: 100% !important; }}
div[data-testid="stVerticalBlock"] {{ gap: 14px; }}
/* Streamlit 위젯 글씨 (+3) */
.stApp [data-testid="stWidgetLabel"] p {{ font-size:16px !important; }}
.stApp div[data-baseweb="select"] div, .stApp input, .stApp textarea {{ font-size:17px !important; }}
.stApp .stButton button p, .stApp [data-testid="stDownloadButton"] button p {{ font-size:17px !important; }}
.stApp [data-testid="stCheckbox"] p, .stApp [data-testid="stPills"] button p {{ font-size:16px !important; }}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {{ font-size:15px !important; }}
.stApp [data-testid="stMarkdownContainer"] p {{ font-size:inherit; }}
.stApp [data-testid="stDataFrame"] {{ font-size:16px; }}
/* header */
.bh {{ margin: 0 -24px 0 -24px; }}
.bh-top {{ background: linear-gradient(90deg,#003A8C 78%,#00A0E8); color:#fff; height: 74px;
  display:flex; align-items:center; padding: 0 28px; gap: 14px; }}
.bh-top img {{ width: 50px; height: 50px; border-radius: 10px; background:#fff; padding:5px; box-sizing:border-box; object-fit:contain; }}
.bh-title {{ font-size:26px; font-weight: 700; line-height: 1.1; color:#FFFFFF; }}
.bh-sub {{ font-size:15.5px; color: #fff; opacity: .9; margin-top: 4px; }}
.bh-steps {{ margin-left: auto; display:flex; align-items:center; gap: 10px; }}
.bh-steps a {{ text-decoration:none; }}
.st-pill {{ display:flex; align-items:center; gap:10px; border:1.5px solid rgba(255,255,255,.35); color:#fff;
  border-radius: 999px; padding: 6px 16px 6px 6px; font-size:16.5px; }}
.st-pill .n {{ width: 26px; height: 26px; border-radius: 50%; border: 1.5px solid rgba(255,255,255,.6);
  display:flex; align-items:center; justify-content:center; font-weight:600; font-size:16px; }}
.st-pill.on {{ background:#fff; border-color:#fff; color:#004098; padding: 6px 22px 6px 6px; }}
.st-pill.on .n {{ width:40px; height:40px; background:#004098; border:5px solid #00A0E8; color:#fff; font-size:19px; }}
.st-pill.on .k {{ font-size:14px; color:#0A7FC8; font-weight:700; display:block; }}
.st-pill.on .t {{ font-size:19px; font-weight:700; }}
.st-dots {{ width:28px; height:1px; background:rgba(255,255,255,.35); }}
.bh-info {{ background:#F4F7FB; border-bottom:1px solid #DBE3EE; height: 42px; display:flex; align-items:center;
  gap: 26px; padding: 0 28px; font-size:15px; color:#4A5A70; white-space:nowrap; overflow:hidden; }}
.bh-info b {{ color:#004098; }}
.bh-info .src {{ margin-left:auto; }}
/* cards */
.card {{ background:#fff; border-radius: 20px; padding: 22px 24px; }}
.card.dark {{ background:{NAVY}; color:#fff; }}
.card.pale {{ background:{PALE}; }}
.ct {{ font-size:20px; font-weight: 700; color:{INK}; margin:0; }}
.dark .ct {{ color:#fff; }}
.cs {{ font-size:15px; color:{FNT}; }}
.dark .cs {{ color:{ONDK2}; }}
.row {{ display:flex; align-items:center; }}
.sp {{ flex:1; }}
.lbl {{ font-size:15.5px; color:{MUT}; }}
.big {{ font-size:37px; font-weight: 500; color:{INK}; line-height:1.1; }}
.mut {{ color:{MUT}; }} .fnt {{ color:{FNT}; }}
.dl {{ border-top: 1px solid {DIV}; }}
a.go {{ color:{ACC}; font-weight:700; text-decoration:none; }}
.tag {{ display:inline-block; padding: 2px 10px; border-radius: 999px; font-size:15px; font-weight: 600; }}
/* streamlit containers used as cards */
[class*="st-key-card"] {{ background:#fff; border-radius:20px; padding: 18px 20px; }}
[class*="st-key-darkcard"] {{ background:{NAVY}; border-radius:20px; padding: 18px 20px; }}
.stButton > button {{ border-radius: 12px; }}
[class*="st-key-primary"] button {{ background:{NAVY}; color:#fff; border:none; font-weight:600; }}
[class*="st-key-primary"] button:hover {{ background:#003273; color:#fff; }}
div[data-testid="stPills"] button {{ border-radius: 999px; }}
/* 왼쪽 남색 메뉴와 흰색 조건 칸: 스크롤해도 화면에 붙어 있게 */
[data-testid="stColumn"]:has(.st-key-railpane), [data-testid="stColumn"]:has(.st-key-leftpane) {{ position: sticky; top: 12px; align-self: flex-start; }}
.rail {{ background:{NAVY}; border-radius:16px; padding:10px 0; min-height: calc(100vh - 160px); display:flex; flex-direction:column; gap:2px; }}
.rail a {{ display:block; text-align:center; color:#CFE3F7; font-size:16px; padding:12px 0; text-decoration:none; border-left:4px solid transparent; }}
.rail a b {{ display:block; font-size:22px; color:#fff; font-weight:500; }}
.rail a.on {{ background:rgba(0,160,232,.22); color:#fff; border-left-color:{SKY}; font-weight:700; }}
.rail a:hover {{ background:rgba(255,255,255,.08); }}
</style>
"""


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def link(**params) -> str:
    return "?" + urlencode({k: v for k, v in params.items() if v not in (None, "")})


# ---------------------------------------------------------------- header
def rail_html(active: str, qp: dict) -> str:
    """왼쪽 남색 메뉴."""
    items = [("▦", "지도", "overview"), ("◫", "상세", "detail"), ("⇣", "자료", "evidence")]
    out = "".join(f'<a class="{"on" if p == active else ""}" href="{link(**{**qp, "page": p, "popup": "0"})}" target="_self"><b>{ic}</b>{lab}</a>'
                  for ic, lab, p in items)
    return f'<div class="rail">{out}</div>'


def header(step: int, month: str, qp: dict) -> str:
    logo = _b64(ASSETS / "logo.png")
    pages = [("1", "전체", "overview"), ("2", "행정동·업종 상세", "detail"), ("3", "근거 확인 및 자료 다운", "evidence")]
    st = []
    for i, (n, name, page) in enumerate(pages, start=1):
        href = link(**{**qp, "page": page, "popup": "0"})
        if i == step:
            st.append(f'<a href="{href}" target="_self"><div class="st-pill on"><div class="n">{n}</div>'
                      f'<div><span class="k">STEP {n} / 3</span><span class="t">{name}</span></div></div></a>')
        else:
            st.append(f'<a href="{href}" target="_self"><div class="st-pill"><div class="n">{n}</div>{name}</div></a>')
        if i < len(pages):
            st.append('<span class="st-dots"></span>')
    m = f"{month[:4]}.{month[4:]}"
    return (f'<div class="bh"><div class="bh-top"><img src="data:image/png;base64,{logo}">'
            f'<div><div class="bh-title">부산신용보증재단</div><div class="bh-sub">부산 행정동 위험 조기진단 · 정책지원 의사결정 보조</div></div>'
            f'<div class="bh-steps">{"".join(st)}</div></div>'
            f'<div class="bh-info"><span>기준월 <b>{m}</b></span><span>예측 대상 향후 6개월 내 폐업</span>'
            f'<span>학습 기준월 2023.01~2026.01</span><span>데이터 갱신 2026.07.15</span><span>모델 v0.1 (가상)</span>'
            f'<span class="src">출처: 인허가(행정안전부) · 카드소비 · 생활인구(부산광역시) · 주민등록(행정안전부)</span></div></div>')


# ---------------------------------------------------------------- overview pieces
def legend_html() -> str:
    items = "".join(f'<div class="row" style="gap:8px;margin:4px 0"><span style="width:14px;height:14px;border-radius:4px;background:{c}"></span>'
                    f'<b style="font-size:15.5px;color:{INK}">{n}</b><span class="cs">{"%.0f%% 이상" % lo if lo else "6% 미만"}</span></div>'
                    for n, lo, c in GRADES)
    items += (f'<div class="row" style="gap:8px;margin:4px 0"><span style="width:14px;height:14px;border-radius:4px;background:{HOLD_COLOR}"></span>'
              f'<b style="font-size:15.5px;color:{INK}">판단 보류</b><span class="cs">영업 점포 30곳 미만</span></div>')
    return f'<div class="card" style="padding:14px 18px"><div class="lbl" style="margin-bottom:6px"><b>폐업확률 등급</b> · 향후 6개월</div>{items}</div>'


def top5_html(top, qp: dict, month: str, upjong: str) -> str:
    rows = []
    for i, r in top.iterrows():
        href = link(**{**qp, "page": "detail", "code": r["code"], "popup": "0"})
        arrow = "↑" if r["mom"] > 0 else ("↓" if r["mom"] < 0 else "")
        rows.append(f'<a href="{href}" target="_self" style="text-decoration:none"><div class="row dl" style="padding:11px 0;gap:10px">'
                    f'<b style="color:{RED};width:16px">{i + 1}</b><span style="color:{INK};font-size:17.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r["gu"]} {r["dong"]}</span><span class="sp"></span>'
                    f'<b style="color:{INK};font-size:17.5px">{r["prob"]:.1f}%</b><span style="color:{RED};font-size:15.5px;width:70px;text-align:right;white-space:nowrap">{r["mom"]:+.1f}%p {arrow}</span></div></a>')
    m = f"{month[:4]}.{month[4:]}"
    return (f'<div class="card"><div class="row" style="gap:8px"><span style="width:4px;height:20px;border-radius:2px;background:{RED}"></span><p class="ct">위험순위 TOP 5</p></div>'
            f'<div class="row" style="margin:10px 0 2px"><b style="color:{RED};font-size:16px">{upjong if upjong != "전체" else "전체 업종"}</b><span class="sp"></span>'
            f'<span class="cs">{m} 기준 · 전월 대비</span></div>{"".join(rows)}</div>')


def info_card_html(r, busan: float, sig: list[str], top_up: str, qp: dict) -> str:
    href = link(**{**qp, "page": "detail", "code": r["code"], "popup": "0"})
    return (f'<div class="card"><div class="row" style="gap:10px"><span style="font-size:25px;font-weight:700;color:{INK}">{r["dong"]}</span>'
            f'<span class="mut" style="font-size:19px">{r["gu"]}</span><span class="sp"></span>'
            f'<span class="tag" style="background:{r["color"]};color:#fff">{r["grade"]}</span></div>'
            f'<div class="row" style="margin-top:14px"><span class="mut">예측 폐업확률</span><span class="sp"></span><b style="font-size:20px;color:{INK}">{r["prob"]:.1f}% <span class="mut" style="font-weight:400">(부산 {busan:.1f}%)</span></b></div>'
            f'<div class="row" style="margin-top:8px;gap:16px;align-items:flex-start"><span class="mut" style="white-space:nowrap">주된 신호</span><span class="sp"></span><b style="color:{RED};text-align:right">{sig[0]}</b></div>'
            f'<div class="row" style="margin-top:8px"><span class="mut">신호 업종</span><span class="sp"></span><b style="color:{INK}">{top_up}</b></div>'
            f'<div style="margin-top:14px"><a class="go" href="{href}" target="_self">상세(②)로 이동 →</a></div></div>')


def compare_html(rows) -> str:
    if len(rows) < 2:
        return f'<div class="cs" style="padding:8px 2px">비교할 행정동을 2곳 이상 고르세요.</div>'
    cols = "".join(f'<th style="text-align:right;color:{ACC if i == 0 else MUT};font-weight:600">{r["dong"]}</th>' for i, r in enumerate(rows))
    spec = [("예측 폐업확률", "prob", "%", True), ("최근 6개월 폐업률", "close_rate_6m", "%", True),
            ("카드소비 전년 동월비", "card_yoy", "%", False), ("방문인구 증감", "pop_yoy", "%", False), ("영업 점포 수", "stores", "곳", None)]
    body = []
    for name, k, u, hi_bad in spec:
        vals = [r[k] for r in rows]
        worst = (max(vals) if hi_bad else min(vals)) if hi_bad is not None else None
        tds = "".join(f'<td style="text-align:right;font-weight:{700 if v == worst else 400};color:{RED if v == worst and hi_bad is not None else INK}">'
                      f'{(f"{v:+.1f}" if k in ("card_yoy", "pop_yoy") else (f"{v:.1f}" if u == "%" else f"{int(v)}"))}{u}</td>' for v in vals)
        bg = f' style="background:#FDF1EE"' if k == "prob" else ""
        body.append(f'<tr{bg}><td style="color:{INK}">{name}</td>{tds}</tr>')
    return (f'<table style="width:100%;border-collapse:collapse;font-size:17px"><tr><th style="text-align:left;color:{FNT};font-weight:400">지표</th>{cols}</tr>'
            + "".join(body) + f'</table><div class="cs" style="margin-top:8px">빨간 숫자 = 고른 동 중 더 위험한 쪽</div>')


def popup_component(top3, busan: float, sigs: list[list[str]]) -> str:
    """'폐업예측 한 눈에 보기' — 마우스를 올린 줄이 펼쳐지는 HTML (components.html 로 넣는다)."""
    rows = []
    for i, r in enumerate(top3):
        hi = r["prob"] >= 10
        col, lt, ltx, gbg = ("#1450D2", "#A9C4F2", "#7EA3E6", "#E3ECFB") if hi else ("#4C8FEA", "#C6DBF8", "#94B9EF", "#EDF4FD")
        sg = "".join(f'<div class="sg"><i></i>{s}</div>' for s in sigs[i])
        w = min(r["prob"] / 15 * 100, 100)
        rows.append(f'''<div class="row{' first' if i == 0 else ''}" style="--c:{col};--lt:{lt};--ltx:{ltx};--gbg:{gbg}"><div class="card">
<div class="rk">{i + 1}순위</div><div class="gr fx">{'높음' if hi else '주의'}</div>
<div class="gu">{r['gu']}</div><div class="dg">{r['dong']}</div>
<div class="lab fx">향후 6개월 폐업확률</div><div class="pv">{r['prob']:.1f}%</div>
<div class="df fx">부산 평균보다 <b>{r['prob'] - busan:+.1f}%p</b></div>
<div class="bar"><div class="fill" style="width:{w:.1f}%"></div><div class="avg fx" style="left:{busan / 15 * 100:.1f}%"><span>부산 평균 {busan:.1f}%</span></div></div>
<div class="sig fx"><div class="sl">위험<br>신호</div><div>{sg}</div></div></div></div>''')
    O = ".list:not(:hover) .row.first, .list .row:hover"
    on = lambda sel: ", ".join(f"{s} {sel}" for s in O.split(", "))
    T = ".45s cubic-bezier(.3,.7,.2,1)"
    return f"""<html><head><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"><style>
body{{margin:0;font-family:Pretendard,'Noto Sans KR',sans-serif}}
.list{{position:relative;width:100%}}
.row{{height:76px;transition:height {T};position:relative}}
.card{{position:absolute;inset:0 0 10px 0;border-radius:14px;background:#F4F6F9;transition:background {T};overflow:hidden}}
.card>*{{position:absolute;transition:all {T};white-space:nowrap;line-height:1}}
.rk{{left:16px;top:20px;width:58px;height:26px;border-radius:13px;background:#E3E8EF;color:#6B7280;font-size:15px;font-weight:700;display:flex;align-items:center;justify-content:center}}
.gu{{left:92px;top:18px;font-size:14px;color:#9CA3AF}}
.dg{{left:92px;top:34px;font-size:17px;font-weight:700;color:#6B7280}}
.pv{{right:18px;top:24px;font-size:23px;font-weight:700;color:var(--ltx)}}
.bar{{left:220px;right:120px;top:26px;height:16px;border-radius:6px;background:#E9EDF3}}
.fill{{height:100%;border-radius:inherit;background:var(--lt);transition:background {T}}}
.avg{{position:absolute;top:-6px;bottom:-6px;width:2px;background:#1A1D23}}
.avg span{{position:absolute;top:100%;left:50%;transform:translateX(-50%);padding-top:8px;font-size:15px;color:#6B7280}}
.fx{{opacity:0;transform:translateY(6px);pointer-events:none;transition:opacity .2s,transform .3s}}
.avg.fx{{transform:none}}
.gr{{left:16px;top:66px;width:84px;height:34px;border-radius:17px;background:var(--gbg);color:var(--c);font-size:17px;font-weight:700;display:flex;align-items:center;justify-content:center}}
.lab{{left:auto;right:18px;top:14px;font-size:16px;color:#6B7280}}
.df{{right:18px;top:104px;font-size:15px;color:#6B7280}} .df b{{color:var(--c)}}
.sig{{left:16px;right:16px;top:190px;display:flex;gap:14px;font-size:17px;color:#1A1D23}}
.sl{{font-weight:700;color:#6B7280;line-height:20px;font-size:16px}}
.sg{{display:flex;align-items:center;gap:8px;line-height:22px}} .sg i{{width:7px;height:7px;border-radius:50%;background:var(--c)}}
{O}{{height:260px}}
{on('.card')}{{background:#fff}}
{on('.rk')}{{top:14px;width:96px;height:42px;border-radius:21px;background:#1C2E57;color:#fff;font-size:18px}}
{on('.gu')}{{left:126px;top:14px;font-size:27px;color:#6B7280}}
{on('.dg')}{{left:126px;top:48px;font-size:35px;color:#1A1D23}}
{on('.pv')}{{top:30px;font-size:67px;color:var(--c);letter-spacing:2px}}
{on('.bar')}{{left:16px;right:16px;top:126px;height:38px;border-radius:10px;background:#EAEFF6}}
{on('.fill')}{{background:var(--c)}}
{on('.fx')}{{opacity:1;transform:none;transition:opacity .3s ease .18s,transform .35s ease .18s}}
</style></head><body><div class="list">{''.join(rows)}</div></body></html>"""


# ---------------------------------------------------------------- detail pieces
def hero_html(r, busan: float, gu_avg: float) -> str:
    w = min(r["prob"] / 12 * 100, 100)
    t1, t2 = busan / 12 * 100, gu_avg / 12 * 100
    return (f'<div class="card dark" style="height:300px;position:relative">'
            f'<div class="row" style="gap:10px"><span style="color:{ONDK2};font-size:18px;font-weight:500">폐업위험률</span>'
            f'<span style="color:#A9C9EC;font-size:16px">모델 예측 · 향후 6개월</span><span class="sp"></span>'
            f'<span style="border:1.5px solid #C2D94D;color:#E9F3C2;border-radius:999px;padding:4px 14px;font-size:16px">↗ 전월 {r["mom"]:+.1f}%p</span></div>'
            f'<div style="font-size:107px;font-weight:500;line-height:1;margin-top:18px;letter-spacing:-2px">{r["prob"]:.1f}%</div>'
            f'<div style="position:absolute;left:24px;right:24px;bottom:56px;height:8px;border-radius:4px;background:{NAVY2}">'
            f'<div style="width:{w:.1f}%;height:100%;border-radius:4px;background:{SKY}"></div>'
            f'<div style="position:absolute;left:{t1:.1f}%;top:-5px;width:2px;height:18px;background:#fff"></div>'
            f'<div style="position:absolute;left:{t2:.1f}%;top:-5px;width:2px;height:18px;background:#fff"></div></div>'
            f'<div class="row" style="position:absolute;left:24px;right:24px;bottom:22px"><b style="color:{ONDK2};font-size:17px">부산 평균 {busan:.1f}% · {r["gu"]} {gu_avg:.1f}%</b>'
            f'<span class="sp"></span><span style="color:#A9C9EC;font-size:15px">0 — 12%</span></div></div>')


def stat_html(label: str, value: str, sub: str, h: int = 143) -> str:
    return (f'<div class="card" style="height:{h}px"><div class="lbl">{label}</div>'
            f'<div class="row" style="margin-top:14px"><span style="font-size:43px;font-weight:500;color:{INK}">{value}</span>'
            f'<span class="sp"></span><span class="cs">{sub}</span></div></div>')


def field_html(r, busan_row: dict) -> str:
    items = [("최근 6개월 폐업률", f'{r["close_rate_6m"]:.1f}%', f'부산 {busan_row["close_rate_6m"]:.1f}%'),
             ("1년 미만 폐업 비중", f'{int(r["young_close_share"])}%', f'부산 {busan_row["young_close_share"]:.0f}%'),
             ("카드소비 전년비", f'{r["card_yoy"]:+.1f}%', f'부산 {busan_row["card_yoy"]:+.1f}%'),
             ("방문인구 전년비", f'{r["pop_yoy"]:+.1f}%', f'부산 {busan_row["pop_yoy"]:+.1f}%')]
    cells = "".join(f'<div style="flex:1;{"border-left:1px solid " + DIV + ";padding-left:18px" if i else ""}">'
                    f'<div class="lbl">{a}</div><div style="font-size:35px;font-weight:500;color:{INK};margin-top:8px">{v}</div><div class="cs">{s}</div></div>'
                    for i, (a, v, s) in enumerate(items))
    return (f'<div class="card" style="height:170px"><div class="row" style="gap:10px"><p class="ct">상권 실측 신호</p><span class="cs" style="font-size:16px">직전 기간</span></div>'
            f'<div class="row" style="gap:18px;margin-top:16px;align-items:flex-start">{cells}</div></div>')


def guarantee_html(g: dict, gu: str) -> str:
    ups = "".join(f'<div class="row dl" style="padding:9px 0"><span style="color:{INK}">{u}</span><span class="sp"></span>'
                  f'<span style="color:{INK};width:70px;text-align:right">{rt:.2f}%</span><span class="mut" style="width:80px;text-align:right">{bal:,.0f}억</span></div>'
                  for u, rt, bal in g["upjong"])
    return (f'<div class="card" style="padding:0;overflow:hidden;height:490px">'
            f'<div style="background:{PALE};padding:22px 24px 18px"><div class="row" style="gap:8px"><p class="ct">재단 보증현황</p><span class="mut">{gu}</span></div>'
            f'<div class="lbl" style="margin-top:10px">보증 사고율 (2025년)</div>'
            f'<div class="row"><span style="font-size:51px;font-weight:500;color:{INK}">{g["rate"]:.2f}%</span><span class="sp"></span>'
            f'<span style="border:1.5px solid #8FB0D9;color:#2F4D73;border-radius:999px;padding:4px 12px;font-size:15px;white-space:nowrap">부산 {g["busan"]:.2f}% · {g["rank"]}위/{g["n"]}</span></div></div>'
            f'<div style="padding:16px 24px"><div class="row" style="gap:10px">'
            f'<div style="flex:1"><div class="cs">보증 잔액</div><b style="font-size:23px;color:{INK}">{g["bal"]:,.0f}억</b><div class="cs">구·군 중 {g["bal_rank"]}위</div></div>'
            f'<div style="flex:1"><div class="cs">신규 보증</div><b style="font-size:23px;color:{INK}">{g["new"]:,.0f}억</b><div class="cs">{g["new_cnt"]:,}개 업체</div></div>'
            f'<div style="flex:1"><div class="cs">보증 사고</div><b style="font-size:23px;color:{INK}">{g["acc"]:,.0f}억</b><div class="cs">{g["acc_cnt"]:,}건</div></div></div>'
            f'<div class="row" style="margin-top:16px"><b style="color:{INK};font-size:17px">업종별 사고율</b><span class="sp"></span><span class="cs">사고율 · 잔액</span></div>{ups}'
            f'<div class="cs" style="margin-top:6px">2025년 · 구·군 단위 (행정동 자료 없음) · 재단 실자료</div></div></div>')


def industry_html(t, busan: float) -> str:
    rows = []
    vmax = 16
    for _, r in t.head(6).iterrows():
        hi = r["prob"] > busan
        if r["hold"]:
            mid = f'<span class="cs">표본 부족 · 판단 보류</span>'
        else:
            mid = (f'<div style="flex:1;height:9px;border-radius:5px;background:#EEF2F7;margin:0 14px"><div style="width:{min(r["prob"] / vmax * 100, 100):.1f}%;height:100%;border-radius:5px;background:{ACC if hi else LBAR}"></div></div>'
                   f'<b style="color:{INK};width:50px;text-align:right;font-weight:{700 if hi else 400}">{r["prob"]:.1f}%</b>'
                   f'<span style="width:46px;text-align:right;font-size:15.5px;color:{ACC if r["mom"] > 0 else FNT}">{r["mom"]:+.1f}</span>')
        rows.append(f'<div class="row dl" style="padding:12px 0"><span style="width:84px;color:{INK};font-weight:{700 if hi else 400}">{r["upjong"]}</span>{mid}</div>')
    return (f'<div class="card" style="height:410px"><div class="row"><p class="ct">업종별 폐업위험</p><span class="sp"></span><span class="cs">향후 6개월 · 전월 %p</span></div>'
            f'<div class="cs" style="margin:6px 0 4px">진한 막대 = 부산 평균({busan:.1f}%)보다 높음</div>{"".join(rows)}</div>')


def _slice(cx, cy, r, a0, a1, g, rc):
    d = g / 2 + rc; R = r - rc; th = math.radians(a1 - a0); bis = math.radians((a0 + a1) / 2)
    apex = d / math.sin(th / 2)
    ax, ay = cx + apex * math.cos(bis), cy + apex * math.sin(bis)
    L = math.sqrt(max(R * R - d * d, 1))
    A0, A1 = math.radians(a0), math.radians(a1)
    p0 = (cx + L * math.cos(A0) + d * math.cos(A0 + math.pi / 2), cy + L * math.sin(A0) + d * math.sin(A0 + math.pi / 2))
    p1 = (cx + L * math.cos(A1) + d * math.cos(A1 - math.pi / 2), cy + L * math.sin(A1) + d * math.sin(A1 - math.pi / 2))
    large = 1 if (a1 - a0) > 180 else 0
    return f"M{ax:.1f} {ay:.1f} L{p0[0]:.1f} {p0[1]:.1f} A{R:.1f} {R:.1f} 0 {large} 1 {p1[0]:.1f} {p1[1]:.1f} Z"


def pie_svg(parts, size=240) -> str:
    cols = [LIME, SKY, "#8ED2F4", "#5B83C9"]
    cx = cy = size / 2; ang = -90; out = []
    for k, (_, p, _) in enumerate(parts):
        a1 = ang + p * 3.6
        c = cols[k % 4]
        out.append(f'<path d="{_slice(cx, cy, size / 2 - 4, ang, a1, 7, 6)}" fill="{c}" stroke="{c}" stroke-width="12" stroke-linejoin="round"/>')
        ang = a1
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(out)}</svg>'


def causes_html(parts) -> str:
    cols = [LIME, SKY, "#8ED2F4", "#5B83C9"]
    leg = "".join(f'<div class="row" style="padding:10px 0;{"border-top:1px solid #2A62B8;" if k else ""}gap:12px;align-items:flex-start">'
                  f'<span style="width:14px;height:14px;border-radius:4px;background:{cols[k]};margin-top:4px"></span>'
                  f'<div><div style="color:{"#fff" if k < 3 else ONDK2};font-weight:{700 if k == 0 else 600};font-size:{16 if k == 0 else 15}px">{n}</div>'
                  f'<div style="color:{ONDK2};font-size:15px;margin-top:3px">{s}</div></div><span class="sp"></span>'
                  f'<b style="color:{"#fff" if k < 3 else ONDK2};font-size:{24 if k == 0 else 20}px;font-weight:{700 if k == 0 else 500}">{p}%</b></div>'
                  for k, (n, p, s) in enumerate(parts))
    return (f'<div class="card dark" style="height:410px"><div class="row"><p class="ct">폐업위험을 높이는 원인</p><span class="sp"></span><span class="cs">SHAP 기여 비중 · 인과 아님</span></div>'
            f'<div class="row" style="gap:24px;margin-top:10px;align-items:center"><div style="flex:1">{leg}</div><div>{pie_svg(parts)}</div></div></div>')


def trend_html(months, line, base, qs, q) -> str:
    W, H = 300, 150
    lo, hi = min(line + base) - 3, max(line + base) + 3
    P = lambda a: " ".join(f"{k * W / (len(a) - 1):.1f},{H - (v - lo) / (hi - lo) * H:.1f}" for k, v in enumerate(a))
    svg = (f'<svg width="100%" viewBox="0 0 {W} {H + 4}" preserveAspectRatio="none" style="height:{H}px">'
           f'<polyline points="{P(base)}" fill="none" stroke="{FNT}" stroke-width="1.5" stroke-dasharray="4 4"/>'
           f'<polyline points="{P(line)}" fill="none" stroke="{LBAR}" stroke-width="3" stroke-linejoin="round"/></svg>')
    mx = max(q)
    bars = "".join(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:6px">'
                   f'<div style="width:14px;height:150px;border-radius:7px;background:#EEF2F7;display:flex;align-items:flex-end">'
                   f'<div style="width:100%;height:{v / mx * 100:.0f}%;border-radius:7px;background:{ACC if k == len(q) - 1 else LBAR}"></div></div>'
                   f'<span class="cs" style="font-size:13.5px">{qs[k] if k in (0, 4, len(q) - 1) else "&nbsp;"}</span></div>' for k, v in enumerate(q))
    return (f'<div class="card" style="height:410px"><p class="ct">언제부터 나빠졌나</p>'
            f'<div class="row" style="gap:20px;margin-top:14px;align-items:flex-start">'
            f'<div style="flex:1.15"><div class="lbl">카드소비 지수 ({months[0]} = 100)</div>{svg}'
            f'<div class="row cs"><span>{months[0]}</span><span class="sp"></span><span>{months[1]}</span></div>'
            f'<div class="row cs" style="gap:8px;margin-top:8px"><span style="width:18px;height:3px;background:{LBAR}"></span>선택 동'
            f'<span style="width:18px;border-top:2px dashed {FNT};margin-left:10px"></span>부산</div></div>'
            f'<div style="flex:1"><div class="lbl">분기별 폐업 신고</div><div class="row" style="margin-top:10px;align-items:flex-end">{bars}</div></div></div>'
            f'<div class="row" style="margin-top:6px"><span class="sp"></span><b style="color:{INK}">최근 분기 {q[-1]}건</b></div></div>')


def compare3_html(r, gu_row: dict, busan_row: dict) -> str:
    spec = [("폐업위험률 (예측)", "prob", "{:.1f}%"), ("최근 6개월 폐업률", "close_rate_6m", "{:.1f}%"),
            ("1년 미만 폐업 비중", "young_close_share", "{:.0f}%"), ("카드소비 전년비", "card_yoy", "{:+.1f}%"), ("방문인구 전년비", "pop_yoy", "{:+.1f}%")]
    rows = "".join(f'<tr style="border-top:1px solid {DIV}"><td style="padding:11px 0;color:{MUT}">{n}</td>'
                   f'<td style="text-align:right;font-weight:700;color:{INK}">{f.format(r[k])}</td><td style="text-align:right;color:{INK}">{f.format(gu_row[k])}</td>'
                   f'<td style="text-align:right;color:{INK}">{f.format(busan_row[k])}</td></tr>' for n, k, f in spec)
    return (f'<div class="card"><p class="ct">주변과 비교</p><table style="width:100%;border-collapse:collapse;font-size:17px;margin-top:8px">'
            f'<tr><th></th><th style="text-align:right;color:{ACC};font-size:15.5px">{r["dong"]}</th><th style="text-align:right;color:{MUT};font-size:15.5px">{r["gu"]}</th>'
            f'<th style="text-align:right;color:{MUT};font-size:15.5px">부산</th></tr>{rows}</table></div>')


def confidence_html(r, month: str) -> str:
    ok = "충분" if r["stores"] >= 30 else "부족"
    items = [("판단 근거 점포", f'{int(r["stores"])}곳', f"30곳 이상이면 판단 · {ok}"), ("6개월 전 예측 적중", "71%", "예시 값"),
             ("자료 최신월", f"{month[:4]}.{month[4:]}", "카드·인구 기준")]
    cells = "".join(f'<div style="flex:1"><div class="cs">{a}</div><div style="font-size:33px;font-weight:500;color:{INK};margin:6px 0">{v}</div><div class="cs">{s}</div></div>' for a, v, s in items)
    return f'<div class="card" style="height:220px"><p class="ct">예측 신뢰도</p><div class="row" style="gap:14px;margin-top:22px;align-items:flex-start">{cells}</div></div>'


def netopen_html(r) -> str:
    net = int(r["open_6m"] - r["close_6m"])
    return (f'<div class="card pale" style="height:220px"><div class="row"><p class="ct">점포 순증</p><span class="sp"></span><span class="cs" style="color:#4A5F78">최근 6개월</span></div>'
            f'<div style="font-size:47px;font-weight:500;color:{INK};margin-top:14px">{net:+d}곳</div>'
            f'<div class="cs" style="color:#4A5F78">개업 {int(r["open_6m"])} · 폐업 {int(r["close_6m"])}</div></div>')


def map_legend_html() -> str:
    return legend_html()
