# -*- coding: utf-8 -*-
"""화면과 문서가 같은 값을 쓰게 만드는 자리.

문서가 화면과 다른 숫자를 쓰면 어느 쪽이 맞는지 알 수 없다.
그래서 계산은 여기 한 곳에서만 부른다.
"""
import pandas as pd

from core import config, metrics, validate, verdict

GRAIN_KO = {"person": "지원자 1명", "application": "지원 1건"}
MANUAL_LIMITS_PATH = config.OUT / "limits_manual.txt"


def load_manual_limits() -> str:
    if MANUAL_LIMITS_PATH.exists():
        return MANUAL_LIMITS_PATH.read_text(encoding="utf-8")
    return ""


def save_manual_limits(text: str):
    MANUAL_LIMITS_PATH.write_text(text or "", encoding="utf-8")


def build(tables) -> dict:
    """검증이 먼저다. 차단이 있으면 계산을 시작하지 않는다.

    ★ Day1 실습 E 에서 여기가 터졌다.
      필수 컬럼을 지운 파일을 넣었더니 검증은 차단을 띄웠는데, 그 전에
      계산이 먼저 돌아 KeyError 로 앱이 죽었다. 앱이 죽으면 사람이 판단할
      화면 자체가 없다 — 차단으로 멈추는 것과 에러로 죽는 것은 다르다.
      그래서 계산을 검증 뒤로 옮겼다. 이것은 Day3 의 "못 믿으면 계산조차
      하지 않는다"와 같은 규칙을 적재 단계에 적용한 것이다.
    """
    checks = validate.run_checks(tables)
    if validate.blocked(checks):
        return {"tables": tables, "checks": checks, "blocked": True}
    try:
        return _build_all(tables, checks)
    except Exception as e:                       # 스키마가 예상과 다르면
        checks.append(validate._r(               # 죽지 말고 차단으로 바꾼다
            "계산 불가", "block",
            f"검증은 통과했으나 계산에서 막혔다: {type(e).__name__} {e}",
            "검증 규칙이 이 상황을 아직 안 보고 있다는 뜻이다"))
        return {"tables": tables, "checks": checks, "blocked": True}


def _build_all(tables, checks) -> dict:
    f = metrics.funnel(tables, config.GRAIN)
    ret, ret_skip = metrics.retention_funnel(tables)
    churn, judged, pending = metrics.churn_split(tables)

    raw = [config.FUNNEL_STEPS[0], config.FUNNEL_STEPS[1]] + config.NON_FUNNEL \
        + config.FUNNEL_STEPS[2:]
    ov = metrics.order_violation(tables, raw, "application")
    skipped = int(ov.loc[ov["구간"].str.contains(config.NON_FUNNEL[0]),
                         "앞 단계 미경유"].max()) if len(ov) else 0
    decomp = verdict.decomp_with_trust(tables)

    out = {
        "tables": tables,
        "checks": checks,
        "blocked": False,
        "grain": config.GRAIN,
        "grain_ko": GRAIN_KO[config.GRAIN],
        "funnel": f,
        "gap": metrics.funnel_gap(tables),
        "worst": int(f.iloc[1:]["직전 대비"].astype(float).idxmin()),
        "retention": ret,
        "retention_skip": ret_skip,
        "churn": churn,
        "judged": judged,
        "pending": pending,
        "skipped_nonfunnel": skipped,
        "kpis": metrics.kpis(tables),
        "monthly": metrics.monthly(tables),
        "axis": config.DECOMP_AXIS,
        "axis_candidates": metrics.axis_candidates(tables),
        "decomp": decomp,
        "gap2": metrics.biggest_gap(decomp),
        "retention_candidates": metrics.retention_candidates(tables),
        "facts": facts(tables),
        "cohort": metrics.cohort_by_start_month(tables),
        "cards": verdict.cards(tables),
        "limits_manual": load_manual_limits(),
    }
    out["sum_check"] = sum_check(out)
    out["order_check"] = order_check(tables)
    out["hand_check"] = hand_check(tables)
    return out


def facts(tables):
    """Day1 프롬프트 5 — 눈에 띄는 사실만. 판단은 하지 않는다.

    "이건 오류입니다"라고 코드가 먼저 말하면 사람이 판단할 기회가 사라진다.
    그래서 사실만 놓고 판정은 검증 규칙과 사람에게 맡긴다.
    """
    out = []
    ev = tables.get("application_events")
    ap = tables.get("applications")
    if ap is not None:
        out.append(f"applications 원본 {len(ap):,}행 · 고유 키 "
                   f"{ap['application_id'].nunique():,}개")
    if ev is not None:
        vc = ev["stage"].value_counts()
        out.append("이벤트 단계별 건수 — "
                   + " · ".join(f"{k} {v:,}" for k, v in vc.items()))
        known = set(config.FUNNEL_STEPS) | set(config.NON_FUNNEL)
        extra = [k for k in vc.index if k not in known]
        if extra:
            out.append(f"config 에 없는 단계 이름 {len(extra)}개: {', '.join(extra)}")
    for name, df in tables.items():
        dcols = [c for c in df.columns if str(df[c].dtype).startswith("datetime")]
        for c in dcols:
            if df[c].isna().any():
                out.append(f"{name}.{c} 날짜로 못 읽은 값 "
                           f"{int(df[c].isna().sum()):,}건")
    an = tables.get("applicants")
    if an is not None and ev is not None:
        orphan = len(set(ev["applicant_id"]) - set(an["applicant_id"]))
        out.append(f"이벤트에는 있는데 지원자 표에 없는 대상 {orphan:,}명")
    return out


def kpi_state(name, value):
    """임계값과 견줘 상태를 돌려준다. ok | warn | block | none"""
    th = config.THRESHOLDS.get(name)
    if th is None or value is None or pd.isna(value):
        return "none"
    if value < th["위험"]:
        return "block"
    if value < th["경고"]:
        return "warn"
    return "ok"


def sum_check(ctx):
    """분해한 칸의 합이 전체와 맞는가 (Day3 프롬프트 7).

    분해 축의 그레인이 화면 기본 그레인과 다를 수 있다 — 공고 속성은 지원 1건에
    붙고, 사람 속성은 지원자 1명에 붙는다. 그래서 축의 그레인으로 견준다.
    차이가 나는 것이 꼭 오류는 아니다. 분류가 없는 대상이 빠졌을 수 있다.
    다만 그게 몇 건인지는 알고 있어야 한다.
    """
    d = ctx["decomp"]
    tbl = metrics.AXES[ctx["axis"]][0]
    grain = "application" if tbl == "applications" else "person"
    total = int(metrics.funnel(ctx["tables"], grain).iloc[0]["인원"])
    parts = int(d["시작"].sum())
    unclassified = int(d.loc[d["칸"] == "(미분류)", "시작"].sum())
    return {"그레인": GRAIN_KO[grain], "칸 합": parts, "전체": total,
            "차이": parts - total, "(미분류) 칸": unclassified}


def order_check(tables):
    """검산 둘 — 퍼널 뒤 단계가 앞 단계 안에 들어 있는가.

    앞을 안 거치고 나타난 대상이 많으면 그건 퍼널이 아니라 분류다.
    분류에 전환율을 매기면 분모가 앞 단계가 아니라서 값이 뜻을 잃는다.
    """
    ov = metrics.order_violation(tables, config.FUNNEL_STEPS, config.GRAIN)
    n = int(ov["앞 단계 미경유"].sum()) if len(ov) else 0
    back = int(ov["역행(뒤가 먼저)"].sum()) if len(ov) else 0
    where = ", ".join(ov.loc[ov["앞 단계 미경유"] > 0, "구간"]) if n else ""
    return {"건수": n, "역행": back, "표": ov,
            "요약": (f"앞 단계를 안 거치고 나타난 대상 {n:,}건"
                     + (f" — {where}" if where else "")
                     + f" · 역행 {back:,}건")}


def hand_check(tables):
    """검산 셋 — 손계산과 자릿수가 맞는가.

    대조값은 config.HAND_BASELINE 하나에서 온다. 화면과 검사 스크립트가
    각자 자기 숫자를 들고 있으면 대조가 아니라 서로 다른 두 주장이 된다.
    """
    hb = config.HAND_BASELINE
    per = metrics.funnel(tables, "person")["인원"].tolist()
    rate = float(metrics.kpis(tables)[config.MAIN_METRIC]["값"])
    diff = round(rate - hb["서류_통과율"], 4)
    same_funnel = per == hb["퍼널_사람"]
    same_rate = abs(diff) <= config.HAND_TOL
    ok = same_funnel and same_rate
    return {
        "표본": hb["퍼널_사람"][0],
        "손": f"{hb['서류_통과율']:.2%}",
        "앱": f"{rate:.2%}",
        "차이": f"{diff * 100:+.2f}%p",
        "판정": "맞음" if ok else "안 맞음",
        "요약": (f"사람 퍼널 {per} vs 손계산 {hb['퍼널_사람']} · "
                 f"{config.MAIN_METRIC} 앱 {rate:.2%} vs 손계산 "
                 f"{hb['서류_통과율']:.2%} (차이 {diff * 100:+.2f}%p)"),
    }
