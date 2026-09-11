# -*- coding: utf-8 -*-
"""제출 전 확인 — 9주차 Day4 실습 A.

이 문서는 **밖으로 나간다.** 지금까지의 검사는 «문서가 잘 만들어졌는가»를
봤다. 이 검사는 «내보내도 되는가»를 본다. 둘은 다른 질문이다.

    1 자가 검사     빈칸 · 수업에서만 쓰는 말이 남아 있는가
    2 요청 줄       결정을 요구하는 동사가 있는가 — 없으면 판정이 안 나온다
    3 내보내면 안 되는 것   실명 · 회사명 · 내부 단가 · 계약 금액 · 연락처

★ 3번에 걸려도 **지우지 않는다.** 무엇이 어디에 있는지만 알려준다.
  지우는 것은 사람이 정한다 — 가려야 할 것과 그냥 닮은 글자는 사람만 가린다.

    python checks/w9d4_submit.py

제출본은 outputs/제출본_제안서.html 로 남는다. 제출한 파일을 저장소에도
그대로 남겨 두라는 것이 오늘의 요구다 — 나중에 «무엇을 제출했는지»를
문서가 아니라 기억으로 맞추게 되면 그때부터 답변지가 못 믿을 것이 된다.
"""
import html as _html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

from core import config, loader, metrics  # noqa: E402
from report import proposal as P  # noqa: E402

# 제출하는 주제. 사람이 쓰는 두 절이 채워진 것으로 고른다 —
# 비어 있는 것을 제출하면 판정이 «문서가 덜 됐다»로만 나온다.
SUBMIT_TOPIC = "축:공고 경쟁도"
OUT = config.OUT / "제출본_제안서.html"

# 수업에서만 쓰는 말. 문서에 남으면 읽는 사람이 «내부 메모»로 읽는다.
# 원본 분류어는 config.PROPOSAL_WORDS 가 인쇄용으로 바꿔 주는데,
# 바뀌지 않고 새어 나오는 자리가 있는지 본다.
CLASSROOM = list(config.PROPOSAL_WORDS["분류"]) + [
    "todo", "TODO", "미확인", "FIXME", "XXX", "임시", "더미", "샘플 데이터",
]

# 내보내면 안 되는 것. 찾기만 한다.
SECRETS = [
    ("법인 표기", r"주식회사|㈜|\(주\)|유한회사|\bInc\.|\bCorp\b|\bLtd\b|\bLLC\b"),
    ("금액", r"[\d,]+\s*(?:원|만원|억원|억|₩)|₩\s*[\d,]+|\bKRW\b|\$\s*[\d,]+"),
    ("단가·계약", r"단가|계약\s*금액|견적|입찰|정산|급여|연봉|시급"),
    ("연락처", r"[\w.+-]+@[\w-]+\.[\w.]+|0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}"),
    ("주민·사번", r"\d{6}\s*[-–]\s*\d{7}|사번|사원번호"),
    ("이름처럼 보이는 것", r"[가-힣]{2,4}\s*(?:님|씨|과장|차장|부장|팀장|대표|이사|상무|전무)"),
    ("파일 경로", r"[A-Za-z]:\\\\|/Users/|/home/[a-z]"),
]

# 금액 규칙이 잡을 수밖에 없는 말. 금액이 아니라 «건수 단위»다.
# 예외는 규칙을 끄는 것이 아니라 **왜 예외인지 적어 두는 것**이다.
MONEY_OK = re.compile(r"[\d,]+\s*(?:건|명|개|쪽|일|월|년|분|초|회|%|%p)")

# «없다»고 적은 말은 새어 나간 것이 아니다.
# 이 문서에는 «건당 금액을 적어 둔 항목이 없습니다 (단가 미확보)» 가 있다.
# 그 «단가» 를 지우면 문서는 무엇을 안 냈는지 말하지 못하게 된다 —
# 규칙을 끄는 것도, 정직한 문장을 지우는 것도 답이 아니라서 예외를 적어 둔다.
ABSENCE = re.compile(r"없|미확보|않|아니|못")


def _absence(text, at, span=34):
    """맞은 자리 둘레에 «없다» 는 말이 있는가. 있으면 부재를 적은 것이다."""
    return bool(ABSENCE.search(text[max(0, at - span): at + span]))


results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label, detail))
    print(f"  [{'지킴' if cond else '걸림'}] {label}"
          + (f"  — {detail}" if detail else ""))
    return bool(cond)


def visible(h: str) -> str:
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", _html.unescape(h))


def main():
    t = {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
         for n in config.TABLES}
    cards = P.load_cards()
    topics = {x["키"]: x for x in metrics.proposal_topics(t)}
    topic = topics[SUBMIT_TOPIC]
    ev = metrics.topic_evidence(t, topic)
    human = P.human_for(topic)
    secs = P.build(topic, ev, cards, human)
    doc = P.to_html(secs, topic, ev.get("표본"))
    text = visible(doc)

    print(f"\n제출 전 확인 — 「{topic['제목']}」\n")

    print("── 1 자가 검사 ──")
    holes = doc.count('class="todo">—<') + text.count(P.NOT_WRITTEN)
    ok(holes == 0, "빈칸 0", f"{holes}개")
    leak = sorted({w for w in CLASSROOM if w in text})
    ok(not leak, "수업에서만 쓰는 말 0",
       " · ".join(leak) or "분류어는 인쇄용으로 바뀌어 나간다")
    ok(not P.human_missing(secs), "사람이 쓰는 절이 비어 있지 않다",
       " · ".join(P.human_missing(secs)) or "위험 · 요청 둘 다 채워져 있다")

    print("\n── 2 요청 줄 ──")
    last = P.last_line(secs)
    ok(P.has_decision_verb(last), "결정을 요구하는 동사가 있다",
       f"«{last[-46:]}»" if last else "요청 절이 비어 있다")
    ok(secs[-1]["키"] == "요청", "마지막 절이 요청이다", secs[-1]["제목"])

    print("\n── 3 내보내면 안 되는 것 (찾기만 한다) ──")
    found, skipped = [], []
    for name, pat in SECRETS:
        hits = []
        for m in re.finditer(pat, text):
            s = m.group(0)
            if name == "금액" and MONEY_OK.match(s):
                continue        # 건·명 단위다. 금액이 아니다
            if name in ("금액", "단가·계약") and _absence(text, m.start()):
                skipped.append(s)   # «없다»고 적은 자리. 새어 나간 것이 아니다
                continue
            hits.append(s)
        if hits:
            found.append((name, sorted(set(hits))[:4]))
    for name, hits in found:
        print(f"     ▲ {name}: {' · '.join(hits)}")
    if skipped:
        print(f"     · «없다»고 적은 자리라 세지 않았다: "
              f"{' · '.join(sorted(set(skipped)))}")
    ok(not found, "실명·회사명·단가·계약 금액·연락처가 없다",
       f"{len(found)}종 걸림 — 지울지는 사람이 정한다" if found
       else "합성 데이터라 실존 이름이 없다")

    # 외부로 나가는 파일이라 파일 자체도 본다. 문서는 파일 하나로 열려야 한다.
    ext = re.findall(r'(?:src|href)="(?!#)([^"]+)"', doc)
    ext = [u for u in ext if not u.startswith("data:")]
    ok(not ext, "바깥에서 끌어오는 것이 없다", " · ".join(ext[:3]) or "[]")

    OUT.write_text(doc, encoding="utf-8")
    print(f"\n  → {OUT.name} ({len(doc) / 1024:.0f}KB) 를 남겼다")

    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)}/{len(results)} 지킴")
    if bad:
        print("걸린 것을 사람이 보고 정한 뒤에 제출한다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
