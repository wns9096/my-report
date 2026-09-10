# -*- coding: utf-8 -*-
"""제안서에 들어갈 그림만 만든다 — 9주차 Day3.

`viz/charts.py` 는 화면용(Altair)이고 여기는 문서용이다. 문서는 파일 하나로
열려야 해서 그림도 문자열이어야 한다 — 그래서 인라인 SVG 를 돌려준다.

규칙 셋. 그림 하나에는 그것이 증명하는 문장 하나가 본문에 있어야 한다.
문장이 없는 그림은 장식이고, 장식은 여기에 없다.

  1) funnel_svg  «여기서 가장 많이 샌다»      단계별 막대 — 병목 하나만 강조색
  2) gap_svg     «이 집단과 저 집단이 다르다»  칸별 막대 — 최고·최저만 색
  3) trend_svg   «줄고 있다 / 늘고 있다»       월별 꺾은선 — 임계선은 점선

색은 셋뿐이다 — 강조 1 · 기본 1 · 회색 1. 전부 `config.COLORS` 에서 온다.
글자와 축은 색을 지정하지 않고 `currentColor` 를 쓴다. 어두운 테마에서
검정 글자가 그대로 남는 것을 막는다 — 문서에서는 먹색을, 화면에서는 테마색을
따라간다.
"""
import html
import re

import pandas as pd

from core import config

ACCENT = config.COLORS["warn"]      # 강조 — 병목 · 최저 칸
BASE = config.COLORS["neutral"]     # 기본 — 나머지 값
GRAY = config.COLORS["muted"]       # 회색 — 견주기만 하는 칸

W = 680
ROW = 30
GAP = 8
FS = 12                             # 기본 글자 크기(px)


def _esc(s):
    return html.escape(str(s), quote=False)


def height_of(svg: str, default=240) -> int:
    """viewBox 에서 높이를 읽는다. 화면에 끼울 때 높이를 줘야 한다."""
    m = re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg or "")
    return int(float(m.group(1))) + 8 if m else default


def frame(svg: str) -> str:
    """화면에 끼울 때 쓰는 껍데기.

    ★ 처음에는 st.html() 로 넣었는데 **아무것도 안 나왔다.** Streamlit 1.45.1
      의 st.html 은 svg 를 통째로 버린다. 에러도 안 난다 — 그냥 없다.
      실제 브라우저로 찍어 보고서야 알았다. 렌더 트리 검사로는 안 보이는 자리다.
      components.html 은 iframe 이라 바깥 글자색이 안 넘어온다. 그래서
      currentColor 가 먹을 색을 여기서 직접 준다 (테마는 light 로 고정돼 있다).
    """
    ink = config.DOC_COLORS["ink"]
    font = "Malgun Gothic, Nanum Gothic, sans-serif"
    return (f'<body style="margin:0;color:{ink};font:13px/1.5 {font}">'
            f'{svg}</body>')


def _tw(s, fs=FS):
    """글자가 차지하는 너비를 잰다. 한글은 폭이 두 배다 —
    ascii 기준으로만 재면 라벨이 잘린다(부록 D의 «글자가 잘림»)."""
    return sum((fs if ord(c) > 0x2000 else fs * 0.55) for c in str(s))


def _wrap(inner, w, h, caption):
    """SVG 껍데기. caption 은 그림 안 맨 아래에 넣는다 —
    그림과 caption 이 따로 떨어지면 옮겨 붙일 때 caption 만 빠진다."""
    cap = (f'<text x="0" y="{h - 4}" font-size="10.5" fill="currentColor" '
           f'opacity=".62">{_esc(caption)}</text>') if caption else ""
    # height="auto" 는 SVG 속성이 아니다 — 브라우저가 무시하고 기본 높이를
    # 써서 그림 위아래로 빈 자리가 크게 남았다. 실제로 그렇게 찍혔다.
    # 비율은 viewBox 가 정하게 두고 크기는 CSS 로 준다.
    return (f'<svg viewBox="0 0 {w} {h}" role="img" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="inherit" '
            f'preserveAspectRatio="xMinYMin meet" '
            f'style="display:block;width:100%;height:auto;max-width:{w}px">'
            f'{inner}{cap}</svg>')


def _bars(rows, caption, unit=""):
    """가로 막대 공통. rows = [(라벨, 값, 표시문구, 색)] — 값은 0 이상 실수.

    막대 길이는 실제 값에서 계산한다. 가장 큰 값이 축의 최대다.
    """
    rows = [r for r in rows if r[1] is not None]      # 값 없는 계열은 안 그린다
    if not rows:
        return ""
    lw = min(210, max(_tw(r[0]) for r in rows) + 10)
    vw = max(_tw(r[2], 11.5) for r in rows) + 12
    x0 = lw + 8
    x1 = W - vw - 6
    span = max(x1 - x0, 60)
    vmax = max(r[1] for r in rows) or 1
    h = len(rows) * (ROW + GAP) + 46

    out = []
    for i, (label, v, shown, color) in enumerate(rows):
        y = i * (ROW + GAP) + 6
        bw = max(span * (v / vmax), 2)
        out.append(
            f'<text x="{lw}" y="{y + ROW / 2 + 4}" text-anchor="end" '
            f'font-size="{FS}" fill="currentColor">{_esc(label)}</text>'
            f'<rect x="{x0}" y="{y}" width="{bw:.1f}" height="{ROW}" '
            f'rx="2" fill="{color}"/>'
            f'<text x="{x0 + bw + 7:.1f}" y="{y + ROW / 2 + 4}" '
            f'font-size="11.5" fill="currentColor" font-weight="600">'
            f'{_esc(shown)}</text>')
    # 축 — 0 과 최댓값만. 눈금이 많으면 값 라벨과 겹친다.
    # 최댓값은 막대에 찍힌 값과 자릿수를 맞춘다. 23.4% 를 «23%» 로 적으면
    # 축과 막대가 서로 다른 값을 말하는 것처럼 보인다.
    top = f"{vmax:,.1f}%" if unit == "%" else f"{vmax:,.0f}{unit}"
    ay = len(rows) * (ROW + GAP) + 2
    out.append(
        f'<line x1="{x0}" y1="{ay}" x2="{x1}" y2="{ay}" '
        f'stroke="currentColor" opacity=".25"/>'
        f'<text x="{x0}" y="{ay + 13}" font-size="10" fill="currentColor" '
        f'opacity=".62">0</text>'
        f'<text x="{x1}" y="{ay + 13}" font-size="10" text-anchor="end" '
        f'fill="currentColor" opacity=".62">{_esc(top)}</text>')
    return _wrap("".join(out), W, h, caption)


def funnel_svg(현황):
    """단계별 도달 막대. 병목 구간의 «도착 단계» 하나만 강조색."""
    f, worst, unit = 현황["표"], 현황["병목"], 현황["단위"]
    rows = []
    for i, r in f.iterrows():
        # pandas 는 None 이 아니라 NaN 을 돌려준다. `is None` 으로 보면
        # 첫 단계에 «nan%» 가 그대로 인쇄된다 — 실제로 그렇게 찍혔다.
        prev = ("" if pd.isna(r["직전 대비"])
                else f"  직전 대비 {float(r['직전 대비']):.1%}")
        rows.append((str(r["단계"]), float(r["인원"]),
                     f"{int(r['인원']):,}{unit}{prev}",
                     ACCENT if i == worst else BASE))
    cap = (f"세는 단위 {현황['그레인']} · 강조한 칸이 병목 구간"
           f"({현황['병목 구간']})의 도착 단계입니다")
    return _bars(rows, cap, unit)


def gap_svg(원인):
    """칸별 전환율 가로 막대. 최고·최저만 색, 나머지는 회색.

    판정 보류된 칸은 그리지 않는다 — 0 으로 그리면 «없다»로 읽힌다.
    몇 칸을 안 그렸는지는 caption 에 적는다.
    """
    g, unit = 원인["표"], 원인["단위"]
    rows = []
    for _, r in g.iterrows():
        if r["사유"] is not None or r["전환율"] is None:
            continue
        color = {"최고": BASE, "최저": ACCENT}.get(r["표시"], GRAY)
        rows.append((str(r["칸"]), float(r["전환율"]) * 100,
                     f"{float(r['전환율']) * 100:.1f}%  "
                     f"({int(r['도달']):,}/{int(r['시작']):,}{unit})", color))
    hidden = int(g["사유"].notna().sum())
    cap = (f"{원인['구간']} 구간 · 축 {원인['축']} · 값은 전환율(%)입니다")
    if hidden:
        cap += f" · 표본이 모자란 {hidden}칸은 그리지 않았습니다"
    return _bars(rows, cap, "%")


def trend_svg(추세):
    """월별 꺾은선. 경고선은 점선.

    믿을 수 있는 구간만 그린다. 관측이 안 찬 달을 함께 그리면 «떨어졌다»로
    읽히는데, 떨어진 것이 아니라 아직 결과가 안 난 것이다.
    위험선은 그리지 않고 caption 에 적는다 — 선을 하나 더 그으면 색이 넷이 된다.
    """
    s = 추세["값"]
    keep = [i for i in s.index if i in set(추세["유효 구간"])]
    s = s.loc[keep].dropna()
    if len(s) < 2:
        return ""
    pct = 추세["형식"] == "%"

    def val(v):
        return float(v) * 100 if pct else float(v)

    ys = [val(v) for v in s.values]
    lines = [val(추세[k]) for k in ("경고",) if 추세.get(k) is not None]
    lo, hi = min(ys + lines), max(ys + lines)
    pad = max((hi - lo) * 0.35, 0.6)
    lo, hi = lo - pad, hi + pad

    left, right, top = 52, W - 14, 26
    h, bottom = 210, 210 - 52
    def px(i):
        return left + (right - left) * (i / max(len(s) - 1, 1))

    def py(v):
        return bottom - (bottom - top) * ((v - lo) / (hi - lo or 1))

    fmt = (lambda v: f"{v:.1f}%") if pct else (lambda v: f"{v:.2f}")
    out = []
    # y 눈금 셋
    for t in (lo, (lo + hi) / 2, hi):
        out.append(
            f'<line x1="{left}" y1="{py(t):.1f}" x2="{right}" y2="{py(t):.1f}" '
            f'stroke="currentColor" opacity=".12"/>'
            f'<text x="{left - 7}" y="{py(t) + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="currentColor" opacity=".62">{fmt(t)}</text>')
    # 경고선 — 점선
    if 추세.get("경고") is not None:
        wy = py(val(추세["경고"]))
        out.append(
            f'<line x1="{left}" y1="{wy:.1f}" x2="{right}" y2="{wy:.1f}" '
            f'stroke="{ACCENT}" stroke-width="1.4" stroke-dasharray="5 4"/>'
            # 라벨을 오른쪽 끝에 두면 마지막 점의 값 라벨과 겹친다.
            f'<text x="{left + 4}" y="{wy - 6:.1f}" '
            f'font-size="10" fill="{ACCENT}">경고선 {fmt(val(추세["경고"]))}</text>')
    # 꺾은선
    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(ys))
    out.append(f'<polyline points="{pts}" fill="none" stroke="{BASE}" '
               f'stroke-width="2"/>')
    for i, v in enumerate(ys):
        out.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3" '
                   f'fill="{BASE}"/>')
        # 값 라벨은 한 칸 걸러 — 열두 개를 다 적으면 겹친다
        if i % 2 == 0 or i == len(ys) - 1:
            out.append(f'<text x="{px(i):.1f}" y="{py(v) - 9:.1f}" '
                       f'text-anchor="middle" font-size="10" '
                       f'fill="currentColor">{fmt(v)}</text>')
        out.append(f'<text x="{px(i):.1f}" y="{bottom + 15}" '
                   f'text-anchor="middle" font-size="9.5" fill="currentColor" '
                   f'opacity=".62">{_esc(str(s.index[i])[-5:])}</text>')

    cap = f"{추세['지표']} 월별"
    dropped = len(추세["값"]) - len(s)
    if dropped:
        cap += (f" · 관측이 덜 찬 최근 {dropped}개월은 그리지 않았습니다 "
                f"(유효 구간 ~{config.VALID_UNTIL})")
    if 추세.get("위험") is not None:
        cap += f" · 위험선 {fmt(val(추세['위험']))}"
    return _wrap("".join(out), W, h, cap)
