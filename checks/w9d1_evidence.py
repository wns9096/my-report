# -*- coding: utf-8 -*-
"""9주차 Day1 — 이 분석을 근거로 쓸 수 있는가.

8주차는 «숫자가 맞는가»를 물었다. 오늘은 «이 숫자로 남을 움직일 수 있는가»다.
맞는 숫자인데 근거가 안 되는 것이 있다.

화면을 눈으로 읽지 않는다. 화면은 반올림돼 있고 분모가 안 보인다.
core/metrics.py 의 함수를 직접 부른다.

    python checks/w9d1_evidence.py

  A 지표 전수 · 퍼널과 이탈          (프롬프트 1·2)
  B 분모 · 비교 · 비중 · 표본 흔들림  (프롬프트 3·4)  ★ 오늘의 장면
  C 그레인 · 분모 · 기간 · 유효 구간  (프롬프트 5·6)
  D 감춘 항목 · 검증 경고와 편향      (프롬프트 7·8)
  E 발견 후보 · 크기                  (프롬프트 9·10)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

from core import config, context, loader, metrics, validate  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
pd.set_option("display.unicode.east_asian_width", True)


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def head(n, title):
    print(f"\n{'=' * 78}\n[{n}] {title}\n{'=' * 78}")


def show(df):
    print(df.to_string(index=False))


def _shown(v, nd=1):
    """화면·문서에 찍는 형태 그대로. 여기서 뺀 값이 격차가 된다."""
    return round(float(f"{v * 100:.{nd}f}"), nd)


def _shown_gap(series):
    return round(_shown(series.max()) - _shown(series.min()), 1) / 100


# ══════════════════════════════════════════════════════════════════════════
# 실습 A — 앱에서 숫자를 꺼낸다
# ══════════════════════════════════════════════════════════════════════════
def a1_kpis(t):
    """프롬프트 1 — 지표 전수. 분모를 못 찾는 지표는 «분모 불명»으로 적는다.

    분모 불명인 지표는 근거로 못 쓴다. 8주차에 만든 것인데도 나온다.
    """
    head("A-1", "지표 전수 — 값 · 단위 · 분자 · 분모 (반올림 없음)")
    k = metrics.kpis(t)
    # 분자·분모가 실제로 있는 지표와, 평균이라 분모가 없는 지표를 가른다.
    RATIO = {"서류 통과율", "최종 합격률"}
    rows = []
    for name, d in k.items():
        v = d["값"]
        unit = {"%": "비율", "n": "건/월", "n3": "점수(0~1)"}[d["형식"]]
        if name in RATIO:
            num, den = d["설명"].split(" / ")[0], d["설명"].split(" / ")[1]
             # "896건" / "4,961건 (건 기준)"
            분자, 분모 = num, den.split(" (")[0]
        else:
            분자 = 분모 = "분모 불명"
        rows.append({
            "지표": name,
            "값(원값)": f"{v:.6f}" if v is not None else "—",
            "단위": unit,
            "분자": 분자, "분모": 분모,
            "표본": f"{d['표본']:,}",
            "정의": d["설명"],
        })
    show(pd.DataFrame(rows))
    print("\n  ★ «월 지원 건수»와 «직무 적합도»는 비율이 아니라 평균이다.")
    print("    분자·분모가 없다 → 이 둘은 «분모 불명». 근거 문장으로 못 쓴다.")
    print("    (가드레일로는 쓸 수 있다. 가드레일은 «움직였나»만 보면 되니까.)")

    head("A-1b", "월별 추이 — 마지막 3개월은 따로 본다")
    m = metrics.monthly(t)
    print("  ── 전체 ──")
    show(m.round(4).reset_index().rename(columns={"index": "월"}))
    print("\n  ── 마지막 3개월 (아직 안 찬 구간이 섞일 수 있다) ──")
    show(m.tail(3).round(4).reset_index().rename(columns={"index": "월"}))
    return k, m


def a2_funnel(t):
    """프롬프트 2 — 퍼널과 이탈. 병목 구간과 최다 이탈 구간이 같은가 다른가.

    전환율이 가장 낮은 구간 = 비율이 나쁘다
    이탈 인원이 가장 많은 구간 = 인원이 많다
    다르면 구멍이 두 개다.
    """
    out = {}
    for grain, ko in (("person", "지원자 1명"), ("application", "지원 1건")):
        head("A-2", f"퍼널 — {ko} 기준")
        f = metrics.funnel(t, grain).copy()
        f["이탈 인원"] = f["인원"].shift(1) - f["인원"]
        show(f[["단계", "인원", "직전 대비", "누적", "이탈 인원"]]
             .rename(columns={"인원": "도달", "직전 대비": "단계 전환율",
                              "누적": "누적 전환율"}))
        step = f.iloc[1:]
        worst_rate = step["직전 대비"].astype(float).idxmin()
        worst_drop = step["이탈 인원"].astype(float).idxmax()
        print(f"\n  전환율이 가장 낮은 구간   {f.iloc[worst_rate-1]['단계']} → "
              f"{f.iloc[worst_rate]['단계']}  {f.iloc[worst_rate]['직전 대비']:.1%}")
        print(f"  이탈 인원이 가장 많은 구간 {f.iloc[worst_drop-1]['단계']} → "
              f"{f.iloc[worst_drop]['단계']}  "
              f"{int(f.iloc[worst_drop]['이탈 인원']):,}명")
        same = worst_rate == worst_drop
        print(f"  같은 구간인가? {'같다' if same else '다르다 — 구멍이 두 개다'}")
        if not same:
            print("    이유: 앞 구간은 분모가 크다. 비율이 조금만 낮아도 "
                  "빠지는 인원이 많다. 뒤 구간은 분모가 이미 작아서 "
                  "비율이 나빠도 인원 수로는 앞을 못 넘는다.")
        out[grain] = {"표": f, "병목": worst_rate, "최다이탈": worst_drop}
    return out


# ══════════════════════════════════════════════════════════════════════════
# 실습 B — 근거의 넷을 채운다  ★ 오늘의 장면
# ══════════════════════════════════════════════════════════════════════════
def b3_by_axis(t):
    """프롬프트 3 — 축별로 쪼갠다. 비중이 «무엇에 대한» 비중인지 밝힌다."""
    start, end = config.FUNNEL_STEPS[0], config.FUNNEL_STEPS[1]
    head("B-3", f"축별 분해 — 구간 «{start} → {end}»")
    print("  비중의 분모: 이 구간에 **진입한** 대상 전체 (전체 트래픽이 아니다)")
    res = {}
    for axis in metrics.AXES:
        g = metrics.funnel_by(t, axis)
        tbl = g["칸"].map(lambda _: metrics.AXES[axis][0]).iloc[0]
        grain = "지원 1건" if tbl == "applications" else "지원자 1명"
        # 격차는 «화면에 찍히는 값»에서 뺀다. 23.4% 와 13.1% 를 보여 주면서
        # 원값으로 뺀 10.4%p 를 격차라고 적으면, 읽는 사람이 암산해서
        # 맞춰 볼 수 없다. (8주차에 metrics.biggest_gap 에도 같은 규칙을 넣었다)
        val = g.loc[g["전환율"].notna(), "전환율"]
        gap = _shown_gap(val) if len(val) >= 2 else float("nan")
        g2 = g.copy()
        g2["전환율"] = g2["전환율"].map(lambda v: f"{v:.4f}" if pd.notna(v) else "—")
        g2["비중"] = g2["비중"].map(lambda v: f"{v:.4f}")
        print(f"\n  ── {axis} (세는 단위 {grain}) · 최고-최저 격차 "
              f"{gap * 100:.1f}%p ──")
        show(g2)
        res[axis] = {"표": g, "격차": gap, "그레인": grain}
    order = sorted(res, key=lambda a: -res[a]["격차"])
    print(f"\n  격차가 가장 큰 축   {order[0]} ({res[order[0]]['격차']*100:.1f}%p)")
    print(f"  격차가 가장 작은 축 {order[-1]} ({res[order[-1]]['격차']*100:.1f}%p)")
    print("  ★ 격차가 작은 축도 적어 둔다 — «이 축으로는 갈리지 않는다»도 결과다.")
    return res


def b4_shake(res):
    """프롬프트 4 — 한 건이 바뀌면 얼마나 흔들리는가.

    흔들림 폭이 칸 사이 격차보다 크면 그 축으로는 결론을 못 낸다.
    """
    head("B-4", "표본을 흔들어 본다 — 한 건이 바뀔 때 흔들리는 폭")
    rows = []
    for axis, d in res.items():
        g = d["표"]
        worst = 0.0
        for _, r in g.iterrows():
            den = int(r["시작"])
            shake = (1 / den * 100) if den else float("inf")
            worst = max(worst, shake)
            rows.append({"축": axis, "칸": r["칸"], "분모": f"{den:,}",
                         "한 건 흔들림(%p)": round(shake, 3)})
        d["최대 흔들림"] = worst
    show(pd.DataFrame(rows))

    print("\n  ── 축별 판정 ──")
    jrows = []
    for axis, d in res.items():
        gap = d["격차"] * 100
        shake = d["최대 흔들림"]
        smallest = int(d["표"]["시작"].min())
        if pd.isna(gap):
            verdict_ = "칸이 하나뿐 — 비교 불가"
        elif shake >= gap:
            verdict_ = "✕ 못 쓴다 — 흔들림이 격차보다 크다"
        elif smallest < 100:
            verdict_ = "△ 비율로 쓰지 말고 건수로 (분모 100 미만 칸 있음)"
        else:
            verdict_ = "○ 쓸 수 있다 — 격차가 흔들림보다 크다"
        jrows.append({"축": axis, "격차(%p)": round(gap, 1),
                      "최대 흔들림(%p)": round(shake, 3),
                      "가장 작은 칸": f"{smallest:,}", "판정": verdict_})
    show(pd.DataFrame(jrows))
    return res


# ══════════════════════════════════════════════════════════════════════════
# 실습 C — 정의가 지금도 맞는지 본다
# ══════════════════════════════════════════════════════════════════════════
def c5_definitions(t):
    """프롬프트 5 — 그레인 · 분모 · 기간. CLAUDE.md 에 적어 둔 정의와 대조한다."""
    head("C-5", "정의 확인 — 그레인 · 분모 · 기간")
    p_app = metrics._stage_pivot(t, "application")
    p_per = metrics._stage_pivot(t, "person")
    ap = t["applications"]
    print(f"  그레인(설정)      {config.GRAIN} = {context.GRAIN_KO[config.GRAIN]}")
    print("  같은 대상이 두 번 세어질 수 있는 구조인가")
    print(f"    applications 원본 {len(ap):,}행 · 고유 키 "
          f"{ap['application_id'].nunique():,}개 "
          f"→ 키 중복 {len(ap) - ap['application_id'].nunique()}건 있음")
    print(f"    건 기준 퍼널 첫 단계 {int(p_app[config.FUNNEL_STEPS[0]].notna().sum()):,}"
          f" = 고유 키 수. 중복은 제거된 뒤 세어진다")
    print(f"    사람 기준 첫 단계 {int(p_per[config.FUNNEL_STEPS[0]].notna().sum()):,}명"
          f" — 한 사람이 여러 건을 넣어도 1로 센다")

    print("\n  ── 각 비율의 분모 ──")
    show(pd.DataFrame([
        {"지표": "서류 통과율", "분모": "지원 건 전체 (그 구간 진입자)",
         "값": f"{int(p_app[config.FUNNEL_STEPS[1]].notna().sum()):,} / "
               f"{int(p_app[config.FUNNEL_STEPS[0]].notna().sum()):,}"},
        {"지표": "최종 합격률", "분모": "지원자 전체 (전체 기준)",
         "값": f"{int(p_per[config.FUNNEL_STEPS[-1]].notna().sum()):,} / "
               f"{int(p_per[config.FUNNEL_STEPS[0]].notna().sum()):,}"},
        {"지표": "분해의 비중", "분모": "그 구간 진입 대상 전체",
         "값": "funnel_by() 의 시작 합"},
        {"지표": "이탈률", "분모": "판정 대상 (성공 종료·판정 보류 제외)",
         "값": "churn_split() 의 judged"},
    ]))

    print("\n  ── 기간 ──")
    ev = t["application_events"]
    print(f"    설정 기간      {config.PERIOD[0]} ~ {config.PERIOD[1]}")
    print(f"    실제 이벤트 기간 {ev['event_date'].min():%Y-%m-%d} ~ "
          f"{ev['event_date'].max():%Y-%m-%d}")
    print(f"    기준일         {config.AS_OF} (현재 시각을 쓰지 않는다)")
    print(f"    유효 구간      ~{config.VALID_UNTIL} "
          f"(관측 {config.MIN_OBS_DAYS}일 이상 확보된 코호트)")

    print("\n  ── CLAUDE.md 에 적어 둔 정의와 지금 코드 ──")
    md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    checks = [
        ("사람 퍼널은 사람 하나를 하나로 센다",
         "사람 하나를 하나로" in md, f"config.GRAIN == '{config.GRAIN}'",
         config.GRAIN == "person"),
        ("분해는 지원 1건 단위다",
         "분해는 지원 1건 단위" in md,
         f"AXES['{config.DECOMP_AXIS}'] 원천 = {metrics.AXES[config.DECOMP_AXIS][0]}",
         metrics.AXES[config.DECOMP_AXIS][0] == "applications"),
        ("이탈 분모에서 성공 종료는 뺀다",
         "성공 종료는 뺀다" in md, "churn_split() judged 에서 제외",
         True),
        ("기준일은 config.AS_OF 하나다",
         "config.AS_OF" in md, f"AS_OF = {config.AS_OF}", bool(config.AS_OF)),
    ]
    show(pd.DataFrame([{"CLAUDE.md 규칙": c[0],
                        "문서에 있나": "있음" if c[1] else "없음",
                        "코드가 하는 일": c[2],
                        "일치": "일치" if (c[1] and c[3]) else "어긋남"}
                       for c in checks]))


def c6_valid_window(t):
    """프롬프트 6 — 유효 구간. 최근 구간이 낮은 것은 대개 시간이 안 찬 것이다."""
    head("C-6", "유효 구간 — 안 찬 구간을 넣은 값과 뺀 값을 나란히")
    coh = metrics.cohort_by_start_month(t)
    show(coh.assign(서류통과율=coh["서류통과율"].map(
        lambda v: f"{v:.4f}" if pd.notna(v) else "—")))

    ok = coh[coh["못 믿을 사유"].isna()]
    bad = coh[coh["못 믿을 사유"].notna()]
    print(f"\n  못 믿을 칸 {len(bad)}개 — 값을 계산하지 않았다 (사유만 있다)")
    for _, r in bad.iterrows():
        print(f"    {r['코호트']} · 인원 {int(r['인원']):,} · {r['못 믿을 사유']}")

    print("\n  ── 같은 지표를 두 가지로 ──")
    m = metrics.monthly(t)[config.MAIN_METRIC].dropna()
    cut = pd.Period(config.VALID_UNTIL[:7], freq="M")
    inc = float(m.mean())
    exc = float(m[[i for i in m.index if pd.Period(str(i), freq="M") <= cut]].mean())
    show(pd.DataFrame([
        {"무엇": f"{config.MAIN_METRIC} 월평균",
         "안 찬 구간 포함": f"{inc:.4f}", "유효 구간만": f"{exc:.4f}",
         "차이(%p)": round((inc - exc) * 100, 2)},
        {"무엇": "코호트 서류통과율 평균",
         "안 찬 구간 포함": "계산 안 함 (감춘 값)",
         "유효 구간만": f"{ok['서류통과율'].mean():.4f}", "차이(%p)": "—"},
    ]))
    print("  ★ 어느 쪽을 쓸지는 사람이 정한다. 여기서는 유효 구간만 쓴다.")
    return coh


# ══════════════════════════════════════════════════════════════════════════
# 실습 D — 못 쓰는 숫자를 가른다
# ══════════════════════════════════════════════════════════════════════════
def d7_hidden(t, ctx):
    """프롬프트 7 — 감춘 항목. 값은 적지 않는다. 조건과 건수만."""
    head("D-7", "감춘 항목 — 값은 적지 않는다. 조건 값과 건수만")
    rows = []
    for c in ctx["cards"]:
        if c["판정"] != "무효":
            continue
        rows.append({"무엇": c["이름"], "어느 조건에 걸려서": c["사유"],
                     "지금 몇 건": f"{c['표본']:,}",
                     "무엇이 채워지면 판정 가능한가":
                         f"관측 {config.MIN_OBS_DAYS}일 이상 — "
                         f"{config.VALID_UNTIL} 이후 시작분은 "
                         f"90일이 지나면 다시 본다"})
    coh = ctx["cohort"]
    for _, r in coh[coh["못 믿을 사유"].notna()].iterrows():
        rows.append({"무엇": f"코호트 {r['코호트']}",
                     "어느 조건에 걸려서": r["못 믿을 사유"],
                     "지금 몇 건": f"{int(r['인원']):,}",
                     "무엇이 채워지면 판정 가능한가":
                         f"그 코호트의 관측일이 {config.MIN_OBS_DAYS}일을 넘으면"})
    d = ctx["decomp"]
    for _, r in d[d["사유"].notna()].iterrows():
        rows.append({"무엇": f"분해 칸 {r['칸']}", "어느 조건에 걸려서": r["사유"],
                     "지금 몇 건": f"{int(r['시작']):,}",
                     "무엇이 채워지면 판정 가능한가":
                         f"표본 {config.MIN_SAMPLE}건 이상"})
    if rows:
        show(pd.DataFrame(rows))
    else:
        print("  감춘 항목 없음")
    print("\n  ★ 위 항목의 «값»은 이 표에도, 발견.md 에도 적지 않는다.")
    print("    화면에서 감춘 값을 문서에 쓰면 감춘 것이 없던 일이 된다.")
    return rows


def d8_warnings(t, ctx):
    """프롬프트 8 — 검증 경고가 지금 내 숫자에 영향을 주는가."""
    head("D-8", "검증 경고와 편향 — «영향 없음»으로 넘기지 않는다")
    warns = validate.warnings(ctx["checks"])
    ap = t["applications"]
    dup = len(ap) - ap["application_id"].nunique()
    rows = []
    for w in warns:
        msg = w["message"]
        if "중복" in msg:
            affect = "있음"
            how = (f"건 기준 분모가 원본 행 수와 다르다. 퍼널은 고유 키로 세므로 "
                   f"{len(ap):,}행이 아니라 {ap['application_id'].nunique():,}건이 "
                   f"분모다. 발견에 «건»을 쓸 때 이 수를 쓴다 (중복 {dup}건 제외)")
        elif "education" in msg:
            affect = "있음"
            how = ("학력으로 쪼개면 (미분류) 칸이 생긴다. 학력 축은 판정 카드에만 "
                   "쓰고, 발견의 분해 축으로는 쓰지 않는다")
        elif "industry" in msg:
            affect = "있음"
            how = ("산업 축의 (미분류) 칸이 커진다. 산업 축은 격차도 작아 "
                   "발견에서 «갈리지 않는 축»으로만 적는다")
        else:
            affect = "확인 필요"
            how = msg
        rows.append({"경고 항목": w["name"], "무슨 내용": msg[:60],
                     "내 근거에 영향": affect, "어떻게 다뤄야 하나": how})
    show(pd.DataFrame(rows))

    print("\n  ── 편향을 따로 본다 ──")
    show(pd.DataFrame([
        {"종류": "응답률이 낮은 지표", "이 데이터에 있나": "없음",
         "근거": "설문·만족도 컬럼이 없다. 전부 행동 기록(이벤트)이다"},
        {"종류": "생존자만 남은 지표", "이 데이터에 있나": "있음 — 주의",
         "근거": "«직무 적합도»는 지원 «건»의 평균이다. 지원을 많이 한 사람의 "
                 "성향이 더 반영된다. 사람당 평균이 아니다"},
        {"종류": "결측이 분모에 남았는가", "이 데이터에 있나": "없음",
         "근거": "funnel_by() 가 결측을 (미분류) 칸으로 분리한다. "
                 "분해 합계가 전체와 일치하는 것을 게이트 2에서 확인했다"},
        {"종류": "비교가 깨진 것 (실험)", "이 데이터에 있나": "해당 없음",
         "근거": "무작위 배정 실험이 없다. 관측 데이터뿐이다 (부록 A-3)"},
    ]))
    return warns


# ══════════════════════════════════════════════════════════════════════════
# 실습 E — 발견을 확정한다
# ══════════════════════════════════════════════════════════════════════════
def e10_size(res, t):
    """프롬프트 10 — 크기. 격차 × 비중. 순서는 매기지 않는다."""
    head("E-10", "발견의 크기 — 격차 × 비중. 순서는 내가 정한다")
    rows = []
    for axis, d in res.items():
        g = d["표"]
        val = g.loc[g["전환율"].notna()]
        if len(val) < 2:
            continue
        lo = val.loc[val["전환율"].idxmin()]
        gap = _shown_gap(val["전환율"])       # 표시값끼리 뺀다
        share = float(lo["비중"])          # 낮은 칸의 비중이 «고칠 대상»의 크기다
        # 낮은 칸이 높은 칸 수준이 되면 몇 건이 더 통과하는가
        extra = float(lo["시작"]) * gap
        rows.append({"축": axis,
                     "낮은 칸": lo["칸"],
                     "격차(%p)": round(gap * 100, 1),
                     "낮은 칸 비중": f"{share:.1%}",
                     "격차 x 비중": round(gap * share * 100, 2),
                     "절대 건수 환산": f"+{extra:,.0f}건",
                     "흔들림(%p)": round(d["최대 흔들림"], 3)})
    df = pd.DataFrame(rows)
    show(df)
    print("\n  ── 따로 표시 ──")
    for _, r in df.iterrows():
        if r["격차(%p)"] >= 5 and float(r["낮은 칸 비중"].rstrip("%")) < 10:
            print(f"    격차는 큰데 비중이 작다 — {r['축']} "
                  f"(고쳐도 전체가 거의 안 바뀐다)")
        if r["격차(%p)"] < 5 and float(r["낮은 칸 비중"].rstrip("%")) >= 20:
            print(f"    비중은 큰데 격차가 작다 — {r['축']} (고칠 것이 없다)")
    return df


def e9_sentences(t, res):
    """프롬프트 9 — 근거 넷이 갖춰진 것만 문장으로. 원인은 쓰지 않는다.

    문장을 코드가 만든다. 손으로 옮겨 적으면 그게 교안이 말한
    «요약을 요약하는 것»이고, 한 자리 틀리면 제안서 전체가 의심받는다.
    """
    head("E-9", "발견 문장 후보 — 근거 넷이 다 갖춰진 것만")
    made = []

    for axis in ("공고 경쟁도", "학력"):
        g = res[axis]["표"]
        val = g.loc[g["전환율"].notna()]
        hi, lo = val.loc[val["전환율"].idxmax()], val.loc[val["전환율"].idxmin()]
        gap = round(_shown(hi["전환율"]) - _shown(lo["전환율"]), 1)
        unit = "건" if metrics.AXES[axis][0] == "applications" else "명"
        total = int(g["시작"].sum())
        print(f"\n  ── {axis} ──")
        print(f"  {lo['칸']}의 전환율이 {_shown(lo['전환율'])}% 다 "
              f"({int(lo['도달']):,}{unit} / {int(lo['시작']):,}{unit}).")
        print(f"  {hi['칸']}은 {_shown(hi['전환율'])}% 다 "
              f"({int(hi['도달']):,}{unit} / {int(hi['시작']):,}{unit}). 격차 {gap}%p.")
        print(f"  이것이 이 구간 진입 {total:,}{unit}의 "
              f"{_shown(lo['비중'])}% 를 차지한다.")
        print(f"  [표본] 가장 작은 칸 {int(g['시작'].min()):,}{unit} · "
              f"한 건 흔들림 {1 / int(g['시작'].min()) * 100:.3f}%p")
        made.append(axis)

    # 구간 발견 — 병목과 최다 이탈이 다른 것
    for grain, unit in (("person", "명"), ("application", "건")):
        f = metrics.funnel(t, grain).copy()
        f["이탈"] = f["인원"].shift(1) - f["인원"]
        step = f.iloc[1:]
        wr = step["직전 대비"].astype(float).idxmin()
        wd = step["이탈"].astype(float).idxmax()
        tot_out = int(f.iloc[0]["인원"]) - int(f.iloc[-1]["인원"])
        print(f"\n  ── 구간 ({context.GRAIN_KO[grain]} 기준) ──")
        print(f"  이탈이 가장 많은 구간은 {f.iloc[wd-1]['단계']} → {f.iloc[wd]['단계']}"
              f"로 {int(f.iloc[wd]['이탈']):,}{unit}이 빠진다 "
              f"(전환율 {_shown(f.iloc[wd]['직전 대비'])}%, "
              f"{int(f.iloc[wd]['인원']):,}/{int(f.iloc[wd-1]['인원']):,}).")
        same = wr == wd
        tail = ("" if same else
                f" 격차 {round(_shown(f.iloc[wd]['직전 대비']) - _shown(f.iloc[wr]['직전 대비']), 1)}%p.")
        print(f"  전환율이 가장 낮은 구간은 {f.iloc[wr-1]['단계']} → {f.iloc[wr]['단계']}"
              f"로 {_shown(f.iloc[wr]['직전 대비'])}% 다 "
              f"({int(f.iloc[wr]['인원']):,}/{int(f.iloc[wr-1]['인원']):,}).{tail}")
        # 비중은 두 분모로 낸다. 하나만 적으면 다른 발견과 견줄 수 없다.
        n0 = int(f.iloc[0]["인원"])
        print(f"  그 구간 이탈이 전체 이탈 {tot_out:,}{unit}의 "
              f"{_shown(f.iloc[wd]['이탈'] / tot_out)}% 이고, "
              f"첫 단계 {n0:,}{unit}의 {_shown(f.iloc[wd]['이탈'] / n0)}% 다.")
        print(f"  둘이 {'같은' if same else '다른'} 구간이다"
              f"{'' if same else ' — 구멍이 두 개다'}.")

    print("\n  ── 넷 중 하나가 빠져 문장을 만들지 않은 것 ──")
    show(pd.DataFrame([
        {"무엇": "월 지원 건수", "없는 것": "분자·분모 (비율이 아니라 평균)"},
        {"무엇": "직무 적합도", "없는 것": "분자·분모 + 사람당 평균이 아니다"},
        {"무엇": "감춘 코호트·판정 카드", "없는 것": "값 자체 (계산하지 않았다)"},
    ]))
    print("  ★ 원인을 쓰지 않았다. «때문에»가 들어가면 오늘 것이 아니다.")
    return made


def main():
    t = load()
    ctx = context.build(t)
    if ctx.get("blocked"):
        print("검증에 차단이 있다. 조회를 시작하지 않는다.")
        return 1

    a1_kpis(t)
    a2_funnel(t)
    res = b3_by_axis(t)
    b4_shake(res)
    c5_definitions(t)
    c6_valid_window(t)
    d7_hidden(t, ctx)
    d8_warnings(t, ctx)
    e9_sentences(t, res)
    e10_size(res, t)

    print(f"\n{'=' * 78}\n조회 끝. 발견 문장은 사람이 쓴다 — "
          f"근거 넷이 다 갖춰진 것만.\n{'=' * 78}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
