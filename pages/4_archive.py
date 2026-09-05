# -*- coding: utf-8 -*-
"""아카이브 — 게이트 1·2·3 통과 기록이 나란히 보이는 자리."""
import pandas as pd
import streamlit as st

from core import config, gates, shell

shell.topbar()
shell.sidebar()
st.subheader("아카이브 · 게이트 통과 기록")

rows = gates.history()
if not rows:
    st.info("★ 아직 통과 기록이 없습니다. 실행 화면에서 게이트 1을 통과시키면 "
            "여기에 남습니다.")
    st.stop()

cols = st.columns(3)
for col, g in zip(cols, (1, 2, 3)):
    last = gates.passed(g)
    info = gates.GATES[g]
    with col:
        with st.container(border=True):
            st.badge(f"{config.MARKS['ok' if last else 'none']} {info['name']}",
                     color="green" if last else "gray")
            st.caption(info["q"])
            st.caption("되돌릴 수 있음" if info["reversible"] else "되돌릴 수 없음")
            st.divider()
            if last:
                st.caption(last["at"])
                st.markdown(last["reason"])
            else:
                st.caption("아직 통과하지 않음")

st.divider()
st.markdown("#### 전체 이력")
df = pd.DataFrame([{
    "게이트": r["name"],
    "일시": r["at"],
    "근거": r["reason"],
    "맥락": ", ".join(f"{k}={v}" for k, v in (r.get("context") or {}).items()),
} for r in reversed(rows)])
st.dataframe(df, hide_index=True, use_container_width=True,
             column_config={
                 "근거": st.column_config.TextColumn("근거", width="large"),
                 "맥락": st.column_config.TextColumn("맥락", width="medium"),
             })
st.caption("게이트 근거는 9주차에 그대로 거버넌스 근거가 된다. "
           "«확인함» 같은 빈 문구를 저장하면 그때 쓸 수 없다.")

st.divider()
st.markdown("#### 남는 문서")
for label, name, hint in (
        ("판단기준.md", "판단기준.md", "도메인이 바뀌어도 남는 것 — 여덟"),
        ("CLAUDE.md", "CLAUDE.md", "다음 프로젝트로 그대로 가져가는 규칙 열넷"),
        ("★_채운자리.md", "★_채운자리.md", "도메인을 바꿀 때 고칠 자리")):
    p = config.ROOT / name
    if p.exists():
        with st.expander(f"{label} — {hint}"):
            st.markdown(p.read_text(encoding="utf-8"))
    else:
        st.info(f"★ `{name}` 가 아직 없습니다.")
