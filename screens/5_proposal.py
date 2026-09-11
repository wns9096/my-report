# -*- coding: utf-8 -*-
"""제안서 — 9주차 Day3. 어제 리포트에 얹혀 있던 임시 탭이 여기로 왔다.

리포트와 제안서는 읽는 사람도 목적도 다른 문서다. 한 화면에 얹어 두면
리포트를 보러 온 사람이 제안서를 지나치고, 제안서를 보러 온 사람이
리포트를 먼저 읽는다.

화면은 거르지 않는다. 거르는 자리는 조립기(`report/proposal.py`) 한 곳뿐이다 —
두 곳에서 거르면 화면에 뜬 절과 내려받은 문서가 달라진다.
"""
import streamlit as st
import streamlit.components.v1 as components

from core import config, gates, metrics, shell
from report import proposal as P
from viz import proposal_charts as pcharts

ALL = "전체 — 후보 목록만 봅니다"

# ★ 칸 이름에 ~ 가 들어간다(«0.65~1.00»). Streamlit 의 글쓰기 함수는 마크다운을
#   해석해서 ~ 로 감싼 부분을 취소선으로 그린다 — 화면에 «0.65 1.00» 이 줄 그어진
#   채로 찍혔다. 문서(HTML)는 이스케이프하니 멀쩡했고 화면만 달랐다.
#   실제 브라우저로 찍어 보고서야 보였다.
_MD = str.maketrans({"~": "\\~", "*": "\\*", "_": "\\_", "`": "\\`"})


def md(s):
    """화면에 그대로 보여야 하는 글자. 마크다운으로 읽히지 않게 막는다."""
    return str(s).translate(_MD)


def _label(t):
    """주제 하나의 목록 라벨. 규모를 라벨에 같이 쓴다 — 규모 없이 고르면
    그날 눈에 띈 것을 고르게 된다."""
    if t["기각사유"]:
        return f"{t['제목']}  (차이 없음)"
    n = t["규모_연간건수"]
    unit = t.get("단위", "건")
    return f"{t['제목']}  · 연 {n:,}{unit}" if n is not None else t["제목"]


def _topic_table(topics):
    import pandas as pd
    return pd.DataFrame([{
        "갈래": t["갈래"], "주제": t["제목"],
        "규모(연간)": t["규모_연간건수"],
        "단위": t.get("단위", ""),
        "기각 사유": t["기각사유"] or "",
    } for t in topics])


def _section(sec, human, on_save):
    with st.container(border=True):
        auto = sec["kind"] == "auto"
        st.badge("자동으로 씁니다" if auto else "사람이 씁니다",
                 icon=":material/functions:" if auto else ":material/edit:",
                 color="blue" if auto else "orange")
        st.markdown(f"##### {sec['제목']}")
        st.caption(sec["질문"])

        if auto:
            for line in sec["문장"]:
                st.write(md(line))
        else:
            key = sec["키"]
            val = st.text_area(
                sec["제목"], value=human.get(key, ""), height=150,
                key=f"pr_{key}", label_visibility="collapsed",
                placeholder=sec.get("안내", ""))
            if st.button("저장", key=f"prs_{key}"):
                on_save(key, val)
            for line in sec["문장"]:      # 요청 절에 자동으로 붙는 줄
                st.write(md(line))

        if sec.get("차트"):
            # 문서와 같은 그림을 쓴다 — 두 벌을 그리면 두 그림이 갈린다.
            # st.html 은 svg 를 통째로 버린다(1.45.1). components.html 로 넣는다.
            components.html(pcharts.frame(sec["차트"]),
                            height=pcharts.height_of(sec["차트"]))
        if sec.get("표") is not None and len(sec["표"]):
            # 문서와 같은 서식으로 보여 준다. 원값을 그대로 띄우면
            # 화면은 0.1806, 문서는 18.1% 가 되어 같은 표가 갈린다.
            st.dataframe(P.display_table(sec["표"]), hide_index=True,
                         use_container_width=True)
        if sec.get("강조") and sec.get("사람글"):
            if P.has_decision_verb(sec["사람글"]):
                st.success(f"● {md(sec['사람글'])}")
            else:
                st.warning(
                    f"▲ {md(sec['사람글'])}\n\n"
                    f"결정을 요구하는 동사"
                    f"({' · '.join(config.PROPOSAL_WORDS['결정동사'])})가 "
                    f"없습니다. 이대로면 보고이지 제안이 아닙니다. "
                    f"저장은 막지 않습니다.")
        if sec.get("안내") and auto is False:
            st.caption(sec["안내"])


# ── 화면 ──────────────────────────────────────────────────────────────────
shell.topbar()
shell.sidebar()
ctx, tables, _missing = shell.load()
st.subheader("제안서")
st.caption(f"읽는 사람은 **{config.PROPOSAL_READER}** 입니다. 읽고 나서 "
           f"{' · '.join(config.PROPOSAL_WORDS['결정'])} 중 하나가 나와야 합니다.")
if not shell.guard(ctx, need_gate=2):
    st.stop()

cards = P.load_cards()
problems = P.card_problems(cards)
if problems:
    st.error(f"✕ 카드가 근거를 못 갖췄습니다 — {len(problems)}건.")
    for b in problems:
        st.markdown(f"- {b}")
    st.stop()

topics = metrics.proposal_topics(tables)
alive = [t for t in topics if not t["기각사유"]]

# ① 주제 고르기 — 기각된 후보도 목록에 남긴다.
#    지우면 «안 봤다»와 «보고 아니었다»가 구분되지 않는다.
choice = st.selectbox(
    f"주제 — 후보 {len(topics)}개 (쓸 만한 것 {len(alive)}개)",
    [ALL] + [_label(t) for t in topics], index=0)

if choice == ALL:
    st.caption("하나만 뽑으면 그날 눈에 띈 것이 그대로 이번 분기의 우선순위가 "
               "됩니다. 뽑을 수 있는 만큼 뽑아 놓고 고릅니다.")
    # 높이를 열어 둔다. 기본 높이면 열여덟 중 열하나만 보이고 나머지는
    # 스크롤 안에 숨는다 — «뽑을 수 있는 만큼 뽑아 놓고 고른다» 는 화면인데
    # 절반이 안 보이면 결국 위에 뜬 것을 고르게 된다.
    st.dataframe(_topic_table(topics), hide_index=True,
                 use_container_width=True,
                 height=(len(topics) + 1) * 35 + 3,
                 column_config={"규모(연간)": st.column_config.NumberColumn(
                     "규모(연간)", format="localized")})
    st.stop()

topic = topics[[_label(t) for t in topics].index(choice)]

# ② 고른 주제의 근거 요약 한 줄
st.info(md(topic["한줄"]), icon=":material/summarize:")
if topic["기각사유"]:
    st.warning(f"▲ 이 후보는 기각한 것입니다 — {md(topic['기각사유'])}. "
               f"문서는 만들 수 있지만 근거로 쓰기 어렵습니다.")

ev = metrics.topic_evidence(tables, topic)
human = P.human_for(topic)
secs = P.build(topic, ev, cards, human)

if not secs:
    st.warning("이 주제로는 채울 수 있는 절이 하나도 없습니다. "
               + " / ".join(f"{k}: {v}" for k, v in ev["없는 이유"].items()))
    st.stop()

# 못 만든 절이 있으면 왜 없는지 한 줄. 빈 화면으로 두지 않는다.
made = {s["키"] for s in secs}
skipped = [k for k in P.SECTIONS if k not in made]
if skipped:
    why = dict(ev["없는 이유"])
    why.setdefault("제안", "이 주제에 붙은 카드가 없습니다 "
                           "(제안카드.md 의 주제키를 봅니다)")
    st.caption("만들지 않은 절 — " + " · ".join(
        f"**{config.word('절', k)}** {why.get(k, '근거가 없습니다')}"
        for k in skipped))

hits = P.check_phrasing(P.auto_sections(secs))
if hits:
    st.error(f"✕ 자동 절에 인과를 단정하는 표현 {len(hits)}건")
    for h in hits:
        st.caption(f"{h['장']} · «{h['단어']}» → {h['대신']}")
else:
    st.caption(f"✓ 자동 절 {sum(1 for s in secs if s['kind'] == 'auto')}개 "
               f"인과 단정 표현 검사 통과")

# ③ 절별 미리보기 — 절 제목과 «답하는 질문»을 같이 보여준다
st.divider()
st.caption("절 " + " → ".join(s["제목"] for s in secs))


def _save(key, val):
    d = dict(P.human_for(topic))
    d[key] = val
    P.save_human_for(topic, d)
    st.success("저장했습니다.")
    st.rerun()


for s in secs:
    _section(s, human, _save)

# ④ 내려받기
st.divider()
missing = P.human_missing(secs)
if missing:
    st.warning(f"▲ 사람이 쓰는 절 {len(missing)}개가 비어 있습니다: "
               f"{', '.join(missing)}. 비운 채로 내보내면 문서에 "
               f"«{P.NOT_WRITTEN}»이 찍힙니다.")
last = P.last_line(secs)
if not P.has_decision_verb(last):
    st.error("✕ 문서 마지막 줄에 결정을 요구하는 동사가 없습니다. "
             "읽은 사람이 «잘 봤다»로 끝냅니다.")

html_ = P.to_html(secs, topic, ev.get("표본"))
st.download_button("제안서.html 내려받기", html_,
                   file_name=f"제안서_{topic['키'].replace(':', '_')}.html",
                   mime="text/html", type="primary")
st.caption(f"파일 하나로 열립니다 ({len(html_) / 1024:.0f}KB). "
           f"외부 CSS·이미지·CDN 을 쓰지 않습니다. 인쇄하면 A4에 맞습니다.")
if gates.is_ephemeral():
    st.caption("배포본은 파일을 남기지 않습니다 — 사람이 쓴 절은 이 세션에만 "
               "있습니다.")
