# -*- coding: utf-8 -*-
"""차트 — 색은 config.COLORS 에서만 가져온다. 여기서 새로 만들지 않는다.

강조 색은 "이걸 봐야 한다"는 뜻일 때만 쓴다. 장식에 쓰면 진짜 경고를 아무도 안 본다.
그리고 색만으로 전달하지 않는다 — 색 + 기호 + 글자를 같이 쓴다.
빨강·초록만으로 판정을 전달하면 스무 명 중 한 명은 구분하지 못한다.

읽히지 않으면 안 그린 것과 같다. 그래서 세 가지를 지킨다.
  · 막대 끝의 숫자가 잘리지 않게 x축 범위에 여유를 둔다
  · 항목 이름을 «…» 로 자르지 않는다 (labelLimit=0)
  · 나란히 둔 두 그림이 서로 어긋날 바에는 그림 하나로 줄인다
"""
import altair as alt
import pandas as pd

from core import config

alt.data_transformers.disable_max_rows()

MARK = config.MARKS       # ● ▲ ✕ ○
KO = config.LABELS_KO     # 정상 / 주의 / 차단 / 없음

# 막대 끝에 붙는 글자가 그림 밖으로 나가 잘리는 것을 막는다.
# 글자 길이만큼 x축을 늘려 준다 — 좁은 화면일수록 이게 없으면 숫자가 사라진다.
_HEADROOM = 1.6
# 항목 이름을 자르지 않는다. 기본값(180px)이면 «경쟁 높음 (0.65~1.…» 이 된다.
_YAXIS = alt.Axis(labelLimit=0, labelFontSize=11)


def _pct(v, nd=1):
    return "—" if v is None or pd.isna(v) else f"{v:.{nd}%}"


def _xmax(series, headroom=_HEADROOM):
    m = float(pd.to_numeric(series, errors="coerce").max() or 0)
    return m * headroom if m > 0 else 1


def funnel_bar(df, title="", worst_idx=None):
    """단계별 인원 막대. 병목 한 칸만 강조색을 쓰고, 거기에 기호를 붙인다."""
    d = df.copy()
    d["순서"] = range(len(d))
    d["상태"] = ["warn" if i == worst_idx else "neutral" for i in range(len(d))]
    d["색"] = [config.COLORS[s] for s in d["상태"]]
    d["표시"] = [
        f"{n:,}명" + (f"   {MARK['warn']} 병목 {r:.1%}" if i == worst_idx else
                      (f"   {r:.1%}" if pd.notna(r) else ""))
        for i, (n, r) in enumerate(zip(d["인원"], d["직전 대비"]))
    ]
    base = alt.Chart(d).encode(
        y=alt.Y("단계:N", sort=alt.SortField("순서"), title=None, axis=_YAXIS),
        x=alt.X("인원:Q", title="인원 (명)",
                scale=alt.Scale(domain=[0, _xmax(d["인원"])], nice=False)),
    )
    bars = base.mark_bar(height=22).encode(
        color=alt.Color("색:N", scale=None),
        tooltip=[alt.Tooltip("단계:N"), alt.Tooltip("인원:Q", format=","),
                 alt.Tooltip("직전 대비:Q", title="직전 단계 대비", format=".1%"),
                 alt.Tooltip("누적:Q", title="첫 단계 대비 누적", format=".2%")],
    )
    text = base.mark_text(align="left", dx=6, fontSize=11,
                          baseline="middle").encode(text="표시:N")
    # ★ 한 칸을 30px 로 뒀더니 막대가 서로 붙고, Vega 가 겹치는 축 이름을
    #   자동으로 지웠다. 네 단계 중 «지원»과 «최종 합격»만 남아 가운데 두
    #   막대가 무엇인지 알 수 없었다. 축 이름이 사라지는 것은 «자리가 없다»는
    #   신호다 — 글자 크기를 줄이는 게 아니라 자리를 준다.
    return (bars + text).properties(
        height=46 * len(d) + 56, title=title,
    ).configure_view(strokeWidth=0)


def decomp_bar(df, axis_name):
    """분해 — 칸별 전환율. 비중은 막대 옆 글자와 표로 같이 낸다.

    ★ 처음에는 전환율 그림과 비중 그림을 나란히 두고 오른쪽 이름을 감췄다.
      두 그림의 정렬 기준이 달라서(왼쪽은 전환율 순, 오른쪽은 비중 순)
      «경쟁 낮음의 비중»으로 읽히는 자리에 다른 칸의 값이 있었다.
      순서를 맞춰 hconcat 으로 묶었더니 이번에는 좁은 화면에서 오른쪽 그림이
      아예 안 그려졌다.

      그림 둘을 나란히 두는 것 자체를 그만뒀다. 비중은 막대 옆 글자와 아래
      표에 있다 — 그림을 하나 더 그리는 것보다 그쪽이 확실히 읽힌다.
      **두 그림을 맞추는 것보다, 하나로 줄이는 편이 안 틀린다.**

    표본 미달 칸은 값 없이 사유만 남는다. 무엇을 감출지는 여기서 정하지 않는다 —
    verdict.decomp_with_trust() 가 이미 «사유» 컬럼에 판정을 넣고 값도 지웠다.
    """
    d = df.copy()
    reasons = d["사유"] if "사유" in d.columns else [None] * len(d)
    d["상태"] = ["none" if (isinstance(r, str) and r) else "ok" for r in reasons]
    d["색"] = [config.COLORS[s] for s in d["상태"]]
    # 감춘 칸은 맨 아래로 내린다. 값이 없으니 전환율 순에 낄 자리가 없다.
    d["정렬"] = [(-1 if s == "none" else float(r))
                 for s, r in zip(d["상태"], d["전환율"].fillna(0))]
    d["라벨"] = [
        (f"{MARK['none']} 판정 보류 — 표본 {int(n):,}건" if s == "none"
         else f"{_pct(r)}   표본 {int(n):,}건 · 전체의 {w:.1%}")
        for s, r, n, w in zip(d["상태"], d["전환율"], d["시작"], d["비중"])
    ]
    base = alt.Chart(d).encode(
        # 축 이름은 위의 «축» 선택기에 이미 있다. 여기 또 쓰면 세로로 겹쳐 쓰인다.
        y=alt.Y("칸:N", sort=alt.SortField("정렬", order="descending"),
                title=None, axis=_YAXIS),
        x=alt.X("전환율:Q", title=f"{axis_name}별 전환율",
                axis=alt.Axis(format="%", tickCount=4),
                scale=alt.Scale(domain=[0, _xmax(d["전환율"], 2.0)], nice=False)),
    )
    bars = base.mark_bar(height=20).encode(
        color=alt.Color("색:N", scale=None),
        tooltip=[alt.Tooltip("칸:N", title=axis_name),
                 alt.Tooltip("시작:Q", title="시작 (건)", format=","),
                 alt.Tooltip("도달:Q", title="도달 (건)", format=","),
                 alt.Tooltip("전환율:Q", format=".1%"),
                 alt.Tooltip("비중:Q", title="전체에서 차지하는 비중",
                             format=".1%")],
    )
    text = base.mark_text(align="left", dx=6, fontSize=11,
                          baseline="middle").encode(text="라벨:N")
    return (bars + text).properties(
        height=44 * len(d) + 56).configure_view(strokeWidth=0)


def monthly_line(monthly, name, warn=None, danger=None):
    """월별 추이 한 장.

    ★ 처음에는 지표 카드마다 손톱만 한 스파크라인을 넣었다. 카드가 네 칸으로
      좁아서 선이 거의 눌려 보이고 월 이름도 겹쳤다. 작게 넷을 넣는 것보다
      크게 하나를 넣는 편이 실제로 읽힌다.

    경고·위험선을 같이 그린다. 값만 있으면 «이게 좋은 건가»에 답할 수 없다.
    (마지막 달이 아직 안 끝났을 수 있다는 것은 그림 밑에 글로 적는다.
     선의 모양으로 말하면 «점선이 무슨 뜻인가»를 또 설명해야 한다.)
    """
    if name not in monthly.columns:
        return None
    s = monthly[name].dropna()
    if len(s) < 2:
        return None
    d = pd.DataFrame({"월": s.index.astype(str), "값": s.values})
    d["마지막 달"] = [i == len(d) - 1 for i in range(len(d))]

    lo = float(min(list(s) + [x for x in (warn, danger) if x is not None]))
    hi = float(max(list(s) + [x for x in (warn, danger) if x is not None]))
    pad = (hi - lo) * 0.25 or 0.01
    yscale = alt.Scale(domain=[lo - pad, hi + pad], nice=False)

    base = alt.Chart(d).encode(
        x=alt.X("월:N", title=None,
                axis=alt.Axis(labelAngle=-45, labelLimit=0, labelFontSize=10)),
        # y축 제목은 안 쓴다. 그림 위 제목에 이미 지표 이름이 있고,
        # 세로로 쓰면 좁은 화면에서 눈금과 겹친다.
        y=alt.Y("값:Q", title=None, scale=yscale,
                axis=alt.Axis(format="%", tickCount=4)),
    )
    line = base.mark_line(color=config.COLORS["neutral"], strokeWidth=2)
    dots = base.mark_point(filled=True, size=45,
                           color=config.COLORS["neutral"]).encode(
        tooltip=[alt.Tooltip("월:N"), alt.Tooltip("값:Q", format=".2%")])
    layers = [line, dots]
    for v, key, label in ((warn, "warn", "경고선"), (danger, "block", "위험선")):
        if v is None:
            continue
        rule = alt.Chart(pd.DataFrame({"값": [v], "이름": [f"{label} {v:.1%}"]}))
        layers.append(rule.mark_rule(strokeDash=[4, 3], strokeWidth=1.5,
                                     color=config.COLORS[key])
                      .encode(y=alt.Y("값:Q", scale=yscale)))
        # 라벨은 왼쪽 끝에 붙인다. x 를 안 주면 한가운데에 찍혀 선 위에 겹친다.
        layers.append(rule.mark_text(align="left", dx=4, dy=-7, fontSize=10,
                                     color=config.COLORS[key])
                      .encode(x=alt.value(4),
                              y=alt.Y("값:Q", scale=yscale), text="이름:N"))
    return alt.layer(*layers).properties(height=230).configure_view(strokeWidth=0)


def cohort_bar(df, value_col, title):
    """코호트 — 못 믿을 사유가 있는 칸은 값을 그리지 않고 «판정 보류»만 남긴다."""
    d = df.copy()
    hidden = [isinstance(s, str) and bool(s) for s in d["못 믿을 사유"]]
    d["표시값"] = [None if h else v for h, v in zip(hidden, d[value_col])]
    d["색"] = [config.COLORS["none"] if h else config.COLORS["neutral"]
               for h in hidden]
    d["표식"] = [f"{MARK['none']} 판정 보류" if h else "" for h in hidden]
    d["바닥"] = [0.0 for _ in hidden]
    top = float(pd.to_numeric(d["표시값"], errors="coerce").max() or 0.1)

    bars = alt.Chart(d).mark_bar(size=26).encode(
        x=alt.X("코호트:N", title="시작 월",
                axis=alt.Axis(labelAngle=-45, labelLimit=0, labelFontSize=10)),
        # y축 제목은 안 쓴다 — 세로로 쓰면 좁은 화면에서 눈금과 겹쳐 뭉갠다.
        # 무슨 값인지는 그림 위 제목과 손을 올렸을 때 나오는 설명에 있다.
        y=alt.Y("표시값:Q", title=None,
                axis=alt.Axis(format="%", tickCount=4),
                # 막대 위 숫자가 천장에 닿지 않게 여유를 둔다
                scale=alt.Scale(domain=[0, top * 1.25], nice=False)),
        color=alt.Color("색:N", scale=None),
        tooltip=[alt.Tooltip("코호트:N", title="시작 월"),
                 alt.Tooltip("인원:Q", format=","),
                 alt.Tooltip("표시값:Q", title=title, format=".1%"),
                 alt.Tooltip("못 믿을 사유:N", title="못 믿는 이유")],
    )
    vals = alt.Chart(d).mark_text(dy=-7, fontSize=10, color="#555").encode(
        x=alt.X("코호트:N"), y=alt.Y("표시값:Q"),
        text=alt.Text("표시값:Q", format=".0%"))
    # 감춘 칸은 세로로 «판정 보류»만. 값은 어디에도 그리지 않는다.
    note = alt.Chart(d).mark_text(angle=270, align="left", dx=0, dy=0,
                                  fontSize=10,
                                  color=config.COLORS["none"]).encode(
        x=alt.X("코호트:N"), y=alt.Y("바닥:Q"), text="표식:N")
    return (bars + vals + note).properties(height=240).configure_view(
        strokeWidth=0)


def verdict_legend():
    """색이 무슨 뜻인지 한 줄. 이 넷은 도메인이 달라도 의미가 같다."""
    return " · ".join(f"{MARK[k]} {KO[k]}" for k in ("ok", "warn", "block", "none"))
