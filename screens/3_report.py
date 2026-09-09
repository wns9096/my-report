# -*- coding: utf-8 -*-
"""리포트 — 자동으로 쓰는 장, 사람이 쓰는 장, 인과 표현 검사, PDF, 게이트 3.

9주차 Day2 에 제안서 탭이 붙었다. **임시 자리다.**
기능을 먼저 만들고 자리는 나중에 정한다 — 자리를 먼저 정하면 아직 없는 메뉴에
맞춰 코드를 짜게 되고, 시간의 절반을 메뉴 배선에 쓴다. 내일 독립 메뉴로 옮긴다.
"""
import streamlit as st

from core import context, gates, shell
from core import config
from report import pdf as pdfmod
from report import proposal as P
from report import sections as S

PROP_HUMAN = "prop_human"       # 제안서에서 사람이 쓴 절 — 이 세션에만 있다


def _leak_check(ctx, sections):
    """어제 감춘 항목의 수치가 문서 어딘가에 새어 나오지 않았는가."""
    body = "\n".join(sections.values())
    leaked = []
    for c in ctx["cards"]:
        if c["판정"] != "무효":
            continue
        # 무효 카드의 이름이 나오는 줄에 % 수치가 붙어 있으면 유출이다
        for line in body.splitlines():
            if c["이름"] in line and "%" in line:
                leaked.append(c["이름"])
                break
    return leaked


def _limits_gap(ctx, sections):
    """화요일 검증 경고가 한계 절에 다 있는가."""
    from core import validate
    limits = sections.get("7. 한계", "")
    return [w["message"] for w in validate.warnings(ctx["checks"])
            if w["message"] not in limits]


def _gate3(ctx, sections, hits, empty):
    st.markdown("#### 게이트 3 · 발송 — **되돌릴 수 없다**")
    # 되돌릴 수 없는 자리는 화면이 그 무게를 보여줘야 한다.
    # 직접 쓴 HTML 대신 st.error 를 쓴다 — 테마를 따라가고, 색의 뜻도 같다.
    st.error("한 번 나간 것은 회수되지 않습니다. 메일을 보냈으면 읽힌 것이고, "
             "문서를 공유했으면 인용된 것입니다.", icon="🚫")

    leaked = _leak_check(ctx, sections)
    blocks = []
    if empty:
        blocks.append(f"사람이 쓰는 장 {len(empty)}개가 비어 있다: {', '.join(empty)}")
    if hits:
        blocks.append(f"인과 단정 표현 {len(hits)}건이 남아 있다")
    if leaked:
        blocks.append(f"감춘 항목의 수치가 문서에 새어 나왔다: {', '.join(leaked)}")

    missing_warn = _limits_gap(ctx, sections)
    if missing_warn:
        blocks.append(f"검증 경고 {len(missing_warn)}건이 한계 절에 없다")

    if blocks:
        for b in blocks:
            st.error(f"✕ {b}")
        st.caption("하나라도 걸리면 통과하지 마십시오.")
    else:
        st.success("● 발송 전 점검 4항목 전부 통과")

    prev = gates.passed(3)
    if prev:
        st.caption(f"직전 통과 — {prev['at']} · {prev['reason']}")

    reason = st.text_area("판단 근거", key="g3_reason", height=80,
                          placeholder="누구에게 무엇을 보내는가. 한계를 몇 건 명시했는가.")
    phrase = st.text_input(
        f"확인 문구를 그대로 입력하십시오 — «{gates.CONFIRM_PHRASE}»", key="g3_phrase")
    ready = (not blocks) and reason.strip() and phrase.strip() == gates.CONFIRM_PHRASE
    if st.button("발송하고 기록 남기기", type="primary", key="g3_btn",
                 disabled=not ready):
        gates.record(3, reason, {"인과 표현": len(hits), "빈 장": empty,
                                 "감춘 값 유출": leaked})
        st.success("게이트 3 통과. 되돌릴 수 없습니다.")
        st.rerun()      # 게이트 상태는 파일에 있다 — 위젯이 스스로 못 읽는다


# ══════════════════════════════════════════════════════════════════════════
# 탭 1 — 리포트 (8주차에 만든 것 그대로)
# ══════════════════════════════════════════════════════════════════════════
def _report_tab(ctx):
    human = S.load_human()

    st.markdown("#### 사람이 쓰는 장")
    st.caption("이 문장이 틀렸을 때 사람이 책임진다. 그래서 자동화하지 않는다. "
               "비워 두면 문서에 «작성되지 않음»이 찍힌다.")
    changed = {}
    for title, hint in S.HUMAN_SECTIONS.items():
        changed[title] = st.text_area(f"{title} — {hint}",
                                      value=human.get(title, ""),
                                      key=f"h_{title}", height=90)
    manual = st.text_area(
        "한계에 사람이 직접 적을 것 — 코드가 모르는 것",
        value=ctx["limits_manual"], key="h_limits", height=90,
        placeholder="데이터에 아예 없어서 못 본 것 · 찾아봤는데 신호가 없던 것 · "
                    "조직 사정으로 못 한 것")
    if st.button("저장", key="save_human"):
        S.save_human({k: v for k, v in changed.items()})
        context.save_manual_limits(manual)
        st.success("저장했습니다.")
        st.rerun()      # 저장한 내용은 파일에 있다 — 다시 읽어야 문서에 반영된다

    ctx = dict(ctx, limits_manual=manual)
    sections = S.build(ctx, human=changed)

    st.divider()

    hits = S.check_phrasing(sections)
    st.markdown("#### 인과 표현 검사")
    st.caption("자동 장과 사람이 쓴 장 **전부**에 건다. 사람이 더 자주 쓴다.")
    if hits:
        st.error(f"✕ 인과를 단정하는 표현 {len(hits)}건")
        for h in hits:
            with st.container(border=True):
                st.markdown(f"**{h['장']}** · 걸린 단어 «{h['단어']}»")
                st.caption(h["문맥"])
                st.markdown(f"대신: {h['대신']}")
    else:
        st.success("● 걸린 표현 없음")

    st.divider()

    st.markdown("#### 문서")
    empty = S.empty_human(sections)
    if empty:
        st.warning(f"비어 있는 장 {len(empty)}개: {', '.join(empty)} — "
                   f"비어 있는 채로 내보내면 «작성되지 않음»이 찍힙니다.")
    for title in S.ORDER:
        body = sections[title]
        with st.expander(title, expanded=(title == "7. 한계")):
            if body == S.NOT_WRITTEN:
                st.caption(S.NOT_WRITTEN)
            else:
                st.text(body)

    st.divider()

    st.markdown("#### PDF")
    if st.button("PDF 만들기", key="mk_pdf"):
        with st.status("PDF 만드는 중", expanded=False) as s:
            try:
                st.write("한글 폰트를 찾는다")
                pdfmod.find_font()
                st.write("차트 3개를 그린다")
                p = pdfmod.build_pdf(sections, ctx, warnings_=hits)
                s.update(label=f"{p.name} — {p.stat().st_size / 1024:.0f} KB",
                         state="complete")
            except pdfmod.FontMissing as e:
                # 화면을 죽이지 않는다. PDF 만 못 만들고 나머지는 그대로 쓴다.
                s.update(label="PDF를 만들지 않았다 — 한글 폰트가 없다", state="error")
                st.error(f"✕ {e}")
                st.caption("폰트 없이 만들면 한글이 전부 네모로 나오는데, 그건 "
                           "파일을 열어 보기 전에는 모른다. 그래서 만들지 않는다.")
    p = config.OUT / "report.pdf"
    if p.exists():
        st.download_button("PDF 내려받기", p.read_bytes(), file_name=p.name,
                           mime="application/pdf", key="dl_report_pdf")

    st.divider()
    _gate3(ctx, sections, hits, empty)


# ══════════════════════════════════════════════════════════════════════════
# 탭 2 — 제안서 (임시 자리)
# ══════════════════════════════════════════════════════════════════════════
def _proposal_tab():
    st.caption("**임시 자리입니다.** 기능을 먼저 만들고 자리는 내일 만듭니다. "
               "카드(`제안카드.md`)는 여기서 **읽기만** 합니다 — 화면에서 값을 "
               "고치기 시작하면 카드와 화면 중 어느 것이 진짜인지 알 수 없게 됩니다.")

    data = P.load_cards()
    problems = P.card_problems(data["cards"])
    if problems:
        # 차단은 실패가 아니다. 카드를 만들지 못했다는 것 자체가 결과일 수 있다.
        st.error(f"✕ 카드가 근거를 못 갖췄습니다 — {len(problems)}건. "
                 f"제안서를 만들지 않았습니다.")
        for b in problems:
            st.markdown(f"- {b}")
        return

    human = st.session_state.setdefault(PROP_HUMAN, {})
    secs = P.build(data, human=human)
    hits = P.check_phrasing(P.auto_sections(secs))

    st.caption(f"카드 {len(data['cards'])}장 · 절 {len(secs)}개 · "
               f"조회 {data['조회']} · 못 채운 자리 {P.todo_count(secs)}곳")

    left, right = st.columns([2, 5], gap="medium")
    with left:
        st.caption("**목차** — 순서는 고정입니다")
        pick = st.radio("목차", [s["title"] for s in secs], key="prop_toc",
                        label_visibility="collapsed")
    sec = next(s for s in secs if s["title"] == pick)

    with right:
        # kind 로만 분기한다. 제목으로 분기하면 절이 하나 늘 때마다 여기도 고쳐야 한다.
        auto = sec["kind"] == "auto"
        st.badge("자동으로 쓴다" if auto else "사람이 쓴다",
                 icon=":material/functions:" if auto else ":material/edit:",
                 color="blue" if auto else "orange")
        st.markdown(f"##### {sec['title']}")

        if sec.get("candidates"):
            st.caption("**후보 — 자동으로 나열한 것입니다. 고치지 못합니다.**")
            with st.container(border=True):
                for c in sec["candidates"]:
                    st.markdown(f"- {c}")

        if auto:
            st.text(sec["body"])
            # 자동 절마다 검사를 건다. 화면에서 지키고 문서에서 안 지키면 의미가 없다.
            mine = [h for h in hits if h["장"] == sec["title"]]
            if mine:
                st.error(f"✕ 인과를 단정하는 표현 {len(mine)}건")
                for h in mine:
                    with st.container(border=True):
                        st.caption(h["문맥"])
                        st.markdown(f"«{h['단어']}» 대신: {h['대신']}")
            else:
                st.caption("✓ 인과 단정 표현 검사 통과")
        else:
            val = st.text_area(sec["title"], key=f"p_{sec['title']}",
                               value=human.get(sec["title"], ""), height=140,
                               placeholder=sec.get("placeholder", ""),
                               label_visibility="collapsed")
            if st.button("저장", key=f"ps_{sec['title']}"):
                st.session_state[PROP_HUMAN][sec["title"]] = val
                st.success("저장했습니다.")
                st.rerun()
            if sec["body"] == P.NOT_WRITTEN:
                st.caption(f"지금은 «{P.NOT_WRITTEN}» 으로 나갑니다. "
                           f"비운 채로 내보내는 것이 채워서 내보내는 것보다 낫습니다.")
        if sec.get("note"):
            st.caption(sec["note"])

    st.divider()
    st.markdown("#### 받아 가기")
    if hits:
        st.warning(f"자동 절에 인과 단정 표현 {len(hits)}건이 남아 있습니다. "
                   f"내보내도 파일에 그대로 들어갑니다.")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("제안서.html 내려받기", P.to_html(secs),
                           file_name="제안서.html", mime="text/html",
                           key="dl_prop_html")
        st.caption("파일 하나로 열립니다. 외부 CSS·이미지·CDN 을 쓰지 않습니다.")
    with c2:
        if st.button("PDF 만들기", key="mk_prop_pdf"):
            with st.status("제안서 PDF 만드는 중", expanded=False) as s:
                try:
                    st.write("한글 폰트를 찾는다")
                    pdfmod.find_font()
                    p = P.build_pdf(secs)
                    s.update(label=f"{p.name} — {p.stat().st_size / 1024:.0f} KB",
                             state="complete")
                except pdfmod.FontMissing as e:
                    s.update(label="PDF를 만들지 않았다 — 한글 폰트가 없다",
                             state="error")
                    st.error(f"✕ {e}")
        pp = config.OUT / "proposal.pdf"
        if pp.exists():
            st.download_button("제안서 PDF 내려받기", pp.read_bytes(),
                               file_name=pp.name, mime="application/pdf",
                               key="dl_prop_pdf")


# ── 화면 ──────────────────────────────────────────────────────────────────
shell.topbar()
shell.sidebar()
ctx, _tables, _missing = shell.load()
st.subheader("리포트")
if not shell.guard(ctx, need_gate=2):
    st.stop()

tab_report, tab_prop = st.tabs(["리포트", "제안서 (임시)"])
with tab_report:
    _report_tab(ctx)
with tab_prop:
    _proposal_tab()
