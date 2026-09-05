# -*- coding: utf-8 -*-
"""Day4 실습 B — 검사를 만들고, 일부러 걸려 봅니다.

  1 경고가 뜬다
  2 어떤 단어가 걸렸는지 보인다   ← 이게 있어야 고칠 수 있다
  3 되돌리면 경고가 사라진다

사람이 쓴 장에도 건다. 거기가 더 자주 틀린다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config, context, loader  # noqa: E402
from report import sections as S  # noqa: E402

PLANT_AUTO = "\n모바일 지원 화면이 불편하기 때문에 완료율이 낮다."
PLANT_HUMAN = "학력 격차 덕분에 서류 통과율이 올랐음이 입증되었다."


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def report(label, hits):
    print(f"  {label}: {len(hits)}건")
    for h in hits:
        print(f"      · {h['장']}  «{h['단어']}»  → 대신: {h['대신']}")
        print(f"        {h['문맥']}")
    return hits


def main():
    ctx = context.build(load())
    ok = True

    print("\n[0] 손대지 않은 상태")
    base = S.build(ctx, human={})
    h0 = report("걸린 표현", S.check_phrasing(base))
    ok &= (len(h0) == 0)

    print("\n[1] 자동 생성 장에 일부러 넣는다")
    planted = S.build(ctx, human={}, inject={"4. 결과": PLANT_AUTO})
    h1 = report("걸린 표현", S.check_phrasing(planted))
    ok &= any(h["장"] == "4. 결과" for h in h1)

    print("\n[2] 사람이 쓴 장에도 넣는다 — 여기가 더 자주 틀린다")
    planted2 = S.build(ctx, human={"6. 해석": PLANT_HUMAN})
    h2 = report("걸린 표현", S.check_phrasing(planted2))
    ok &= any(h["장"] == "6. 해석" for h in h2)

    print("\n[3] 오탐 확인 — 멀쩡한 문장을 잡으면 사람이 검사를 끈다")
    # 처음에는 "인해"를 부분 문자열로 찾아서 "확**인해**야 한다"가 걸렸다.
    # 검사가 멀쩡한 문장을 잡으면 사람이 검사를 끄기 시작한다.
    ok_cases = ["다음 분기에 확인해야 한다", "재확인해 두었다",
                "기여도가 가장 큰 칸이다", "표본이 적어 확인하지 못했다"]
    ng_cases = ["제도 변경으로 인해 값이 달라졌다", "이로 인해 분모가 줄었다",
                "경쟁이 낮기 때문에 잘 통과한다", "효과가 입증되었다"]
    for c in ok_cases:
        h = S.check_phrasing({"t": c})
        print(f"  {'통과' if not h else '오탐':<4} {c}")
        ok &= not h
    for c in ng_cases:
        h = S.check_phrasing({"t": c})
        print(f"  {'잡음' if h else '놓침':<4} {c}  → {[x['단어'] for x in h]}")
        ok &= bool(h)

    print("\n[4] 되돌린다")
    h3 = report("걸린 표현", S.check_phrasing(S.build(ctx, human={})))
    ok &= (len(h3) == 0)

    print("\n" + ("자동 장과 사람 장 양쪽에서 잡히고, 되돌리면 사라진다"
                  if ok else "기대와 다르다 — check_phrasing 이 그 장에 안 걸려 있다"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
