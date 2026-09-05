# -*- coding: utf-8 -*-
"""차트 — 색은 config.COLORS 에서만 가져온다. 여기서 새로 만들지 않는다.

강조 색은 "이걸 봐야 한다"는 뜻일 때만 쓴다. 장식에 쓰면 진짜 경고를 아무도 안 본다.
그리고 색만으로 전달하지 않는다 — 색 + 기호 + 글자를 같이 쓴다.
빨강·초록만으로 판정을 전달하면 스무 명 중 한 명은 구분하지 못한다.
"""
import altair as alt
import pandas as pd

from core import config

alt.data_transformers.disable_max_rows()

MARK = config.MARKS       # ● ▲ ✕ ○
KO = config.LABELS_KO     # 정상 / 주의 / 차단 / 없음


def _pct(v, nd=1):
    return "—" if v is None or pd.isna(v) else f"{v:.{nd}%}"


def funnel_bar(df, title="", worst_idx=None):
    """단계별 인원 막대. 병목 한 칸만 강조색을 쓰고, 거기에 기호를 붙인다."""
    d = df.copy()
    d["순서"] = range(len(d))
    d["상태"] = ["warn" if i == worst_idx else "neutral" for i in range(len(d))]
    d["색"] = [config.COLORS[s] for s in d["상태"]]
    d["표시"] = [
        f"{n:,}" + (f"  {MARK['warn']} 병목 {r:.1%}" if i == worst_idx else
                    (f"  {r:.1%}" if pd.notna(r) else ""))
        for i, (n, r) in enumerate(zip(d["인원"], d["직전 대비"]))
    ]
    base = alt.Chart(d).encode(
        y=alt.Y("단계:N", sort=alt.SortField("순서"), title=None),
        x=alt.X("인원:Q", title="인원"),
    )
    bars = base.mark_bar(height=22).encode(
        color=alt.Color("색:N", scale=None),
        tooltip=["단계", "인원",
                 alt.Tooltip("직전 대비:Q", format=".1%"),
                 alt.Tooltip("누적:Q", format=".1%")],
    )
    text = base.mark_text(align="left", dx=4, fontSize=11).encode(text="표시:N")
    return (bars + text).properties(height=28 * len(d) + 20, title=title)


def decomp_bar(df, axis_name):
    """분해 — 전환율 막대 + 비중. 표본 미달 칸은 값 없이 사유만 남는다.

    무엇을 감출지는 여기서 정하지 않는다. verdict.decomp_with_trust() 가
    이미 «사유» 컬럼에 판정을 넣어 두었고 값도 지웠다.
    차트가 임계값을 또 들고 있으면 두 곳이 갈릴 수 있다.
    """
    d = df.copy()
    reasons = d["사유"] if "사유" in d.columns else [None] * len(d)
    d["상태"] = ["none" if (isinstance(r, str) and r) else "ok" for r in reasons]
    d["색"] = [config.COLORS[s] for s in d["상태"]]
    d["라벨"] = [
        (f"{MARK['none']} {KO['none']} — 표본 {int(s):,}"
         if st == "none" else
         f"{MARK['ok']} {_pct(r)}   비중 {w:.0%} · n={int(s):,}")
        for st, r, w, s in zip(d["상태"], d["전환율"], d["비중"], d["시작"])
    ]
    base = alt.Chart(d).encode(
        y=alt.Y("칸:N", sort="-x", title=axis_name),
        x=alt.X("전환율:Q", title="전환율", axis=alt.Axis(format="%")),
    )
    bars = base.mark_bar(height=20).encode(
        color=alt.Color("색:N", scale=None),
        tooltip=["칸", "시작", "도달",
                 alt.Tooltip("전환율:Q", format=".1%"),
                 alt.Tooltip("비중:Q", format=".1%")],
    )
    text = base.mark_text(align="left", dx=4, fontSize=11).encode(text="라벨:N")
    return (bars + text).properties(height=26 * len(d) + 20)


def share_bar(df, axis_name):
    """비중 막대 — 전환율만 보면 규모를 놓친다. 옆에 나란히 둔다."""
    d = df.copy()
    d["라벨"] = [f"{w:.0%}" for w in d["비중"]]
    base = alt.Chart(d).encode(
        y=alt.Y("칸:N", sort="-x", title=None, axis=alt.Axis(labels=False)),
        x=alt.X("비중:Q", title="비중", axis=alt.Axis(format="%")),
    )
    bars = base.mark_bar(height=20, color=config.COLORS["muted"])
    text = base.mark_text(align="left", dx=4, fontSize=11,
                          color="#555").encode(text="라벨:N")
    return (bars + text).properties(height=26 * len(d) + 20)


def sparkline(series, name):
    d = pd.DataFrame({"월": series.index.astype(str), "값": series.values}).dropna()
    if d.empty:
        return None
    return alt.Chart(d).mark_line(point=True, color=config.COLORS["neutral"]).encode(
        x=alt.X("월:N", title=None, axis=alt.Axis(labelAngle=-45, labelFontSize=9)),
        y=alt.Y("값:Q", title=None, scale=alt.Scale(zero=False)),
        tooltip=["월", alt.Tooltip("값:Q", format=".3f")],
    ).properties(height=90, title=alt.TitleParams(name, fontSize=11))


def cohort_bar(df, value_col, title):
    """코호트 — 못 믿을 사유가 있는 칸은 값을 그리지 않고 «판정 보류»만 남긴다."""
    d = df.copy()
    hidden = [isinstance(s, str) and bool(s) for s in d["못 믿을 사유"]]
    d["표시값"] = [None if h else v for h, v in zip(hidden, d[value_col])]
    d["색"] = [config.COLORS["none"] if h else config.COLORS["neutral"]
               for h in hidden]
    d["표식"] = [f"{MARK['none']} 판정 보류" if h else "" for h in hidden]
    d["바닥"] = [0.0 for _ in hidden]
    bars = alt.Chart(d).mark_bar().encode(
        x=alt.X("코호트:N", title=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("표시값:Q", title=title, axis=alt.Axis(format="%")),
        color=alt.Color("색:N", scale=None),
        tooltip=["코호트", "인원", alt.Tooltip("표시값:Q", format=".1%"),
                 "못 믿을 사유"],
    )
    note = alt.Chart(d).mark_text(angle=270, align="left", dy=0, dx=0,
                                  fontSize=10,
                                  color=config.COLORS["none"]).encode(
        x=alt.X("코호트:N"), y=alt.Y("바닥:Q"), text="표식:N")
    return (bars + note).properties(height=210)


def verdict_legend():
    """색이 무슨 뜻인지 한 줄. 이 넷은 도메인이 달라도 의미가 같다."""
    return " · ".join(f"{MARK[k]} {KO[k]}" for k in ("ok", "warn", "block", "none"))
