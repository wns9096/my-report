# -*- coding: utf-8 -*-
"""README 에 넣을 화면 사진을 실제 브라우저로 찍는다.

AppTest 는 렌더 트리를 돌려주지만 «보이는 모습»은 안 준다.
색이 의미를 나르는 앱이라 그건 확인이 반쪽이다 — 그래서 진짜 브라우저로 찍는다.

    pip install playwright && python -m playwright install chromium
    python checks/shots.py            (앱을 직접 띄우고 찍는다)

playwright 는 requirements.txt 에 넣지 않는다. 사진 찍는 데만 쓰는 도구인데
배포처가 브라우저까지 내려받게 만들 이유가 없다.

사진은 docs/shots/ 에 남는다.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "shots"
PORT = 8877
BASE = f"http://localhost:{PORT}"

# (파일명, 열 경로, 누를 탭, 이 글자가 보이게 스크롤, 설명)
# 픽셀로 스크롤하면 화면을 조금만 고쳐도 엉뚱한 데를 찍는다. 글자를 기준으로 잡는다.
SHOTS = [
    ("1_run.png", "/", None, None, "실행 — 검증과 게이트 1"),
    ("2_dashboard.png", "/dashboard", None, None, "대시보드 — 지표와 월별 추이"),
    ("2_funnel.png", "/dashboard", None, "획득 퍼널", "퍼널 — 병목 한 칸만 강조"),
    ("2_decomp.png", "/dashboard", None, "분해", "분해 — 감춘 칸은 값을 안 그린다"),
    ("2_verdict.png", "/dashboard", None, "게이트 2 · 출구", "판정과 게이트 2"),
    ("3_report.png", "/report", None, None, "리포트 — 사람이 쓰는 장과 인과 검사"),
    # 9주차 Day3 — 제안서가 독립 메뉴로 나왔다. 기본값은 후보 목록이고,
    # 주제를 골라야 문서가 조립된다. 둘 다 찍는다.
    ("5_topics.png", "/proposal", None, None,
     "제안서 — 주제 후보. 기각된 것도 목록에 남는다"),
    ("5_proposal.png", "/proposal", None, "누구에게서 벌어집니까",
     "고른 주제로 조립된 절 — 자동과 사람이 배지로 갈린다"),
    ("5_request.png", "/proposal", None, "무엇을 결정해야 합니까",
     "요청 — 결정 선택지 셋과 마지막 줄"),
    ("4_archive.png", "/archive", None, None, "아카이브 — 게이트 통과 기록"),
    # 깨뜨리기는 맨 마지막에 찍는다. 시험용 데이터가 세션에 남아
    # 뒤 화면까지 물들이기 때문이다.
    ("1_break.png", "/", None, None, "깨뜨려 보기 — 차단이 뜨고 통과 버튼이 잠긴다"),
]


def _wait(page, ms=2500):
    """Streamlit 이 다 그릴 때까지 기다린다. 스피너가 사라질 때까지 본다."""
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def main():
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(12)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(viewport={"width": 1440, "height": 1000},
                              device_scale_factor=2)
            for name, path, tab, scroll, label in SHOTS:
                page.goto(BASE + path)
                _wait(page)
                if tab:
                    # 탭은 role=tab 이다. 누르지 않으면 첫 탭만 보인다 —
                    # 탭 몸통은 둘 다 실행되지만 «보이는» 것은 하나다.
                    page.get_by_role("tab", name=tab).click()
                    page.wait_for_timeout(1500)
                if name in ("5_proposal.png", "5_request.png"):
                    # 주제를 골라야 문서가 나온다. selectbox 는 combobox 다.
                    page.get_by_role("combobox").first.click()
                    page.wait_for_timeout(700)
                    opt = page.get_by_text("공고 경쟁도 칸 사이", exact=False)
                    opt.last.click()
                    page.wait_for_selector("text=무엇을 결정해야 합니까",
                                           timeout=30000)
                    _wait(page, 2500)
                if name == "1_break.png":
                    # 깨뜨려 보기 자리를 펴고 첫 버튼을 실제로 누른다.
                    # expander 는 <details><summary> 라 summary 를 눌러야 한다.
                    # expander 는 <details> 다. 눌러서 여는 것보다 열린 상태로
                    # 만들어 두는 편이 확실하다 — Streamlit 의 겹친 요소가
                    # 클릭을 가로챈다.
                    page.evaluate(
                        "document.querySelectorAll('details')"
                        ".forEach(d => d.open = true)")
                    page.wait_for_timeout(900)
                    # 파일 올리는 자리의 겹친 요소가 클릭을 가로챈다.
                    # DOM 클릭을 직접 보내면 React 가 그대로 받는다.
                    page.get_by_role("button", name="넣어 보기").first.evaluate(
                        "e => e.click()")
                    page.wait_for_selector("text=시험용 데이터", timeout=20000)
                    _wait(page, 2000)
                if scroll:
                    # scroll_into_view_if_needed 는 «조금이라도 보이면» 안 움직인다.
                    # 화면 맨 아래에 걸쳐 있어도 안 움직여서 엉뚱한 곳을 찍었다.
                    # .first 는 목차 줄에 걸린다 — 본문의 그 절이 아니라
                    # 화면 맨 위 «절 A → B → C» 캡션이 먼저 잡혔다.
                    # 맨 위로 되돌린 뒤 Playwright 의 것으로 맞춘다.
                    # scrollIntoView 는 «가장 가까운 스크롤 상자»를 움직이는데,
                    # 그림이 iframe 으로 들어간 화면에서는 창이 안 움직여
                    # 요청 절 대신 맨 위가 찍혔다. scroll_into_view_if_needed 는
                    # 상자를 찾아 주지만 «조금이라도 보이면» 안 움직이므로,
                    # 먼저 맨 위로 돌려 반드시 움직이게 한다.
                    page.mouse.wheel(0, -20000)
                    page.wait_for_timeout(400)
                    # ★ 제목(heading)을 먼저 찾는다. 글자로만 찾으면 «감춰 둔
                    #   입력창 라벨»이 잡힌다 — label_visibility="collapsed" 는
                    #   DOM 에 남아 있고 안 보일 뿐이라, 거기로 맞추려다 30초
                    #   기다리고 실패했다.
                    head = page.get_by_role("heading", name=scroll)
                    loc = (head.last if head.count()
                           else page.get_by_text(scroll, exact=False).last)
                    loc.scroll_into_view_if_needed()
                    page.wait_for_timeout(1200)
                    loc.scroll_into_view_if_needed()
                    page.mouse.wheel(0, -90)      # 제목이 맨 위에 붙지 않게
                    page.wait_for_timeout(900)
                page.screenshot(path=str(OUT / name))
                print(f"  찍음  {name:<18} {label}")
            b.close()
    finally:
        srv.terminate()
        srv.wait(timeout=15)

    total = sum(p.stat().st_size for p in OUT.glob("*.png")) / 1024
    print(f"\n{len(list(OUT.glob('*.png')))}장 · {total:.0f}KB → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
