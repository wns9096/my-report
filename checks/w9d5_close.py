# -*- coding: utf-8 -*-
"""9주가 끝났는가 — Day5(토) 마감 검사.

Day5 안내의 「시작 전 확인할 것 다섯」을 사람이 눈으로 보는 대신 여기서 본다.
그리고 트랙 B 의 마감 조건 하나를 더 본다 —
**「적용」 다섯 줄이 정말 부록에서 고른 것인가.**

★ 일곱 번째가 이 검사를 만든 까닭이다. 「문장을 새로 만들지 마」는 지키기가
  쉬운 규칙이 아니다. 부록에 있는 문장을 다듬고 싶어지고, 다듬으면 그 순간
  **그날 실제로 배운 것**이 **지금 그럴듯한 것**으로 바뀐다. 사람이 기억할
  일이 아니라 글자로 대조할 일이다.

    python checks/w9d5_close.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

from report import proposal as P  # noqa: E402

CRITERIA = ROOT / "판단기준.md"
CARDS = ROOT / "제안카드.md"
ANSWERS = ROOT / "제안서_답변지.md"
SUBMIT = ROOT / "outputs" / "제출본_제안서.html"

# 8주차 나흘 + 9주차 나흘. 덧붙임(정리·다듬기·벤치마크)은 세지 않는다 —
# 「쌓인 날짜가 다 있는가」를 보는 것이지 분량을 보는 것이 아니다.
DAYS = [
    ("8주차 화", "## 화 —"), ("8주차 수", "## 수 —"),
    ("8주차 목", "## 목 —"), ("8주차 금", "## 금 —"),
    ("9주차 Day1", "## 2026-09-09 —"), ("9주차 Day2", "## 2026-09-09 (Day2)"),
    ("9주차 Day3", "## 2026-09-10 (Day3)"), ("9주차 Day4", "## 2026-09-11 (Day4)"),
]

# 이 도메인의 말. 여기 걸리면 다음 데이터로 못 옮긴다.
DOMAIN = ["지원자", "지원", "공고", "서류", "면접", "합격", "학력", "경쟁도",
          "직무", "산업", "고용", "구직", "이직", "채용", "적합도"]
# 분석 일반 용어. 걸려도 안 고친다 — 업종을 옮겨도 그대로 쓰는 말이다.
# 세기는 한다. 「안 고친다」와 「안 본다」는 다르다.
GENERIC = ["퍼널", "전환율", "이탈"]

# 본문에 «열세 곳» 처럼 적어 둔 수를 되읽는다. 숫자로 적으면 이 표가 없어도
# 되지만, 읽는 글에 «13곳» 이라고 쓰지 않는다.
_HAN = {"열": 10, "하나": 1, "둘": 2, "셋": 3, "넷": 4, "다섯": 5,
        "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9,
        "한": 1, "두": 2, "세": 3, "네": 4}


def _han(text):
    """«열세 곳» 같은 말에서 수를 꺼낸다. 못 읽으면 -1."""
    m = re.search(r"(열)?(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|한|두|세|네)?\s*곳",
                  text)
    if not m:
        return -1
    return (10 if m.group(1) else 0) + _HAN.get(m.group(2) or "", 0)


results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label))
    print(f"  [{'지킴' if cond else '걸림'}] {label}"
          + (f"  — {detail}" if detail else ""))
    return bool(cond)


def main():
    if not CRITERIA.exists():
        return ok(False, "판단기준.md 가 있다") or 1
    doc = CRITERIA.read_text(encoding="utf-8")

    print("\n9주 마감 — Day5 안내의 「시작 전 확인할 것 다섯」\n")

    # ── 1 · 2 카드 ────────────────────────────────────────────────────────
    cards = P.load_cards()
    stop = [c for c in cards if c["분류"] == "하지 말 것"]
    ok(cards and stop, "제안 카드가 있고 「하지 말 것」이 비어 있지 않다",
       f"카드 {len(cards)}장 · 하지 말 것 {len(stop)}장")
    없는확신 = [c.get("제목", "?") for c in cards if not c.get("확신도", "").strip()]
    ok(not 없는확신, "카드마다 확신도가 붙어 있다",
       " · ".join(없는확신) or f"{len(cards)}장 전부")

    # ── 3 제안서 ─────────────────────────────────────────────────────────
    if SUBMIT.exists():
        html = SUBMIT.read_text(encoding="utf-8")
        ok('class="box"' in html, "제안서에 한 장 요약이 있다",
           f"{SUBMIT.name} · {len(html) // 1024}KB")
        ok(P.has_decision_verb(re.sub(r"<[^>]+>", " ", html)),
           "제안서에 결정을 요구하는 「요청」 줄이 있다")
    else:
        ok(False, "제출본 제안서가 있다", f"{SUBMIT.name} 가 없다")
        ok(False, "제안서에 결정을 요구하는 「요청」 줄이 있다")

    # ── 4 답변지 ─────────────────────────────────────────────────────────
    ans = ANSWERS.read_text(encoding="utf-8") if ANSWERS.exists() else ""
    ok(ans and re.search(r"\*\*A\*\*", ans) and re.search(r"\*\*C\*\*", ans),
       "지적 분류표(A/B/C)가 있다", f"{ANSWERS.name}")
    ok("안 받아들인다" in ans, "안 고친 이유가 적혀 있다",
       f"{ans.count('안 받아들인다')}건")

    # ── 5 판단기준 여덟 날 ────────────────────────────────────────────────
    print("\n── 판단기준.md 에 쌓인 날 ──")
    빈날 = [n for n, mark in DAYS if mark not in doc]
    ok(not 빈날, "8주차 나흘 + 9주차 나흘이 다 있다",
       " · ".join(빈날) or f"{len(DAYS)}장 전부")

    # ── 6 · 7 적용 절 ────────────────────────────────────────────────────
    print("\n── 「적용」 다섯 줄 (Day5 트랙 B) ──")
    if "## 적용 —" not in doc or "# 부록 —" not in doc:
        ok(False, "「적용」 절과 부록이 갈려 있다", "둘 중 하나가 없다")
        return 1
    본문 = doc.split("## 적용 —", 1)[1].split("# 부록 —", 1)[0]
    부록 = doc.split("# 부록 —", 1)[1]
    다섯 = re.findall(r"^\d+\.\s+(.+?)$", 본문, flags=re.M)
    ok(len(다섯) == 5, "다섯 줄이다", f"{len(다섯)}줄")

    # ★ 오늘의 핵심. 고른 것인가, 쓴 것인가.
    #   ★ 견줄 때는 **빈칸을 하나로 눌러** 견준다. 부록에서는 같은 문장이 두 줄로
    #     접혀 있어서, 이어 붙인 형태와 글자가 안 맞는다. 사람 눈에는 같은 문장인데
    #     검사만 못 찾는 것은 검사가 문서를 읽는 방식이 사람과 다른 것이다.
    #     (Day4 의 w9d4_answers.py 에서 같은 자리를 한 번 헤맸다)
    flat = re.sub(r"\s+", " ", 부록)
    지어냄 = [ln for ln in 다섯
              if re.sub(r"\s+", " ", ln.strip()) not in flat]
    ok(not 지어냄, "다섯 줄이 전부 부록에 글자 그대로 있다",
       (" / ".join(t[:34] + "…" for t in 지어냄) + " ← 부록에 없는 말이다")
       if 지어냄 else "새로 쓴 문장 0")
    출처 = re.findall(r"〈(.+?)〉", 본문)
    ok(len(출처) == len(다섯), "줄마다 어느 장에서 왔는지 적혀 있다",
       f"{len(출처)}개")

    # ── 8 도메인 단어 ────────────────────────────────────────────────────
    print("\n── 다음 데이터로 옮길 수 있는가 ──")
    걸린 = sorted({w for w in DOMAIN if w in doc})
    ok(not 걸린, "업종·데이터 이름이 없다",
       " · ".join(걸린) or "0개 — 그대로 다음 데이터에 쓴다")
    쓴일반 = {w: doc.count(w) for w in GENERIC if w in doc}
    print("     · 분석 일반 용어는 세기만 한다: "
          + (" · ".join(f"{w} {n}" for w, n in 쓴일반.items()) or "0")
          + " — 업종을 옮겨도 쓰는 말이라 안 고친다")

    # ── 9 손으로 쓴 숫자 둘 ──────────────────────────────────────────────
    # ★ 이 앱에서 틀린 숫자는 늘 손으로 쓴 자리에서 나왔다. 오늘도 이 두 줄을
    #   적으면서 한 번 어긋났다 — 부록만 센 값과 파일 전체를 센 값을 섞었다.
    print("\n── 손으로 쓴 숫자를 다시 센다 ──")
    센값 = sum(부록.count(w) for w in GENERIC)
    적힌 = _han(본문)
    ok(적힌 == 센값, "「적용」 절이 적어 둔 일반 용어 수가 맞다",
       f"적힌 {적힌} · 세어 보니 {센값}")
    거절 = ans.count("안 받아들인다")
    맞나 = f"안 고친 것이 {거절}건" in ans
    ok(맞나, "답변지가 적어 둔 «안 고친 것» 수가 맞다",
       f"«안 받아들인다» {거절}건")

    # ── 알림 — 세지는 않는다 ─────────────────────────────────────────────
    # 배포 주소는 코드에서 안 나온다. 사람이 적어야 하고, 안 적으면 낼 때마다
    # 찾아야 한다. 검사를 실패시키지는 않는다 — 이건 «문서가 틀렸다»가 아니라
    # «아직 안 적었다»라서, 둘을 같은 칸에 두면 «걸림»의 뜻이 흐려진다.
    rm = (ROOT / "README.md").read_text(encoding="utf-8")
    print("\n── 손으로 적어야 하는 것 ──")
    print("     · 배포 URL: "
          + ("README 「배포」 절에 적혀 있다" if "(여기에 적는다)" not in rm
             else "**아직 안 적었다** — share.streamlit.io 에서 복사해 "
                  "README 「배포 URL」 칸에 넣는다"))

    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)}/{len(results)} 지킴")
    if bad:
        print("9주가 아직 안 끝났다. 걸린 것부터 채운다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
