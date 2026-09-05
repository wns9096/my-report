# -*- coding: utf-8 -*-
"""배포본에서 깨뜨려 보는 자리가 실제로 동작하는가.

day1_break.py 는 data/ 의 파일을 직접 바꿔치기해서 확인한다.
그건 내 컴퓨터에서만 할 수 있다 — 배포된 앱을 여는 사람은 못 한다.

그래서 화면 안에 «깨뜨려 보기» 버튼을 넣었고, 여기서는 그 버튼을
실제로 눌러 확인한다. 버튼을 넣어 놓고 안 눌러 보면
day1_break.py 를 만들어 놓고 안 돌리는 것과 같다.

  1 버튼을 누르면 차단이 뜨고 통과 버튼이 잠긴다
  2 «원본으로 되돌리기»를 누르면 풀린다
  3 시험용 데이터는 원본 파일을 건드리지 않는다   ← 가장 중요
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config  # noqa: E402
from checks.day1_break import CARD_BLOCK  # noqa: E402
from checks.ui_smoke import run  # noqa: E402

# 화면의 버튼 라벨과, 눌렀을 때 기대하는 것
CASES = [
    ("필수 컬럼을 지운다", "차단"),
    ("날짜를 1년 옮긴다", "차단"),
    ("행을 50개로 줄인다", "차단"),
    ("같은 키에 다른 값을 넣는다", "차단"),
]


def _state(at):
    """차단 카드 수와 통과 버튼 상태를 읽는다."""
    ta = [t for t in at.text_area if t.key == "g1_reason"]
    if ta and not ta[0].value:
        ta[0].set_value("자동 점검")
        at.run()
    cards = len([1 for m in at.markdown if str(m.value).strip() == CARD_BLOCK])
    btn = [b for b in at.button if b.label == "통과시키기"]
    return cards, ("잠김" if (btn and btn[0].disabled) else
                   "눌림 가능" if btn else "없음")


def _fingerprint():
    """data/ 파일들의 (크기·수정시각) 지문. 시험용이 원본을 건드리면 바뀐다."""
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                  for p in config.DATA.glob("*") if p.is_file())


def main():
    before = _fingerprint()
    ok = True

    at = run("실행")
    if at.exception:
        print(f"  실행 화면이 열리지 않는다: {at.exception[0].value}")
        return 1
    base_cards, base_btn = _state(at)
    print(f"\n[0] 원본 — 차단 {base_cards} · 통과 버튼 {base_btn}")
    ok &= (base_cards == 0 and base_btn == "눌림 가능")

    print("\n[1] 화면의 버튼을 실제로 누른다")
    for label, expect in CASES:
        at = run("실행")
        # 「넣어 보기」 버튼은 카드마다 하나씩이라 라벨이 같다. 순서로 찾는다.
        idx = [i for i, (lb, _) in enumerate(CASES) if lb == label][0]
        target = [b for b in at.button if b.key == f"brk_{idx}"]
        if not target:
            print(f"  없음   {label:<22} 버튼을 못 찾았다")
            ok = False
            continue
        target[0].click()
        at.run()
        cards, btn = _state(at)
        hit = (cards >= 1 and btn == "잠김") if expect == "차단" else True
        ok &= hit
        print(f"  {'맞음' if hit else '틀림':<4} {label:<22} → 차단 카드 {cards} · "
              f"통과 버튼 {btn}")

        # 되돌리기
        undo = [b for b in at.button if b.key == "undo_break"]
        if undo:
            undo[0].click()
            at.run()
            c2, b2 = _state(at)
            back = (c2 == 0 and b2 == "눌림 가능")
            ok &= back
            print(f"  {'맞음' if back else '틀림':<4} {'  ↳ 되돌리면':<22} → 차단 카드 "
                  f"{c2} · 통과 버튼 {b2}")
        else:
            print("  틀림   ↳ 되돌리기 버튼이 없다")
            ok = False

    print("\n[2] 원본 파일이 그대로인가 — 시험용은 세션에만 있어야 한다")
    after = _fingerprint()
    same = before == after
    ok &= same
    print(f"  {'맞음' if same else '틀림':<4} data/ 파일 {len(after)}개의 "
          f"크기·수정시각이 {'그대로다' if same else '바뀌었다'}")

    print("\n" + ("배포본에서도 깨뜨려 볼 수 있고, 원본은 안 바뀐다"
                  if ok else "기대와 다르다"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
