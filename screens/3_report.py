# -*- coding: utf-8 -*-
"""리포트 — 자동으로 쓰는 장, 사람이 쓰는 장, 인과 표현 검사, PDF, 게이트 3."""
import streamlit as st

from core import context, gates, shell
from core import config
from report import pdf as pdfmod
from report import sections as S


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


# ── 화면 ──────────────────────────────────────────────────────────────────
shell.topbar()
shell.sidebar()
ctx, _tables, _missing = shell.load()
st.subheader("리포트")
if not shell.guard(ctx, need_gate=2):
    st.stop()

human = S.load_human()

# ── 사람이 쓰는 장 ────────────────────────────────────────────────────────
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
    st.rerun()          # 저장한 내용은 파일에 있다 — 다시 읽어야 문서에 반영된다

ctx = dict(ctx, limits_manual=manual)
sections = S.build(ctx, human=changed)

st.divider()

# ── 인과 표현 검사 ────────────────────────────────────────────────────────
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

# ── 문서 미리보기 ─────────────────────────────────────────────────────────
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

# ── PDF ──────────────────────────────────────────────────────────────────
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
                       mime="application/pdf")

st.divider()
_gate3(ctx, sections, hits, empty)
