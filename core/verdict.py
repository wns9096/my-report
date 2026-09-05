# -*- coding: utf-8 -*-
"""판정층 — Day3 실습 C.

순서가 중요하다. 좋은 결과를 먼저 보면 뒤의 확인을 대충 한다.
그래서 규율에 맡기지 않고 코드로 박는다.

  1 믿을 수 있는가      →  아니면 여기서 끝. 계산하지 않는다
  2 주지표가 움직였는가  →  아니면 "효과 없음"
  3 가드레일은 괜찮은가  →  나빠졌으면 "주의 필요"
  4 다 통과            →  "성공"
"""
import pandas as pd

from core import config, metrics

# 주지표가 "움직였다"의 하한.
# 근거: 최소 표본 30에서 한 건이 바뀌면 비율이 3.3%p 움직인다. 가장 작은 칸에서
#       잡음만으로 생길 수 있는 폭이 그 정도이므로, 그 1.5배인 5%p를 하한으로 둔다.
MOVE_MIN = 0.05

# 가드레일이 "나빠졌다"의 기준.
# 근거: (1) config.THRESHOLDS 의 경고선 아래로 내려가면 나빠진 것이다 —
#           그 값들은 7주차에 근거를 적고 정한 것이다.
#       (2) 경고선 위여도 기준 대비 10% 이상 빠지면 눈에 띄는 변화다.
GUARD_DROP = 0.10

VERDICTS = {
    "성공":      "ok",
    "주의 필요":  "warn",
    "효과 없음":  "none",
    "무효":      "block",
}


def _guard_state(name, value, base):
    """가드레일 한 항목의 상태. (악화 여부, 설명)"""
    th = config.THRESHOLDS.get(name, {})
    warn = th.get("경고")
    drop = (base - value) / base if base else 0.0
    bad = (warn is not None and value < warn) or (drop >= GUARD_DROP)
    fmt = (lambda v: f"{v:.3f}") if name == "직무 적합도" else (lambda v: f"{v:.2f}")
    why = f"{name} {fmt(value)} (기준 {fmt(base)}, {-drop:+.1%})"
    if warn is not None and value < warn:
        why += f" · 경고선 {fmt(warn)} 아래"
    return bad, why


def judge(name, before, after, sample, obs_days, guards, base_guards, fairness=None):
    """카드 한 장. 못 믿을 조건에 걸리면 before/after 를 아예 쓰지 않는다."""
    reason = metrics.trust_check(sample=sample, obs_days=obs_days, fairness=fairness)
    if reason:
        # 계산해 놓고 숨기는 것이 아니다. 값을 카드에 담지 않는다.
        return {"이름": name, "판정": "무효", "사유": reason, "표본": int(sample),
                "이전": None, "이후": None, "변화": None, "가드레일": None}

    delta = after - before
    card = {"이름": name, "판정": None, "사유": "", "표본": int(sample),
            "이전": f"{before:.1%}", "이후": f"{after:.1%}",
            "변화": f"{delta * 100:+.1f}%p", "가드레일": None,
            "델타": delta}

    if abs(delta) < MOVE_MIN:
        card["판정"] = "효과 없음"
        card["사유"] = f"변화 {delta * 100:+.1f}%p — 움직였다고 볼 하한 {MOVE_MIN:.0%} 미만"
        return card

    if not guards:
        card["판정"] = "주의 필요"
        card["사유"] = "가드레일 없음 — 무엇을 희생했는지 확인되지 않음"
        return card

    states = [_guard_state(k, v, base_guards[k]) for k, v in guards.items()]
    card["가드레일"] = " · ".join(w for _, w in states)
    if any(bad for bad, _ in states):
        card["판정"] = "주의 필요"
        card["사유"] = "주지표는 개선됐으나 가드레일이 나빠졌다"
    else:
        card["판정"] = "성공"
        card["사유"] = "주지표 개선 · 가드레일 이상 없음"
    return card


# ══════════════════════════════════════════════════════════════════════════
def _person_frame(tables):
    """지원자 1명 = 한 행. 주지표와 가드레일을 사람 단위로 붙인다."""
    s = metrics._person_span(tables)
    p = metrics._stage_pivot(tables, "person")
    as_of = pd.Timestamp(config.AS_OF)
    ap = tables["applications"].drop_duplicates("application_id")
    fit = ap.groupby("applicant_id")["fit_score"].mean()
    an = tables["applicants"].drop_duplicates("applicant_id").set_index("applicant_id")

    months = ((as_of - s["첫 지원일"]).dt.days / 30.44).clip(lower=1.0)
    return pd.DataFrame({
        "코호트": s["첫 지원일"].dt.to_period("M").astype(str),
        "관측 일수": (as_of - s["첫 지원일"]).dt.days,
        "서류 통과": p[config.FUNNEL_STEPS[1]].reindex(s.index).notna(),
        "월 지원 건수": s["지원 건수"] / months,
        "직무 적합도": fit.reindex(s.index),
        "학력": an["education"].reindex(s.index).fillna("(미기재)"),
        # 카드 축을 바꾸면 여기에 그 컬럼을 사람 단위로 붙인다.
    })


def cards(tables):
    """판정 카드 — 구간 비교(학력) + 전후 비교(시작 시점).

    이 도메인에는 A/B 실험이 없다. 그래서 실험 장 대신 비교 장이다.
    무작위 배정이 없으므로 인과를 주장할 수 없다 — 문서 5장 첫 문단에 박아 둔다.
    """
    d = _person_frame(tables)
    base = float(d["서류 통과"].mean())
    base_guards = {"월 지원 건수": float(d["월 지원 건수"].mean()),
                   "직무 적합도": float(d["직무 적합도"].mean())}
    out = []

    # ── 구간 비교 — 분해 축의 각 칸을 전체 평균과 견준다 ─────────────────
    for cell, g in d.groupby(config.CARD_AXIS):
        out.append(judge(
            f"{config.CARD_AXIS} · {cell}",
            before=base, after=float(g["서류 통과"].mean()),
            sample=len(g), obs_days=float(g["관측 일수"].median()),
            guards={"월 지원 건수": float(g["월 지원 건수"].mean()),
                    "직무 적합도": float(g["직무 적합도"].mean())},
            base_guards=base_guards,
        ))

    # ── 전후 비교 — 시작 시점으로 자른다 ─────────────────────────────────
    valid = config.VALID_UNTIL[:7]
    first = d[d["코호트"] <= "2025-06"]
    second = d[(d["코호트"] > "2025-06") & (d["코호트"] <= valid)]
    late = d[d["코호트"] > valid]

    out.append(judge(
        "시작 시점 · 상반기 → 하반기(유효 구간 내)",
        before=float(first["서류 통과"].mean()), after=float(second["서류 통과"].mean()),
        sample=len(second), obs_days=float(second["관측 일수"].median()),
        guards={"월 지원 건수": float(second["월 지원 건수"].mean()),
                "직무 적합도": float(second["직무 적합도"].mean())},
        base_guards={"월 지원 건수": float(first["월 지원 건수"].mean()),
                     "직무 적합도": float(first["직무 적합도"].mean())},
    ))
    out.append(judge(
        f"시작 시점 · 유효 구간 밖({valid} 이후)",
        before=float(second["서류 통과"].mean()), after=float(late["서류 통과"].mean()),
        sample=len(late), obs_days=float(late["관측 일수"].median()),
        guards=None, base_guards=base_guards,
    ))
    return out


def decomp_with_trust(tables, axis=None):
    """분해 결과에 못 믿을 조건을 건다. 걸린 칸은 전환율을 지운다."""
    axis = axis or config.DECOMP_AXIS
    g = metrics.funnel_by(tables, axis)
    g["사유"] = [metrics.trust_check(sample=int(n)) for n in g["시작"]]
    g.loc[g["사유"].notna(), ["도달", "전환율"]] = None
    return g


def count_by_verdict(cards_):
    c = {}
    for k in cards_:
        c[k["판정"]] = c.get(k["판정"], 0) + 1
    return c
