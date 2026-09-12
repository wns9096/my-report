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
    (6, "A2", "경쟁도가 무엇을 재는 값인지 없다",
     r"확인필요.{0,40}실제지원자수·모집인원"),
    (7, "A", "최종 합격이 어느 칸에서 나왔는지", r"경쟁낮음\(0\.00~0\.35\)2\.9%"),
    (8, "A+B", "뒤쪽 몇 달을 왜 뺐는가", r"관측이덜찬뒤쪽3개월을빼고"),
    (8.5, "A", "결과가 덜 온 건이 분모에 있다", r"273건\(5\.5%\)"),
    (9, "A", "교락을 통제한 분석이 없다", r"30\.7%·22\.4%·17\.7%"),
    (10, "A", "시점이 대신 설명하는 것 아닌가", r"달마다따로보면"),
    (11, "A", "건끼리 독립이 아니다", r"공고1개당20\.7건"),
    # ★ 열쇠에 수를 박아 두었다가 걸렸다. 가정을 하나 더 넣자 «5개» 가 «6개» 가
    #   되면서 문서는 멀쩡한데 검사가 «갈렸다» 고 했다. w9d5_close.py 에서
    #   찾은 것과 같은 함정이다 — **검사가 세는 수를 열쇠에 넣지 않는다.**
    (12, "B", "요청 절이 단정형이다", r"환산값입니다—위가정\d+개"),
]

# 강사 벤치마크 앱(자동 채점) 이 짚은 것. 페르소나와 겹치는 자리도 있고
# 아닌 자리도 있다 — 겹치지 않는 자리가 사람이 안 보는 자리였다.
#
# ★ 여기 없는 것이 넷 있다. 채점기가 짚었지만 **안 고친 것**이다.
#   안 고친 이유는 제안서_답변지.md 에 있고, 그 이유가 이 문서의 답변이다.
#   점수를 올리려고 고쳐서는 안 되는 것(확신도 올리기 · 확인 계획 지우기 ·
#   전제 줄 줄이기)은 여기에 절대 넣지 않는다.
BENCH = [
    (13, "A", "누가 하는지 없다", r"담당나\.어느공고에낼지고르는사람도"),
    (14, "A", "언제 하는지 없다", r"다음분기첫지원전1주안에후보공고목록"),
    (15, "A", "얼마나 드는 일인지 없다", r"한분기164건이고그66개에공고당2\.5건"),
    (16, "A", "어느 표를 읽었는지 없다", r"출처표4개—지원자520행"),
    (17, "A", "입구 검사 결과가 문서에 없다", r"입구검사13건—차단0·경고4·통과9"),
    (18, "A", "경쟁도를 «모른다»고만 적었다", r"공고240개전부에값이있고\(결측0건\)"),
    (19, "A", "되돌리는 데 얼마나 걸리는지 없다", r"되돌리는데걸리는시간은다음지원한건까지다"),
    (20, "A", "결정 시한이 없다", r"1월첫주안에필요합니다"),
    (21, "A", "문제 정의에 크기가 없다", r"4,065건이빠집니다"),
    (22, "B", "상관인지 개입 결과인지 안 보인다",
     r"상관이지인과가아닙니다"),
    # ★ 열쇠가 문장을 통째로 물고 있었다. 「세는 것과 판정하는 것은 다르다」를
    #   덧붙이자 멀쩡한 문서가 「안 해소」로 나왔다. 열쇠는 규칙이 있는지만
    #   봐야 하고, 그 규칙을 둘러싼 문장까지 물면 안 된다.
    (23, "A", "조기 중단 규칙이 없다", r"판정하는것은석달뒤한번이다"),
    (24, "A", "무엇을 바꾸는 결정인지 범위가 없다", r"채용시스템을바꾸는것이아니라"),
    (25, "A", "경고를 문서가 안 물고 왔다", r"학력6\.9%·공고산업12\.5%·지원산업13\.2%"),
    (26, "A", "모른다고만 하고 잴 수 있는 것을 안 쟀다", r"r=-0\.07.{0,60}r=0\.02"),
    # ★ 두 번째 판정에서도 남은 둘. 하나는 낱말이 없어서였고(27),
    #   하나는 «찾는다»고 적어 두고 안 찾은 것이었다(28).
    (27, "A", "인과가 아닌데 왜 이 제안이 서는지 없다",
     r"이제안은인과를필요로하지않는다"),
    (28, "A", "경쟁도 정의를 찾겠다고만 하고 안 찾았다",
     r"공고마다따로매겨지는0~1값"),
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


def hand(t, flat):
    """사람이 **손으로** 적은 숫자를 다시 세서 문서와 견준다.

    ★ 이 앱에서 틀린 숫자는 늘 손으로 쓴 자리에서 나왔다. 조회에서 온 값은
      한 번도 안 틀렸다. 담당·일정·공수와 위험 절은 사람이 쓰는 자리라
      여기 적힌 숫자는 아무도 다시 세 주지 않는다 — 그래서 여기서 센다.
    """
    po, ap = t["postings"], t["applications"].drop_duplicates("application_id")
    m = ap.merge(po[["posting_id", "competition"]], on="posting_id", how="left")
    low = po.loc[po["competition"] < 0.35, "posting_id"]
    inlow, hi = m.loc[m["posting_id"].isin(low)], m.loc[m["competition"] >= 0.65]
    mv = len(hi) // 2
    cnt = ap.groupby("posting_id").size().rename("건수")
    d = po.set_index("posting_id").join(cnt).fillna({"건수": 0})
    fit = m[["fit_score", "competition"]].corr().iloc[0, 1]
    f = metrics.funnel(t, "application")
    처음, 끝 = int(f.iloc[0]["인원"]), int(f.iloc[-1]["인원"])
    빠짐 = 처음 - int(f.iloc[1]["인원"])
    쓴다 = [
        (f"{len(low)}개", "경쟁도 0.35 미만 공고 수"),
        (f"{len(inlow) / len(low):.1f}건", "그 공고당 지금 지원 건수"),
        (f"{(len(inlow) + mv) / len(low):.1f}건", "한꺼번에 옮겼을 때 공고당"),
        (f"{round(mv / 4):,}건", "한 분기에 옮기는 양"),
        (f"{mv / 4 / len(low):.1f}건", "그 공고당 분기 증가분"),
        (f"{round(len(ap) / 12):,}건", "한 달치 지원 — 되돌려도 남는 양"),
        (f"{빠짐:,}건", "이 구간에서 빠지는 양"),
        (f"{빠짐 / (처음 - 끝) * 100:.1f}%", "퍼널 전체 이탈 대비"),
        (f"{po['competition'].min():.3f}", "경쟁도 최솟값"),
        (f"{po['competition'].max():.3f}", "경쟁도 최댓값"),
        (f"{po['competition'].mean():.3f}", "경쟁도 평균"),
        (f"{d['competition'].corr(d['건수']):.2f}", "경쟁도와 공고당 건수 상관"),
        (f"{fit:.2f}", "경쟁도와 적합도 상관"),
    ]
    for 값, 뜻 in 쓴다:
        ok(값.replace(",", "").replace(" ", "")
           in flat.replace(",", "") or 값 in flat,
           f"손으로 쓴 «{값}» 이 조회값과 같다", 뜻)


def main():
    t = {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
         for n in config.TABLES}
    topic = {x["키"]: x for x in metrics.proposal_topics(t)}[TOPIC]
    ev = metrics.topic_evidence(t, topic)
    secs = P.build(topic, ev, P.load_cards(), P.human_for(topic))
    text = visible(P.to_html(secs, topic, ev.get("표본"), ev.get("출처")))
    flat = re.sub(r"\s+", "", text)

    print(f"\n답변지에 «고쳤다»고 적은 것이 문서에 있는가 — "
          f"{len(ITEMS) + len(BENCH)}건\n")
    print("── 페르소나 둘이 짚은 것 ──")
    for no, kind, what, pat in ITEMS:
        ok(re.search(pat, flat), f"{no:>4} [{kind}] {what}")
    print("\n── 강사 벤치마크 앱이 짚은 것 ──")
    for no, kind, what, pat in BENCH:
        ok(re.search(pat, flat), f"{no:>4} [{kind}] {what}")

    print("\n── 손으로 쓴 숫자를 다시 센다 ──")
    hand(t, flat)

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
