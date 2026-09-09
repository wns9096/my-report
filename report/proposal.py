# -*- coding: utf-8 -*-
"""제안서 조립층 — 9주차 Day2.

자동으로 쓴다 → 한 장 요약 · 하지 말 것 · 다시 할 것 · 할 것 · 부록(근거 상세)
사람이 쓴다   → 이 제안이 틀린다면 · 적용 (후보는 자동, 고르는 것은 사람)

가르는 기준은 하나다 — **이 절을 데이터에서 다시 조회하면 똑같이 나오는가.**
그렇다면 자동, 아니면 사람이다. `sections.py` 와 같은 이유로 오른쪽을
자동화하지 않는다. 자동화하는 순간 책임의 주체가 사라진다.

`sections.py` 는 건드리지 않는다. 리포트와 제안서는 다른 문서다.
같은 원칙을 따로 된 파일에 적용한다. 다만 인과 표현 검사는 **재사용한다** —
금지어 목록을 두 곳에 두면 한 곳만 고쳐지고, 그때부터 두 문서가 다른 기준으로
검사된다.
"""
import html
import re
from pathlib import Path

from core import config
from report import pdf as pdfmod
# ★ 새로 만들지 않는다. sections.py 의 것을 그대로 쓴다.
from report.sections import BANNED, NOT_WRITTEN, SUGGEST, check_phrasing

# 이 이름들은 이 모듈을 거친다. 화면과 검사가 sections 와 proposal 을
# 둘 다 임포트하지 않게 하려고 다시 내보낸다 — 새로 만들지는 않는다.
__all__ = ["build", "load_cards", "card_problems", "to_html", "build_pdf",
           "auto_sections", "next_candidates", "todo_count", "is_todo",
           "ORDER", "KINDS", "HUMAN_TITLES", "TODO",
           "BANNED", "SUGGEST", "check_phrasing", "NOT_WRITTEN"]

CARDS_PATH = config.ROOT / "제안카드.md"
CRITERIA_PATH = config.ROOT / "판단기준.md"

# 못 채운 자리에 쓰는 말. 카드에 이 말이 있으면 화면에도 이 말이 그대로 뜬다.
TODO = "미확인"

# 분류 셋. 순서가 곧 본문 순서다 — 바꾸지 않는다.
KINDS = ("하지 말 것", "다시 할 것", "할 것")

# ── 절 순서 — 고정 ────────────────────────────────────────────────────────
# 「할 것」을 앞에 두면 읽는 사람이 거기서 멈추고 「하지 말 것」은 안 읽힌다.
# 멈추자는 제안이 가장 안 읽히므로 가장 앞에 둔다.
SUMMARY = "한 장 요약"
WRONG = "이 제안이 틀린다면"
NEXT = "적용"
APPENDIX = "부록 (근거 상세)"

ORDER = [SUMMARY, *KINDS, WRONG, NEXT, APPENDIX]
HUMAN_TITLES = (WRONG, NEXT)

PLACEHOLDERS = {
    WRONG: "이 제안이 틀렸다면 무엇 때문인지, 확인하려면 무엇을 보면 되는지 "
           "적으십시오.",
    NEXT: "위 후보 중 무엇을 다음에 볼 것인지, 왜 그것인지 적으십시오.",
}


# ══════════════════════════════════════════════════════════════════════════
# 카드 읽기 — 화면은 읽기만 한다
# ══════════════════════════════════════════════════════════════════════════
_FIELD = re.compile(r"^-\s*([^:]{1,10}):\s*(.*)$")
_FIELDS = ("제목", "분류", "확신도", "근거", "크기", "비용", "효과", "되돌림", "출처")


def load_cards(path=None) -> dict:
    """제안카드.md 를 딕셔너리로 읽는다.

    이 파일이 원본이다. 여기서 고치지 않고, 여기서 계산하지도 않는다.
    """
    p = Path(path) if path else CARDS_PATH
    if not p.exists():
        return {"cards": [], "원본": p.name, "조회": "", "본문": ""}
    text = p.read_text(encoding="utf-8")
    m = re.search(r"조회 일시:\s*(\S+\s+\S+)", text)

    cards = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        lines = block.splitlines()
        f = {}
        for ln in lines[1:]:
            mm = _FIELD.match(ln.strip())
            if mm and mm.group(1).strip() in _FIELDS:
                f[mm.group(1).strip()] = mm.group(2).strip()
        if f.get("분류") in KINDS:
            f["카드"] = lines[0].strip()
            cards.append(f)
    return {"cards": cards, "원본": p.name,
            "조회": m.group(1) if m else "", "본문": text}


def card_problems(cards: list[dict]) -> list[str]:
    """근거 없는 제안을 막는다. 차단은 실패가 아니다 — 오늘의 결과일 수 있다."""
    bad = []
    if not cards:
        bad.append("카드가 한 장도 없다. 발견.md 로 돌아가 근거 넷이 갖춰진 "
                   "문장부터 다시 고른다.")
        return bad
    if not any(c["분류"] == "하지 말 것" for c in cards):
        bad.append("「하지 말 것」이 하나도 없다. 지금 하는 게 다 옳을 리 없다.")
    for c in cards:
        t = c.get("제목", c["카드"])
        g = c.get("근거", "")
        if "/" not in g:
            bad.append(f"「{t}」 근거에 분자·분모가 없다.")
        if "비중" not in g:
            bad.append(f"「{t}」 근거에 비중이 없다. 비중을 모르면 큰일인지 모른다.")
        if c["분류"] == "할 것" and not c.get("효과", "").startswith("실측"):
            bad.append(f"「{t}」 효과를 실측하지 않았는데 「할 것」에 있다. "
                       f"「다시 할 것」으로 옮긴다.")
    return bad


def is_todo(v: str) -> bool:
    return bool(v) and v.startswith(TODO)


def _size(c) -> float:
    """크기 숫자만 뽑는다. 「미확인」이면 견줄 수 없으므로 -1."""
    m = re.match(r"([0-9]+(?:\.[0-9]+)?)", c.get("크기", ""))
    return float(m.group(1)) if m else -1.0


# ══════════════════════════════════════════════════════════════════════════
# 자동으로 쓰는 절
# ══════════════════════════════════════════════════════════════════════════
def _a_summary(cards, data) -> str:
    """넷을 넘기지 않는다. 다섯째 줄이 생기면 잘못 조립한 것이다.

    배경·목적은 여기 넣지 않는다 — 부록으로 뺀다.
    """
    big = max(cards, key=_size) if cards else None

    # 발견 — 크기가 가장 큰 카드의 근거를 그대로 옮긴다. 표본은 근거 줄로 뺀다.
    if big:
        ev = big["근거"].split(" · 표본")[0]
        ev = re.sub(r"^값\s*", "", ev)
        sample = big["근거"].split("표본", 1)[1].strip() if "표본" in big["근거"] else TODO
    else:
        ev, sample = TODO, TODO

    # 제안 — 본문과 같은 순서로 제목만 나열한다
    parts = []
    for k in KINDS:
        titles = [f"「{c.get('제목', c['카드'])}」" for c in cards if c["분류"] == k]
        parts.append(f"{k} " + (" ".join(titles) if titles else "(카드 없음)"))

    # 불확실 — 못 채운 자리 중 크기가 가장 큰 카드의 것. 효과부터 본다.
    # 효과를 먼저 보는 이유: 읽는 사람이 움직이는 근거가 효과다.
    unc = TODO
    for c in sorted(cards, key=_size, reverse=True):
        for fld in ("효과", "비용", "크기", "되돌림"):
            if is_todo(c.get(fld, "")):
                unc = f"「{c.get('제목', c['카드'])}」의 {fld} · {c[fld]}"
                break
        if unc != TODO:
            break

    return "\n".join([
        f"발견    {ev}",
        f"제안    {' · '.join(parts)}",
        f"불확실  {unc}",
        f"근거    {data['조회']} 조회 · 표본 {sample} · 상세는 부록",
    ])


def _a_kind(cards, kind) -> str:
    """한 분류의 카드를 늘어놓는다. 카드에 없는 것은 쓰지 않는다."""
    mine = [c for c in cards if c["분류"] == kind]
    if not mine:
        return ("(카드 없음) 이 분류의 카드를 만들지 않았다. "
                "제안카드.md 의 「할 것 — 없다」에 왜인지 적어 두었다.\n"
                "빈 채로 내보낸다 — 채우면 정하지 않은 것을 정한 것처럼 만든다.")
    out = []
    for c in mine:
        out.append(f"「{c.get('제목', c['카드'])}」")
        for fld in ("근거", "비용", "효과", "되돌림"):
            # 한글은 폭이 두 배다. {:<4} 로 맞추면 「되돌림」 줄만 한 칸 밀린다.
            out.append(f"  {fld}{' ' * (8 - 2 * len(fld))}{c.get(fld, TODO)}")
        out.append(f"  (출처 {c.get('출처', TODO)} · 확신도 {c.get('확신도', TODO)})")
        out.append("")
    return "\n".join(out).rstrip()


def _a_appendix(cards, data) -> str:
    """근거 상세 — 카드의 근거 줄과 크기를 그대로 옮긴다. 새로 계산하지 않는다."""
    out = [f"원본 {data['원본']} · 조회 {data['조회']}",
           "아래 줄은 발견.md 문장을 카드로 옮긴 것이고, 이 절은 그 카드를 "
           "다시 옮긴 것이다. 계산은 어디서도 새로 하지 않는다.", ""]
    for c in cards:
        out.append(f"{c['카드']} — {c.get('제목', '')}")
        out.append(f"  출처    {c.get('출처', TODO)}")
        out.append(f"  근거    {c.get('근거', TODO)}")
        out.append(f"  크기    {c.get('크기', TODO)}")
        out.append("")
    return "\n".join(out).rstrip()


# ══════════════════════════════════════════════════════════════════════════
# 사람이 쓰는 절
# ══════════════════════════════════════════════════════════════════════════
_DECISION = re.compile(r"\*\*내가 내린 결정\*\*(.*?)(?=\n## |\Z)", re.S)


def next_candidates(path=None, blocks=2) -> list[str]:
    """판단기준.md 의 최근 「내가 내린 결정」 문장들.

    후보는 자동으로 나열하고, 그중 무엇을 고를지는 사람이 정한다.
    후보 자체는 편집할 수 없게 한다 — 자동으로 나온 것을 사람이 고치면
    판단기준.md 와 화면 중 어느 것이 진짜인지 알 수 없게 된다.
    """
    p = Path(path) if path else CRITERIA_PATH
    if not p.exists():
        return []
    out = []
    for tbl in _DECISION.findall(p.read_text(encoding="utf-8"))[-blocks:]:
        for ln in tbl.splitlines():
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 3 and not set(cells[0]) <= set("- "):
                if cells[0] in ("무엇",):
                    continue
                out.append(f"{cells[0]} → {cells[1]}")
    return out


def _h_body(title, human) -> str:
    return (human or {}).get(title, "").strip() or NOT_WRITTEN


# ══════════════════════════════════════════════════════════════════════════
# 조립
# ══════════════════════════════════════════════════════════════════════════
def build(cards: dict, human: dict | None = None) -> list[dict]:
    """절 목록을 돌려준다. 절마다 kind 가 auto 인지 human 인지 붙는다.

    kind 가 오늘의 채점 기준이다. 화면은 이 값으로만 편집 가능 여부를 가른다 —
    화면이 제목을 보고 분기하면 절이 하나 늘 때마다 화면도 고쳐야 한다.
    """
    items = cards.get("cards", [])
    secs = []
    for title in ORDER:
        if title == SUMMARY:
            secs.append({"title": title, "kind": "auto",
                         "body": _a_summary(items, cards)})
        elif title in KINDS:
            secs.append({"title": title, "kind": "auto",
                         "body": _a_kind(items, title)})
        elif title == APPENDIX:
            secs.append({"title": title, "kind": "auto",
                         "body": _a_appendix(items, cards)})
        elif title == WRONG:
            secs.append({"title": title, "kind": "human",
                         "body": _h_body(title, human),
                         "placeholder": PLACEHOLDERS[title],
                         "note": "문서 전체에 하나만 둔다. 카드마다 두면 "
                                 "아무도 안 읽는다."})
        elif title == NEXT:
            secs.append({"title": title, "kind": "human",
                         "body": _h_body(title, human),
                         "placeholder": PLACEHOLDERS[title],
                         "candidates": next_candidates(),
                         "note": "후보는 자동, 고르는 것은 사람이다."})
    return secs


def auto_sections(secs) -> dict:
    """인과 표현 검사에 넣을 자동 절만 골라 {제목: 본문} 으로."""
    return {s["title"]: s["body"] for s in secs if s["kind"] == "auto"}


def todo_count(secs) -> int:
    return sum(s["body"].count(TODO) for s in secs) + \
        sum(1 for s in secs if s["body"] == NOT_WRITTEN)


# ══════════════════════════════════════════════════════════════════════════
# 내보내기 — HTML
# ══════════════════════════════════════════════════════════════════════════
# 수업자료/제안서_템플릿.html 이 이 저장소에 없다. 구조와 클래스 이름
# (num · todo)만 교안에서 가져와 여기서 만든다. 외부 CSS·이미지·CDN 은 쓰지
# 않는다 — 인터넷 없이 열려야 한다.
_CSS = """
:root { --ink:#1a1a1a; --line:#d8dde3; --muted:#6b6b6b;
        --num:%(neutral)s; --todo:%(warn)s; }
* { box-sizing:border-box; }
body { margin:0; background:#fff; color:var(--ink);
       font:15px/1.7 "Malgun Gothic","Nanum Gothic","Apple SD Gothic Neo",sans-serif; }
.wrap { max-width:820px; margin:0 auto; padding:40px 20px 80px; }
h1 { font-size:24px; margin:0 0 6px; }
.meta { color:var(--muted); font-size:13px; margin-bottom:28px; }
section { border-top:1px solid var(--line); padding:22px 0 4px; }
h2 { font-size:17px; margin:0 0 10px; display:flex; align-items:baseline; gap:8px; }
.kind { font-size:11px; font-weight:600; letter-spacing:.04em;
        border:1px solid var(--line); border-radius:10px; padding:1px 7px;
        color:var(--muted); }
.kind.human { color:var(--todo); border-color:var(--todo); }
pre.body { margin:0; white-space:pre-wrap; word-break:break-word;
           font:inherit; }
.num { color:var(--num); font-variant-numeric:tabular-nums; font-weight:600; }
.todo { color:var(--todo); font-weight:600; }
ul.cand { margin:0 0 12px; padding-left:20px; color:var(--muted);
          font-size:13.5px; }
.note { color:var(--muted); font-size:12.5px; margin-top:8px; }
@media print { .wrap { padding:0; } section { break-inside:avoid; } }
""" % config.COLORS
# ★ 처음에는 이 CSS 에 16진수를 직접 적었다가 앱점검 규칙 6에 걸렸다.
#   판정 색을 파일 안에서 새로 만들면 config.COLORS 를 고쳐도 이 파일만 옛 색으로
#   남는다. 어제 조회 스크립트에서 겪은 것과 같은 일이다 —
#   **규칙을 한 곳에 넣는 것만으로는 안 된다. 새로 만드는 파일마다 다시 넣어야 한다.**
#   그래서 % 치환으로 config.COLORS 에서 받아 온다. 무채색(글자·선)은 판정 색이
#   아니라 여기 둔다.

# 숫자 · 백분율 · %p 를 감싼다. 이스케이프한 뒤에 돌린다 —
# html.escape(quote=False) 는 숫자를 만들지 않으므로 태그 안을 건드리지 않는다.
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?p?")


def _mark(text: str) -> str:
    s = html.escape(text, quote=False)
    s = s.replace(TODO, f'<span class="todo">{TODO}</span>')
    s = s.replace(NOT_WRITTEN, f'<span class="todo">{NOT_WRITTEN}</span>')
    return _NUM.sub(lambda m: f'<span class="num">{m.group(0)}</span>', s)


def to_html(secs: list[dict]) -> str:
    """단일 파일 HTML. 안 채워진 자리는 class="todo" 로 남긴다 — 채우지 않는다."""
    body = []
    for s in secs:
        kind_ko = "자동" if s["kind"] == "auto" else "사람"
        body.append(f'<section>\n<h2>{html.escape(s["title"], quote=False)}'
                    f'<span class="kind {s["kind"]}">{kind_ko}</span></h2>')
        if s.get("candidates"):
            body.append("<ul class=\"cand\">" + "".join(
                f"<li>{_mark(c)}</li>" for c in s["candidates"]) + "</ul>")
        body.append(f'<pre class="body">{_mark(s["body"])}</pre>')
        if s.get("note"):
            body.append(f'<p class="note">{_mark(s["note"])}</p>')
        body.append("</section>")
    return (
        "<!doctype html>\n<html lang=\"ko\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        f"<title>제안서 — {html.escape(config.DATASET, quote=False)}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
        f"<h1>제안서</h1>\n<p class=\"meta\">"
        f"{html.escape(config.DATASET, quote=False)} · "
        f"{config.PERIOD[0]} ~ {config.PERIOD[1]} · 기준일 {config.AS_OF}"
        f"</p>\n" + "\n".join(body) + "\n</div>\n</body>\n</html>\n")


# ══════════════════════════════════════════════════════════════════════════
# 내보내기 — PDF
# ══════════════════════════════════════════════════════════════════════════
def build_pdf(secs: list[dict], out_path=None):
    """리포트 PDF 와 같은 방식이다. 새 패턴을 만들지 않는다.

    폰트도 report/pdf.py 의 것을 그대로 쓴다. 못 찾으면 FontMissing 이 올라가고
    이 버튼만 안 된다 — 화면은 살아 있다.
    """
    out_path = out_path or (config.OUT / "proposal.pdf")
    reg, bold = pdfmod.find_font()      # 없으면 반쪽짜리를 남기기 전에 멈춘다

    doc = pdfmod.Doc()
    doc.add_font("KO", "", str(reg))
    doc.add_font("KO", "B", str(bold))
    doc.set_auto_page_break(True, margin=18)
    doc.add_page()

    doc.set_font("KO", "B", 18)
    doc.multi_cell(0, 10, "제안서", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("KO", "", 10)
    doc.set_text_color(*pdfmod._rgb("none"))
    doc.multi_cell(0, 6, f"{config.DATASET}  ·  {config.PERIOD[0]} ~ "
                         f"{config.PERIOD[1]}  ·  기준일 {config.AS_OF}",
                   new_x="LMARGIN", new_y="NEXT")
    doc.set_text_color(0)
    doc.ln(4)

    for s in secs:
        doc.set_font("KO", "B", 13)
        doc.ln(3)
        doc.multi_cell(0, 8, f"{s['title']}  "
                             f"[{'자동' if s['kind'] == 'auto' else '사람'}]",
                       new_x="LMARGIN", new_y="NEXT")
        if s.get("candidates"):
            doc.set_font("KO", "", 9)
            doc.set_text_color(*pdfmod._rgb("none"))
            for c in s["candidates"]:
                doc.multi_cell(0, 5, f"  · {c}", new_x="LMARGIN", new_y="NEXT")
            doc.set_text_color(0)
        doc.set_font("KO", "", 9.5)
        empty = s["body"] == NOT_WRITTEN
        if empty:
            doc.set_text_color(*pdfmod._rgb("muted"))
        doc.multi_cell(0, 5.4, s["body"].replace("**", ""),
                       new_x="LMARGIN", new_y="NEXT")
        if empty:
            doc.set_text_color(0)

    doc.output(str(out_path))
    return out_path
