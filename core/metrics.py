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

# 세는 단위의 이름. 화면·문서가 다 이것을 쓴다 — 두 곳에 두면 갈라진다.
GRAIN_UNIT = {"person": "지원자 1명", "application": "지원 1건"}


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
# 축 값이 비어 있는 행을 담는 칸. 칸 이름이지 «누구»가 아니다 —
# 원인 절에서 최고·최저로 지목하지 않는다. 표에는 그대로 남는다.
UNCLASSIFIED = "(미분류)"

# 지표가 재고 있는 퍼널 구간. 여기 없는 지표는 구간이 아니라 평균이다 —
# 평균에는 «어느 칸에서 빠지는가»가 없으니 쪼갤 구간도 없다.
# ★ 그레인을 같이 적는다. 서류 통과율은 «건» 으로 재고 최종 합격률은 «명»
#   으로 잰다. 구간만 맞춰 놓았더니, 명 기준 문서(축:학력, 79.2%)에 건 기준
#   서류 통과율 추세(18.1%)가 붙어서 한 문서에 «서류 통과율» 이 둘이 됐다.
METRIC_SPAN = {
    config.MAIN_METRIC: ("application",
                         (config.FUNNEL_STEPS[0], config.FUNNEL_STEPS[1])),
    "최종 합격률": ("person",
                    (config.FUNNEL_STEPS[0], config.FUNNEL_STEPS[-1])),
}


def _metric_grain(name):
    """지표를 어느 단위로 재는가. 표에 없는 지표는 기본 그레인이다."""
    got = METRIC_SPAN.get(name)
    return got[0] if got else config.GRAIN


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
# 구간 이름은 읽는 사람이 무슨 뜻인지 바로 알 수 있어야 한다.
# «(~.35)» 같은 표기는 쓰는 사람만 안다 — 경계값을 0.00~1.00 으로 다 적는다.
COMPETITION_LABELS = [
    "경쟁 낮음 (0.00~0.35)",
    "경쟁 보통 (0.35~0.65)",
    "경쟁 높음 (0.65~1.00)",
]


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
    m[col] = m[col].fillna(UNCLASSIFIED)

    g = m.groupby(col).agg(시작=(start, "sum"), 도달=(end, "sum")).reset_index()
    g = g.rename(columns={col: "칸"})
    g["전환율"] = g["도달"] / g["시작"].replace(0, pd.NA)
    g["비중"] = g["시작"] / g["시작"].sum()
    # 비중 × 격차가 실제 크기다. 전환율이 낮아도 규모가 작으면 손댈 값이 적다.
    if g["전환율"].notna().any():
        g["기여도(%p)"] = ((g["전환율"].mean() - g["전환율"]) * g["비중"] * 100).round(2)
    return g.sort_values("시작", ascending=False).reset_index(drop=True)


def biggest_gap(df):
    """격차가 가장 큰 두 칸 (Day3 프롬프트 1).

    격차는 «화면에 찍히는 값»에서 뺀다. 원값으로 빼면 23.4% 와 13.1% 를
    보여 주면서 격차를 10.4%p 라고 적게 되고, 읽는 사람이 암산해서 맞춰 볼 수
    없다. 자릿수를 맞춰 놓지 않으면 맞는 값도 틀린 것처럼 보인다.
    소수 첫째 자리까지 보여 주므로 거기서 뺀다.
    """
    d = df.loc[df["전환율"].notna()].sort_values("전환율")
    if len(d) < 2:
        return None
    lo, hi = d.iloc[0], d.iloc[-1]
    shown_lo = round(float(lo["전환율"]) * 100, 1)
    shown_hi = round(float(hi["전환율"]) * 100, 1)
    return {"낮은 칸": lo["칸"], "낮은 값": shown_lo / 100,
            "높은 칸": hi["칸"], "높은 값": shown_hi / 100,
            "격차": round(shown_hi - shown_lo, 1) / 100}


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


# ══════════════════════════════════════════════════════════════════════════
# 9주차 Day3 실습 A — 주제 후보 · 주제별 근거
# ══════════════════════════════════════════════════════════════════════════
# 후보는 하나만 뽑지 않는다. 하나만 뽑으면 그날 눈에 띈 것이 그대로 이번 분기의
# 우선순위가 된다. 뽑을 수 있는 만큼 뽑아 놓고 고른다.
#
# ★ 새 임계값을 만들지 않았다. 격차 하한은 core/verdict.py 의 MOVE_MIN(5%p)을,
#   비교 기간 길이는 config.MIN_OBS_DAYS(90일)를 빌려 썼다.
#     MOVE_MIN  — 그 값의 뜻이 «최소 표본에서 잡음만으로 생길 수 있는 폭의 1.5배»다.
#                 여기서 묻는 것도 «잡음이 아니라 신호인가»라서 같은 자를 쓴다.
#                 여기서 새로 정하면 판정과 주제 선정이 서로 다른 자를 쓰게 된다.
#     90일      — 관측이 차는 데 그만큼 걸린다. 그보다 짧게 끊어 견주면
#                 아직 안 찬 달을 «떨어졌다»고 읽는다.
TREND_MONTHS = max(1, round(config.MIN_OBS_DAYS / 30.44))


def _gap_min():
    """격차 하한. verdict 를 모듈 맨 위에서 부르면 순환이라 여기서 부른다."""
    from core.verdict import MOVE_MIN
    return MOVE_MIN


def _period_years():
    """기간을 «해»로 잰다. 계산에 현재 시각을 쓰지 않는다 — config.PERIOD 뿐이다."""
    a, b = pd.Timestamp(config.PERIOD[0]), pd.Timestamp(config.PERIOD[1])
    return ((b - a).days + 1) / 365.25


def _pp(v):
    """화면에 찍히는 자리(소수 첫째)까지 반올림한 %. 격차는 이 값끼리 뺀다."""
    return round(float(v) * 100, 1)


def _topic(key, kind, title, line, size, axis=None, span=None, grain=None,
           reject=None, **extra):
    d = {"키": key, "갈래": kind, "제목": title, "한줄": line,
         "규모_연간건수": size, "근거축": axis, "구간": span,
         "세는 단위": grain, "기각사유": reject}
    d.update(extra)
    return d


def proposal_topics(tables):
    """제안서로 쓸 만한 주제 후보를 가능한 만큼 뽑는다.

    후보가 나오는 곳 넷 — 퍼널 구간 · 분해 축 · 임계값 · 추세.

    ★ 기각과 «후보가 아님»은 다르다.
        기각      비교했는데 차이가 작다 → 목록에 남기고 사유를 적는다.
                  지우면 «안 봤다»와 «보고 아니었다»가 구분되지 않는다.
        후보 아님  못 믿을 조건에 걸려 비교 자체가 안 된다 → 애초에 안 만든다.
    """
    from core import verdict as _v      # 순환을 피해 여기서 부른다
    gap_min, years = _gap_min(), _period_years()
    out = []

    # ── ① 퍼널 구간 — 낮은 구간과 «그다음으로 낮은» 구간의 격차 ─────────
    for grain, unit in (("person", "명"), ("application", "건")):
        f = funnel(tables, grain)
        rows = []
        for i in range(1, len(f)):
            r = f.iloc[i]
            if pd.isna(r["직전 대비"]):
                continue
            rows.append({"구간": f"{f.iloc[i - 1]['단계']} → {r['단계']}",
                         "전환율": float(r["직전 대비"]),
                         "분모": int(f.iloc[i - 1]["인원"]),
                         "도달": int(r["인원"])})
        rows.sort(key=lambda x: x["전환율"])
        for i in range(len(rows) - 1):
            lo, nx = rows[i], rows[i + 1]
            if trust_check(sample=lo["분모"]):
                continue                # 비교 자체가 안 된다 — 기각이 아니다
            gap = round(_pp(nx["전환율"]) - _pp(lo["전환율"]), 1) / 100
            size = round(gap * lo["분모"] / years)
            out.append(_topic(
                f"구간:{grain}:{lo['구간']}", "퍼널 구간",
                f"{lo['구간']} 구간 전환율 격차 ({unit} 기준)",
                f"{lo['구간']} 전환율 {_pp(lo['전환율'])}% "
                f"({lo['도달']:,}{unit} / {lo['분모']:,}{unit}). "
                f"그다음으로 낮은 {nx['구간']} {_pp(nx['전환율'])}% 보다 "
                f"{_pp(gap)}%p 낮습니다.",
                size, span=lo["구간"], grain=GRAIN_UNIT[grain],
                reject=None if gap >= gap_min else
                f"격차 {_pp(gap)}%p 가 하한 {_pp(gap_min):.0f}%p 아래입니다",
                낮은=lo["구간"], 높은=nx["구간"], 격차=gap,
                분모=lo["분모"], 도달=lo["도달"], 단위=unit))

    # ── ② 분해 축 — 최고 칸과 최저 칸의 격차 ──────────────────────────
    span = f"{config.FUNNEL_STEPS[0]} → {config.FUNNEL_STEPS[1]}"
    for axis in AXES:
        try:
            g = _v.decomp_with_trust(tables, axis)
        except KeyError:
            continue
        ok = g.loc[g["사유"].isna() & g["전환율"].notna()]
        if len(ok) < 2:
            continue                    # 믿을 수 있는 칸이 둘 미만 — 후보가 아니다
        hi, lo = ok.loc[ok["전환율"].idxmax()], ok.loc[ok["전환율"].idxmin()]
        gap = round(_pp(hi["전환율"]) - _pp(lo["전환율"]), 1) / 100
        unit = "건" if AXES[axis][0] != "applicants" else "명"
        size = round(gap * int(lo["시작"]) / years)
        out.append(_topic(
            f"축:{axis}", "분해 축", f"{axis} 칸 사이 전환율 격차",
            f"{span} 구간을 {axis}로 쪼개면 {lo['칸']} {_pp(lo['전환율'])}% "
            f"({int(lo['도달']):,}{unit} / {int(lo['시작']):,}{unit}), "
            f"{hi['칸']} {_pp(hi['전환율'])}% 로 {_pp(gap)}%p 벌어집니다.",
            size, axis=axis, span=span, grain=GRAIN_UNIT[
                "application" if AXES[axis][0] != "applicants" else "person"],
            reject=None if gap >= gap_min else
            f"격차 {_pp(gap)}%p 가 하한 {_pp(gap_min):.0f}%p 아래입니다",
            낮은=lo["칸"], 높은=hi["칸"], 격차=gap,
            분모=int(lo["시작"]), 도달=int(lo["도달"]), 단위=unit,
            비중=float(lo["비중"]), 감춘칸=int(g["사유"].notna().sum())))

    # ── ③ 임계값 — 정해 둔 경고·위험선을 벗어난 지표 ──────────────────
    k = kpis(tables)
    for name, th in config.THRESHOLDS.items():
        v = k[name]["값"]
        if v is None:
            continue
        base, level = (th["위험"], "위험") if v < th["위험"] else \
            ((th["경고"], "경고") if v < th["경고"] else (th["경고"], None))
        ratio = k[name]["형식"] == "%"
        if level is None:
            size, reject = None, f"경고선 {th['경고']} 위입니다 (현재 {v:.3f})"
        elif ratio:
            size = round((base - v) * k[name]["표본"] / years)
            reject = None
        else:
            # 비율이 아니라 평균이다. 분자·분모가 없어 건수로 환산할 수 없다.
            size = None
            reject = (f"{name} 은 비율이 아니라 평균입니다. 분자·분모가 없어 "
                      f"건수로 환산할 수 없습니다")
        shown = f"{_pp(v)}%" if ratio else f"{v:.3f}"
        shown_b = f"{_pp(base)}%" if ratio else f"{base:.3f}"
        out.append(_topic(
            f"임계값:{name}", "임계값", f"{name} 임계값",
            f"{name} 현재 {shown} 입니다. {level or '경고'}선 {shown_b} 를 "
            f"{'밑돕니다' if level else '넘습니다'} (표본 {k[name]['표본']:,}).",
            # ★ «세는 단위» 칸에 지표 설명(«106명 / 520명 (사람 기준)»)을
            #   넣었더니 문서 머리글에 계산식이 그대로 찍혔다. 단위 칸에는
            #   단위를 넣는다. 설명은 현황 문장이 이미 말한다.
            size, grain=GRAIN_UNIT[_metric_grain(name)], reject=reject,
            지표=name, 현재=v, 기준=base, 수준=level,
            # ★ 보이는 글자는 만드는 자리가 하나여야 한다. 문서에서 다시
            #   서식을 매기면 화면 0.1806 · 문서 18.1% 로 갈린다.
            표시=shown, 기준표시=shown_b, 표본=k[name]["표본"]))

    # ── ④ 추세 — 최근 N개월이 직전 N개월보다 떨어졌는가 ────────────────
    m = monthly(tables)
    cut = pd.Period(config.VALID_UNTIL[:7], freq="M")
    m = m.loc[[i for i in m.index if pd.Period(str(i), freq="M") <= cut]]
    n = TREND_MONTHS
    for name in [config.MAIN_METRIC, "최종 합격률"] + config.GUARDRAILS:
        s = m[name].dropna()
        if len(s) < 2 * n:
            continue                    # 견줄 구간이 없다 — 후보가 아니다
        rec, prv = float(s.iloc[-n:].mean()), float(s.iloc[-2 * n:-n].mean())
        ratio = name in (config.MAIN_METRIC, "최종 합격률")
        drop = round(_pp(prv) - _pp(rec), 1) / 100 if ratio else (prv - rec)
        if ratio:
            size = round(drop * k[name]["표본"] / years) if drop > 0 else None
            reject = None if drop >= gap_min else (
                f"하락폭 {_pp(drop)}%p 가 하한 {_pp(gap_min):.0f}%p 아래입니다"
                if drop > 0 else f"떨어지지 않았습니다 ({_pp(-drop)}%p 올랐습니다)")
            shown = f"{_pp(rec)}% (직전 {n}개월 {_pp(prv)}%)"
        else:
            size = None
            reject = (f"{'떨어졌습니다' if drop > 0 else '떨어지지 않았습니다'} "
                      f"({prv:.3f} → {rec:.3f}). 다만 비율이 아니라 평균이라 "
                      f"건수로 환산할 수 없습니다")
            shown = f"{rec:.3f} (직전 {n}개월 {prv:.3f})"
        out.append(_topic(
            f"추세:{name}", "추세", f"{name} 최근 {n}개월 변화",
            f"{name} 최근 {n}개월 평균이 {shown} 입니다. "
            f"견준 구간은 {s.index[-2 * n]} ~ {s.index[-1]} 입니다.",
            size, grain=GRAIN_UNIT[_metric_grain(name)], reject=reject,
            지표=name, 최근=rec, 직전=prv, 하락=drop,
            표시=shown, 개월=n, 견준구간=f"{s.index[-2 * n]} ~ {s.index[-1]}",
            변화표시=(f"{_pp(abs(drop))}%p" if ratio else f"{abs(drop):.3f}"),
            방향=("떨어졌습니다" if drop > 0 else "올랐습니다")))

    # 규모가 큰 순서로. 기각된 것은 맨 뒤로 보내되 지우지 않는다.
    out.sort(key=lambda d: (d["기각사유"] is not None,
                            -(d["규모_연간건수"] or 0)))
    return out


def _span_pair(span):
    """«A → B» 를 (A, B) 로. 구간이 없으면 (None, None) — 그러면 첫 구간이다."""
    if not span:
        return (None, None)
    a, _, b = str(span).partition("→")
    return (a.strip() or None, b.strip() or None)


def _topic_span(topic):
    """이 주제가 말하는 구간. 없으면 None.

    구간 주제와 분해 축 주제는 «구간» 에 박혀 있다. 임계값·추세 주제는 지표가
    재고 있는 구간을 찾아 쓴다 — 지표가 평균이면 구간이 없다.
    """
    if topic.get("구간"):
        return topic["구간"]
    got = METRIC_SPAN.get(topic.get("지표"))
    return f"{got[1][0]} → {got[1][1]}" if got else None


def _topic_metric(topic):
    """이 주제의 지표. 추세를 보여도 되는 지표인지를 여기서 정한다.

    ★ 예전에는 지표가 없으면 무조건 주지표(서류 통과율)로 떨어뜨렸다. 그래서
      «면접 통과 → 최종 합격» 을 다루는 문서에도, «고용 형태» 를 다루는
      문서에도 서류 통과율 추세가 똑같이 붙었다. 주제와 상관없는 그림이다.
    """
    if topic.get("지표"):
        return topic["지표"]
    span, grain = _span_pair(_topic_span(topic)), _grain_of(topic)
    for name, (g, sp) in METRIC_SPAN.items():
        if sp == span and g == grain:
            return name
    return None


def _grain_of(topic):
    """이 주제를 어느 단위로 세는가. 키에 박아 둔 것을 그대로 읽는다."""
    if topic["키"].startswith("구간:"):
        return topic["키"].split(":")[1]
    if topic["키"].startswith("축:"):
        axis = topic["키"].split(":", 1)[1]
        return "person" if AXES[axis][0] == "applicants" else "application"
    # ★ 임계값·추세 주제는 지표가 재는 단위를 따른다. 예전에는 기본 그레인
    #   (명)으로 떨어뜨려서, 서류 통과율(건 기준 18.1%)을 다루는 문서가
    #   명 기준 퍼널(79.2%)을 같이 실었다. 한 문서에 같은 이름의 값이 둘이었다.
    got = METRIC_SPAN.get(topic.get("지표"))
    return got[0] if got else config.GRAIN


def _cause_axis(tables, grain, span=None):
    """이 그레인으로 쪼갤 수 있는 축 중 격차가 가장 큰 것.

    그레인이 다른 축으로 쪼개면 분모가 달라져 견줄 수 없다. 그래서 먼저 거른다.
    구간도 그대로 넘긴다 — 받아 놓고 안 쓰던 인자였다. 그래서 주제가 말하는
    구간과 문서가 쪼개는 구간이 달랐다.
    """
    from core import verdict as _v
    start, end = _span_pair(span)
    best = None
    for axis in AXES:
        if ("person" if AXES[axis][0] == "applicants" else "application") != grain:
            continue
        try:
            g = _v.decomp_with_trust(tables, axis, start=start, end=end)
        except KeyError:
            continue
        ok = g.loc[g["사유"].isna() & g["전환율"].notna()]
        if len(ok) < 2:
            continue
        gap = round(_pp(ok["전환율"].max()) - _pp(ok["전환율"].min()), 1) / 100
        if best is None or gap > best[1]:
            best = (axis, gap, g)
    return best


# ══════════════════════════════════════════════════════════════════════════
# 9주차 Day4 — 가정을 흔들어 본다
# ══════════════════════════════════════════════════════════════════════════
# 읽는 사람이 격차를 보고 처음 묻는 것은 «그 값이 맞는가» 가 아니라
# «다른 것으로 설명되는 것 아닌가» 다. 가정만 적어 두면 그 질문에 답이 없다.
# 그래서 가정마다 **흔들어 본 결과**를 같은 줄에 적는다.
#
# ★ 새 계산식을 만들지 않는다. 표를 거른 뒤 **같은 함수**를 다시 돌린다.
#   여기서 따로 계산하면 본문과 견딤이 서로 다른 자를 쓰게 된다.


def _slice(tables, app_ids):
    """지원 건 일부만 남긴 표 묶음. 계산은 원래 함수가 그대로 한다."""
    keep = set(app_ids)
    out = dict(tables)
    for name in ("applications", "application_events"):
        df = tables[name]
        out[name] = df.loc[df["application_id"].isin(keep)]
    return out


def _axis_rates(tables, axis, span):
    """이 축의 칸별 전환율. 못 믿을 조건은 그대로 건다."""
    from core import verdict as _v
    start, end = _span_pair(span)
    g = _v.decomp_with_trust(tables, axis, start=start, end=end)
    ok = g.loc[g["사유"].isna() & g["전환율"].notna()]
    return {str(r["칸"]): float(r["전환율"]) for _, r in ok.iterrows()}


def _max_lag(tables, span):
    """이 구간의 결과가 오기까지 실제로 걸린 가장 긴 날 수."""
    start, end = _span_pair(span)
    ev = tables["application_events"]
    a = ev.loc[ev["stage"] == (start or config.FUNNEL_STEPS[0]),
               ["application_id", "event_date"]]
    b = ev.loc[ev["stage"] == (end or config.FUNNEL_STEPS[1]),
               ["application_id", "event_date"]]
    j = a.merge(b, on="application_id", suffixes=("_s", "_e"))
    if j.empty:
        return None
    return int((j["event_date_e"] - j["event_date_s"]).dt.days.max())


def stress(tables, topic):
    """가정을 흔들어 본다. 못 흔드는 것은 «안 해 봤다»고 적는다.

    돌려주는 것은 {키: 한 줄} — 키가 없으면 그 줄은 «안 해 봤습니다» 가 된다.
    """
    out = {}
    span = _topic_span(topic)
    axis, lo, hi = topic.get("근거축"), topic.get("낮은"), topic.get("높은")
    ap = tables["applications"].drop_duplicates("application_id")

    # ① 달마다 나눠도 격차가 남는가 — 시점이 대신 설명하는 것 아닌가
    if axis and lo and hi:
        months, held = 0, 0
        gaps = []
        m = ap.copy()
        m["월"] = m["applied_date"].dt.to_period("M").astype(str)
        for _mo, g in m.groupby("월"):
            r = _axis_rates(_slice(tables, g["application_id"]), axis, span)
            if lo not in r or hi not in r:
                continue        # 그 달에 못 믿을 조건에 걸린 칸이 있다
            months += 1
            d = round(_pp(r[hi]) - _pp(r[lo]), 1)
            gaps.append(d)
            held += d > 0
        if months:
            out["시점"] = (f"달마다 따로 보면 표본 조건을 넘긴 {months}개월 중 "
                           f"{held}개월에서 같은 방향이었습니다 "
                           f"(격차 {min(gaps):.1f} ~ {max(gaps):.1f}%p).")
    else:
        out["시점"] = ("축이 아니라 구간이라 달마다 쪼개면 칸이 "
                       "못 믿을 조건에 걸립니다. 안 해 봤습니다.")

    # ② 결과가 아직 안 온 건을 빼도 격차가 남는가 — 우측 절단
    lag = _max_lag(tables, span)
    if lag is not None and axis and lo and hi:
        cut = pd.Timestamp(config.AS_OF) - pd.Timedelta(days=lag)
        ripe = ap.loc[ap["applied_date"] <= cut]
        n_raw, n_cut = len(ap), len(ap) - len(ripe)
        r = _axis_rates(_slice(tables, ripe["application_id"]), axis, span)
        if lo in r and hi in r:
            d = round(_pp(r[hi]) - _pp(r[lo]), 1)
            out["성숙"] = (
                f"이 구간의 결과는 길어야 {lag}일 안에 옵니다. 아직 올 수 있는 "
                f"{n_cut:,}건({n_cut / n_raw:.1%})을 빼면 격차가 "
                f"{_pp(topic.get('격차', 0))}%p 에서 {d:.1f}%p 가 됩니다.")

    # ③ 분모가 서로 독립인가 — 같은 공고에 여러 건이 들어갔다
    if "posting_id" in ap.columns:
        n_post, n_co = ap["posting_id"].nunique(), ap["company"].nunique()
        out["독립"] = (f"고유 공고 {n_post:,}개 · 회사 {n_co:,}개에 "
                       f"{len(ap):,}건이 들어갔습니다 (공고 1개당 "
                       f"{len(ap) / n_post:.1f}건). 건끼리 독립이 아닙니다.")

    # ④ 이 제안이 앞 단계만 늘리는 것은 아닌가 — 마지막 단계로도 봐 본다
    last = config.FUNNEL_STEPS[-1]
    if axis and lo and hi and _span_pair(span)[1] != last:
        r = _axis_rates(tables, axis, f"{config.FUNNEL_STEPS[0]} → {last}")
        if lo in r and hi in r:
            out["끝단계"] = (
                f"같은 칸을 {last} 기준으로 보면 {lo} {_pp(r[lo])}% · "
                f"{hi} {_pp(r[hi])}% 로 순서가 "
                f"{'같습니다' if r[hi] > r[lo] else '뒤집힙니다'}.")
    return out


def topic_evidence(tables, topic):
    """고른 주제 하나가 쓸 근거를 한 번에 모아 돌려준다.

    이 함수는 **조회만 한다.** 문장은 만들지 않는다 — 문장은 report/proposal.py 다.
    없는 것은 지어내지 않고 None 으로 두되, 왜 없는지를 «없는 이유» 에 남긴다.
    실측과 환산값은 키를 나눈다. 섞으면 어느 쪽이 잰 값인지 안 보인다.
    """
    grain = _grain_of(topic)
    unit = "명" if grain == "person" else "건"
    years = _period_years()
    # ★ 표본이 몇인지가 문서에 없으면, 읽는 사람은 4,961이 한 사람 것인지
    #   여러 사람 것인지 모른 채로 읽는다. 머리글 한 줄이면 되는 것이었다.
    _ap = tables["applications"].drop_duplicates("application_id")
    ev = {"주제": topic, "세는 단위": GRAIN_UNIT[grain],
          "표본": {"지원자": int(_ap["applicant_id"].nunique()),
                   "지원": int(len(_ap)),
                   "공고": int(_ap["posting_id"].nunique())
                   if "posting_id" in _ap.columns else None},
          "현황": None, "원인": None, "규모": None, "추세": None, "없는 이유": {}}

    # ── 현황 — 그 주제가 속한 퍼널 전체 ────────────────────────────────
    f = funnel(tables, grain).copy()
    f["구간"] = [None] + [f"{f.iloc[i - 1]['단계']} → {f.iloc[i]['단계']}"
                          for i in range(1, len(f))]
    worst = int(f.iloc[1:]["직전 대비"].astype(float).idxmin())
    # 표는 «구간»으로 낸다. 단계로 내면 첫 줄의 직전 대비가 반드시 빈칸이 되고,
    # 빈칸은 문서에 그대로 인쇄된다. 단계별 도달은 그림이 보여준다.
    span_tbl = pd.DataFrame([
        {"구간": f.iloc[i]["구간"],
         f"진입({unit})": int(f.iloc[i - 1]["인원"]),
         f"도달({unit})": int(f.iloc[i]["인원"]),
         "전환율": float(f.iloc[i]["직전 대비"]),
         "첫 단계 대비": float(f.iloc[i]["누적"])}
        for i in range(1, len(f))])
    # ★ 이 주제가 말하는 구간을 «초점» 으로 따로 잡는다. 예전에는 초점 없이
    #   늘 병목만 실어서, 다른 구간을 다루는 문서도 첫 줄이 병목 이야기였다.
    #   퍼널에 없는 구간(지원 → 최종 합격 처럼 여러 칸을 건너뛰는 것)이면
    #   초점은 None 이고, 그때는 병목을 그대로 쓴다.
    span = _topic_span(topic)
    focus = None
    if span is not None:
        hit = [i for i in range(1, len(f)) if f.iloc[i]["구간"] == span]
        if hit:
            i = hit[0]
            focus = {"구간": span,
                     "시작": f.iloc[i - 1]["단계"], "끝": f.iloc[i]["단계"],
                     "전환율": float(f.iloc[i]["직전 대비"]),
                     "분모": int(f.iloc[i - 1]["인원"]),
                     "도달": int(f.iloc[i]["인원"]),
                     "병목인가": i == worst}
    ev["현황"] = {"표": f, "구간표": span_tbl, "병목": worst, "단위": unit,
                  "그레인": GRAIN_UNIT[grain], "초점": focus,
                  "병목 구간": f.iloc[worst]["구간"],
                  "병목 전환율": float(f.iloc[worst]["직전 대비"]),
                  "병목 분모": int(f.iloc[worst - 1]["인원"]),
                  "병목 도달": int(f.iloc[worst]["인원"])}

    # ── 원인 — 그 주제의 분해 축 표 ────────────────────────────────────
    axis = topic.get("근거축")
    got = None
    if span is None:
        # 구간이 없는 주제(평균 지표)는 쪼갤 것이 없다. 첫 구간을 대신
        # 쪼개서 «원인» 이라고 부르면 그건 다른 이야기를 적는 것이다.
        ev["없는 이유"]["원인"] = (
            f"{topic.get('지표') or topic['제목']} — 비율이 아니라 평균입니다. "
            f"어느 칸에서 빠지는지가 없어 쪼갤 구간이 없습니다")
    elif axis:
        from core import verdict as _v
        got = (axis, None, _v.decomp_with_trust(tables, axis, *_span_pair(span)))
    else:
        got = _cause_axis(tables, grain, span)
    if got is None and "원인" not in ev["없는 이유"]:
        ev["없는 이유"]["원인"] = (
            f"{span} 구간을 {GRAIN_UNIT[grain]} 단위로 쪼갤 수 있는 축 중 "
            f"믿을 수 있는 칸이 둘 이상인 것이 없습니다")
    if got is not None:
        a, _gap, g = got
        ok = g.loc[g["사유"].isna() & g["전환율"].notna()]
        # ★ «(미분류)» 는 칸이 아니라 «안 적어 둔 것» 이다. 이 절이 답하는
        #   질문은 «누구에게서 벌어집니까» 인데, 미분류는 누구가 아니다.
        #   지우지는 않는다 — 표에는 그대로 두고 지목만 하지 않는다.
        named = ok.loc[ok["칸"] != UNCLASSIFIED]
        pick = named if len(named) >= 2 else ok
        g = g.copy()
        g["표시"] = ""
        if len(pick) >= 2:
            g.loc[pick["전환율"].idxmax(), "표시"] = "최고"
            g.loc[pick["전환율"].idxmin(), "표시"] = "최저"
        ev["원인"] = {
            "축": a, "표": g,
            # 그려진 것만 센다. 표본이 모자라 아예 안 그린 미분류를 두고
            # «최고·최저에서 뺐습니다» 라고 적으면, 읽는 사람은 있지도 않은
            # 막대를 찾는다.
            "미분류": int(((g["칸"] == UNCLASSIFIED) & g["사유"].isna()
                           & g["전환율"].notna()).sum()),
            "미분류칸": UNCLASSIFIED, "단위": "명" if AXES[a][0] == "applicants" else "건",
            "구간": span,
            "최고": g.loc[g["표시"] == "최고"].iloc[0].to_dict() if (g["표시"] == "최고").any() else None,
            "최저": g.loc[g["표시"] == "최저"].iloc[0].to_dict() if (g["표시"] == "최저").any() else None,
            "감춘 칸": g.loc[g["사유"].notna(), ["칸", "시작", "사유"]],
        }

    # ── 규모 — 연간 건수 + 환산에 쓴 가정 ──────────────────────────────
    if topic.get("규모_연간건수") is None:
        ev["없는 이유"]["규모"] = topic.get("기각사유") or "환산할 분모가 없습니다"
    else:
        ev["규모"] = {
            "실측": {"격차": topic.get("격차"), "분모": topic.get("분모"),
                     "단위": topic.get("단위", unit)},
            "환산값": {"연간건수": topic["규모_연간건수"], "단위": topic.get("단위", unit)},
            "가정": [
                "지금 벌어진 격차가 앞으로도 그대로 이어진다고 봅니다. "
                "개입 효과를 실측한 값이 아닙니다.",
                f"기간 {config.PERIOD[0]} ~ {config.PERIOD[1]} "
                f"({years:.2f}년)으로 나눠 한 해분으로 환산했습니다.",
                f"분모는 그 구간·칸에 실제로 진입한 "
                f"{topic.get('분모', 0):,}{topic.get('단위', unit)} 입니다.",
                # ★ 견준 대상을 안 적으면 «낮다»의 기준이 문서 밖에 있다.
                #   더 중요한 것은, 거기까지 갈 수 있다고 «본» 것이지
                #   갈 수 있음을 «잰» 것이 아니라는 점이다.
                # «이(가)» 같은 양쪽 표기는 안 쓴다. 사람이 안 쓰는 말이다 —
                # 이름이 무엇이든 붙는 «쪽» 으로 문장을 짠다.
                (f"견준 대상은 {topic.get('높은')} 입니다. "
                 f"{topic.get('낮은')} 쪽이 거기까지 올라갈 수 있다고 보고 "
                 f"낸 값이지, 올라갈 수 있음을 잰 값이 아닙니다."
                 if topic.get("높은") and topic.get("낮은") else
                 "견준 대상을 따로 두지 않았습니다."),
                "금액으로 환산하지 않았습니다. 건당 금액을 적어 둔 항목이 없습니다 "
                "(단가 미확보).",
            ],
        }
        # 가정과 **같은 순서·같은 개수**로 짝을 맞춘다. 짝이 없는 줄은
        # «안 해 봤습니다» 가 된다 — 빈칸으로 두면 안 한 것인지 못 한 것인지
        # 읽는 사람이 알 수 없다.
        st = stress(tables, topic)
        ev["규모"]["흔든것"] = st
        ev["규모"]["흔들기"] = [
            st.get("시점", "안 해 봤습니다."),
            st.get("성숙", "안 해 봤습니다."),
            st.get("독립", "안 해 봤습니다."),
            st.get("끝단계", "안 해 봤습니다."),
            "안 해 봤습니다. 건당 금액이 없으면 흔들어 볼 것도 없습니다.",
        ]

    # ── 추세 — 관련 지표의 최근 12개월 ─────────────────────────────────
    name = _topic_metric(topic)
    m = monthly(tables)
    s = (m[name].dropna() if name and name in m.columns
         else pd.Series(dtype=float))
    if name is None:
        ev["없는 이유"]["추세"] = (
            f"{span or topic['제목']} 을(를) 달마다 잰 값이 없습니다. "
            f"다른 지표의 추세를 대신 싣지 않습니다")
    elif s.empty:
        ev["없는 이유"]["추세"] = f"{name} 의 월별 값이 없습니다"
    else:
        cut = pd.Period(config.VALID_UNTIL[:7], freq="M")
        valid = [i for i in s.index if pd.Period(str(i), freq="M") <= cut]
        th = config.THRESHOLDS.get(name, {})
        ev["추세"] = {"지표": name, "값": s.tail(12),
                      "유효 구간": valid,
                      "경고": th.get("경고"), "위험": th.get("위험"),
                      "형식": "%" if name in (config.MAIN_METRIC, "최종 합격률") else "n"}
    return ev
