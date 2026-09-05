# -*- coding: utf-8 -*-
"""계산층 — Day2(세는 코드) · Day3(안 보여주는 코드).

세는 단위(그레인)를 무엇으로 잡느냐에 따라 다른 숫자가 나온다.
둘 다 맞는 숫자다. 다른 질문에 답할 뿐이다.
"""
import pandas as pd

from core import config

# ══════════════════════════════════════════════════════════════════════════
# Day2 실습 A — 획득 퍼널
# ══════════════════════════════════════════════════════════════════════════
_KEY = {"person": "applicant_id", "application": "application_id"}


def _stage_pivot(tables, grain):
    """대상별 · 단계별 최초 도달일. 고유값으로 센다."""
    ev = tables["application_events"]
    key = _KEY[grain]
    return ev.pivot_table(index=key, columns="stage",
                          values="event_date", aggfunc="min")


def funnel(tables, grain=None):
    """단계별 인원과 전환율.

    반환: DataFrame[단계, 인원, 직전 대비, 누적]
      · 인원      — 해당 단계에 도달한 고유 대상 수
      · 직전 대비 — 인원 / 직전 단계 인원
      · 누적      — 인원 / 첫 단계 인원
    """
    grain = grain or config.GRAIN
    p = _stage_pivot(tables, grain)
    rows, first, prev = [], None, None
    for step, label in zip(config.FUNNEL_STEPS, config.FUNNEL_LABELS):
        n = int(p[step].notna().sum()) if step in p.columns else 0
        first = n if first is None else first
        rows.append({
            "단계": label,
            "인원": n,
            "직전 대비": None if prev is None else (n / prev if prev else None),
            "누적": (n / first) if first else None,
        })
        prev = n
    return pd.DataFrame(rows)


def funnel_gap(tables):
    """같은 퍼널을 두 그레인으로 세어 나란히 놓는다 (대조용)."""
    a = funnel(tables, "person").rename(columns={"인원": "사람"})[["단계", "사람"]]
    b = funnel(tables, "application").rename(columns={"인원": "건"})[["단계", "건"]]
    m = a.merge(b, on="단계")
    m["건/사람"] = (m["건"] / m["사람"]).round(2)
    return m


def order_violation(tables, steps, grain=None):
    """앞 단계를 거치지 않고 다음 단계에 나타난 대상 수. 퍼널인지 분류인지 판정."""
    grain = grain or config.GRAIN
    p = _stage_pivot(tables, grain)
    rows = []
    for a, b in zip(steps, steps[1:]):
        if a not in p.columns or b not in p.columns:
            continue
        rows.append({
            "구간": f"{a} → {b}",
            "앞 단계 미경유": int((p[b].notna() & p[a].isna()).sum()),
            "역행(뒤가 먼저)": int((p[b] < p[a]).sum()),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════
# Day2 실습 C — 유지 퍼널
# ══════════════════════════════════════════════════════════════════════════
def _person_span(tables):
    """지원자별 첫/마지막 지원 이벤트, 지원 건수, 지속 일수."""
    ev = tables["application_events"]
    ap = ev[ev["stage"] == config.FUNNEL_STEPS[0]]
    g = ap.groupby("applicant_id")["event_date"]
    out = pd.DataFrame({"첫 지원일": g.min(), "마지막 지원일": g.max(),
                        "지원 건수": g.count()})
    out["지속 일수"] = (out["마지막 지원일"] - out["첫 지원일"]).dt.days
    return out


def retention_candidates(tables):
    """Day2 프롬프트 4 — 유지 단계 후보를 나열한다. 순서는 정하지 않는다.

    후보마다 (어떤 컬럼으로 정의되는가 · 몇 명이 해당되는가 · 무엇을 볼 수 있는가).
    순서를 코드가 정해주면 판단할 것이 없어진다. 채택/제외는 사람이 적는다.
    """
    s = _person_span(tables)
    ev = tables["application_events"]
    as_of = pd.Timestamp(config.AS_OF)
    months = ((as_of - s["첫 지원일"]).dt.days / 30.44).clip(lower=1.0)
    doc = set(ev.loc[ev["stage"] == config.FUNNEL_STEPS[1], "applicant_id"])
    win = set(ev.loc[ev["stage"] == config.FUNNEL_STEPS[-1], "applicant_id"])

    rows = [
        ("재지원 (2건 이상)", "application_events.stage=지원 을 사람별로 센다",
         int((s["지원 건수"] >= 2).sum()),
         "한 번 오고 마는지, 다시 오는지",
         "제외 — 520명 전원이 해당해 단계가 갈리지 않는다"),
        ("4주 이상 지속", "첫 지원일 ~ 마지막 지원일 >= 28일",
         int((s["지속 일수"] >= 28).sum()),
         "한 달을 넘기는가",
         "채택 — 2단계"),
        ("8주 이상 지속", "같은 간격 >= 56일",
         int((s["지속 일수"] >= 56).sum()),
         "두 달을 넘기는가",
         "채택 — 3단계"),
        ("16주 이상 지속", "같은 간격 >= 112일",
         int((s["지속 일수"] >= 112).sum()),
         "네 달을 넘기는가",
         "채택 — 4단계"),
        ("꾸준함 (월 2건 이상)", "지원 건수 ÷ 관측 개월 >= 2",
         int(((s["지원 건수"] / months) >= 2).sum()),
         "얼마나 자주 오는가",
         "제외 — 지속 일수와 겹친다. 굵게 묶는 편이 낫다"),
        ("서류 통과 경험", "application_events.stage=서류 통과",
         len(doc),
         "남아 있는 것이 성과로 이어지는가",
         "제외 — 오래 지속하지 않고도 통과한다. 앞 단계를 안 거치므로 분류다"),
        ("성공 종료 (최종 합격)", "application_events.stage=최종 합격",
         len(win),
         "유지의 끝이 무엇인가",
         "제외 — 유지가 아니라 종료다. 이탈 분류에서 따로 센다"),
    ]
    df = pd.DataFrame(rows, columns=["후보", "어떤 컬럼으로", "해당 인원",
                                     "무엇을 볼 수 있는가", "판단"])
    df["비율"] = df["해당 인원"] / len(s)
    return df


def retention_funnel(tables):
    """유지 퍼널 — 그레인은 지원자. 관측 전체 기간 기준.

    획득 퍼널과 달리 단계가 주어지지 않았다. 아래 정의는 내가 정한 것이다.
      1 첫 지원        지원 이벤트가 1건 이상
      2 4주 이상 지속  첫 지원 ~ 마지막 지원 간격 >= 28일
      3 8주 이상 지속  같은 간격 >= 56일
      4 16주 이상 지속 같은 간격 >= 112일
    뒤 단계는 앞 단계를 반드시 거친다 — 지속 일수가 단조라서 구조적으로 보장된다.
    """
    s = _person_span(tables)
    masks = [s["지원 건수"] >= 1]
    masks += [s["지속 일수"] >= w * 7 for w in config.RETENTION_WEEKS]
    rows, first, prev = [], None, None
    for label, m in zip(config.RETENTION_STEPS, masks):
        n = int(m.sum())
        first = n if first is None else first
        rows.append({"단계": label, "인원": n,
                     "직전 대비": None if prev is None else (n / prev if prev else None),
                     "누적": n / first if first else None})
        prev = n
    df = pd.DataFrame(rows)
    # 앞 단계를 거치지 않고 나타난 대상 — 0이 아니면 퍼널이 아니다
    skips = []
    for i in range(1, len(masks)):
        skips.append({
            "구간": f"{config.RETENTION_STEPS[i-1]} → {config.RETENTION_STEPS[i]}",
            "앞 단계 미경유": int((masks[i] & ~masks[i - 1]).sum()),
        })
    return df, pd.DataFrame(skips)


def churn_split(tables):
    """이탈 / 유지 / 성공 종료 / 판정 보류 — 순서가 없으므로 퍼널이 아니라 분류다.

    전환율을 내지 않는다. 구성비만 낸다 (Day2 부록 B).

    ★ Day2 실습 B 에서 여기가 틀렸다.
      처음에는 이탈률의 분모를 "관측 60일이 지난 사람 전원(471명)"으로 잡았다.
      최종 합격자는 지원을 멈추므로 무활동 일수가 길다 — 성공한 사람이
      이탈로 세어진다. 성공 종료는 이탈이 아니므로 분모에서 뺀다.
      471 − 106 = 365 가 판정 대상이다. 이탈률 51.2% → 65.8%.
    """
    s = _person_span(tables)
    ev = tables["application_events"]
    win = set(ev.loc[ev["stage"] == config.FUNNEL_STEPS[-1], "applicant_id"])
    as_of = pd.Timestamp(config.AS_OF)
    s["무활동 일수"] = (as_of - s["마지막 지원일"]).dt.days
    s["관측 일수"] = (as_of - s["첫 지원일"]).dt.days

    def label(idx, row):
        if idx in win:
            return "성공 종료"
        if row["관측 일수"] < config.JUDGE_MIN_DAYS:
            return "판정 보류"
        return "이탈" if row["무활동 일수"] > config.CHURN_GAP_DAYS else "유지"

    s["구분"] = [label(i, r) for i, r in s.iterrows()]
    # 판정 대상 = 유지 + 이탈. 성공 종료와 판정 보류는 분모에서 뺀다.
    judged = int(s["구분"].isin(["유지", "이탈"]).sum())
    vc = s["구분"].value_counts()
    out = pd.DataFrame({"구분": vc.index, "인원": vc.values})
    out["구성비(판정 대상 기준)"] = [
        (n / judged if g in ("유지", "이탈") else None)
        for g, n in zip(out["구분"], out["인원"])
    ]
    return out, judged, int((s["구분"] == "판정 보류").sum())


# ══════════════════════════════════════════════════════════════════════════
# Day2 실습 D — 지표 카드 · 월별
# ══════════════════════════════════════════════════════════════════════════
def kpis(tables):
    """지표 넷. 값과 함께 표본 수를 같이 돌려준다 — 표본 없이는 판정할 수 없다."""
    ap = tables["applications"]
    p = _stage_pivot(tables, "application")
    n_apply = int(p[config.FUNNEL_STEPS[0]].notna().sum())
    n_doc = int(p[config.FUNNEL_STEPS[1]].notna().sum())
    pp = _stage_pivot(tables, "person")
    n_person = int(pp[config.FUNNEL_STEPS[0]].notna().sum())
    n_final = int(pp[config.FUNNEL_STEPS[-1]].notna().sum())

    s = _person_span(tables)
    as_of = pd.Timestamp(config.AS_OF)
    months = ((as_of - s["첫 지원일"]).dt.days / 30.44).clip(lower=1.0)
    per_month = (s["지원 건수"] / months).mean()

    fit = ap.drop_duplicates("application_id")["fit_score"]
    return {
        "서류 통과율": {"값": n_doc / n_apply if n_apply else None, "표본": n_apply,
                        "형식": "%", "설명": f"{n_doc:,}건 / {n_apply:,}건 (건 기준)"},
        "최종 합격률": {"값": n_final / n_person if n_person else None, "표본": n_person,
                        "형식": "%", "설명": f"{n_final:,}명 / {n_person:,}명 (사람 기준)"},
        "월 지원 건수": {"값": float(per_month), "표본": int(len(s)),
                         "형식": "n", "설명": "지원자별 (지원 건수 ÷ 관측 개월)의 평균"},
        "직무 적합도": {"값": float(fit.mean()), "표본": int(fit.notna().sum()),
                        "형식": "n3", "설명": "지원 건별 fit_score 평균 (중복 제거 후)"},
    }


def monthly(tables):
    """월별 추이 — 열 이름은 kpis() 의 지표 이름과 같게 한다 (스파크라인용)."""
    ev, ap = tables["application_events"], tables["applications"]
    ev = ev.copy()
    ev["월"] = ev["event_date"].dt.to_period("M").astype(str)
    apply_m = (ev[ev["stage"] == config.FUNNEL_STEPS[0]]
               .groupby("월")["application_id"].nunique())
    doc_m = (ev[ev["stage"] == config.FUNNEL_STEPS[1]]
             .groupby("월")["application_id"].nunique())
    person_m = (ev[ev["stage"] == config.FUNNEL_STEPS[0]]
                .groupby("월")["applicant_id"].nunique())
    final_m = (ev[ev["stage"] == config.FUNNEL_STEPS[-1]]
               .groupby("월")["applicant_id"].nunique())
    a = ap.drop_duplicates("application_id").copy()
    a["월"] = a["applied_date"].dt.to_period("M").astype(str)
    fit_m = a.groupby("월")["fit_score"].mean()

    return pd.DataFrame({
        "서류 통과율": (doc_m / apply_m),
        "최종 합격률": (final_m / person_m),
        "월 지원 건수": (apply_m / person_m),
        "직무 적합도": fit_m,
        "표본": apply_m,
    }).sort_index()


# ══════════════════════════════════════════════════════════════════════════
# Day3 실습 A — 분해
# ══════════════════════════════════════════════════════════════════════════
AXES = {
    "학력":        ("applicants", "education"),
    "산업":        ("applications", "industry"),
    "직무":        ("applications", "role"),
    "고용 형태":    ("applications", "employment_type"),
    "공고 경쟁도":  ("applications", "공고 경쟁도"),
    "과제 유무":    ("applications", "과제 유무"),
}

# 공고 경쟁도를 세 칸으로 묶는 경계.
# 근거: 분포의 사분위(0.34 / 0.51 / 0.66)에 맞춰 아래·가운데·위로 나눴다.
#       열 칸으로 잘게 쪼개면 칸마다 최소 표본 30을 못 넘는다.
COMPETITION_BINS = [-0.01, 0.35, 0.65, 1.01]
COMPETITION_LABELS = ["경쟁 낮음 (~.35)", "경쟁 보통 (.35~.65)", "경쟁 높음 (.65~)"]


def merge_1to1(left, right, on):
    """붙이면서 행이 늘어나면 멈춘다.

    한 대상에 행이 여럿인 표를 그냥 붙이면 대상이 복제된다(팬아웃).
    평균이 조용히 왜곡되는데 숫자는 멀쩡하게 나오므로 눈에 안 띈다.
    그래서 조용히 넘어가지 않고 여기서 걸리게 둔다.

    오른쪽 표를 미리 키 단위로 줄여 놓았더라도 이 확인은 남긴다 —
    나중에 누가 그 줄을 지웠을 때 값이 조용히 틀리는 대신 여기서 멈춘다.
    """
    before = len(left)
    out = left.merge(right, on=on, how="left")
    if len(out) != before:
        raise ValueError(f"조인에서 행이 늘었다: {before:,} → {len(out):,} "
                         f"(키 {on}). 오른쪽 표를 키 단위로 집계한 뒤 붙여야 한다")
    return out


def applications_plus(tables):
    """지원 표에 공고 속성을 붙인다. 팬아웃이 나면 멈춘다."""
    ap = tables["applications"].drop_duplicates("application_id").copy()
    po = tables.get("postings")
    if po is None or "posting_id" not in ap.columns:
        return ap
    po = po.drop_duplicates("posting_id")
    cols = [c for c in ("competition", "has_test") if c in po.columns]
    if not cols:
        return ap
    ap = merge_1to1(ap, po[["posting_id"] + cols], "posting_id")
    if "competition" in ap.columns:
        ap["공고 경쟁도"] = pd.cut(ap["competition"], bins=COMPETITION_BINS,
                                   labels=COMPETITION_LABELS)
        ap["공고 경쟁도"] = ap["공고 경쟁도"].astype(object)
    if "has_test" in ap.columns:
        ap["과제 유무"] = ap["has_test"].map({True: "과제 있음", False: "과제 없음"})
    return ap


def _axis_frame(tables, axis):
    """축 하나에 대해 (그레인 키, [키, 축값] 표, 단계 도달표)를 돌려준다."""
    tbl, col = AXES[axis]
    if tbl == "applications":
        key, src = "application_id", applications_plus(tables)
        p = _stage_pivot(tables, "application")
    else:
        key = "applicant_id"
        src = tables["applicants"].drop_duplicates("applicant_id")
        p = _stage_pivot(tables, "person")
    return key, src[[key, col]].copy(), p, col


def axis_candidates(tables):
    """축 후보 — 몇 칸으로 나뉘는가 · 가장 작은 칸이 최소 표본을 넘는가 · 격차."""
    rows = []
    for name in AXES:
        try:
            key, src, _, col = _axis_frame(tables, name)
        except KeyError:
            continue
        if col not in src.columns:
            continue
        g = src.groupby(col, dropna=False)[key].nunique()
        d = funnel_by(tables, name)
        rate = d.loc[d["전환율"].notna(), "전환율"]
        rows.append({
            "축": name,
            "칸 수": int(g.size),
            "가장 작은 칸": int(g.min()) if g.size else 0,
            "미분류": int(src[col].isna().sum()),
            "최소 표본 미달 칸": int((g < config.MIN_SAMPLE).sum()),
            "격차(%p)": round(float(rate.max() - rate.min()) * 100, 1)
            if len(rate) > 1 else None,
        })
    out = pd.DataFrame(rows)
    return out.sort_values("격차(%p)", ascending=False, na_position="last") \
              .reset_index(drop=True)


def funnel_by(tables, axis, start=None, end=None):
    """분해 — 한 축으로 쪼개 [시작 단계] → [끝 단계] 구간을 본다.

    반환: DataFrame[칸, 시작, 도달, 전환율, 비중]
      · 비중 — 그 칸의 시작 인원 / 전체 시작 인원. 전환율만 보면 규모를 놓친다.
              비중 3% × 전환율 20% 를 고쳐도 전체는 거의 안 움직인다.
    """
    start = start or config.FUNNEL_STEPS[0]
    end = end or config.FUNNEL_STEPS[1]
    key, src, p, col = _axis_frame(tables, axis)

    reach = p[[c for c in (start, end) if c in p.columns]].notna()
    m = src.merge(reach, left_on=key, right_index=True, how="inner")
    m[col] = m[col].fillna("(미분류)")

    g = m.groupby(col).agg(시작=(start, "sum"), 도달=(end, "sum")).reset_index()
    g = g.rename(columns={col: "칸"})
    g["전환율"] = g["도달"] / g["시작"].replace(0, pd.NA)
    g["비중"] = g["시작"] / g["시작"].sum()
    # 비중 × 격차가 실제 크기다. 전환율이 낮아도 규모가 작으면 손댈 값이 적다.
    if g["전환율"].notna().any():
        g["기여도(%p)"] = ((g["전환율"].mean() - g["전환율"]) * g["비중"] * 100).round(2)
    return g.sort_values("시작", ascending=False).reset_index(drop=True)


def biggest_gap(df):
    """격차가 가장 큰 두 칸 (Day3 프롬프트 1)."""
    d = df.loc[df["전환율"].notna()].sort_values("전환율")
    if len(d) < 2:
        return None
    lo, hi = d.iloc[0], d.iloc[-1]
    return {"낮은 칸": lo["칸"], "낮은 값": float(lo["전환율"]),
            "높은 칸": hi["칸"], "높은 값": float(hi["전환율"]),
            "격차": float(hi["전환율"] - lo["전환율"])}


# ══════════════════════════════════════════════════════════════════════════
# Day3 실습 B — 못 믿을 조건  ★ 오늘의 핵심
# ══════════════════════════════════════════════════════════════════════════
def trust_check(sample=None, obs_days=None, fairness=None):
    """못 믿을 조건. 하나라도 걸리면 사유(문자열)를, 다 통과하면 None 을 돌려준다.

    호출하는 쪽은 None 일 때만 지표를 계산한다. 계산해 놓고 숨기는 것이 아니다 —
    걸리면 계산 자체를 하지 않는다. 손에 없으면 못 쓴다.

    조건 셋 (근거는 config 에 있다)
      1 표본이 MIN_SAMPLE 미만        값이 흔들린다
      2 관측 기간이 MIN_OBS_DAYS 미만  아직 진행 중이다
      3 비교가 공정하지 않다           무엇 때문인지 못 가린다
    """
    if sample is not None and sample < config.MIN_SAMPLE:
        return (f"표본 {int(sample):,}건 (최소 {config.MIN_SAMPLE}건) — "
                f"한 건이 바뀌면 비율이 {1 / max(sample, 1):.1%} 움직인다")
    if obs_days is not None and obs_days < config.MIN_OBS_DAYS:
        return (f"관측 {int(obs_days)}일 (최소 {config.MIN_OBS_DAYS}일) — "
                f"아직 다음 단계로 갈 시간이 없다")
    if fairness:
        return f"비교 조건 불일치 — {fairness}"
    return None


def cohort_by_start_month(tables):
    """시작 시점별 다음 단계 도달률 — 우측 절단을 눈으로 본다 (Day2 실습 E)."""
    s = _person_span(tables)
    p = _stage_pivot(tables, "person")
    as_of = pd.Timestamp(config.AS_OF)
    d = pd.DataFrame({
        "코호트": s["첫 지원일"].dt.to_period("M").astype(str),
        "관측 일수": (as_of - s["첫 지원일"]).dt.days,
        "서류 통과": p[config.FUNNEL_STEPS[1]].reindex(s.index).notna(),
        "최종 합격": p[config.FUNNEL_STEPS[-1]].reindex(s.index).notna(),
    })
    g = d.groupby("코호트").agg(인원=("관측 일수", "size"),
                                관측일수=("관측 일수", "median"),
                                서류통과율=("서류 통과", "mean"),
                                최종합격률=("최종 합격", "mean")).reset_index()
    g["못 믿을 사유"] = [trust_check(sample=n, obs_days=d_)
                         for n, d_ in zip(g["인원"], g["관측일수"])]
    return g
