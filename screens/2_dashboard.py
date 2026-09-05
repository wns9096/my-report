# -*- coding: utf-8 -*-
"""대시보드 — 퍼널 · 지표 카드 · 분해 · 판정. 그리고 게이트 2."""
import pandas as pd
import streamlit as st

from core import config, context, gates, metrics, shell, verdict
from viz import charts

MARK = config.MARKS
KO = config.LABELS_KO
BADGE = {"ok": "green", "warn": "orange", "block": "red", "none": "gray"}


def _fmt(v, kind):
    if v is None or pd.isna(v):
        return "—"
    return {"%": f"{v:.1%}", "n": f"{v:.2f}", "n3": f"{v:.3f}"}[kind]


def _kpi_card(col, name, d, monthly):
    """지표 하나.

    ★ 처음에는 카드 안에 값·배지·설명·스파크라인을 순서대로 쌓았다.
      설명 길이가 지표마다 달라서 카드 높이가 제각각이 되고, 짧은 카드의
      스파크라인만 위로 올라와 줄이 안 맞았다. 넷을 나란히 두는 그림에서
      높이가 어긋나면 비교하는 그림이 아니게 된다.

      그래서 설명은 카드 밖(도움말)으로 빼고, 카드 안에는 세 줄만 둔다 —
      이름 · 값과 전월 대비 · 판정. 세 줄은 지표가 달라도 길이가 같다.
    """
    state = context.kpi_state(name, d["값"])
    help_ = f"{d['설명']} · 표본 {d['표본']:,}"

    # ★ 큰 숫자 옆에 화살표(전월 대비)를 붙였다가 뺐다.
    #   큰 숫자는 «기간 전체» 값이고 화살표는 «지난달 대비»다. 기준이 다른
    #   두 숫자를 붙여 놓으면 «18.1% 가 5.2%p 올랐다»로 읽힌다.
    #   추이는 밑의 월별 그림이 기준을 밝히고 보여 준다.
    if name in monthly.columns:
        m = monthly[name].dropna()
        if len(m) >= 2:
            help_ += (f" · 월별로는 {_fmt(float(m.min()), d['형식'])}"
                      f"~{_fmt(float(m.max()), d['형식'])} 사이")
    with col:
        with st.container(border=True):
            st.metric(f"{name} (기간 전체)", _fmt(d["값"], d["형식"]), help=help_)
            st.badge(f"{MARK[state]} {KO[state]}", color=BADGE[state])


def _verdict_card(c):
    state = verdict.VERDICTS[c["판정"]]
    with st.container(border=True):
        head, body = st.columns([1, 6])
        with head:
            st.badge(f"{MARK[state]} {c['판정']}", color=BADGE[state])
        with body:
            st.markdown(f"**{c['이름']}**")
            if c["판정"] == "무효":
                # 값을 계산하지 않았다. 감춘 것이 아니라 손에 없다.
                st.caption(f"{c['사유']} · 표본 {c['표본']:,} — 지표를 계산하지 않았다")
            else:
                st.markdown(f"{c['이전']} → **{c['이후']}** ({c['변화']}) "
                            f"· 표본 {c['표본']:,}")
                st.caption(c["사유"]
                           + (f" · 가드레일 {c['가드레일']}" if c["가드레일"] else ""))


def _trend_note(ctx):
    """월별 주지표가 갑자기 두 배로 뛰지 않았는가 — 데이터가 바뀐 신호일 수 있다."""
    m = ctx["monthly"][config.MAIN_METRIC].dropna()
    if len(m) < 2:
        return "월이 둘 미만이라 볼 수 없다"
    ratio = (m / m.shift(1)).dropna()
    worst = ratio.abs().sub(1).abs().idxmax()
    return (f"{config.MAIN_METRIC} 월별 {m.min():.1%}~{m.max():.1%} · "
            f"전월 대비 변동이 가장 큰 달 {worst} ({(ratio[worst] - 1) * 100:+.0f}%)")


def _gate2(ctx):
    """출구 게이트. 옮기고 나서 반드시 하는 검산 셋이 여기 다 있어야 한다.

      1 분해한 칸의 합 = 전체인가            (안 맞으면 미분류가 있다)
      2 퍼널 뒤 단계가 앞 단계에 들어 있는가  (앞을 안 거치고 온 것이 몇 건인가)
      3 손계산 표본과 자릿수가 맞는가

    셋 다 코드가 아니라 사람이 판정한다. 코드는 재료만 놓는다.
    """
    st.markdown("#### 게이트 2 · 출구 — 계산 결과가 말이 되는가")

    hidden = [c for c in ctx["cards"] if c["판정"] == "무효"]
    hidden_cells = int(ctx["decomp"]["사유"].notna().sum())
    hidden_coh = int(ctx["cohort"]["못 믿을 사유"].notna().sum())
    ss = context.sum_check(ctx)
    ov = ctx["order_check"]
    hand = ctx["hand_check"]

    rows = [
        {"검산": "① 분해한 칸의 합이 전체와 같은가",
         "결과": f"[{ss['그레인']}] 칸 합 {ss['칸 합']:,} · 전체 {ss['전체']:,} · "
                 f"차이 {ss['차이']:,} · (미분류) {ss['(미분류) 칸']:,}",
         "판정": "맞음" if ss["차이"] == 0 else "안 맞음"},
        {"검산": "② 퍼널 뒤 단계가 앞 단계 안에 들어 있는가",
         "결과": ov["요약"],
         "판정": "맞음" if ov["건수"] == 0 else "퍼널이 아니라 분류다"},
        {"검산": "③ 손계산 표본과 자릿수가 맞는가",
         "결과": hand["요약"],
         "판정": hand["판정"]},
        {"검산": "값이 상식 범위인가",
         "결과": "전환율 0~100% · 인원 음수 없음 · 단계마다 줄어듦", "판정": "맞음"},
        {"검산": "감춰진 항목",
         "결과": f"판정 카드 {len(hidden)}건 · 분해 칸 {hidden_cells}칸 · "
                 f"코호트 {hidden_coh}개", "판정": "—"},
        {"검산": "지난 기간과 크게 다르지 않은가",
         "결과": _trend_note(ctx), "판정": "—"},
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"검산": st.column_config.TextColumn(width="medium"),
                                "판정": st.column_config.TextColumn(width="small")})
    st.caption("①②③ 은 교안이 «옮기고 나서 반드시 하는 검산 셋»으로 꼽은 것이다. "
               "여기서 안 맞으면 아래 숫자는 전부 다시 만들어야 한다.")

    prev = gates.passed(2)
    if prev:
        st.caption(f"직전 통과 — {prev['at']} · {prev['reason']}")

    reason = st.text_area("판단 근거", key="g2_reason", height=80,
                          placeholder="무엇을 보고 왜 말이 된다고 판단했는지 적으십시오.")
    if st.button("통과시키기", type="primary", key="g2_btn",
                 disabled=not gates.passed(1) or not reason.strip()):
        gates.record(2, reason, {"감춘 항목": len(hidden) + hidden_cells + hidden_coh,
                                 "분해 합계 차이": ss["차이"],
                                 "앞 단계 미경유": ov["건수"],
                                 "손계산 차이": hand["차이"]})
        st.success("게이트 2 통과 기록을 남겼습니다.")
        st.rerun()      # 게이트 상태는 파일에 있다 — 위젯이 스스로 못 읽는다


# ── 화면 ──────────────────────────────────────────────────────────────────
shell.topbar()
shell.sidebar()
ctx, _tables, _missing = shell.load()
st.subheader("대시보드")
if not shell.guard(ctx, need_gate=1):
    st.stop()

# ── 지표 카드 ─────────────────────────────────────────────────────────────
st.markdown("#### 지표")
ks = ctx["kpis"]
cols = st.columns(len(ks))
for col, (name, d) in zip(cols, ks.items()):
    _kpi_card(col, name, d, ctx["monthly"])
st.caption(f"«정상 / 주의 / 차단»을 가르는 값과 그 근거는 설정 파일 한 곳에 "
           f"적혀 있다. 모든 계산의 기준일은 {config.AS_OF}로 고정돼 있어 "
           f"언제 돌려도 같은 값이 나온다.")

_th = config.THRESHOLDS.get(config.MAIN_METRIC, {})
_trend = charts.monthly_line(ctx["monthly"], config.MAIN_METRIC,
                             warn=_th.get("경고"), danger=_th.get("위험"))
if _trend is not None:
    st.markdown(f"##### {config.MAIN_METRIC} 월별 추이")
    st.altair_chart(_trend, use_container_width=True)
    st.caption("마지막 달은 아직 결과가 다 나오지 않았을 수 있다. "
               "점 하나가 내려갔다고 성과가 나빠진 것으로 읽지 않는다.")

st.divider()

# ── 퍼널 ─────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])
with left:
    st.markdown(f"#### 획득 퍼널 — **{ctx['grain_ko']}** 기준")
    st.altair_chart(charts.funnel_bar(ctx["funnel"], worst_idx=ctx["worst"]),
                    use_container_width=True)
    f = ctx["funnel"]
    w = ctx["worst"]
    st.caption(f"병목: {f.iloc[w-1]['단계']} → {f.iloc[w]['단계']} "
               f"{f.iloc[w]['직전 대비']:.1%} · 누적 {f.iloc[-1]['누적']:.2%}")
with right:
    st.markdown("#### 같은 퍼널을 두 단위로 세면")
    st.dataframe(
        ctx["gap"], hide_index=True, use_container_width=True,
        column_config={
            "사람": st.column_config.NumberColumn("지원자 (명)", format="localized"),
            "건": st.column_config.NumberColumn("지원 (건)", format="localized"),
            "건/사람": st.column_config.NumberColumn(
                "1명당 건수", format="%.2f",
                help="한 사람이 이 단계까지 평균 몇 건을 넣었는가"),
        })
    st.caption("둘 다 맞는 숫자다. 답하는 질문이 다를 뿐이다. "
               "지원자 1명 기준은 «이 사람이 결국 합격했는가», "
               "지원 1건 기준은 «이 지원서가 통과했는가»에 답한다.")

st.divider()

# ── 유지 퍼널 ────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])
with left:
    st.markdown("#### 유지 퍼널 — 단계는 내가 정의했다")
    st.altair_chart(charts.funnel_bar(ctx["retention"]), use_container_width=True)
with right:
    st.markdown("#### 퍼널인가 분류인가")
    st.dataframe(
        ctx["retention_skip"], hide_index=True, use_container_width=True,
        column_config={"앞 단계 미경유": st.column_config.NumberColumn(
            "앞 단계 미경유 (명)", format="localized")})
    skip = int(ctx["retention_skip"]["앞 단계 미경유"].sum())
    if skip == 0:
        st.caption("앞 단계를 거치지 않고 나타난 대상 0건 — 퍼널로 부를 수 있다.")
    else:
        st.warning(f"앞 단계 미경유 {skip:,}건. 퍼널이 아니라 분류일 수 있다.")
    st.markdown("**이탈 분류** — 순서가 없으므로 전환율을 내지 않는다")
    # 컬럼 이름을 안 맞춰 두면 서식이 안 먹고 0.6575 · None 이 그대로 나온다.
    # 값이 없는 칸은 빈칸으로 둔다 — «None» 은 사람에게 하는 말이 아니다.
    # 비중이 없는 행(성공 종료·판정 보류)은 분모 밖이라 값이 비어 있다.
    # 그냥 두면 화면에 «None» 이 찍힌다 — 사람에게 하는 말이 아니다.
    # Styler 로 빈 칸을 «—» 로 바꾼다.
    _churn = ctx["churn"].style.format(
        {"인원": "{:,.0f}", "구성비(판정 대상 기준)": "{:.1%}"}, na_rep="—")
    st.dataframe(
        _churn, hide_index=True, use_container_width=True,
        column_config={
            "인원": st.column_config.Column("인원 (명)"),
            "구성비(판정 대상 기준)": st.column_config.Column(
                "판정 대상 중 비중",
                help="분모는 판정 대상이다. 성공 종료와 판정 보류는 분모 밖이라 "
                     "비중을 내지 않는다."),
        })
    st.caption(f"이탈률의 분모는 **판정 대상 {ctx['judged']:,}명**이다. "
               f"관측이 {config.JUDGE_MIN_DAYS}일에 못 미쳐 아직 판정하지 않은 "
               f"{ctx['pending']:,}명과, 최종 합격해서 활동을 멈춘 사람은 뺐다 — "
               f"합격한 사람을 이탈로 세면 안 된다.")

with st.expander("유지 단계 후보 — 순서는 코드가 아니라 내가 정했다"):
    st.dataframe(ctx["retention_candidates"], hide_index=True,
                 use_container_width=True,
                 column_config={"비율": st.column_config.ProgressColumn(
                     "비율", format="%.1f%%", min_value=0, max_value=100)})
    st.caption("후보를 먼저 늘어놓고 순서를 사람이 정한다. "
               "순서까지 코드가 정해주면 판단할 것이 없어진다.")

st.divider()

# ── 분해 ─────────────────────────────────────────────────────────────────
st.markdown("#### 분해")
# ★ 여기는 st.segmented_control 이 더 잘 어울린다. 그런데 못 쓴다.
#   Streamlit 1.45.1 의 AppTest 가 단일 선택 값을 리스트처럼 훑어서,
#   이 위젯이 화면에 있으면 두 번째 상호작용에서 검사가 통째로 죽는다
#   (ValueError: content: "공" is not in list — 첫 글자만 떼어 간다).
#   다중 선택 모드는 멀쩡하지만 축은 하나만 골라야 한다.
#   위젯을 얻고 검사를 잃는 거래는 하지 않는다 — 검사 못 하는 화면은
#   만든 것과 동작하는 것이 다른지 알 수 없다. 고쳐지면 그때 바꾼다.
axis = st.selectbox(
    "축", list(metrics.AXES),
    index=list(metrics.AXES).index(ctx["axis"]),
    help="축을 두세 개 시도해 보는 것이 정상이다. 한 번에 맞히는 것이 아니다.")
d = verdict.decomp_with_trust(ctx["tables"], axis) if axis != ctx["axis"] \
    else ctx["decomp"]
gap = metrics.biggest_gap(d)
_grain = "application" if metrics.AXES[axis][0] == "applications" else "person"
st.caption(f"보는 구간은 «{config.FUNNEL_STEPS[0]} → {config.FUNNEL_STEPS[1]}», "
           f"세는 단위는 {context.GRAIN_KO[_grain]}다. "
           f"기호 — {charts.verdict_legend()}")

st.altair_chart(charts.decomp_bar(d, axis), use_container_width=True)

if gap:
    st.markdown(
        f"전환율이 가장 높은 칸은 **{gap['높은 칸']}** 으로 {gap['높은 값']:.1%}, "
        f"가장 낮은 칸은 **{gap['낮은 칸']}** 으로 {gap['낮은 값']:.1%}다. "
        f"두 칸의 차이는 **{gap['격차'] * 100:.1f}%p**."
        + ("" if gap["격차"] >= 0.05 else
           "  \n차이가 5%p 하한 아래다. 이 축으로는 안 갈린다 — 그것도 결과다."))
if "기여도(%p)" in d.columns:
    st.caption("전환율이 낮다고 다 급한 것은 아니다. 그 칸이 전체의 3%뿐이면 "
               "고쳐도 전체는 거의 안 움직인다. 표의 «기여도 (%p)» 가 그 크기다 — "
               "그 칸을 전체 평균까지 끌어올렸을 때 전체 전환율이 몇 %p "
               "움직이는가를 나타낸다.")
    shown = d.drop(columns=["사유"]) if "사유" in d.columns else d
    # ★ 전환율·비중은 0~1 사이의 «비율»이다. 서식을 두 번 틀렸다.
    #   "%.1f%%" 로 찍으면 0.234 를 «0.2%» 로 쓴다 — 값이 100배 틀리게 보인다.
    #   그렇다고 percent 서식을 쓰면 «17.62%» 가 되어 바로 위 그림의 «17.6%» 와
    #   자릿수가 어긋난다. 같은 값이 두 자리로 보이면 읽는 사람이 둘을 다른
    #   값으로 읽는다. 그래서 표시용으로 100을 곱해 두고 자릿수를 직접 맞춘다.
    shown = shown.copy()
    for c in ("전환율", "비중"):
        if c in shown.columns:
            shown[c] = shown[c] * 100
    st.dataframe(
        shown, hide_index=True, use_container_width=True,
        column_config={
            "시작": st.column_config.NumberColumn("시작 (건)", format="localized"),
            "도달": st.column_config.NumberColumn("도달 (건)", format="localized"),
            "전환율": st.column_config.ProgressColumn(
                "전환율", format="%.1f%%", min_value=0,
                max_value=float(shown["전환율"].max() or 1)),
            "비중": st.column_config.NumberColumn(
                "전체에서 차지하는 비중", format="%.1f%%"),
            "기여도(%p)": st.column_config.NumberColumn(
                "기여도 (%p)", format="%.2f",
                help="이 칸이 전체 평균과 같아진다면 전체 전환율이 몇 %p "
                     "움직이는가. 음수면 그 칸이 지금 평균보다 낫다는 뜻이다."),
        })

with st.expander("축 후보 여섯 — 왜 이 축을 골랐는가"):
    st.dataframe(ctx["axis_candidates"], hide_index=True,
                 use_container_width=True)
    st.markdown(
        "물어본 것 셋 — 격차가 보이는가 · **손을 쓸 수 있는가** · "
        "각 칸에 최소 표본이 되는가. 두 번째가 핵심이다.\n\n"
        f"- **{config.DECOMP_AXIS}** ← 고름. 격차가 두 번째로 크지만 "
        "어떤 공고에 지원할지는 바꿀 수 있다\n"
        "- 학력 12.5%p — 격차는 가장 크나 우리가 바꿀 수 있는 값이 아니다. "
        "교안의 «날씨» 축이다\n"
        "- 산업 4.7% · 직무 3.2% · 과제 유무 2.0% · 고용 형태 1.1% — "
        "5%p 하한 아래. 이 축들로는 안 갈린다는 것을 확인한 것이고, 그것도 결과다")

st.divider()

# ── 코호트 · 우측 절단 ───────────────────────────────────────────────────
st.markdown("#### 시작 시점별 — 최근 구간은 성과가 아니라 시간의 문제일 수 있다")
st.altair_chart(charts.cohort_bar(ctx["cohort"], "서류통과율", "서류 통과율"),
                use_container_width=True)
hid = ctx["cohort"]["못 믿을 사유"].notna().sum()
st.caption(f"회색 칸 {hid}개는 아직 관측 기간이 {config.MIN_OBS_DAYS}일에 못 미쳐 "
           f"값을 그리지 않았다. 성적이 나쁜 것이 아니라 아직 결과가 안 난 것이다. "
           f"값을 믿을 수 있는 구간은 {config.PERIOD[0]} ~ {config.VALID_UNTIL}다.")

st.divider()

# ── 판정 카드 ────────────────────────────────────────────────────────────
st.markdown("#### 판정")
st.caption("이 비교는 인과를 주장할 수 없다. 무작위 배정이 없었으므로 "
           "다른 요인의 영향을 배제하지 못한다.")
dist = verdict.count_by_verdict(ctx["cards"])
st.write(" · ".join(f"{config.MARKS[verdict.VERDICTS[k]]} {k} {v}"
                    for k, v in dist.items()))
st.caption(f"비교 기준은 **{config.CARD_AXIS}**다. 주지표와 가드레일이 사람에 "
           f"붙는 값이라 지원자 1명 단위로 견준다 — 위의 분해(지원 1건 단위)와 "
           f"세는 단위가 다르다. 한쪽으로 맞추면 한쪽이 틀린다.")
for c in ctx["cards"]:
    _verdict_card(c)

st.divider()
_gate2(ctx)
