# -*- coding: utf-8 -*-
"""my-report — 8주차에 만드는 내 앱.

화  데이터를 거부할 수 있게 만든다      실행 화면 · 검증 · 게이트 1
수  숫자를 내고 대조한다                대시보드 · 퍼널 · 지표
목  무엇을 감출지 정한다                분해 · 못 믿을 조건 · 판정 · 게이트 2
금  문장으로 내보낸다                   리포트 · 인과 검사 · PDF · 게이트 3

메뉴는 st.navigation 으로 만든다. screens/ 자동 멀티페이지는 파일 이름이 곧
메뉴라서 순서와 묶음을 못 바꾸고, 이름을 고치면 URL 이 같이 바뀐다.
여기서는 파일 이름과 메뉴 이름이 따로다 — 파일은 ASCII, 메뉴는 우리말이다.
(st.navigation 을 쓰면 screens/ 자동 스캔은 꺼진다. 실제로 확인했다.)
"""
import streamlit as st

from core import config, gates

st.set_page_config(page_title=f"{config.DATASET} · my-report",
                   layout="wide", initial_sidebar_state="expanded")

# 앞 게이트를 안 지났으면 자물쇠를 붙인다. 목록에서 아예 빼는 것도 되지만
# 그러면 메뉴가 사라져 앱이 고장 난 것처럼 보이고, 확인 스크립트가 그 화면을
# 열 수 없다. 있다는 것은 보이되 왜 잠겼는지 말해 주는 쪽으로 했다.
def _icon(need):
    return ":material/lock:" if (need and not gates.passed(need)) else None


PAGES = {
    "분석": [
        st.Page("screens/1_run.py", title="실행", icon=":material/play_arrow:",
                default=True),
        st.Page("screens/2_dashboard.py", title="대시보드",
                icon=_icon(1) or ":material/insights:"),
        st.Page("screens/3_report.py", title="리포트",
                icon=_icon(2) or ":material/description:"),
    ],
    "기록": [
        st.Page("screens/4_archive.py", title="아카이브",
                icon=":material/inventory_2:"),
    ],
}

st.navigation(PAGES).run()
