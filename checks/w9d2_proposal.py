# -*- coding: utf-8 -*-
"""제안서가 카드에 없는 것을 쓰지 않았는가 · 자동과 사람이 코드로 갈렸는가.

오늘의 채점 기준은 «화면에 뭐가 뜨는지»가 아니라 «자동 절과 사람 절이 코드로
나뉘어 있는가»다. 그래서 그것부터 기계로 본다.

가장 센 검사는 6번이다 — 자동 절에 있는 모든 숫자가 제안카드.md 안에 있는가.
어제 발견.md 에 걸었던 것과 같은 검사다. 조립층은 옮기기만 해야 하고,
옮기기만 했다면 새 숫자가 생길 수 없다.

여기서 걸리면 고칠 쪽은 **코드**다. 카드를 코드에 맞추는 것이 아니다.

    python checks/w9d2_proposal.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from report import proposal as P  # noqa: E402
from report import sections as S  # noqa: E402

SCREEN = ROOT / "screens" / "3_report.py"

EXPECTED_ORDER = ["한 장 요약", "하지 말 것", "다시 할 것", "할 것",
                  "이 제안이 틀린다면", "적용", "부록 (근거 상세)"]

# 숫자 덩어리. 자릿수 구분 쉼표와 소수점까지 한 덩어리로 본다.
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")

results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label, detail))
    print(f"  [{'지킴' if cond else '걸림'}] {label}"
          + (f"  — {detail}" if detail else ""))
    return bool(cond)


def main():
    data = P.load_cards()
    cards = data["cards"]
    secs = P.build(data)
    auto = P.auto_sections(secs)
    card_text = data["본문"]

    print("\n제안서 점검\n")

    # 1 — 카드
    ok(cards, "카드를 읽었다", f"{len(cards)}장 · 조회 {data['조회']}")
    ok(not P.card_problems(cards), "카드가 근거를 갖췄다",
       " / ".join(P.card_problems(cards)) or "차단 사유 없음")
    ok(sum(1 for c in cards if c["분류"] == "하지 말 것") >= 1,
       "「하지 말 것」이 하나 이상이다",
       "없으면 지금 하는 게 다 옳다는 뜻이 된다")

    # 2 — 절 순서
    ok(P.ORDER == EXPECTED_ORDER, "절 순서가 고정됐다",
       " → ".join(P.ORDER))
    ok([s["title"] for s in secs] == EXPECTED_ORDER,
       "조립한 순서가 선언된 순서와 같다")
    ok(P.ORDER.index("하지 말 것") < P.ORDER.index("할 것"),
       "「하지 말 것」이 「할 것」보다 앞이다",
       "「할 것」을 먼저 두면 멈추자는 제안은 안 읽힌다")

    # 3 — kind 분기 (오늘의 채점 기준)
    kinds = {s["title"]: s["kind"] for s in secs}
    ok(all(k in ("auto", "human") for k in kinds.values()),
       "절마다 kind 가 붙었다", str(kinds))
    human_t = [t for t, k in kinds.items() if k == "human"]
    ok(set(human_t) == set(P.HUMAN_TITLES),
       "사람이 쓰는 절이 선언된 것과 같다", " · ".join(human_t))
    ok(human_t.count("이 제안이 틀린다면") == 1,
       "「이 제안이 틀린다면」이 문서 전체에 하나다",
       "카드마다 있으면 아무도 안 읽는다")
    nxt = next(s for s in secs if s["title"] == "적용")
    ok(nxt["kind"] == "human" and nxt.get("candidates"),
       "「적용」은 사람 절인데 후보는 자동이다",
       f"후보 {len(nxt.get('candidates') or [])}개")

    # 4 — 화면이 kind 로만 분기하는가
    src = SCREEN.read_text(encoding="utf-8")
    tab = src.split("def _proposal_tab")[1].split("# ═════")[0]
    ok('sec["kind"] == "auto"' in tab, "화면이 kind 로 분기한다",
       "제목으로 분기하면 절이 늘 때마다 화면도 고쳐야 한다")
    ok(tab.count("st.text_area") == 1, "제안서 탭의 입력창이 하나뿐이다",
       f"{tab.count('st.text_area')}개")
    ok(tab.index("if auto:") < tab.index("st.text_area"),
       "입력창이 auto 분기 **뒤**에 있다", "auto 절에는 입력창이 없다")

    # 5 — 한 장 요약은 넷을 넘지 않는다
    lines = [ln for ln in auto["한 장 요약"].splitlines() if ln.strip()]
    ok(len(lines) == 4, "한 장 요약이 넷이다", f"{len(lines)}줄")
    ok("/" in lines[0], "발견 줄에 분모가 있다", lines[0][:60] + "…")

    # 6 — ★ 자동 절에 카드에 없는 숫자가 없다
    stray = []
    for title, body in auto.items():
        for n in NUM.findall(body):
            if n not in card_text:
                stray.append(f"{title}:«{n}»")
    ok(not stray, "자동 절의 숫자가 전부 카드에 있다",
       f"카드에 없는 숫자 {len(stray)}개 — {', '.join(stray[:6])}"
       if stray else "조립층은 옮기기만 했다")

    # 7 — 미확인을 지우지도 채우지도 않았다
    #
    # ★ 처음에는 «분류 절의 미확인 개수 == 카드의 미확인 개수»로 셌다가 걸렸다.
    #   6 vs 5. 카드 3의 「크기」 미확인은 분류 절이 아니라 부록에 나가기 때문이다.
    #   문서에는 여섯 곳 다 있었으니 틀린 쪽은 코드가 아니라 세는 방식이었다.
    #   개수를 세면 «어느 자리에 나가는지»를 검사가 미리 정해 버린다.
    #   그래서 자리를 묻지 않고 «그 문장이 문서에 있는가»로 바꿨다. 양방향으로 본다.
    todos = [(c["카드"], f, c[f]) for c in cards
             for f in ("크기", "비용", "효과", "되돌림") if P.is_todo(c.get(f, ""))]
    joined = "\n".join(auto.values())
    lost = [f"{k}·{f}" for k, f, v in todos if v not in joined]
    ok(not lost, "카드의 「미확인」이 하나도 안 지워졌다",
       f"문서에 없는 것 {lost}" if lost else f"{len(todos)}곳 전부 문서에 있다")

    # 거꾸로 — 문서의 미확인이 전부 카드에서 온 것인가. 화면이 지어낸 todo 는 없는가.
    made_up = [ln.strip()[:40] for ln in joined.splitlines()
               if P.TODO in ln and not any(v in ln for _, _, v in todos)]
    ok(not made_up, "문서의 「미확인」이 전부 카드에서 왔다",
       f"카드에 없는 미확인 {made_up}" if made_up else "지어낸 todo 없음")

    # 8 — 문장 검사를 재사용했다
    ok(P.check_phrasing is S.check_phrasing, "check_phrasing 을 재사용했다",
       "새로 만들면 한 곳만 고쳐지고 두 문서가 다른 기준으로 검사된다")
    ok(P.BANNED is S.BANNED, "금지어 목록도 같은 것이다",
       f"{len(P.BANNED)}개")

    hits = P.check_phrasing(auto)
    ok(not hits, "자동 절에 인과 단정 표현이 없다",
       " / ".join(f"{h['장']}«{h['단어']}»" for h in hits) or "0건")

    # 9 — 일부러 걸어 본다. 통과만 보고 넘어가면 검사가 도는지 모른다.
    hurt = dict(data)
    hurt["cards"] = [dict(c) for c in cards]
    hurt["cards"][0]["효과"] = "경쟁도가 높기 때문에 통과율이 낮다"
    caught = P.check_phrasing(P.auto_sections(P.build(hurt)))
    ok(caught, "일부러 넣은 「때문에」가 잡힌다",
       f"{len(caught)}건 잡음 (파일은 안 건드렸다 — 메모리에서만)")

    # 10 — HTML
    h = P.to_html(secs)
    ok('class="todo"' in h, "안 채운 자리가 HTML 에 todo 로 남았다")
    ok('class="num"' in h, "숫자에 num 이 붙었다")
    n_html = h.count('class="todo"')
    ok(n_html >= len(todos), "HTML 의 todo 가 카드의 미확인만큼 이상이다",
       f"HTML {n_html}곳 · 카드 {len(todos)}곳 "
       f"(빈 사람 절 {sum(1 for s in secs if s['body'] == P.NOT_WRITTEN)}개 포함)")
    outside = [p for p in ("http://", "https://", "<script src", "<link ",
                           "cdn.", "@import")
               if p in h]
    ok(not outside, "외부 CSS·이미지·CDN 이 없다",
       f"걸린 것 {outside}" if outside else "인터넷 없이 열린다")
    ok(P.NOT_WRITTEN in h, "안 쓴 사람 절이 «작성되지 않음» 으로 나간다")

    # 11 — PDF (폰트가 없는 곳에서는 건너뛴다)
    from report import pdf as pdfmod
    try:
        pdfmod.find_font()
    except pdfmod.FontMissing:
        print("  [건너뜀] PDF — 한글 폰트가 없다 (배포처에서는 packages.txt 가 깐다)")
    else:
        p = P.build_pdf(secs)
        ok(p.exists() and p.stat().st_size > 5000, "제안서 PDF 가 만들어진다",
           f"{p.name} {p.stat().st_size / 1024:.0f}KB")

    bad = [(l, d) for good, l, d in results if not good]
    print(f"\n{len(results) - len(bad)}/{len(results)} 지킴")
    if bad:
        print("\n걸린 것 — 고칠 쪽은 코드다:")
        for l, d in bad:
            print(f"  · {l} — {d}")
        return 1
    print("자동 절은 카드를 옮기기만 했고, 사람 절은 사람이 쓴다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
