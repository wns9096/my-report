# -*- coding: utf-8 -*-
"""아카이브 — 게이트 1·2·3 통과 기록이 나란히 보이는 자리."""
import pandas as pd
import streamlit as st

from core import config, gates, shell

shell.topbar()
shell.sidebar()
st.subheader("아카이브 · 게이트 통과 기록")

if gates.is_ephemeral():
    st.warning(
        "▲ **여기 남긴 기록은 앱이 다시 뜨면 사라집니다.** 배포처의 파일계는 "
        "다시 뜰 때 초기화됩니다. 저장소에 커밋된 기록만 남아 있습니다.\n\n"
        "판단 기록이 이 앱의 핵심 산출물이므로, 실제로 쓰려면 보관처를 "
        "밖으로 빼야 합니다 — 9주차에 할 일입니다.")

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

            # ★ 「되돌릴 수 있음」이 글자로만 있었다. 되돌리는 자리가 없으면
            #   그 말은 확인할 수 없고, 게이트 3의 「없음」도 마찬가지로 아무것도
            #   막지 않는다. 막는 것은 gates.revoke() 의 분기 조건이고
            #   여기는 그것을 부르는 자리다 — 화면이 규칙을 만들지 않는다.
            if last and info["reversible"]:
                with st.expander("되돌리기"):
                    why = st.text_input(
                        "되돌리는 근거", key=f"undo_reason_{g}",
                        placeholder="무엇을 다시 보게 됐는지 적습니다")
                    if st.button("이 게이트를 되돌린다", key=f"undo_{g}"):
                        try:
                            gates.revoke(g, why)
                        except ValueError as e:
                            st.error(f"{e} — 근거 없이 되돌리면 "
                                     f"기록이 «무슨 일이 있었나»에 답하지 못합니다.")
                        else:
                            st.rerun()
            elif last:
                st.caption("이미 나간 뒤라 되돌릴 수 없습니다. "
                           "다시 내보내려면 새로 통과시킵니다.")

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
