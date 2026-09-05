# -*- coding: utf-8 -*-
"""실행 화면 — 데이터를 적재하고, 검증하고, 게이트 1을 통과한다."""
import streamlit as st

from core import config, gates, loader, shell, validate

BADGE = {"ok": "green", "warn": "orange", "block": "red"}


def _check_card(r):
    """검증 하나를 카드로. 색은 config.COLORS 의 의미를 배지 색으로 옮긴 것이다.

    직접 쓴 HTML 로 그리지 않는다 — 테마가 바뀌면 그 부분만 색이 안 따라온다.
    """
    lv = r["level"]
    with st.container(border=True):
        head, body = st.columns([1, 6])
        with head:
            st.badge(f"{config.MARKS[lv]} {config.LABELS_KO[lv]}", color=BADGE[lv])
        with body:
            st.markdown(f"**{r['name']}** — {r['message']}")
            if r["detail"]:
                st.caption(r["detail"])


def _gate1(results):
    is_blocked = validate.blocked(results)
    warns = validate.warnings(results)
    st.markdown("#### 게이트 1 · 입구 — 이 데이터로 분석을 시작해도 되는가")

    if is_blocked:
        st.error("✕ 차단이 있습니다. 이대로는 분석할 수 없습니다. "
                 "통과 버튼이 잠깁니다.")
    elif warns:
        st.warning(f"▲ 경고 {len(warns)}건. 넘길 수 있지만 근거를 적어야 합니다.")
    else:
        st.success("● 검증 전부 통과. 경고 없음.")

    prev = gates.passed(1)
    if prev:
        st.caption(f"직전 통과 — {prev['at']} · {prev['reason']}")

    reason = st.text_area(
        "판단 근거",
        key="g1_reason",
        placeholder='"확인함"은 근거가 아닙니다. 무엇을 보고 왜 괜찮다고 판단했는지 적으십시오.',
        height=80)
    ok = st.button("통과시키기", type="primary",
                   disabled=is_blocked or not reason.strip(),
                   key="g1_btn",
                   help="차단이 있으면 잠깁니다" if is_blocked else None)
    if ok:
        gates.record(1, reason, {"검증": validate.counts(results),
                                 "경고": [w["message"] for w in warns]})
        st.success("게이트 1 통과 기록을 남겼습니다. 아카이브 화면에서 볼 수 있습니다.")
        # 게이트 상태는 위젯이 아니라 파일에 있다. 위젯은 스스로 다시 그리지만
        # 메뉴의 자물쇠와 사이드바 배지는 파일을 다시 읽어야 바뀐다.
        # st.rerun() 을 남발하면 상태가 꼬이지만, 여기는 그 예외다.
        st.rerun()


def _break_options(tables):
    """일부러 깨뜨려 보는 자리.

    ★ 이 앱의 화요일 주장은 «앱이 데이터를 거부할 수 있는가»다.
      그런데 배포본을 여는 사람 눈에는 «정상 9 · 경고 4 · 차단 0»만 보인다.
      거부하는 모습을 볼 방법이 없으면 주장은 말로만 남는다.
      그래서 깨뜨리는 일을 화면 안으로 들여왔다.

    원본은 건드리지 않는다. 사본을 만들어 이 세션에만 얹는다.
    """
    import pandas as pd

    def drop_col(t):
        d = {k: v.copy() for k, v in t.items()}
        d["applications"] = d["applications"].drop(columns=["applied_date"])
        return d, "applications 에서 applied_date 를 지웠다"

    def shift_year(t):
        d = {k: v.copy() for k, v in t.items()}
        d["applications"]["applied_date"] = (
            d["applications"]["applied_date"] + pd.DateOffset(years=1))
        return d, "applications 의 날짜를 1년 뒤로 옮겼다"

    def cut_rows(t):
        d = {k: v.copy() for k, v in t.items()}
        d["applications"] = d["applications"].head(50)
        d["application_events"] = d["application_events"].head(50)
        return d, "행을 50개만 남겼다"

    def dup_key(t):
        d = {k: v.copy() for k, v in t.items()}
        a = d["applications"]
        dup = a.head(20).copy()
        dup["fit_score"] = dup["fit_score"] + 0.1      # 값이 «다른» 중복
        d["applications"] = pd.concat([a, dup], ignore_index=True)
        return d, "같은 키에 값이 다른 행 20개를 넣었다"

    return {
        "필수 컬럼을 지운다": (drop_col, "차단 — 날짜가 없으면 어떤 비율도 못 낸다"),
        "날짜를 1년 옮긴다": (shift_year, "차단 — 기간 밖이 100%다. 파일이 잘못 온 것"),
        "행을 50개로 줄인다": (cut_rows, "차단 — 쪼개는 순간 전부 표본 부족이 된다"),
        "같은 키에 다른 값을 넣는다": (dup_key, "차단 — 어느 행을 쓸지 정할 수 없다"),
    }


def _sandbox(tables):
    over = st.session_state.get(shell.OVERRIDE)
    with st.expander("★ 이 앱이 정말 데이터를 거부하는가 — 여기서 깨뜨려 보십시오",
                     expanded=bool(over)):
        if over:
            st.warning(f"▲ 지금 보고 있는 것은 **시험용 데이터**입니다 — "
                       f"{over['what']}.\n\n"
                       f"원본 파일은 그대로입니다. 이 사본은 이 세션에만 있습니다.")
            if st.button("원본으로 되돌리기", type="primary", key="undo_break"):
                del st.session_state[shell.OVERRIDE]
                st.rerun()
            return

        st.caption("검증을 만들었다고 끝이 아닙니다. 실제로 막히는지 봐야 합니다. "
                   "누르면 원본의 **사본**을 망가뜨려 이 세션에만 얹습니다.")
        opts = _break_options(tables)
        cols = st.columns(2)
        for i, (label, (fn, expect)) in enumerate(opts.items()):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{label}**")
                    st.caption(f"예상: {expect}")
                    if st.button("넣어 보기", key=f"brk_{i}"):
                        # 먼저 예상을 적어 두고 넣는다. 예상과 다르면 그 차이가
                        # 배울 거리다 — 넣고 나서 이유를 만들면 아무것도 안 배운다.
                        d, what = fn(tables)
                        st.session_state[shell.OVERRIDE] = {"tables": d, "what": what}
                        st.rerun()

        st.divider()
        up = st.file_uploader(
            "직접 만든 파일을 넣어 보십시오 (csv · parquet · xlsx)",
            accept_multiple_files=True, key="brk_up",
            help="파일 이름이 곧 테이블 이름입니다 — applications.csv 처럼.")
        if up and st.button("올린 파일로 보기", key="brk_up_go"):
            d = {k: v.copy() for k, v in tables.items()}
            names = []
            for f in up:
                name, df = loader.read_upload(f)
                d[name] = df
                names.append(name)
            st.session_state[shell.OVERRIDE] = {
                "tables": d, "what": f"올린 파일로 바꿨다 ({', '.join(names)})"}
            st.rerun()


# ── 화면 ──────────────────────────────────────────────────────────────────
shell.topbar()
shell.sidebar()
ctx, tables, missing = shell.load()

st.subheader("실행 · 데이터 적재와 검증")

if missing or not tables:
    st.warning(
        f"★ **Day1 준비 — 내 데이터를 연결하십시오**\n\n"
        f"`data/` 에서 다음을 못 찾았습니다: {', '.join(missing) or '(전부)'}\n\n"
        f"parquet · csv · 엑셀 을 넣고 `core/config.py` 의 `TABLES` 에 "
        f"확장자를 뺀 이름을 적으십시오.")
    st.stop()

prof = loader.profile(tables)
c1, c2, c3 = st.columns(3)
c1.metric("테이블", f"{len(tables)}개", border=True)
c2.metric("총 행", f"{int(prof['행'].sum()):,}", border=True)
c3.metric("메모리", f"{prof['메모리(MB)'].sum():.0f} MB", border=True,
          help="무료 배포 한도 1,024MB")
_sandbox(tables)

st.dataframe(
    prof, hide_index=True, use_container_width=True,
    column_config={
        "행": st.column_config.NumberColumn("행", format="%,d"),
        "메모리(MB)": st.column_config.ProgressColumn(
            "메모리(MB)", format="%.1f MB", min_value=0,
            max_value=float(prof["메모리(MB)"].max())),
    })

if ctx and ctx.get("facts"):
    with st.expander("눈에 띄는 것 — 사실만. 판단은 아래 검증과 사람이 한다"):
        for f in ctx["facts"]:
            st.markdown(f"- {f}")

st.divider()
results = ctx["checks"]
cnt = validate.counts(results)
st.markdown(f"#### 검증 — 규칙 5종 · 결과 {len(results)}건")
a, b, c = st.columns(3)
with a:
    st.badge(f"{config.MARKS['ok']} 정상 {cnt['ok']}", color="green")
with b:
    st.badge(f"{config.MARKS['warn']} 경고 {cnt['warn']}", color="orange")
with c:
    st.badge(f"{config.MARKS['block']} 차단 {cnt['block']}", color="red")

for r in sorted(results, key=lambda x: {"block": 0, "warn": 1, "ok": 2}[x["level"]]):
    _check_card(r)

st.divider()
_gate1(results)
