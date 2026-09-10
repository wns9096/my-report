# -*- coding: utf-8 -*-
"""8주차 나흘치 + 9주차 확인을 한 번에 돌린다.

문서는 손으로 쓴다. 손으로 쓴 숫자는 반드시 어긋난다 —
그래서 문서도 검사 대상이다.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

STEPS = [
    ("Day1 실습 E — 깨뜨려 보기 (차단·버튼 잠김)", "checks/day1_break.py"),
    ("Day1 — 배포본에서 깨뜨려 보기 (화면 버튼)", "checks/sandbox_break.py"),
    ("Day2 실습 B — 손계산 대조", "checks/day2_crosscheck.py"),
    ("Day3 실습 B·C — 감추기와 판정 순서", "checks/day3_trust.py"),
    ("Day4 실습 B — 인과 표현 검사", "checks/day4_phrasing.py"),
    ("게이트 1·2·3 통과 + PDF", "checks/run_gates.py"),
    ("화면 다섯이 열리는가", "checks/ui_smoke.py"),
    ("앱점검 — 나흘치 규칙을 앱이 지키는가", "checks/app_audit.py"),
    ("9주차 Day1 — 발견.md 의 숫자가 조회값과 같은가", "checks/w9d1_verify.py"),
    # Day2 의 w9d2_proposal.py 를 여기로 옮겼다. 규칙이 사라진 것이 아니라
    # 자동/사람 분리·카드 대조를 그대로 안고 Day3 의 검사가 더 붙은 것이다.
    ("9주차 Day3 — 제안서 자가 검사 (자동/사람 · 카드 대조 · 결정 줄)",
     "checks/w9d3_proposal.py"),
]


def unguarded():
    """출력을 안 지키는 검사 스크립트를 찾는다.

    검사를 돌리기 전에 먼저 본다. 새로 만든 스크립트가 이 한 줄을 빠뜨리면
    cp949 콘솔에서 «검사 실패»로 보이는데, 실은 검사가 아니라 print 가
    죽은 것이다. 그 자리를 두 번 헤맸으므로 사람이 기억하지 않게 만든다.
    """
    return [s for _, s in STEPS
            if "use_utf8" not in (ROOT / s).read_text(encoding="utf-8")]


def main():
    bare = unguarded()
    if bare:
        print("[걸림] 출력을 안 지키는 검사 — " + " · ".join(bare))
        print("       checks/_console.py 의 use_utf8() 을 맨 앞에서 부른다.")
        return 1

    # ★ 자식의 출력 인코딩도 cp949 다. 부모가 utf-8 로 «읽는» 것만으로는
    #   모자라고, 자식이 utf-8 로 «쓰게» 해야 한다. 스크립트 안의 use_utf8()
    #   와 겹치지만 겹치는 편이 낫다 — 둘 중 하나만으로는 한쪽 경로가 뚫린다.
    env = dict(os.environ, PYTHONIOENCODING="utf-8:replace")

    bad = []
    for label, script in STEPS:
        r = subprocess.run([sys.executable, script], cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        mark = "통과" if r.returncode == 0 else "실패"
        print(f"[{mark}] {label}")
        if r.returncode != 0:
            bad.append(label)
            print((r.stdout or "")[-1500:])
            print((r.stderr or "")[-800:])
    print("\n" + (f"{len(STEPS)}건 전부 통과" if not bad else f"실패 {len(bad)}건"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
