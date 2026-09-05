# -*- coding: utf-8 -*-
"""Day3 실습 B·C 확인.

만든 것과 동작하는 것은 다르다. 화요일에 깨진 파일을 넣어본 것과 같은 이유로,
오늘 만든 "감추기"와 "판정 순서"도 실제로 도는지 본다.

  1 걸린 항목에 사유가 뜬다
  2 걸린 항목에 지표 값이 안 보인다     ← 가장 중요
  3 판정 순서가 코드로 박혀 있다 (주지표가 좋아도 가드레일을 본다)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config, context, loader, metrics, verdict  # noqa: E402


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def main():
    t = load()
    ctx = context.build(t)
    ok = True

    print("\n[1] 못 믿을 조건에 걸린 항목")
    hid_cards = [c for c in ctx["cards"] if c["판정"] == "무효"]
    hid_coh = ctx["cohort"][ctx["cohort"]["못 믿을 사유"].notna()]
    hid_cell = ctx["decomp"][ctx["decomp"]["사유"].notna()]
    print(f"  판정 카드 {len(hid_cards)}건 · 코호트 {len(hid_coh)}개 · "
          f"분해 칸 {len(hid_cell)}칸")
    for c in hid_cards:
        print(f"    · {c['이름']} — {c['사유']}")
    for _, r in hid_coh.iterrows():
        print(f"    · 코호트 {r['코호트']} — {r['못 믿을 사유']}")

    print("\n[2] 걸린 항목에 값이 남아 있는가")
    for c in hid_cards:
        bad = [k for k in ("이전", "이후", "변화", "가드레일") if c[k] is not None]
        print(f"  {'없음' if not bad else '남아있음'}  {c['이름']}"
              + (f"  → {bad}" if bad else ""))
        ok &= not bad
    for _, r in hid_coh.iterrows():
        # 화면은 cohort_bar 에서 표시값을 None 으로 만든다
        print(f"  없음  코호트 {r['코호트']} — 차트에 표시값을 그리지 않는다")

    print("\n[3] 판정 순서 — 일부러 넣어 본다")
    base_g = {"월 지원 건수": 2.00, "직무 적합도": 0.520}
    cases = [
        ("표본 부족 → 무효",
         dict(sample=12, obs_days=200, before=.50, after=.70,
              guards=base_g, base_guards=base_g), "무효"),
        ("관측 부족 → 무효",
         dict(sample=200, obs_days=30, before=.50, after=.70,
              guards=base_g, base_guards=base_g), "무효"),
        ("배정 불공정 → 무효",
         dict(sample=200, obs_days=200, before=.50, after=.70,
              guards=base_g, base_guards=base_g,
              fairness="두 기간 사이에 제도가 바뀌었다"), "무효"),
        ("변화 작다 → 효과 없음",
         dict(sample=200, obs_days=200, before=.50, after=.52,
              guards=base_g, base_guards=base_g), "효과 없음"),
        ("주지표 개선 + 가드레일 악화 → 주의 필요",
         dict(sample=200, obs_days=200, before=.50, after=.70,
              guards={"월 지원 건수": 1.40, "직무 적합도": 0.520},
              base_guards=base_g), "주의 필요"),
        ("가드레일 없음 → 주의 필요",
         dict(sample=200, obs_days=200, before=.50, after=.70,
              guards=None, base_guards=base_g), "주의 필요"),
        ("주지표 개선 + 가드레일 정상 → 성공",
         dict(sample=200, obs_days=200, before=.50, after=.70,
              guards=base_g, base_guards=base_g), "성공"),
    ]
    for label, kw, want in cases:
        got = verdict.judge(label, **kw)
        hit = got["판정"] == want
        ok &= hit
        extra = "" if got["이전"] else "  (값 없음)"
        print(f"  {'맞음' if hit else '틀림':<4} {label:<34} → {got['판정']}{extra}")

    print("\n[4] 팬아웃 가드 — 붙이다 행이 늘면 멈추는가")
    import pandas as pd
    left = pd.DataFrame({"k": ["a", "b", "c"], "v": [1, 2, 3]})
    ok_right = pd.DataFrame({"k": ["a", "b", "c"], "w": [10, 20, 30]})
    bad_right = pd.DataFrame({"k": ["a", "a", "b", "c"], "w": [10, 11, 20, 30]})
    try:
        n = len(metrics.merge_1to1(left, ok_right, "k"))
        print(f"  통과   1:1 조인 3행 → {n}행")
        ok &= (n == 3)
    except ValueError as e:
        print(f"  오탐   {e}")
        ok = False
    try:
        metrics.merge_1to1(left, bad_right, "k")
        print("  놓침   행이 늘었는데 그냥 통과했다")
        ok = False
    except ValueError as e:
        print(f"  잡음   {e}")

    print("\n[5] 분해 합계가 전체와 맞는가")
    ss = context.sum_check(ctx)
    print(f"  칸 합 {ss['칸 합']:,} · 전체 {ss['전체']:,} · 차이 {ss['차이']:,}")
    ok &= (ss["차이"] == 0)

    print("\n" + ("감추기와 판정 순서가 실제로 동작한다" if ok else "기대와 다르다"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
