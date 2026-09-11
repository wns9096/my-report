# -*- coding: utf-8 -*-
"""받은 지적이 지금 문서에서 실제로 해소됐는가 — 9주차 Day4 프롬프트 8.

`제안서_답변지.md` 에 **고쳤다**고 적은 것이 문서에 실제로 들어가 있는지 본다.
답변지와 문서가 갈리면 답변지가 거짓말이 된다 — 같은 지적이 다시 왔을 때
읽으라고 만든 파일인데, 그 안의 「고쳤습니다」가 사실이 아니면 못 쓴다.

★ 아래 항목 중 넷(2·3·4·6)은 **사람이 쓰는 절**에 들어 있다.
  사람이 그 글을 고치면 여기서 걸린다. 그것이 맞다 — 검사가 틀린 것이 아니라
  그 지적이 다시 열린 것이다. 답변지를 같이 고쳐야 한다.

    python checks/w9d4_answers.py
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

TOPIC = "축:공고 경쟁도"
ANSWERS = ROOT / "제안서_답변지.md"

# (번호, 분류, 지적 한 줄, 문서에서 찾을 것)
# 찾을 것은 **조회로 나온 값**이나 옮겨 온 말이다. 낱말 하나가 아니라
# 그 지적이 해소됐을 때만 나올 수 있는 글자를 고른다.
#
# ★ 찾을 때는 **빈칸을 전부 지우고** 견준다. 문서가 숫자를 <span> 으로 감싸기
#   때문에 태그를 벗기면 «21.3 건» 처럼 띄어진다. 눈에 보이는 글자는 «21.3건»
#   인데 검사만 못 찾는 것은, 검사가 문서를 읽는 방식이 사람과 다른 것이다.
ITEMS = [
    (1, "A", "서류만 늘리는 제안 아닌가", r"최종합격기준으로보면"),
    (2, "A", "옮길 자리가 있는지 모른다", r"공고당21\.3건에서31\.2건"),
    (3, "A", "0.5가 왜 기준인지 없다", r"평균0\.511"),
    (4, "A", "접는 기준이 서류 통과율뿐이다", r"면접통과건수가직전분기보다"),
    (5, "A", "표본이 한 사람 것인지 모른다", r"표본520명"),
    (6, "A2", "경쟁도가 무엇을 재는 값인지 없다", r"확인필요.{0,40}산출식"),
    (7, "A", "최종 합격이 어느 칸에서 나왔는지", r"경쟁낮음\(0\.00~0\.35\)2\.9%"),
    (8, "A+B", "뒤쪽 몇 달을 왜 뺐는가", r"관측이덜찬뒤쪽3개월을빼고"),
    (8.5, "A", "결과가 덜 온 건이 분모에 있다", r"273건\(5\.5%\)"),
    (9, "A", "교락을 통제한 분석이 없다", r"30\.7%·22\.4%·17\.7%"),
    (10, "A", "시점이 대신 설명하는 것 아닌가", r"달마다따로보면"),
    (11, "A", "건끼리 독립이 아니다", r"공고1개당20\.7건"),
    (12, "B", "요청 절이 단정형이다", r"환산값입니다—위가정5개"),
]

results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label, detail))
    print(f"  [{'해소' if cond else '미해소'}] {label}"
          + (f"  — {detail}" if detail else ""))
    return bool(cond)


def visible(h: str) -> str:
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", _html.unescape(h))


def main():
    t = {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
         for n in config.TABLES}
    topic = {x["키"]: x for x in metrics.proposal_topics(t)}[TOPIC]
    ev = metrics.topic_evidence(t, topic)
    secs = P.build(topic, ev, P.load_cards(), P.human_for(topic))
    text = visible(P.to_html(secs, topic, ev.get("표본")))
    flat = re.sub(r"\s+", "", text)

    print(f"\n답변지에 «고쳤다»고 적은 것이 문서에 있는가 — {len(ITEMS)}건\n")
    for no, kind, what, pat in ITEMS:
        ok(re.search(pat, flat), f"{no:>4} [{kind}] {what}")

    print("\n── 답변지 자체 ──")
    if not ANSWERS.exists():
        ok(False, "답변지가 있다", f"{ANSWERS.name} 가 없다")
        return 1
    doc = ANSWERS.read_text(encoding="utf-8")
    # ★ 오늘의 채점 기준. 전부 고쳤다면 판단을 안 한 것이다.
    n_c = len(re.findall(r"안 받아들인다", doc))
    ok(n_c >= 1, "안 고친 것이 하나 이상 있다",
       f"{n_c}건 — 전부 고쳤다면 판단을 안 한 것이다")
    ok("해당 없음" not in doc.replace("「해당 없음」은 이유가 아니다", ""),
       "«해당 없음» 을 이유로 쓰지 않았다")
    ok(re.search(r"\|\s*\*\*B\*\*\s*\|", doc), "B(있는데 못 찾음)로 분류한 것이 있다",
       "0이면 문서 전체를 대조하지 않은 것이다")
    ok("동료" in doc and "대신했다" in doc,
       "동료 지적을 무엇으로 대신했는지 적혀 있다")

    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)}/{len(results)} 해소")
    if bad:
        print("답변지와 문서가 갈렸다. 둘 중 하나를 고친다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
