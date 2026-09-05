# -*- coding: utf-8 -*-
"""문서층 — Day4.

숫자는 거짓말을 안 하는데 문장은 한다.
그래서 가르는 기준은 하나다 — 이 문장이 틀렸을 때 누가 책임지는가.

  사실이 틀린 것뿐 → 자동으로 쓴다   요약 · 방법 · 결과 · 비교 · 한계
  사람이 책임진다   → 사람이 쓴다     배경 · 해석 · 제안

오른쪽을 자동화하는 순간 책임의 주체가 사라진다.
"""
import json
import re

import pandas as pd

from core import config, validate
from core.verdict import MOVE_MIN as _MOVE

# ── 사람이 쓰는 장 저장소 ─────────────────────────────────────────────────
HUMAN_PATH = config.OUT / "human_sections.json"
NOT_WRITTEN = "(작성되지 않음)"


def load_human() -> dict:
    if HUMAN_PATH.exists():
        return json.loads(HUMAN_PATH.read_text(encoding="utf-8"))
    return {}


def save_human(d: dict):
    HUMAN_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════
# Day4 실습 B — 인과를 단정하는 말
# ══════════════════════════════════════════════════════════════════════════
# 관측한 데이터로는 인과를 주장할 수 없다. 이 말들이 그것을 해버린다.
#
# ★ 오탐 하나를 겪고 고쳤다.
#   처음에는 "인해"를 그냥 부분 문자열로 찾았는데 "확**인해**야 한다"가 걸렸다.
#   검사가 멀쩡한 문장을 잡으면 사람이 검사를 끄기 시작한다 — 검증 규칙을 적게
#   만드는 것과 같은 이유다. 그래서 앞 글자를 보는 패턴으로 바꿨다.
#   목록은 (표시할 말, 찾을 정규식) 짝이다.
BANNED_PATTERNS = [
    # 기본
    ("때문에", r"때문에"),
    ("때문이다", r"때문이다"),
    ("덕분에", r"덕분에"),
    ("효과로", r"효과로"),
    ("입증", r"입증"),
    ("증명", r"증명"),
    ("확실히", r"확실히"),
    ("탓에", r"탓에"),
    ("로 인해", r"(?<![가-힣])(?:으로|로)\s*인해"),
    # 이 도메인에서 자주 쓰게 되는 표현
    ("유발", r"유발"),
    ("기인", r"기인(?:한|했|하)"),
    ("원인이다", r"원인이다"),
    ("영향을 미쳤", r"영향을\s*미"),
    ("견인", r"견인"),
    ("기여했", r"기여(?:했|한다|한 )"),
]

BANNED = [w for w, _ in BANNED_PATTERNS]

# 금지어를 대신할 말 — 화면에 같이 띄운다.
SUGGEST = {
    "때문에": "A가 낮은 구간에서 B도 낮다",
    "덕분에": "적용한 뒤 값이 높았다",
    "효과로": "차이가 관측되었다",
    "입증": "차이가 관측되었다",
    "증명": "차이가 관측되었다",
    "확실히": "가능성이 있다",
    "로 인해": "같은 구간에서 함께 나타났다",
    "인해": "같은 구간에서 함께 나타났다",
    "견인": "함께 늘었다",
    "기여했": "함께 늘었다",
}


def check_phrasing(sections: dict) -> list[dict]:
    """자동 장과 사람이 쓴 장 **전부**에 건다.

    사람이 쓴 해석에 "때문에"가 훨씬 자주 들어간다. 거기를 빼면 검사가 무의미하다.
    """
    hits = []
    for title, body in sections.items():
        if not body:
            continue
        for w in BANNED:
            for m in re.finditer(re.escape(w), body):
                s, e = max(0, m.start() - 25), min(len(body), m.end() + 25)
                hits.append({
                    "장": title,
                    "단어": w,
                    "문맥": "…" + body[s:e].replace("\n", " ") + "…",
                    "대신": SUGGEST.get(w, "관측된 사실까지만 쓴다"),
                })
    return hits


# ══════════════════════════════════════════════════════════════════════════
# 자동으로 쓰는 장
# ══════════════════════════════════════════════════════════════════════════
def _pct(v, nd=1):
    return "—" if v is None or pd.isna(v) else f"{v:.{nd}%}"


def _s1_summary(ctx) -> str:
    """요약 — 기간 · 주요 지표 2~4개 · 가장 낮은 구간. 원인은 쓰지 않는다."""
    f, k = ctx["funnel"], ctx["kpis"]
    lo = f.iloc[1:]["직전 대비"].astype(float).idxmin()
    lines = [
        f"기간 {config.PERIOD[0]} ~ {config.PERIOD[1]} · 데이터셋 {config.DATASET}",
        f"분석 단위는 {ctx['grain_ko']}이다. 대상 {f.iloc[0]['인원']:,}"
        f"{'명' if ctx['grain'] == 'person' else '건'}.",
        "",
        "주요 지표",
    ]
    for name in [config.MAIN_METRIC, "최종 합격률"] + config.GUARDRAILS:
        v = k[name]
        val = _pct(v["값"]) if v["형식"] == "%" else f"{v['값']:.2f}"
        lines.append(f"  · {name} {val}  (표본 {v['표본']:,})")
    lines += [
        "",
        f"가장 낮은 구간은 {f.iloc[lo-1]['단계']} → {f.iloc[lo]['단계']} 구간으로 "
        f"{_pct(f.iloc[lo]['직전 대비'])}이다.",
        f"첫 단계에서 마지막 단계까지의 누적 전환율은 {_pct(f.iloc[-1]['누적'], 2)}이다.",
    ]
    return "\n".join(lines)


def _s3_method(ctx) -> str:
    """방법 — 분석 단위(그레인) · 무엇을 뺐는지 · 어떤 기준으로 판정했는지."""
    lines = [
        # 이 줄은 처음에 "…이기 때문이다"로 썼다가 check_phrasing 에 걸렸다.
        # 자동 문장도 조립하다 보면 연결어로 인과를 쓴다. 그래서 자기 문장을 검사한다.
        f"분석 단위(그레인)는 **{ctx['grain_ko']}**이다. "
        f"같은 대상이 여러 번 나타나도 하나로 센다. "
        f"답하려는 질문은 \"이 대상이 결국 전환했는가\"이다.",
        "",
        "같은 데이터를 건 단위로 세면 값이 달라진다: "
        + " · ".join(f"{r['단계']} 사람 {r['사람']:,} / 건 {r['건']:,}"
                     for _, r in ctx["gap"].iterrows()),
        "",
        "퍼널 단계: " + " → ".join(config.FUNNEL_STEPS),
        f"뺀 단계: {', '.join(config.NON_FUNNEL)} — "
        f"{ctx['skipped_nonfunnel']:,}건이 이 단계를 거치지 않고 다음 단계에 나타났다. "
        f"앞 단계를 거치지 않으면 순서가 아니라 분류다.",
        "",
        "유지 퍼널 단계는 주어져 있지 않아 직접 정의했다: "
        + " → ".join(config.RETENTION_STEPS) + ".",
        f"이탈은 최종 단계 도달 없이 {config.CHURN_GAP_DAYS}일 넘게 활동이 없는 경우로 본다. "
        f"최종 단계 도달은 이탈이 아니라 성공 종료로 따로 센다.",
        "",
        "판정 기준",
        f"  · 최소 표본 {config.MIN_SAMPLE}건 · 최소 관측 {config.MIN_OBS_DAYS}일. "
        f"둘 중 하나라도 못 넘으면 지표를 계산하지 않는다.",
        "  · 임계값: "
        + " · ".join(f"{n} 경고 {v['경고']} / 위험 {v['위험']}"
                     for n, v in config.THRESHOLDS.items()),
        f"  · 유효 구간은 {config.PERIOD[0]} ~ {config.VALID_UNTIL}이다. "
        f"그 뒤 시작분은 관측 기간이 {config.MIN_OBS_DAYS}일에 못 미쳐 판정하지 않았다.",
        "",
        f"쪼갠 축은 둘이고 그레인이 다르다. "
        f"분해는 «{config.DECOMP_AXIS}» — 지원 1건에 붙는 속성이라 건 단위로 본다. "
        f"판정 비교는 «{config.CARD_AXIS}» — 주지표와 가드레일이 사람에 붙으므로 "
        f"사람 단위로 본다.",
        f"주지표는 {config.MAIN_METRIC}, 가드레일은 "
        f"{' · '.join(config.GUARDRAILS)}이다. "
        f"주지표가 {int(_MOVE * 100)}%p 이상 움직였을 때만 가드레일을 보고 판정한다.",
    ]
    return "\n".join(lines)


def _s4_results(ctx) -> str:
    """결과 — 단계별 값과 분해 결과를 나열한다. "왜"가 들어가면 해석이다."""
    f, r = ctx["funnel"], ctx["retention"]
    lines = ["획득 퍼널"]
    for _, row in f.iterrows():
        prev = "—" if pd.isna(row["직전 대비"]) else _pct(row["직전 대비"])
        lines.append(f"  · {row['단계']} {row['인원']:,}  직전 대비 {prev}  "
                     f"누적 {_pct(row['누적'])}")
    lines += ["", "유지 퍼널 (직접 정의한 단계)"]
    for _, row in r.iterrows():
        prev = "—" if pd.isna(row["직전 대비"]) else _pct(row["직전 대비"])
        lines.append(f"  · {row['단계']} {row['인원']:,}  직전 대비 {prev}")
    lines += ["", "이탈 분류 — 순서가 없으므로 전환율이 아니라 구성비다"]
    for _, row in ctx["churn"].iterrows():
        share = "" if pd.isna(row["구성비(판정 대상 기준)"]) else \
            f"  구성비 {_pct(row['구성비(판정 대상 기준)'])}"
        lines.append(f"  · {row['구분']} {row['인원']:,}명{share}")
    lines += ["", f"분해 — 축은 {ctx['axis']}, 구간은 "
                  f"{config.FUNNEL_STEPS[0]} → {config.FUNNEL_STEPS[1]}, "
                  f"그레인은 지원 1건"]
    for _, row in ctx["decomp"].iterrows():
        if row["사유"]:
            lines.append(f"  · {row['칸']} — 판정하지 않음 ({row['사유']})")
        else:
            lines.append(f"  · {row['칸']} {_pct(row['전환율'])}  "
                         f"비중 {_pct(row['비중'], 0)}  n={int(row['시작']):,}")
    g = ctx.get("gap2")
    if g:
        lines.append(f"  격차가 가장 큰 두 칸: {g['높은 칸']} {_pct(g['높은 값'])} vs "
                     f"{g['낮은 칸']} {_pct(g['낮은 값'])} — "
                     f"{g['격차'] * 100:.1f}%p")
    ss = ctx.get("sum_check")
    if ss:
        lines.append(f"  칸 합 {ss['칸 합']:,} = 전체 {ss['전체']:,} "
                     f"(차이 {ss['차이']:,}, (미분류) {ss['(미분류) 칸']:,})")
    lines += ["", "다른 축으로도 쪼개 봤다 — 격차가 없는 것도 결과다"]
    for _, row in ctx["axis_candidates"].iterrows():
        mark = " ← 이 축을 골랐다" if row["축"] == ctx["axis"] else ""
        lines.append(f"  · {row['축']} 격차 {row['격차(%p)']}%p · "
                     f"{int(row['칸 수'])}칸 · 가장 작은 칸 "
                     f"{int(row['가장 작은 칸']):,}{mark}")
    return "\n".join(lines)


def _s5_compare(ctx) -> str:
    """전후 비교 — 무작위 배정이 없다. 인과를 주장할 수 없다는 문장을 본문 첫 문단에.

    교안의 _s5_experiments() 자리다. 이 도메인에는 A/B 실험이 없으므로
    〖 내 도메인이라면 〗 박스대로 전후 비교 장으로 바꿨다.
    """
    lines = [
        "이 비교는 인과를 주장할 수 없다. 무작위 배정이 없었으므로 다른 요인의 "
        "영향을 배제하지 못한다. 아래는 관측된 차이일 뿐이다.",
        "",
    ]
    for c in ctx["cards"]:
        if c["판정"] == "무효":
            # 못 믿을 조건에 걸린 항목은 사유만 적고 수치를 쓰지 않는다.
            lines.append(f"  · {c['이름']} — 무효. {c['사유']}")
        else:
            lines.append(
                f"  · {c['이름']} — {c['판정']}. "
                f"{c['이전']} → {c['이후']} ({c['변화']}), 표본 {c['표본']:,}"
            )
            if c.get("가드레일"):
                lines.append(f"      가드레일 {c['가드레일']}")
    return "\n".join(lines)


def _s7_limits(ctx) -> str:
    """한계 — 사람이 매번 쓰는 것이 아니라 조립한다.

    1 검증에서 난 경고를 전부 가져온다
    2 못 믿을 조건에 걸려 판정하지 않은 항목
    3 항상 넣는 두 문장
    4 사람이 직접 적은 것 (코드가 모르는 것)
    """
    lines = []

    warns = validate.warnings(ctx["checks"])
    if warns:
        lines.append("검증에서 난 경고")
        for w in warns:
            lines.append(f"  · {w['message']}"
                         + (f" — {w['detail']}" if w["detail"] else ""))
    else:
        lines.append(f"검증 {len(ctx['checks'])}건 전부 통과. 경고 없음.")

    hidden = [c for c in ctx["cards"] if c["판정"] == "무효"]
    hidden += [{"이름": f"{ctx['axis']} · {r['칸']}", "사유": r["사유"]}
               for _, r in ctx["decomp"].iterrows() if r["사유"]]
    hidden += [{"이름": f"코호트 {r['코호트']}", "사유": r["못 믿을 사유"]}
               for _, r in ctx["cohort"].iterrows() if r["못 믿을 사유"]]
    lines += ["", f"판정하지 않은 것 ({len(hidden)}건) — 값이 없는 것이 아니라 "
                  f"믿을 수 없어 계산하지 않았다"]
    for h in hidden:
        lines.append(f"  · {h['이름']} — {h['사유']}")

    lines += [
        "",
        "항상 적는 것",
        "  · 관측 데이터이므로 인과를 주장할 수 없다. 무작위 배정이 없었다.",
        f"  · 관측 기간이 {config.PERIOD[0]} ~ {config.PERIOD[1]}이므로 "
        f"그보다 긴 주기의 변화는 관측되지 않는다.",
    ]

    manual = ctx.get("limits_manual", "").strip()
    lines += ["", "코드가 모르는 것 — 사람이 적는다"]
    lines.append(("  " + manual.replace("\n", "\n  ")) if manual
                 else f"  {NOT_WRITTEN}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# 조립
# ══════════════════════════════════════════════════════════════════════════
AUTO_SECTIONS = {
    "1. 요약": _s1_summary,
    "3. 방법": _s3_method,
    "4. 결과": _s4_results,
    "5. 전후 비교": _s5_compare,
    "7. 한계": _s7_limits,
}

ORDER = ["1. 요약", "2. 배경", "3. 방법", "4. 결과",
         "5. 전후 비교", "6. 해석", "7. 한계", "8. 제안"]

HUMAN_SECTIONS = {"2. 배경": "왜 이 분석을 했는가. 어떤 결정을 앞두고 있는가",
                  "6. 해석": "숫자가 무엇을 뜻하는가",
                  "8. 제안": "무엇을 할 것인가, 무엇을 하지 않을 것인가"}


def build(ctx, human=None, inject=None) -> dict:
    """여덟 장을 조립한다. 사람이 안 쓴 장은 비운다 — 자동으로 채우지 않는다."""
    human = human if human is not None else load_human()
    out = {}
    for title in ORDER:
        if title in AUTO_SECTIONS:
            out[title] = AUTO_SECTIONS[title](ctx)
        else:
            out[title] = (human.get(title) or "").strip() or NOT_WRITTEN
    if inject:
        for title, extra in inject.items():
            out[title] = out.get(title, "") + "\n" + extra
    return out


def empty_human(sections: dict) -> list[str]:
    return [t for t in HUMAN_SECTIONS if sections.get(t, NOT_WRITTEN) == NOT_WRITTEN]
