# -*- coding: utf-8 -*-
"""화면 넷이 공유하는 껍데기 — 적재·컨텍스트·상단 바.

화면마다 각자 적재하면 캐시 지문이 갈려 두 화면이 다른 숫자를 보게 된다.
계산이 core/context.py 한 곳에서 나오듯, 적재도 여기 한 곳에서 나온다.
"""
import streamlit as st

from core import config, context, gates, loader


def stamp():
    """data/ 가 바뀌면 캐시를 버린다 — 깨진 파일을 넣었을 때 바로 반영되게.

    이름 앞에 _ 를 붙이면 안 된다. Streamlit 은 _ 로 시작하는 인자를
    캐시 키에서 빼기 때문에, 파일을 바꿔도 옛 값이 나온다.
    """
    parts = []
    for p in sorted(config.DATA.glob("*")):
        if p.is_file():
            parts.append(f"{p.name}:{p.stat().st_mtime_ns}:{p.stat().st_size}")
    return "|".join(parts)


OVERRIDE = "sandbox_tables"


def load():
    """원본을 읽는다. 다만 이 세션이 시험용 데이터를 얹어 두었으면 그것을 쓴다.

    시험용은 세션에만 있다. data/ 의 파일은 절대 건드리지 않는다 —
    배포본은 여러 사람이 같은 서버를 보므로, 한 사람이 넣은 깨진 파일이
    원본을 덮으면 다른 사람의 화면까지 바뀐다.
    """
    over = st.session_state.get(OVERRIDE)
    if over:
        tables = over["tables"]
        return context.build(tables), tables, []
    tables, missing = loader.load_all(stamp())
    ctx = context.build(tables) if tables and not missing else None
    return ctx, tables, missing


def topbar():
    """네 화면 전부에 뜨는 맥락 줄.

    직접 쓴 HTML 로 그리지 않는다. 테마를 바꾸면 손으로 쓴 색만 안 따라와서
    밝은 테마용 회색이 어두운 배경에 그대로 남는다.
    container(border=True) 는 테마를 따라간다.
    """
    with st.container(border=True):
        c = st.columns([3, 2, 2, 2])
        c[0].caption(f"**{config.DATASET}**")
        c[1].caption(f"{config.PERIOD[0]} ~ {config.PERIOD[1]}")
        c[2].caption(f"그레인 {context.GRAIN_KO[config.GRAIN]}")
        c[3].caption(f"유효 구간 ~{config.VALID_UNTIL}")


def sidebar():
    with st.sidebar:
        st.divider()
        st.caption(f"기간 {config.PERIOD[0]} ~ {config.PERIOD[1]}")
        st.caption(f"기준일 {config.AS_OF}")
        st.caption(f"그레인 {context.GRAIN_KO[config.GRAIN]}")
        st.caption(f"최소 표본 {config.MIN_SAMPLE} · 최소 관측 {config.MIN_OBS_DAYS}일")
        st.divider()
        st.caption("게이트")
        for g in (1, 2, 3):
            done = gates.passed(g)
            st.badge(f"{g} {gates.GATES[g]['name'].split(' · ')[-1]}",
                     icon=":material/check:" if done else ":material/lock:",
                     color="green" if done else "gray")


def guard(ctx, need_gate=None):
    """계산할 수 없거나 앞 게이트를 안 지났으면 화면을 열지 않는다.

    True 를 돌려주면 그릴 수 있다는 뜻이다.
    """
    if ctx is None:
        st.warning("★ 데이터가 연결되지 않았습니다. 실행 화면에서 확인하십시오.")
        return False
    if ctx.get("blocked"):
        st.error("✕ 검증에 차단이 있습니다. 계산을 시작하지 않았습니다. "
                 "실행 화면에서 무엇이 걸렸는지 보십시오.")
        return False
    if need_gate and not gates.passed(need_gate):
        st.info(f"★ 게이트 {need_gate}를 먼저 통과시키십시오. "
                f"근거를 적고 통과시키면 여기가 열립니다.")
        return False
    return True


def level_badge(level, text=""):
    """판정 색은 config.COLORS 하나에서 온다. 배지 색 이름은 그 의미의 이름표다."""
    color = {"ok": "green", "warn": "orange", "block": "red", "none": "gray"}[level]
    st.badge(f"{config.MARKS[level]} {config.LABELS_KO[level]}"
             + (f" {text}" if text else ""), color=color)
