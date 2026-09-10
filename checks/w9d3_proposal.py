# -*- coding: utf-8 -*-
"""제안서 자가 검사 — 9주차 Day3.

교안 프롬프트 11 이 «열어서 검사하라»고 한 다섯 가지를 기계가 본다.
  1 빈칸            값이 없는 자리가 몇 개인가                목표 0
  2 정체불명 용어    우리 팀 밖 사람이 뜻을 모를 표현           목표 0
  3 그래프          그림마다 대응하는 문장이 본문에 있는가      목표 0
  4 마지막 줄       결정을 요구하는 동사가 있는가              있어야 한다
  5 절 개수         일곱을 넘는가                            7 이하

Day2 의 `w9d2_proposal.py` 를 여기로 **옮겼다.** 규칙이 사라진 것이 아니다 —
자동/사람 분리와 «카드에 없는 값을 쓰지 않는다»는 그대로 아래에 있다.

★ 어제는 자동 절의 숫자가 카드 안에 있는 문자열인지 봤다. 오늘은 문장이
  카드가 아니라 조회 결과에서 나오므로 문자열 대조로는 안 된다.
  그래서 **다시 계산해서 견준다** — 병목·격차·연간 환산·분기 누적 넷을
  이 스크립트가 따로 구해 문서의 값과 맞춘다.

    python checks/w9d3_proposal.py
"""
import html as _html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config, loader, metrics, verdict  # noqa: E402
from report import proposal as P  # noqa: E402
from report import sections as S  # noqa: E402

# 문서로 뽑아 볼 주제. 절이 여섯 다 나오는 것으로 고른다.
MAIN_TOPIC = "축:공고 경쟁도"

results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label, detail))
    print(f"  [{'지킴' if cond else '걸림'}] {label}"
          + (f"  — {detail}" if detail else ""))
    return bool(cond)


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def visible_text(h: str) -> str:
    """사람 눈에 보이는 글자만. 태그와 스타일은 뺀다."""
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return _html.unescape(h)


def main():
    t = load()
    cards = P.load_cards()
    topics = metrics.proposal_topics(t)
    years = metrics._period_years()

    print("\n제안서 자가 검사\n")
    print("── 재료 ──")
    ok(cards, "카드를 읽었다", f"{len(cards)}장")
    ok(not P.card_problems(cards), "카드가 근거를 갖췄다",
       " / ".join(P.card_problems(cards)) or "차단 사유 없음")
    ok(all(len(P.todo_parts(c[f])) >= 3
           for c in cards for f in ("크기", "비용", "효과", "되돌림")
           if P.is_todo(c.get(f, ""))),
       "「확인 필요」가 낱말 하나로 남지 않았다",
       "무엇을 · 누가 · 모르는 채로 할 수 있는 결정 셋")

    print("\n── 주제 후보 ──")
    ok(len(topics) >= 5, "후보가 다섯 이상이다", f"{len(topics)}개")
    rejected = [x for x in topics if x["기각사유"]]
    ok(rejected, "기각된 후보가 목록에 남아 있다",
       f"{len(rejected)}개 — 지우면 «안 봤다»와 «보고 아니었다»가 안 갈린다")
    ok(all(x["기각사유"] for x in topics[-len(rejected):]) if rejected else True,
       "기각된 것이 맨 뒤로 갔다")
    ok(metrics._gap_min() == verdict.MOVE_MIN, "새 임계값을 만들지 않았다",
       f"격차 하한은 판정의 MOVE_MIN({verdict.MOVE_MIN}) 을 빌려 썼다")
    small = [x for x in topics if x["키"].startswith(("축:", "구간:"))
             and x.get("분모", 10 ** 9) < config.MIN_SAMPLE]
    ok(not small, "못 믿을 조건에 걸린 칸은 후보로 안 만들었다",
       f"분모 {config.MIN_SAMPLE} 미만 후보 {len(small)}개")
    # 규모가 «연간»인가 — 기간으로 나눴는지 다시 계산해서 본다
    bad_size = []
    for x in topics:
        if x["규모_연간건수"] is None or x.get("격차") is None:
            continue
        want = round(x["격차"] * x["분모"] / years)
        if want != x["규모_연간건수"]:
            bad_size.append(f"{x['제목']} {x['규모_연간건수']}≠{want}")
    ok(not bad_size, "규모가 연간 건수다 (격차 × 분모 ÷ 기간)",
       " / ".join(bad_size) or f"기간 {years:.2f}년으로 나눴다")

    print("\n── 절 구조 (후보 전부) ──")
    worst = []
    for x in topics:
        ev = metrics.topic_evidence(t, x)
        secs = P.build(x, ev, cards, P.human_for(x))
        keys = [s["키"] for s in secs]
        if len(secs) > 7:
            worst.append(f"{x['제목']} 절 {len(secs)}개")
        if keys != [k for k in P.SECTIONS if k in set(keys)]:
            worst.append(f"{x['제목']} 순서 어긋남 {keys}")
        if sum(1 for s in secs if s["kind"] == "human") != 2:
            worst.append(f"{x['제목']} 사람 절 "
                         f"{sum(1 for s in secs if s['kind'] == 'human')}개")
        for s in secs:
            if s["kind"] == "auto" and len(s["문장"]) > 3:
                worst.append(f"{x['제목']}·{s['제목']} {len(s['문장'])}문장")
    ok(not worst, "절 7 이하 · 순서 고정 · 사람 절 둘 · 한 절 3문장 이하",
       " / ".join(worst[:4]) or f"후보 {len(topics)}개 전부")

    made_none = [x["제목"] for x in topics
                 if len(P.build(x, metrics.topic_evidence(t, x), cards,
                                {})) < len(P.SECTIONS)]
    ok(made_none, "채울 수 없는 절은 아예 안 만든다",
       f"{len(made_none)}개 주제에서 절이 빠졌다 — 자리를 비우는 것과 다르다")

    print("\n── 문서 하나를 열어서 ──")
    topic = next(x for x in topics if x["키"] == MAIN_TOPIC)
    ev = metrics.topic_evidence(t, topic)
    human = P.human_for(topic)
    secs = P.build(topic, ev, cards, human)
    doc = P.to_html(secs, topic)
    text = visible_text(doc)

    ok(len(secs) <= 7, "절 개수가 일곱 이하다", f"{len(secs)}개")

    # 1 빈칸
    # ★ 처음에는 본문의 «—» 를 전부 셌다가 7개가 나왔다. 그중 여섯은 빈칸이
    #   아니라 문장 안의 줄표였다. 빈칸은 «값이 없어서 비워 둔 칸» 이므로
    #   그 표시(todo 로 찍힌 —)와 «작성되지 않음» 만 센다.
    holes = doc.count('class="todo">—<') + text.count(P.NOT_WRITTEN)
    ok(holes == 0, "빈칸 0",
       f"빈 표 칸 + «{P.NOT_WRITTEN}» → {holes}개")

    # 2 정체불명 용어 — 이 문서는 전부 우리말이다. 라틴 문자가 나오면 코드다.
    strange = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_.]{2,}", text)))
    ok(not strange, "정체불명 용어 0",
       f"{strange[:6]}" if strange else "함수·항목 이름이 문서에 없다")

    # 3 그래프 — 그림마다 그것이 증명하는 문장이 같은 절에 있는가
    nochart = []
    for s in secs:
        if not s.get("차트"):
            continue
        body = " ".join(s["문장"])
        keys = {"현황": ("전환율", "구간"), "원인": ("벌어", "%"),
                "규모": ("움직", "구간")}.get(s["키"], ())
        if not body or not any(k in body for k in keys):
            nochart.append(s["제목"])
    ok(not nochart, "대응 문장 없는 그래프 0",
       " / ".join(nochart) or
       f"그림 {sum(1 for s in secs if s.get('차트'))}개 전부 문장이 있다")

    # 4 마지막 줄
    last = P.last_line(secs)
    ok(P.has_decision_verb(last), "마지막 줄에 결정을 요구하는 동사가 있다",
       f"«{last[-46:]}»")
    ok(secs[-1]["키"] == "요청", "마지막 절이 요청이다", secs[-1]["제목"])

    print("\n── 자동/사람 (Day2 에서 옮겨 온 규칙) ──")
    ok(P.check_phrasing is S.check_phrasing, "인과 검사를 재사용했다",
       f"금지어 {len(P.BANNED)}개")
    hits = P.check_phrasing(P.auto_sections(secs))
    ok(not hits, "자동 절에 인과 단정 표현이 없다",
       " / ".join(f"{h['장']}«{h['단어']}»" for h in hits) or "0건")
    hurt = [dict(s) for s in secs]
    hurt[0]["문장"] = list(hurt[0]["문장"]) + ["경쟁이 높기 때문에 낮습니다."]
    ok(P.check_phrasing(P.auto_sections(hurt)),
       "일부러 넣은 「때문에」가 잡힌다", "메모리에서만 넣었다")
    ok(all(s["kind"] == ("human" if s["키"] in P.HUMAN_KEYS else "auto")
           for s in secs), "kind 가 선언대로다")
    src = (ROOT / "screens" / "5_proposal.py").read_text(encoding="utf-8")
    ok(src.count("st.text_area") == 1 and 'kind"] == "auto"' in src,
       "화면이 kind 로 분기하고 입력창은 하나다")
    ok("st.tabs" not in (ROOT / "screens" / "3_report.py")
       .read_text(encoding="utf-8"),
       "리포트 화면에 제안서 탭이 없다", "독립 메뉴로 옮겼다")

    print("\n── 값 대조 (다시 계산해서 견준다) ──")
    h, c, m = ev["현황"], ev["원인"], ev["규모"]
    f = metrics.funnel(t, "application")
    want_worst = int(f.iloc[1:]["직전 대비"].astype(float).idxmin())
    ok(h["병목"] == want_worst, "병목 구간이 다시 계산한 것과 같다",
       h["병목 구간"])
    want_gap = round(round(float(c["최고"]["전환율"]) * 100, 1)
                     - round(float(c["최저"]["전환율"]) * 100, 1), 1) / 100
    ok(abs(want_gap - topic["격차"]) < 1e-9, "격차가 표시값끼리 뺀 값이다",
       f"{want_gap * 100:.1f}%p")
    ok(m["환산값"]["연간건수"] == round(topic["격차"] * topic["분모"] / years),
       "연간 환산이 다시 계산한 것과 같다",
       f"연 {m['환산값']['연간건수']:,}{m['환산값']['단위']}")
    quarter = round(m["환산값"]["연간건수"] / 4)
    ok(f"{quarter:,}" in text, "분기 누적이 문서에 그 값으로 있다",
       f"{quarter:,}{m['환산값']['단위']}")
    ok(len(m["가정"]) >= 3, "환산에 쓴 가정이 문서에 있다",
       f"{len(m['가정'])}개")

    print("\n── HTML ──")
    # xmlns 의 네임스페이스 주소는 «가져오는 것»이 아니라 «이름표»다.
    # 그것까지 잡으면 검사가 멀쩡한 SVG 를 막고, 그러면 사람이 검사를 끈다.
    net = doc.replace('xmlns="http://www.w3.org/2000/svg"', "")
    outside = [p for p in ("http://", "https://", "<script", "<link ", "cdn.",
                           "@import", "url(") if p in net]
    ok(not outside, "외부 CSS·이미지·CDN 이 없다", str(outside) or "파일 하나로 열린다")
    ok("@page" in doc and "A4" in doc, "A4 인쇄 규칙이 있다",
       "size: A4; margin: 18mm 16mm")
    css = doc.split("<style>")[1].split("</style>")[0]
    hexes = sorted(set(re.findall(r"#[0-9A-Fa-f]{6}", css)))
    ok(len(hexes) <= 4, "문서 색이 넷 이하다", f"{hexes}")
    svg = "".join(s.get("차트") or "" for s in secs)
    fills = sorted(set(re.findall(r'fill="(#[0-9A-Fa-f]{6})"', svg)))
    ok(len(fills) <= 3, "그림 색이 셋 이하다", f"{fills}")
    bars = svg.count("<rect")
    labels = svg.count("<text")
    ok(labels >= bars, "막대마다 값 라벨이 있다", f"막대 {bars} · 글자 {labels}")
    ok(svg.count("viewBox") == sum(1 for s in secs if s.get("차트")),
       "그림마다 viewBox 가 있다")

    out = config.OUT / "제안서.html"
    out.write_text(doc, encoding="utf-8")
    print(f"\n  → {out.name} ({len(doc) / 1024:.0f}KB) 를 남겼다")

    bad = [(l, d) for good, l, d in results if not good]
    print(f"\n{len(results) - len(bad)}/{len(results)} 지킴")
    if bad:
        print("\n걸린 것:")
        for l, d in bad:
            print(f"  · {l} — {d}")
        return 1
    print("읽은 사람이 승인·조건부 승인·보류 중 하나를 고를 수 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
