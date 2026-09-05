# -*- coding: utf-8 -*-
"""화~금 4일치 확인을 한 번에 돌린다."""
import subprocess
import sys
from pathlib import Path

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
