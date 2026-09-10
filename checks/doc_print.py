# -*- coding: utf-8 -*-
"""제안서를 실제 브라우저로 A4 에 인쇄해 본다.

AppTest 도, HTML 문자열 검사도 «종이에 얹었을 때»를 모른다.
표 한 칸이 안 접혀서 문서가 840px 로 늘어나 A4 밖으로 나간 적이 있는데,
화면은 넓어서 멀쩡해 보였고 자가 검사 39개도 전부 통과했다.
**폭은 재 봐야 안다.**

    pip install playwright pypdf && python -m playwright install chromium
    python checks/doc_print.py

shots.py 와 같은 이유로 requirements.txt 에 넣지 않는다 — 배포처가 브라우저를
내려받게 만들 이유가 없다. 그래서 run_all.py 에도 넣지 않았다. 손으로 돌린다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

from core import config, loader, metrics  # noqa: E402
from report import proposal as P  # noqa: E402

# A4 폭 210mm 에서 좌우 여백 16mm 씩을 뺀 것을 96dpi 로 옮긴 값.
# 브라우저가 인쇄할 때 잡는 폭이 이것이다.
A4_PX = round((210 - 16 * 2) / 25.4 * 96)

# 넘치는 요소를 찾는다. 폭이 아니라 «오른쪽 끝»을 본다 —
# 폭이 맞아도 왼쪽으로 밀려 있으면 오른쪽이 잘린다.
FIND_OVER = """(w) => {
  const out = [];
  document.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.right > w + 1) out.push(
      e.tagName + ' ' + (e.className || '') + ' → ' +
      Math.round(r.right) + 'px  «' +
      (e.textContent || '').trim().slice(0, 30) + '»');
  });
  return out.slice(0, 3);
}"""


def main():
    from playwright.sync_api import sync_playwright
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

    t = {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
         for n in config.TABLES}
    cards = P.load_cards()
    topics = metrics.proposal_topics(t)
    tmp = config.OUT / "_print"
    tmp.mkdir(parents=True, exist_ok=True)

    print(f"\n제안서를 A4 에 얹어 본다 — 본문 폭 {A4_PX}px · 후보 {len(topics)}개\n")
    bad, pages = [], []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": A4_PX, "height": 1100})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        for x in topics:
            ev = metrics.topic_evidence(t, x)
            secs = P.build(x, ev, cards, P.human_for(x))
            f = tmp / (x["키"].replace(":", "_").replace(" ", "") + ".html")
            f.write_text(P.to_html(secs, x), encoding="utf-8")
            page.goto(f.as_uri())
            page.wait_for_timeout(250)
            over = page.evaluate(FIND_OVER, A4_PX)
            n = ""
            if PdfReader:
                pdf = f.with_suffix(".pdf")
                page.pdf(path=str(pdf), format="A4", print_background=True)
                n = f"{len(PdfReader(str(pdf)).pages)}쪽"
                pages.append(len(PdfReader(str(pdf)).pages))
            mark = "걸림" if over else "지킴"
            if over:
                bad.append((x["제목"], over))
            print(f"  [{mark}] {x['제목'][:34]:<34} {n}")
            for o in over:
                print(f"          넘침 {o}")
        b.close()

    print()
    if errs:
        print(f"[걸림] 브라우저 오류 {len(errs)}건 — {errs[0][:90]}")
    if pages:
        print(f"쪽수 {min(pages)} ~ {max(pages)}쪽")
    print(f"{len(topics) - len(bad)}/{len(topics)} 가로로 안 넘친다"
          + ("" if bad else " · 브라우저 오류 0"))
    return 1 if (bad or errs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
