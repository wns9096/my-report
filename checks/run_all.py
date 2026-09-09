# -*- coding: utf-8 -*-
"""8주차 나흘치 + 9주차 확인을 한 번에 돌린다.

문서는 손으로 쓴다. 손으로 쓴 숫자는 반드시 어긋난다 —
그래서 문서도 검사 대상이다.
"""
import subprocess
import sys
from pathlib import Path

# 출력이 한글이다. cp949 콘솔(예: cmd.exe)에서 그대로 찍으면
# UnicodeEncodeError 로 죽는다 — 검사가 아니고 출력이 이유로 죽는 것은
# 맨 머리에서 막는다. 사람이 결과를 볼 수 없으면 검사를 돌린 것이 아니다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    ("Day1 실습 E — 깨뜨려 보기 (차단·버튼 잠김)", "checks/day1_break.py"),
    ("Day1 — 배포본에서 깨뜨려 보기 (화면 버튼)", "checks/sandbox_break.py"),
    ("Day2 실습 B — 손계산 대조", "checks/day2_crosscheck.py"),
    ("Day3 실습 B·C — 감추기와 판정 순서", "checks/day3_trust.py"),
    ("Day4 실습 B — 인과 표현 검사", "checks/day4_phrasing.py"),
    ("게이트 1·2·3 통과 + PDF", "checks/run_gates.py"),
    ("4개 화면이 열리는가", "checks/ui_smoke.py"),
    ("앱점검 — 나흘치 규칙을 앱이 지키는가", "checks/app_audit.py"),
    ("9주차 Day1 — 발견.md 의 숫자가 조회값과 같은가", "checks/w9d1_verify.py"),
    ("9주차 Day2 — 제안서의 자동/사람 분리와 카드 대조", "checks/w9d2_proposal.py"),
]


def main():
    bad = []
    for label, script in STEPS:
        r = subprocess.run([sys.executable, script], cwd=ROOT,
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
