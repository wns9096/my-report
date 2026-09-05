# -*- coding: utf-8 -*-
"""Day2 실습 B — 손계산 대조.

7주차에 손으로(그리고 별도 스크립트로) 구한 값이 mydomain/config.py 의
BASELINE 에 남아 있다. 앱이 낸 값과 그대로 비교한다.
대조할 값이 있으면 표본을 다시 셀 필요가 없다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import config, context, loader, metrics  # noqa: E402

# 손계산 값의 원본은 core/config.py 하나다.
# 화면(게이트 2)과 이 스크립트가 각자 숫자를 들고 있으면 대조가 아니라
# 서로 다른 두 주장이 된다.
HAND = config.HAND_BASELINE


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def line(label, hand, app, tol=0.0):
    ok = (abs(hand - app) <= tol) if isinstance(hand, float) else (hand == app)
    print(f"  {'일치' if ok else '불일치':<4} {label:<22} 손계산 {hand!s:>12}   앱 {app!s:>12}")
    return ok


def main():
    t = load()
    all_ok = True

    print("\n[1] 획득 퍼널 — 건 기준")
    app_cnt = metrics.funnel(t, "application")["인원"].tolist()
    all_ok &= line("단계별 인원", HAND["퍼널_건"], app_cnt)

    print("\n[2] 획득 퍼널 — 사람 기준 (내가 정한 그레인)")
    app_per = metrics.funnel(t, "person")["인원"].tolist()
    all_ok &= line("단계별 인원", HAND["퍼널_사람"], app_per)

    print("\n[3] 세 값만 뽑기 (교안 프롬프트 2)")
    f = metrics.funnel(t, "person")
    lo = f.iloc[1:]["직전 대비"].astype(float).idxmin()
    print(f"  첫 단계 인원        {f.iloc[0]['인원']:,}명")
    print(f"  가장 낮은 구간      {f.iloc[lo-1]['단계']} → {f.iloc[lo]['단계']}"
          f"  {f.iloc[lo]['직전 대비']:.2%}")
    print(f"  최종 누적 전환율    {f.iloc[-1]['누적']:.2%}")

    print("\n[4] 주지표")
    k = metrics.kpis(t)
    all_ok &= line("서류 통과율", HAND["서류_통과율"], round(k["서류 통과율"]["값"], 4), config.HAND_TOL)

    print("\n[5] 이탈 분류")
    split, judged, pending = metrics.churn_split(t)
    d = dict(zip(split["구분"], split["인원"]))
    all_ok &= line("판정 대상", HAND["판정대상"], judged)
    all_ok &= line("성공 종료", HAND["성공종료"], int(d.get("성공 종료", 0)))
    all_ok &= line("이탈률", HAND["이탈률"],
                   round(int(d.get("이탈", 0)) / judged, 3), 0.0015)

    print("\n[6] 순서 판정 — 과제·테스트를 단계로 두면")
    raw5 = ["지원", "서류 통과", "과제·테스트 통과", "면접 통과", "최종 합격"]
    ov = metrics.order_violation(t, raw5, "application")
    skip = int(ov.loc[ov["구간"].str.startswith("과제"), "앞 단계 미경유"].iloc[0])
    all_ok &= line("과제 미경유", HAND["순서위반_RAW5"], skip)

    print("\n[7] 재현성 — 같은 데이터로 두 번 계산 (부록 A)")
    all_ok &= line("두 번 돌린 결과", app_per, metrics.funnel(load(), "person")["인원"].tolist())

    # ── 부록 A. 대조할 값이 아예 없을 때 쓰는 셋 ─────────────────────────
    # 손계산 값이 있어도 같이 돌린다. 1분이면 되고, 안 하는 것보다 훨씬 낫다.
    print("\n[8] 자릿수 확인 — 3%인가 30%인가")
    cum = float(f.iloc[-1]["누적"])
    digits_ok = 0.05 <= cum <= 0.60
    print(f"  {'맞음' if digits_ok else '이상':<4} 사람 기준 누적 {cum:.2%} "
          f"— 사람이 여러 번 지원하므로 건 기준(2.38%)보다 한 자릿수 크다")
    all_ok &= digits_ok

    print("\n[9] 합계 확인 — 분해 칸의 합이 전체와 같은가")
    ctx = context.build(t)
    ss = context.sum_check(ctx)
    all_ok &= line(f"칸 합 ({ss['그레인']})", ss["전체"], ss["칸 합"])

    print("\n[10] 양 끝 확인 — 첫 단계가 전체이고 마지막이 가장 적은가")
    ends_ok = (int(f.iloc[0]["인원"]) == len(t["applicants"])
               and f["인원"].is_monotonic_decreasing)
    print(f"  {'맞음' if ends_ok else '이상':<4} 첫 {int(f.iloc[0]['인원']):,} "
          f"= 지원자 표 {len(t['applicants']):,} · "
          f"단계마다 줄어듦 {bool(f['인원'].is_monotonic_decreasing)}")
    all_ok &= ends_ok

    print("\n[11] 두 그레인이 같은 값을 낼 수 없는 자리인가")
    gapdf = metrics.funnel_gap(t)
    diff = (gapdf["건"] / gapdf["사람"]).round(2).tolist()
    print(f"  건/사람 배수 {diff} — 앞 단계일수록 크다. "
          f"한 사람이 여러 건을 넣기 때문에 나오는 모양이다")

    print("\n" + ("전부 일치" if all_ok else "불일치 있음 — 그레인 → 분모 → 필터 → 기간 순으로 확인"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
