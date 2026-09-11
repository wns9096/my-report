# -*- coding: utf-8 -*-
"""제안서 조립층 — 9주차 Day3. **어제 것을 두고 처음부터 다시 짰다.**

어제는 «카드를 문서 구조로 옮기는 것»이었다. 오늘은 «읽은 사람이 결정을
내릴 수 있는가»다. 읽는 사람이 다르면 문서가 다르다 — 그래서 절이 바뀌었다.

  분석 문서   같은 분석을 하는 사람이 읽는다. 어떻게 계산했나가 궁금하다.
  제안서      결정 권한을 가진 사람이 읽는다. 뭘 해야 하나 · 얼마짜리인가 ·
              틀리면 어쩌나가 궁금하다.

그래서 이 문서에는 계산 과정이 들어가지 않는다. 함수 이름도 항목 이름도
부록으로조차 넣지 않는다. 궁금하면 앱을 열면 된다.

절의 순서가 곧 설득의 순서다 — 현황 → 원인 → 규모 → 제안 → 위험 → 요청.
규모를 제안 뒤에 두면 «왜 이걸 해야 하지»가 안 풀린 채로 제안을 읽고,
위험을 요청 뒤에 두면 결정한 다음에 리스크를 듣는다.

  자동으로 쓴다  현황 · 원인 · 규모 · 제안   틀리면 «사실»이 틀린 것이다
  사람이 쓴다    위험 · 요청                언제 접을지, 무엇을 결정해 달라고
                                          할지는 데이터가 못 정한다

사람이 쓰는 절은 **둘뿐이다.** 셋 이상이면 자동화가 덜 된 것이고,
하나도 없으면 책임질 사람이 없는 문서다.

인쇄되는 말은 이 파일에 없다. 전부 `core/config.py` 의 PROPOSAL_WORDS 에서 온다.
아래 키(«현황» 같은 것)는 인쇄되지 않는 내부 이름이다.
"""
import html
import json
import re

import pandas as pd

from core import config
# ★ 인과 표현 검사는 새로 만들지 않는다. 8주차 것을 그대로 쓴다.
#   목록을 두 곳에 두면 한 곳만 고쳐지고, 그때부터 두 문서가 다른 기준이 된다.
from report.sections import BANNED, NOT_WRITTEN, SUGGEST, check_phrasing
from viz import proposal_charts as pcharts

__all__ = ["build", "load_cards", "card_problems", "to_html", "one_pager",
           "auto_sections", "human_missing", "has_decision_verb", "last_line",
           "load_human", "save_human", "human_for", "save_human_for",
           "is_todo", "todo_parts", "fmt_value", "display_table",
           "SECTIONS", "HUMAN_KEYS", "TODO",
           "BANNED", "SUGGEST", "check_phrasing", "NOT_WRITTEN"]

CARDS_PATH = config.ROOT / "제안카드.md"
HUMAN_PATH = config.OUT / "proposal_human.json"

# 못 채운 자리에 쓰는 말. 문서에 인쇄되는 값이라 config 에서 온다.
TODO = config.PROPOSAL_WORDS["확인필요"]

# 절의 내부 이름과 순서. 순서를 바꾸지 않는다 — 설득의 순서다.
SECTIONS = ("현황", "원인", "규모", "제안", "위험", "요청")
HUMAN_KEYS = ("위험", "요청")


# ══════════════════════════════════════════════════════════════════════════
# 재료 — 카드 · 사람이 쓴 절
# ══════════════════════════════════════════════════════════════════════════
_FIELD = re.compile(r"^-\s*([^:]{1,10}):\s*(.*)$")
# ★ 담당 · 일정 · 공수를 뒤늦게 더했다. 값도 효과도 되돌림도 다 적어 두고
#   «그래서 누가 · 언제 하느냐» 만 없었는데, 읽는 사람은 그 셋이 없으면
#   실행할 수 있는 제안으로 안 읽는다. 근거가 아니라 실행의 자리다.
_FIELDS = ("제목", "분류", "주제키", "확신도", "근거", "크기",
           "담당", "일정", "공수", "비용", "효과", "되돌림", "출처")


def load_cards(path=None) -> list[dict]:
    """제안카드.md 를 읽는다. 화면도 이 파일도 카드를 고치지 않는다 — 읽기만 한다."""
    p = path or CARDS_PATH
    if not p.exists():
        return []
    cards = []
    for block in re.split(r"^## ", p.read_text(encoding="utf-8"), flags=re.M)[1:]:
        lines = block.splitlines()
        f = {}
        for ln in lines[1:]:
            m = _FIELD.match(ln.strip())
            if m and m.group(1).strip() in _FIELDS:
                f[m.group(1).strip()] = m.group(2).strip()
        if f.get("분류") in config.PROPOSAL_WORDS["분류"]:
            f["카드"] = lines[0].strip()
            cards.append(f)
    return cards


def is_todo(v) -> bool:
    return bool(v) and str(v).startswith(TODO)


def todo_parts(v) -> list[str]:
    """«확인 필요» 를 셋으로 쪼갠다 — 무엇을 · 누가 · 모르는 채로 할 수 있는 결정.

    셋이 갖춰지면 그 자리는 구멍이 아니라 요청이 된다. 낱말 하나로 두면 구멍이다.
    """
    return [s.strip() for s in str(v).split(" — ")[1:]]


def card_problems(cards) -> list[str]:
    """근거 없는 제안을 막는다. 차단은 실패가 아니다 — 오늘의 결과일 수 있다."""
    if not cards:
        return ["카드가 한 장도 없습니다. 근거 넷이 갖춰진 문장부터 다시 고릅니다."]
    bad = []
    if not any(c["분류"] == "하지 말 것" for c in cards):
        bad.append("「하지 말 것」이 하나도 없습니다. 지금 하는 게 다 옳을 리 없습니다.")
    for c in cards:
        t = c.get("제목", c["카드"])
        for fld in ("담당", "일정"):
            if not str(c.get(fld, "")).strip():
                bad.append(f"「{t}」 {fld} 가 비어 있습니다 — 누가 · 언제 가 "
                           f"없으면 실행할 수 있는 제안이 아닙니다.")
        for fld in ("비용", "효과", "되돌림", "크기", "공수"):
            v = c.get(fld, "")
            if is_todo(v) and len(todo_parts(v)) < 3:
                bad.append(f"「{t}」 {fld} 가 낱말 하나로 남았습니다 — "
                           f"무엇을·누가·모르는 채로 할 수 있는 결정 셋으로 적습니다.")
        if c["분류"] == "할 것" and not c.get("효과", "").startswith("실측"):
            bad.append(f"「{t}」 효과를 실측하지 않았는데 「할 것」에 있습니다.")
    return bad


def load_human() -> dict:
    if HUMAN_PATH.exists():
        return json.loads(HUMAN_PATH.read_text(encoding="utf-8"))
    return {}


def save_human(d: dict):
    HUMAN_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def human_for(topic) -> dict:
    """사람이 쓴 절은 주제마다 다르다.

    «무엇을 결정해 달라»는 주제가 바뀌면 통째로 바뀐다. 한 벌만 두면
    주제를 바꿔도 같은 요청문이 따라와서, 읽는 사람이 다른 결정을 하게 된다.
    """
    return load_human().get(topic["키"], {})


def save_human_for(topic, d: dict):
    all_ = load_human()
    all_[topic["키"]] = d
    save_human(all_)


def has_decision_verb(text) -> bool:
    """요청 문장에 결정을 요구하는 동사가 있는가.

    없으면 그것은 보고이지 제안이 아니다. 읽은 사람이 «잘 봤다»로 끝낸다.
    """
    return any(v in str(text) for v in config.PROPOSAL_WORDS["결정동사"])


# ══════════════════════════════════════════════════════════════════════════
# 문장 — 한 절에 세 문장을 넘지 않는다
# ══════════════════════════════════════════════════════════════════════════
def _pp(v, nd=1):
    return f"{float(v) * 100:.{nd}f}"


def _josa(word, pair=("은", "는")):
    """받침에 따라 조사를 고른다.

    «서류 통과율는» 같은 문장은 사람이 안 쓴다. 한 글자가 틀리면 문서 전체가
    기계가 쓴 것으로 읽히고, 그러면 숫자도 안 믿는다.
    """
    # 이름 뒤 괄호는 곁말이다. 조사는 이름에 붙는다 —
    # «경쟁 높음 (0.65~1.00)가» 가 아니라 «경쟁 높음(0.65~1.00)은».
    w = re.sub(r"\s*\([^()]*\)\s*$", "", str(word))
    ch = w.rstrip(" ]」』%").strip()[-1:]
    if not ch:
        return pair[1]
    if "가" <= ch <= "힣":
        return pair[0] if (ord(ch) - 0xAC00) % 28 else pair[1]
    # 숫자는 읽는 소리로 본다 — 0(영·공, 정수면 십·백) 1(일) 3(삼) 6(육)
    # 7(칠) 8(팔) 에 받침이 있다. 0 을 빠뜨려서 «0.480를» 이 나왔다.
    if ch.isdigit():
        return pair[0] if ch in "013678" else pair[1]
    return pair[1]


def _gap_pp(hi, lo):
    """격차는 화면에 찍히는 값끼리 뺀다. 원값으로 빼면 암산이 안 맞는다."""
    return f"{round(round(float(hi) * 100, 1) - round(float(lo) * 100, 1), 1):.1f}"


def _s_현황(topic, ev, cards, human):
    """이 절은 **주제가 말하는 것**을 먼저 적는다.

    ★ 예전에는 주제와 상관없이 늘 «가장 낮은 구간»부터 적었다. 그래서
      «면접 통과 → 최종 합격» 을 다루는 문서도, «월 지원 건수 임계값» 을
      다루는 문서도 첫 줄이 똑같았다. 임계값 넷과 추세 넷은 여덟 문서가
      글자 하나 안 다른 같은 문서였다 — 제목만 달랐다.
    """
    h = ev.get("현황")
    if not h:
        return None
    f, unit, w = h["표"], h["단위"], h["병목"]
    n = len(f) - 1
    fo, 갈래 = h.get("초점"), topic.get("갈래")
    문장, 차트 = [], pcharts.funnel_svg(h)

    if 갈래 == "임계값":
        수준 = topic.get("수준")
        문장.append(
            f"{topic['지표']}{_josa(topic['지표'])} 지금 {topic['표시']}입니다 "
            f"(표본 {topic.get('표본', 0):,}). "
            f"{수준 or '경고'}선 {topic['기준표시']}"
            f"{_josa(topic['기준표시'], ('을', '를'))} "
            f"{'밑돕니다' if 수준 else '넘습니다'}.")
    elif 갈래 == "추세":
        문장.append(
            f"{topic['지표']}{_josa(topic['지표'])} 최근 {topic['개월']}개월 "
            f"평균이 {topic['표시']}입니다. 견준 구간은 "
            f"{topic['견준구간']}입니다.")
        문장.append(f"직전 {topic['개월']}개월보다 "
                    f"{topic['변화표시']} {topic['방향']}.")
    elif fo:
        문장.append(
            f"{fo['시작']} {fo['분모']:,}{unit} 가운데 {fo['끝']}까지 가는 것은 "
            f"{fo['도달']:,}{unit}입니다 (전환율 {_pp(fo['전환율'])}%).")
    else:
        문장.append(
            f"{f.iloc[w - 1]['단계']} {h['병목 분모']:,}{unit} 가운데 "
            f"{f.iloc[w]['단계']}까지 가는 것은 {h['병목 도달']:,}{unit}입니다.")

    # 퍼널 그림에는 대응하는 문장이 있어야 한다 — 이 줄이 그 문장이다.
    if fo and fo["병목인가"]:
        문장.append(f"구간 {n}개 가운데 이 구간 전환율 "
                    f"{_pp(fo['전환율'])}%가 가장 낮습니다.")
    else:
        문장.append(f"구간 {n}개 가운데 가장 낮은 것은 {h['병목 구간']} "
                    f"{_pp(h['병목 전환율'])}%입니다.")
    # ★ «전환율 18.1%» 만으로는 얼마짜리인지 안 보인다. 이 구간에서 실제로
    #   몇이 빠지고 그것이 퍼널 전체 이탈의 몇 할인지를 같은 자리에 적는다.
    #   «여기부터 보라» 는 말을 숫자가 대신하게 한다.
    if 갈래 not in ("임계값", "추세"):
        분모 = fo["분모"] if fo else h["병목 분모"]
        도달 = fo["도달"] if fo else h["병목 도달"]
        전체 = int(f.iloc[0]["인원"]) - int(f.iloc[-1]["인원"])
        빠짐 = 분모 - 도달
        if 전체 > 0:
            문장.append(
                f"여기서 {빠짐:,}{unit}{_josa(unit, ('이', '가'))} 빠집니다 — "
                f"{len(f)}단계를 지나며 빠지는 {전체:,}{unit}의 "
                f"{빠짐 / 전체 * 100:.1f}%입니다.")
    out = {"문장": 문장[:3], "차트": 차트, "표": h["구간표"]}
    if 갈래 in ("임계값", "추세"):
        out["질문"] = config.word("질문", "현황:지표")
    return out


def _s_원인(topic, ev, cards, human):
    c = ev.get("원인")
    if not c or not c.get("최저") or not c.get("최고"):
        return None
    lo, hi, unit = c["최저"], c["최고"], c["단위"]
    hidden = len(c["감춘 칸"])
    문장 = [
        f"{c['구간']} 구간을 {c['축']}{_josa(c['축'], ('으로', '로'))} 나누면 "
        f"{lo['칸']}{_josa(lo['칸'], ('이', '가'))} {_pp(lo['전환율'])}%입니다 "
        f"({int(lo['도달']):,}{unit} / {int(lo['시작']):,}{unit}).",
        f"가장 높은 {hi['칸']} {_pp(hi['전환율'])}%와 견주면 "
        f"{_gap_pp(hi['전환율'], lo['전환율'])}%p 벌어지고, 낮은 쪽이 이 구간에 "
        f"들어온 것의 {_pp(lo['비중'], 1)}%를 차지합니다.",
    ]
    # ★ B(있는데 못 찾았다). «견준 값이지 바꿔 보고 잰 값이 아니다» 는 규모 절
    #   가정 표 첫 줄에만 있었다. 이 절이 «누구에게서 벌어집니까» 에 답하는
    #   자리이므로, 그 답이 **어떤 종류의 값인지**도 여기서 말해야 한다.
    #   ★ 새 문장으로 붙였더니 네 문장이 되는 문서가 넷 나왔다 — 한 절 세 문장
    #     규칙에 걸렸다. 단서는 단서끼리 한 줄에 모은다. 규칙을 늘리는 것보다
    #     같은 종류를 한 자리에 두는 것이 읽기에도 낫다.
    꼬리 = ["칸을 나눠 견준 값이고 한쪽 배분을 바꿔 보고 잰 값이 아닙니다"]
    if hidden:
        꼬리.append(f"표본이 모자란 {hidden}칸은 값을 내지 않았습니다")
    if c.get("미분류"):
        # 표에는 남아 있다. 안 지목했을 뿐이라는 것을 문서가 말해야 한다.
        꼬리.append(f"값을 안 적어 둔 「{c['미분류칸']}」 칸은 "
                    f"높고 낮음을 견주지 않았습니다")
    if 꼬리:
        문장.append(" · ".join(꼬리) + ".")
    t = c["표"].loc[c["표"]["사유"].isna(), ["칸", "시작", "도달", "전환율", "비중"]]
    return {"문장": 문장, "차트": pcharts.gap_svg(c),
            "표": t.rename(columns={"시작": f"진입({unit})",
                                    "도달": f"도달({unit})"})}


def _s_규모(topic, ev, cards, human):
    m = ev.get("규모")
    if not m:
        return None
    real, conv = m["실측"], m["환산값"]
    unit = conv["단위"]
    # ★ 처음에는 «지금 벌어진 격차는 18.1%p» 라고만 썼다. 무엇과 견준
    #   격차인지가 없어서 «낮다»의 기준이 문서에 없었다. 비교 대상을 반드시 적는다.
    lo_n, hi_n = topic.get("낮은"), topic.get("높은")
    비교 = (f"{lo_n}{_josa(lo_n)} {hi_n}보다 " if lo_n and hi_n else "격차가 ")
    문장 = [
        f"{비교}{_pp(real['격차'])}%p 낮고, 낮은 쪽에 들어온 것이 "
        f"{real['분모']:,}{unit}입니다.",
        f"이 격차가 그대로 이어진다고 보면 한 해에 "
        f"{conv['연간건수']:,}{unit}{_josa(unit, ('이', '가'))} 여기서 더 "
        f"빠집니다 (환산값입니다. 아래 가정 {len(m['가정'])}개를 두고 냈습니다).",
    ]
    차트, tr = None, ev.get("추세")
    if tr:
        svg = pcharts.trend_svg(tr)
        s = tr["값"].loc[[i for i in tr["값"].index if i in set(tr["유효 구간"])]]
        if svg and len(s) >= 2:
            fmt = (lambda v: f"{_pp(v)}%") if tr["형식"] == "%" else \
                (lambda v: f"{float(v):.3f}")
            문장.append(
                f"{tr['지표']}{_josa(tr['지표'])} 관측이 덜 찬 뒤쪽 "
                f"{max(0, len(tr['값']) - len(s)) or ''}개월을 빼고 "
                f"{s.index[0]} ~ {s.index[-1]} 구간에서 {fmt(s.iloc[0])}에서 "
                f"{fmt(s.iloc[-1])}로 움직였습니다.")
            차트 = svg
    # ★ 가정만 적어 두면 «다른 것으로 설명되는 것 아닌가» 에 답이 없다.
    #   가정과 **같은 줄에** 흔들어 본 결과를 적는다. 못 흔든 줄은
    #   «안 해 봤습니다» 라고 적는다 — 빈칸이면 안 한 것인지 못 한 것인지
    #   읽는 사람이 모른다.
    흔 = m.get("흔들기")
    표 = (pd.DataFrame({"환산에 쓴 가정": m["가정"], "흔들어 봤더니": 흔})
          if 흔 and len(흔) == len(m["가정"])
          else pd.DataFrame({"환산에 쓴 가정": m["가정"]}))
    return {"문장": 문장, "차트": 차트, "표": 표}


def _s_제안(topic, ev, cards, human):
    """이 주제에 붙은 카드가 없으면 절을 **아예 만들지 않는다.**

    자리를 비워 두는 것과 자리를 안 만드는 것은 다르다. 비워 두면 그 빈칸이
    그대로 인쇄된다.
    """
    mine = [c for c in cards if c.get("주제키") == topic["키"]]
    if not mine:
        return None
    kinds = {}
    for c in mine:
        k = config.word("분류", c["분류"])
        kinds[k] = kinds.get(k, 0) + 1
    # 열을 셋으로 두었더니 좁은 칸에서 머리글자가 세로로 쪼개졌다("구 분").
    # A4 폭에서 읽히려면 두 열이 맞다.
    rows = []
    for c in mine:
        who = config.word("분류", c["분류"])
        rows.append({"항목": "구분", "내용": who})
        rows.append({"항목": "무엇을", "내용": c.get("제목", "")})
        # 읽는 순서가 곧 결정 순서다 — 무엇을 · 누가 · 언제 · 얼마나 · 얼마가
        # 드나 · 얼마를 버나 · 틀리면 어떻게 되돌리나.
        for fld in ("담당", "일정", "공수", "비용", "효과", "되돌림"):
            v = c.get(fld, TODO)
            if is_todo(v):
                p = todo_parts(v)
                v = (f"{TODO} · 모르는 것 {p[0]} · 확인 {p[1]} · "
                     f"그래도 되는 결정 {p[2]}") if len(p) >= 3 else v
            rows.append({"항목": fld, "내용": v})
    return {
        "문장": [
            " · ".join(f"{k} {n}건" for k, n in kinds.items()) + "입니다.",
            "내용은 " + " / ".join(f"「{c.get('제목', '')}」" for c in mine)
            + "입니다.",
        ],
        "차트": None, "표": pd.DataFrame(rows),
    }


def _s_위험(topic, ev, cards, human):
    """사람이 쓴 글은 «문장» 이 아니라 «사람글» 에 둔다.

    ★ 처음에는 사람이 쓴 글을 문장 목록에 넣었더니, 화면에서 입력창과 본문에
      **같은 글이 두 번** 나왔다. 자동으로 조립한 문장과 사람이 쓴 글은 자리가
      다르다 — 섞어 두면 화면이 둘 다 그린다.
    """
    return {"문장": [], "차트": None, "표": None,
            "사람글": (human.get("위험") or "").strip() or NOT_WRITTEN,
            "안내": "이 판단이 틀렸다면 어디서 틀린 것인지, 언제 접을지를 적습니다. "
                    "데이터가 못 정하는 것입니다."}


def _s_요청(topic, ev, cards, human):
    """사람이 문장을 쓴다. 자동으로 지어내지 않는다.

    다만 규모와 결정 선택지 셋은 자동으로 붙인다 — 그건 조회하면 같은 값이다.
    선택지가 «보류» 하나뿐이면 그것은 선택지가 아니다.
    """
    m = ev.get("규모")
    문장 = []
    if m:
        n, unit = m["환산값"]["연간건수"], m["환산값"]["단위"]
        문장 = [
            # ★ B(있는데 못 찾았다) 처리. «개입 효과를 실측한 값이 아니다» 는
            #   규모 절의 가정 표에 있었는데, 결정하는 사람은 요청 절만 보고
            #   판정한다. 거기서는 «한 해 136건입니다» 라는 단정문이었다.
            #   단서를 붙인 뒤 단서 없이 다시 쓰면 단서를 안 붙인 것과 같다.
            #   내용을 새로 쓰지 않고 말만 앞으로 당긴다.
            f"이 주제의 규모는 한 해 {n:,}{unit}입니다 "
            f"(환산값입니다 — 위 가정 {len(m.get('가정') or [])}개를 두고 "
            f"냈습니다).",
            f"결정을 다음 분기로 미루면 그동안 "
            f"{round(n / 4):,}{unit}{_josa(unit, ('이', '가'))} 더 쌓입니다 "
            f"(한 해분을 네 분기로 고르게 나눈 값입니다).",
        ]
        # 결정하는 사람이 가장 먼저 묻는 것 — «앞 단계만 늘리는 것 아닌가».
        # 그 답을 결정 바로 앞에 둔다. 뒤에 두면 결정한 다음에 읽는다.
        끝 = (m.get("흔든것") or {}).get("끝단계")
        if 끝:
            문장.append(끝)
    tbl = pd.DataFrame({"선택지": list(config.PROPOSAL_WORDS["결정"]),
                        "따라오는 것": list(config.PROPOSAL_WORDS["결정"].values())})
    return {"문장": 문장, "차트": None, "표": tbl, "강조": True,
            "사람글": (human.get("요청") or "").strip() or NOT_WRITTEN,
            "안내": f"읽는 사람은 {config.PROPOSAL_READER} 입니다. "
                    f"결정을 요구하는 동사"
                    f"({' · '.join(config.PROPOSAL_WORDS['결정동사'])})가 "
                    f"들어가야 제안입니다."}


_MAKERS = {"현황": _s_현황, "원인": _s_원인, "규모": _s_규모,
           "제안": _s_제안, "위험": _s_위험, "요청": _s_요청}


# ══════════════════════════════════════════════════════════════════════════
# 조립
# ══════════════════════════════════════════════════════════════════════════
def build(topic, evidence, cards, human=None) -> list[dict]:
    """절 목록을 돌려준다. 근거가 없는 절은 만들지 않는다.

    거르는 자리는 여기 한 곳뿐이다. 화면에서 또 거르면 두 곳이 갈린다.
    """
    human = human or {}
    out = []
    for key in SECTIONS:
        made = _MAKERS[key](topic, evidence, cards, human)
        if made is None:
            continue
        out.append({"키": key, "제목": config.word("절", key),
                    "질문": config.word("질문", key),
                    "kind": "human" if key in HUMAN_KEYS else "auto",
                    **made})
    return out


def auto_sections(secs) -> dict:
    """인과 표현 검사에 넣을 자동 절만. 사람이 쓴 문장 때문에 조립이 실패하면 안 된다."""
    return {s["제목"]: "\n".join(s["문장"]) for s in secs if s["kind"] == "auto"}


def human_missing(secs) -> list[str]:
    return [s["제목"] for s in secs if s["kind"] == "human"
            and s.get("사람글") == NOT_WRITTEN]


def last_line(secs) -> str:
    """문서의 마지막 줄. 여기에 결정 동사가 없으면 오늘은 실패다."""
    if not secs:
        return ""
    tail = secs[-1]
    return tail.get("사람글") or (tail["문장"][-1] if tail["문장"] else "")


def _first_sentence(text) -> str:
    """첫 문장만. 사람이 여러 문단을 쓰면 요약 박스가 본문보다 길어진다."""
    t = str(text).strip().splitlines()[0].strip() if str(text).strip() else ""
    m = re.search(r"^(.{10,}?다\.)(\s|$)", t)
    return m.group(1) if m else t


def one_pager(secs) -> list[tuple]:
    """한 장 요약 — 여섯을 압축한 것이다. 순서가 본문과 같아야 한다.

    새 문장을 만들지 않는다. 각 절의 첫 문장(요청은 요청문)을 그대로 가져온다.
    """
    out = []
    for s in secs:
        line = s.get("사람글") or (s["문장"][0] if s["문장"] else "")
        if line:
            out.append((s["키"], _first_sentence(line)))
    return out


# ══════════════════════════════════════════════════════════════════════════
# HTML — A4 로 인쇄된다. 파일 하나로 열린다.
# ══════════════════════════════════════════════════════════════════════════
# 색은 넷까지 — 먹색 본문 · 회색 보조 · 강조 1색 · 위험 1색.
# 강조와 위험은 config.COLORS 에서 받는다. 파일 안에서 새로 만들지 않는다.
_CSS = """
@page { size: A4; margin: 18mm 16mm; }
/* 색은 넷 — 먹색 본문 · 회색 보조 · 강조 1 · 위험 1.
   선과 머리행 배경은 새 색이 아니라 먹색을 옅게 쓴 것이다. */
:root { --ink:__INK__; --sub:__SUB__;
        --accent:__ACCENT__; --danger:__DANGER__;
        --line:rgba(26,26,26,.14); --head:rgba(26,26,26,.045); }
* { box-sizing:border-box; }
body { margin:0; background:#fff; color:var(--ink);
       font:10.5pt/1.65 "Malgun Gothic","Nanum Gothic","Apple SD Gothic Neo",sans-serif; }
.sheet { max-width:180mm; margin:0 auto; padding:16mm 6mm 24mm; }
h1 { font-size:17pt; margin:0 0 4px; line-height:1.35; }
.meta { color:var(--sub); font-size:8.5pt; margin:0 0 14px; }
.box { border:1px solid var(--line); border-left:3px solid var(--accent);
       padding:11px 13px; margin:0 0 20px; }
.box dl { margin:0; display:grid; grid-template-columns:64px 1fr; gap:3px 10px; }
.box dt { color:var(--sub); font-size:8.5pt; padding-top:2px; }
.box dd { margin:0; }
section { margin:0 0 18px; }
h2 { font-size:12pt; margin:0; page-break-after:avoid; break-after:avoid; }
.q { color:var(--sub); font-size:8.5pt; margin:1px 0 8px;
     page-break-after:avoid; break-after:avoid; }
p { margin:0 0 6px; }
figure { margin:10px 0 6px; page-break-inside:avoid; break-inside:avoid; }
table { border-collapse:collapse; width:100%; font-size:9pt; margin:8px 0 0;
        page-break-inside:avoid; break-inside:avoid; }
th, td { text-align:left; padding:5px 8px; border:0;
         border-bottom:1px solid var(--line); vertical-align:top; }
/* 첫 열이 «이름» 인 표만 붙여 둔다 — 좁아져서 «구 분» 처럼 쪼개지지 않게.
   ★ 처음에는 모든 표에 걸었더니, 첫 열이 긴 문장인 표(환산에 쓴 가정)가
     한 줄로 늘어나 A4 밖으로 840px 까지 삐져나갔다. 화면에서는 안 보였다 —
     화면이 넓었기 때문이다. 종이 폭으로 재 보고서야 나왔다. */
table.kv th:first-child, table.kv td:first-child { white-space:nowrap; }
th { background:var(--head); font-weight:600; color:var(--sub); }
td.n, th.n { text-align:right; }
.num { font-variant-numeric:tabular-nums; font-weight:700; }
.unit { font-size:.85em; font-weight:400; }
.todo { color:var(--danger); font-weight:600; }
.ask { border-top:1px solid var(--ink); margin-top:12px; padding-top:10px;
       font-size:11.5pt; font-weight:700; }
.said { white-space:pre-wrap; margin:0 0 6px; }
.note { color:var(--sub); font-size:8.5pt; margin-top:4px; }
"""
# ★ 처음에는 % 치환으로 색을 넣었다가 바로 터졌다 — CSS 안의
#   width:100% 같은 글자가 서식 기호로 읽혔기 때문이다.
#   서식 문자열은 내용이 기호를 안 쓸 때만 안전하다. CSS 는 그런 내용이 아니다.
_CSS = (_CSS.replace("__ACCENT__", config.COLORS["warn"])
            .replace("__DANGER__", config.COLORS["block"])
            .replace("__INK__", config.DOC_COLORS["ink"])
            .replace("__SUB__", config.DOC_COLORS["sub"]))

# 숫자는 굵게, 뒤에 붙는 단위는 한 단계 작게.
_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)(%p|%|건|명|개월|장|건씩)?")


def _mark(text) -> str:
    s = html.escape(str(text), quote=False)
    s = s.replace(TODO, f'<span class="todo">{TODO}</span>')
    s = s.replace(NOT_WRITTEN, f'<span class="todo">{NOT_WRITTEN}</span>')
    return _NUM.sub(
        lambda m: f'<span class="num">{m.group(1)}</span>'
                  + (f'<span class="unit">{m.group(2)}</span>' if m.group(2) else ""),
        s)


# 첫 열을 «이름» 으로 볼 글자 수 상한. 넘으면 문장이지 이름이 아니다.
# 근거: 가장 긴 이름이 «면접 통과 → 최종 합격»(13자)이고, 가정 표의 첫 칸은
#       100자가 넘는 문장이다. 그 사이 어디를 잘라도 같은 결과라 16으로 둔다.
LABEL_MAX = 16


def _is_kv(df) -> bool:
    """첫 열이 이름 열인가. 표의 내용을 보고 정한다 — CSS 가 못 보는 것이다."""
    first = df.columns[0]
    vals = [str(first)] + [fmt_value(v, first) for v in df[first]]
    return max(len(v) for v in vals) <= LABEL_MAX


def _table_html(df) -> str:
    if df is None or len(df) == 0:
        return ""
    head = "".join(f'<th class="{"n" if _numeric(df[c]) else ""}">'
                   f'{html.escape(str(c), quote=False)}</th>' for c in df.columns)
    body = []
    for _, r in df.iterrows():
        tds = []
        for c in df.columns:
            v = r[c]
            cls = "n" if _numeric(df[c]) else ""
            tds.append(f'<td class="{cls}">{_cell(v, c)}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    cls = ' class="kv"' if _is_kv(df) else ""
    return (f'<table{cls}><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def _numeric(col) -> bool:
    return pd.api.types.is_numeric_dtype(col)


_PCT_COLS = ("전환율", "비중", "직전", "누적", "대비", "율")


def fmt_value(v, name="") -> str:
    """표 한 칸을 사람이 읽는 값으로. **화면과 문서가 이 함수 하나를 쓴다.**

    ★ 화면은 st.dataframe 이 원값을 그대로 보여 주고 문서는 18.1% 로 보여 줬다.
      같은 표인데 0.1806 과 18.1% 로 갈렸다 — 계산이 한 곳이어도 «보이는 값»이
      두 곳에서 만들어지면 똑같이 갈린다.
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    # 열 이름으로 비율을 알아본다. «첫 단계 대비» 를 빼먹었더니 원시 실수
    # 0.1806087482362427 이 그대로 인쇄됐다.
    if isinstance(v, float) and any(k in str(name) for k in _PCT_COLS):
        return f"{v * 100:.1f}%"
    if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer()):
        return f"{int(v):,}"
    return str(v)


def display_table(df):
    """화면에 그대로 띄울 수 있게 모든 칸을 문자열로 바꾼 사본."""
    if df is None or len(df) == 0:
        return df
    out = df.copy()
    for c in out.columns:
        out[c] = [fmt_value(v, c) for v in df[c]]
    return out


def _cell(v, name="") -> str:
    s = fmt_value(v, name)
    return '<span class="todo">—</span>' if s == "—" else _mark(s)


def _sample(sample) -> str:
    """표본 규모 한 구절. 없으면 아무것도 안 쓴다.

    ★ 4,961 이 한 사람 것인지 여러 사람 것인지가 문서에 없었다. 읽는 사람이
      제일 먼저 묻는 것이었는데 머리글 한 줄이면 되는 것이었다.
    """
    if not sample:
        return ""
    part = [f"{v:,}{u}" for k, u in (("지원자", "명"), ("공고", "개"))
            for v in [sample.get(k)] if v]
    return (" · 표본 " + " · ".join(part)) if part else ""


_SRC_NAMES = {"applicants": "지원자", "postings": "공고",
              "applications": "지원", "application_events": "단계 이벤트"}


def _source(src) -> str:
    """어느 표를 읽었고 입구 검사가 어떻게 나왔는가. 없으면 아무것도 안 쓴다.

    ★ 화면(게이트 1)은 이 검사를 늘 돌리고 있었는데 문서만 결과를 안 실었다.
      되짚어 볼 수 없는 숫자는 근거가 아니라 주장이다. 경고를 숨기지 않는다 —
      경고가 0인 데이터가 아니라, 경고를 세어 두고 넘긴 데이터다.
    """
    if not src:
        return ""
    t = src.get("표") or {}
    c = src.get("검사") or {}
    부 = []
    for key, ko in _SRC_NAMES.items():
        if key not in t:
            continue
        n, uniq = t[key], src.get("고유지원")
        부.append(f"{ko} {n:,}행(고유 {uniq:,})"
                  if key == "applications" and uniq and uniq != n
                  else f"{ko} {n:,}행")
    검 = ""
    if c:
        검 = (f" · 입구 검사 {sum(c.values())}건 — 차단 {c.get('block', 0)} · "
              f"경고 {c.get('warn', 0)} · 통과 {c.get('ok', 0)}")
        if src.get("경고종류"):
            검 += f" (경고 종류: {' · '.join(src['경고종류'])})"
    if not 부 and not 검:
        return ""
    return ('<p class="meta">출처 표 ' + str(len(부)) + '개 — '
            + html.escape(" · ".join(부) + 검,
                                                  quote=False) + "</p>\n")


def to_html(secs, topic=None, sample=None, source=None) -> str:
    """단일 파일 HTML. 빈 절은 그리지 않는다. 외부 CSS·이미지·CDN 을 쓰지 않는다."""
    body = []
    summary = one_pager(secs)
    if summary:
        dl = "".join(f"<dt>{html.escape(config.word('요약', k), quote=False)}"
                     f"</dt><dd>{_mark(v)}</dd>" for k, v in summary)
        body.append(f'<div class="box"><dl>{dl}</dl></div>')
    for s in secs:
        if not s["문장"] and not s.get("사람글") and s.get("표") is None:
            continue                        # 빈 절은 그리지 않는다
        part = [f'<section><h2>{html.escape(s["제목"], quote=False)}</h2>'
                f'<p class="q">{html.escape(s["질문"], quote=False)}</p>']
        for line in s["문장"]:
            part.append(f"<p>{_mark(line)}</p>")
        if s.get("차트"):
            part.append(f'<figure>{s["차트"]}</figure>')
        part.append(_table_html(s.get("표")))
        if s.get("사람글"):
            # ★ 사람이 쓴 글은 문단으로 나뉘어 있는데 한 <p> 에 통째로 넣고
            #   있었다. 위험 절은 .said 의 pre-wrap 이 줄바꿈을 살려 줘서 티가
            #   안 났고, 요청 절은 .ask 에 그것이 없어 **세 문단이 한 덩어리**로
            #   붙어 나왔다. 한 문단일 때는 아무 문제가 없다가 문단이 늘자 났다.
            #   그리고 강조는 **마지막 문단 하나**에만 건다 — 다 굵게 하면
            #   아무것도 강조가 아니고, 결정문이 그 안에 묻힌다.
            paras = [x.strip() for x in
                     re.split(r"\n\s*\n", str(s["사람글"]).strip()) if x.strip()]
            for i, para in enumerate(paras):
                cls = ("ask" if s.get("강조") and i == len(paras) - 1 else "said")
                part.append(f'<p class="{cls}">{_mark(para)}</p>')
        part.append("</section>")
        body.append("".join(part))

    title = (topic or {}).get("제목", "제안")
    return (
        '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{html.escape(str(title), quote=False)}</title>\n'
        f"<style>{_CSS}</style>\n</head>\n<body>\n<div class=\"sheet\">\n"
        f'<h1>{html.escape(str(title), quote=False)}</h1>\n'
        f'<p class="meta">{html.escape(config.DATASET, quote=False)} · '
        f'{config.PERIOD[0]} ~ {config.PERIOD[1]} · 기준일 {config.AS_OF} · '
        f'세는 단위 {html.escape(str((topic or {}).get("세는 단위", "")), quote=False)}'
        f'{_sample(sample)}'
        f"</p>\n" + _source(source) + "\n".join(body)
        + "\n</div>\n</body>\n</html>\n")
