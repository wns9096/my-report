# -*- coding: utf-8 -*-
"""4개 화면이 실제로 열리는지, 게이트 버튼이 실제로 눌리는지 확인한다.

streamlit.testing.v1.AppTest 는 실제 Streamlit 런타임으로 app.py 를 실행한다.
직접 만든 가짜 객체가 아니라 진짜 렌더 트리를 돌려준다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402


# 메뉴 이름 → 실제 스크립트. st.navigation 을 쓰면 파일 이름과 메뉴 이름이
# 따로 논다 — 그게 목적이다. 대신 전환은 파일 경로로 한다.
SCREENS = {
    "실행": "screens/1_run.py",
    "대시보드": "screens/2_dashboard.py",
    "리포트": "screens/3_report.py",
    "아카이브": "screens/4_archive.py",
}


def run(screen=None, timeout=120):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=timeout)
    at.run()
    if screen and screen != "실행":
        at.switch_page(SCREENS[screen])
        at.run()
    return at


def main():
    fails = []
    for screen in SCREENS:
        at = run(screen)
        ok = not at.exception
        print(f"  {'열림' if ok else '에러':<4} {screen:<8} "
              f"elements={len(at.markdown) + len(at.dataframe) + len(at.button)}")
        if not ok:
            fails.append((screen, at.exception[0].value))
    for s, e in fails:
        print(f"\n[{s}] {e}")
    print("\n" + ("4개 화면 전부 열림" if not fails else f"{len(fails)}개 화면 에러"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
