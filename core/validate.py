# -*- coding: utf-8 -*-
"""검증층 — Day1 실습 D.

규칙을 하나 만들 때마다 묻는 것은 하나다:
  이 규칙이 깨진 채로 계산하면 값이 틀리는가?
    틀린다              → block (차단)
    해석만 조심하면 된다 → warn  (경고)

검증은 많을수록 좋은 것이 아니라 지켜지는 만큼만 있는 것이 좋다.
그래서 **차단 규칙은 셋**만 만든다 — 행 수 · 필수 컬럼 · 날짜 범위.
실습 F 에서 참고 12건 중 둘(키 중복 · 결측률)을 경고 전용으로 더 켰다.
경고는 앱을 멈추지 않으므로 사람이 끄게 만들지 않는다.
나머지 참고 함수는 파일 아래쪽에 호출되지 않는 채로 둔다.
"""
import pandas as pd

from core import config

# 이 컬럼이 없으면 어떤 비율도 못 낸다.
REQUIRED = {
    "applications":       ["application_id", "applicant_id", "applied_date"],
    "application_events": ["application_id", "applicant_id", "stage", "event_date"],
    "applicants":         ["applicant_id", "start_date"],
    "postings":           ["posting_id"],
}

# 규칙 1 임계값 — 근거는 아래 run_checks 의 주석에 있다.
MIN_ROWS = 200

# 규칙 3 임계값 — 기간 밖 행이 이 비율을 넘으면 파일 자체를 의심한다.
OUT_OF_PERIOD_BLOCK = 0.20

# 실습 F 추가 — 결측률 경고 하한. 차단하지 않는다.
MISSING_WARN = 0.05


def _r(name, level, message, detail=""):
    """검증 결과 한 건. level 은 ok | warn | block."""
    return {"name": name, "level": level, "message": message, "detail": detail}


def run_checks(tables):
    """차단 규칙 3건 + 경고 2건. 메시지에는 반드시 실제 숫자를 넣는다.

    "행 수 부족"은 판단 재료가 아니다. "12행 (최소 200)"이어야 한다.
    얼마나 모자란지가 보여야 대응이 갈린다 — 12행이면 파일이 잘못 온 것이고,
    198행이면 아직 덜 쌓인 것이다.
    """
    out = []
    lo, hi = pd.Timestamp(config.PERIOD[0]), pd.Timestamp(config.PERIOD[1])

    # ── 규칙 1. 행 수 ─────────────────────────────────────────────────────
    # 200행 미만이면 차단.
    # 근거: 분해 화면에서 한 칸의 최소 표본을 30으로 잡았고(config.MIN_SAMPLE),
    #       쓸 만한 축은 6칸 안팎으로 갈린다. 30 × 6 = 180 → 200.
    #       이보다 적으면 쪼개는 순간 전부 "표본 부족"이 되어 분해를 할 이유가 없다.
    for name in ("applications", "application_events"):
        df = tables.get(name)
        if df is None:
            out.append(_r(f"행 수 · {name}", "block",
                          f"{name} 테이블이 없음", "TABLES 에 적힌 이름과 파일명을 맞춘다"))
            continue
        n = len(df)
        if n < MIN_ROWS:
            out.append(_r(f"행 수 · {name}", "block",
                          f"{name} {n:,}행 (최소 {MIN_ROWS:,})",
                          "쪼개면 모든 칸이 최소 표본 30 미만이 된다"))
        else:
            out.append(_r(f"행 수 · {name}", "ok",
                          f"{name} {n:,}행 (최소 {MIN_ROWS:,})"))

    # ── 규칙 2. 필수 컬럼 ─────────────────────────────────────────────────
    # 없으면 차단.
    # 근거: 식별자나 날짜가 빠지면 퍼널 단계를 이을 수 없다. 비율의 분모가
    #       사라지므로 "조심해서 해석"할 여지가 없다. 계산 자체가 불가능하다.
    for name, cols in REQUIRED.items():
        df = tables.get(name)
        if df is None:
            continue
        miss = [c for c in cols if c not in df.columns]
        if miss:
            out.append(_r(f"필수 컬럼 · {name}", "block",
                          f"{name} 에 {len(miss)}개 없음: {', '.join(miss)}",
                          f"있는 컬럼: {', '.join(map(str, df.columns))}"))
        else:
            out.append(_r(f"필수 컬럼 · {name}", "ok",
                          f"{name} 필수 {len(cols)}개 모두 있음"))

    # ── 규칙 3. 날짜 범위 ─────────────────────────────────────────────────
    # 기간 밖이 20%를 넘으면 차단, 그 이하면 경고.
    # 근거: 몇 건이면 그 행만 빼고 진행하면 된다 → 경고.
    #       다섯 중 하나가 밖이면 파일이 잘못 온 것이다. 분모를 믿을 수 없으므로
    #       그 행만 빼는 대응이 성립하지 않는다 → 차단.
    for name, col in (("applications", "applied_date"),
                      ("application_events", "event_date"),
                      ("applicants", "start_date")):
        df = tables.get(name)
        if df is None or col not in df.columns:
            continue
        s = pd.to_datetime(df[col], errors="coerce")
        n = int(s.notna().sum())
        if n == 0:
            out.append(_r(f"날짜 범위 · {name}", "block",
                          f"{name}.{col} 에 읽히는 날짜가 0건", "형식이 날짜가 아니다"))
            continue
        out_n = int(((s < lo) | (s > hi)).sum())
        ratio = out_n / n
        span = f"{s.min():%Y-%m-%d} ~ {s.max():%Y-%m-%d}"
        base = (f"{name}.{col} 기간 밖 {out_n:,}건 / {n:,}건 ({ratio:.1%}) · "
                f"실제 {span} · 기준 {config.PERIOD[0]} ~ {config.PERIOD[1]}")
        if ratio > OUT_OF_PERIOD_BLOCK:
            out.append(_r(f"날짜 범위 · {name}", "block", base,
                          f"기간 밖 비율이 {OUT_OF_PERIOD_BLOCK:.0%}를 넘는다. 파일이 잘못 왔을 수 있다"))
        elif out_n:
            out.append(_r(f"날짜 범위 · {name}", "warn", base,
                          "해당 행을 빼고 계산한다. 분모가 그만큼 줄어든다"))
        else:
            out.append(_r(f"날짜 범위 · {name}", "ok", base))

    # ── 실습 F 추가 — 키 중복 (경고) ──────────────────────────────────────
    # 교안 부록 A 는 "키 중복"을 차단 쪽 예로 든다. 여기서는 경고로 낮췄다.
    # 근거: 중복 행이 서로 값이 다르면 어느 쪽을 쓸지 정할 수 없다 → 차단.
    #       값이 완전히 같으면 고유값으로 세는 순간 사라진다 → 경고.
    #       그래서 "같은 행인가"를 실제로 확인하고 판정을 나눈다.
    #       몇 건인지는 알고 있어야 한다. 원본 행 수와 퍼널 첫 단계가 어긋나는 이유다.
    for name, key in (("applications", "application_id"),
                      ("applicants", "applicant_id"),
                      ("postings", "posting_id")):
        df = tables.get(name)
        if df is None or key not in df.columns:
            continue
        dup = int(len(df) - df[key].nunique())
        if not dup:
            continue
        same = bool(df[df[key].duplicated(keep=False)]
                    .groupby(key, observed=True)
                    .apply(lambda g: g.drop_duplicates().shape[0] == 1,
                           include_groups=False).all())
        lvl = "warn" if same else "block"
        out.append(_r(
            f"키 중복 · {name}.{key}", lvl,
            f"{name}.{key} 중복 {dup:,}건 / {len(df):,}행 "
            f"(고유 {df[key].nunique():,}) · 중복 행의 값은 "
            f"{'완전히 같다' if same else '서로 다르다'}",
            "고유값으로 세면 사라진다. 원본 행 수와 퍼널 첫 단계가 어긋나는 이유다"
            if same else "어느 행을 쓸지 정할 수 없다. 계산이 틀린다"))

    # ── 실습 F 추가 — 결측률 (경고) ───────────────────────────────────────
    # 참고 12건에서 하나를 켰다. 규칙은 여전히 셋이고 이것은 경고 전용이다.
    # 근거: 5% 이상 비면 그 컬럼으로 쪼갤 때 (미분류) 칸이 생긴다. 분해 합계가
    #       전체와 안 맞는 이유가 되므로 몇 건인지 알고 있어야 한다.
    #       채우지는 않는다 — 구조적 결측을 채우면 위조다.
    for name, df in tables.items():
        for c in df.columns:
            rate = float(df[c].isna().mean())
            if rate >= MISSING_WARN:
                out.append(_r(f"결측률 · {name}.{c}", "warn",
                              f"{name}.{c} 결측 {rate:.1%} "
                              f"({int(df[c].isna().sum()):,}건 / {len(df):,}행)",
                              "구조적 결측일 수 있다. 채우지 않고 (미분류) 칸으로 남긴다"))

    return out


def counts(results):
    c = {"ok": 0, "warn": 0, "block": 0}
    for r in results:
        c[r["level"]] = c.get(r["level"], 0) + 1
    return c


def blocked(results):
    return any(r["level"] == "block" for r in results)


def warnings(results):
    return [r for r in results if r["level"] == "warn"]


# ══════════════════════════════════════════════════════════════════════════
# 참고용 — 호출되지 않는다. 내 데이터에 맞는 것만 골라 run_checks 로 옮겨 쓴다.
# 7주차에 화면으로 본 12건이다. 지금은 3건만 켜 두었다.
# ══════════════════════════════════════════════════════════════════════════
def _ref_missing_rate(tables, col_thresh=0.30):
    """결측률이 임계 이상인 컬럼을 경고로. 구조적 결측이면 채우지 않는다."""
    out = []
    for name, df in tables.items():
        for c in df.columns:
            rate = df[c].isna().mean()
            if rate >= col_thresh:
                out.append(_r(f"결측률 · {name}.{c}", "warn",
                              f"{name}.{c} 결측 {rate:.1%} ({int(df[c].isna().sum()):,}건)",
                              "구조적 결측이면 채우지 않는다. 채우면 위조다"))
    return out


def _ref_duplicate_key(tables, name, key):
    df = tables.get(name)
    if df is None or key not in df.columns:
        return []
    dup = int(len(df) - df[key].nunique())
    lv = "block" if dup else "ok"
    return [_r(f"키 중복 · {name}.{key}", lv,
               f"{name}.{key} 중복 {dup:,}건 / {len(df):,}행")]


def _ref_fanout(tables, left, right, key):
    """한 대상에 행이 여럿인 표를 그냥 붙이면 대상이 복제된다."""
    l, r = tables.get(left), tables.get(right)
    if l is None or r is None or key not in l.columns or key not in r.columns:
        return []
    grown = len(l.merge(r[[key]], on=key, how="left")) - len(l)
    lv = "block" if grown else "ok"
    return [_r(f"조인 안전성 · {left}×{right}", lv,
               f"조인하면 {len(l):,}행 → {len(l) + grown:,}행 (+{grown:,})",
               "집계하지 않고 붙이면 평균이 조용히 왜곡된다")]


def _ref_order_violation(tables, before, after):
    """뒤 단계가 앞 단계보다 먼저 일어난 건. 순서가 역행하면 차단."""
    ev = tables.get("application_events")
    if ev is None:
        return []
    p = ev.pivot_table(index="application_id", columns="stage",
                       values="event_date", aggfunc="min")
    if before not in p.columns or after not in p.columns:
        return []
    bad = int((p[after] < p[before]).sum())
    lv = "block" if bad else "ok"
    return [_r(f"순서 · {before}→{after}", lv, f"역행 {bad:,}건")]
