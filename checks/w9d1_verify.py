# -*- coding: utf-8 -*-
"""발견.md 의 숫자가 지금 조회한 값과 같은가.

교안이 «조회하지 않은 값을 넣지 마»라고 했다. 그런데 문서를 손으로 쓰는 순간
반드시 어긋난다 — 데이터가 늘거나, 반올림 규칙이 바뀌거나, 옮겨 적다 틀린다.
그래서 문서에 적힌 문장을 다시 조회해서 대조한다.

여기서 걸리면 고칠 쪽은 **문서**다. 값을 문서에 맞추는 것이 아니다.

    python checks/w9d1_verify.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()      # 출력 때문에 죽지 않게. checks/_console.py 참고

from core import config, context, metrics  # noqa: E402
from checks.w9d1_evidence import _shown, _shown_gap, load  # noqa: E402

DOC = ROOT / "발견.md"


def claims():
    """문서에 적혀 있어야 하는 문자열을 지금 조회해서 만든다."""
    t = load()
    out = []

    def need(label, s):
        out.append((label, str(s)))

    # ── 발견 1 · 3 — 축별 분해 ──────────────────────────────────────────
    for axis, unit, tag in (("공고 경쟁도", "건", "발견 1"), ("학력", "명", "발견 3")):
        g = metrics.funnel_by(t, axis)
        v = g.loc[g["전환율"].notna()]
        hi, lo = v.loc[v["전환율"].idxmax()], v.loc[v["전환율"].idxmin()]
        need(f"{tag} 낮은 칸 값", f"{_shown(lo['전환율'])}%")
        need(f"{tag} 낮은 칸 분자/분모",
             f"({int(lo['도달']):,}{unit} / {int(lo['시작']):,}{unit})")
        need(f"{tag} 비교 대상 값", f"{_shown(hi['전환율'])}%")
        need(f"{tag} 비교 분자/분모",
             f"({int(hi['도달']):,}{unit} / {int(hi['시작']):,}{unit})")
        need(f"{tag} 격차",
             f"{round(_shown(hi['전환율']) - _shown(lo['전환율']), 1)}%p")
        need(f"{tag} 비중", f"{_shown(lo['비중'])}%")
        need(f"{tag} 가장 작은 칸", f"{int(g['시작'].min()):,}")
        need(f"{tag} 흔들림", f"{1 / int(g['시작'].min()) * 100:.3f}%p")

    # ── 발견 2 — 구멍 둘 (사람 기준) ────────────────────────────────────
    f = metrics.funnel(t, "person").copy()
    f["이탈"] = f["인원"].shift(1) - f["인원"]
    step = f.iloc[1:]
    wr = step["직전 대비"].astype(float).idxmin()
    wd = step["이탈"].astype(float).idxmax()
    tot_out = int(f.iloc[0]["인원"]) - int(f.iloc[-1]["인원"])
    need("발견 2 최다이탈 전환율", f"{_shown(f.iloc[wd]['직전 대비'])}%")
    need("발견 2 최다이탈 분자/분모",
         f"({int(f.iloc[wd]['인원']):,}명 / {int(f.iloc[wd-1]['인원']):,}명)")
    need("발견 2 최다이탈 인원", f"{int(f.iloc[wd]['이탈']):,}명")
    need("발견 2 병목 전환율", f"{_shown(f.iloc[wr]['직전 대비'])}%")
    need("발견 2 병목 분자/분모",
         f"({int(f.iloc[wr]['인원']):,}명 / {int(f.iloc[wr-1]['인원']):,}명)")
    need("발견 2 전환율 격차",
         f"{round(_shown(f.iloc[wd]['직전 대비']) - _shown(f.iloc[wr]['직전 대비']), 1)}%p")
    need("발견 2 전체 이탈", f"{tot_out:,}명")
    need("발견 2 이탈 대비 비중", f"{_shown(f.iloc[wd]['이탈'] / tot_out)}%")
    need("발견 2 첫 단계 대비 비중",
         f"{_shown(f.iloc[wd]['이탈'] / int(f.iloc[0]['인원']))}%")

    # ── 발견 4 — 건 기준 첫 관문 ────────────────────────────────────────
    fa = metrics.funnel(t, "application")
    first_out = int(fa.iloc[0]["인원"]) - int(fa.iloc[1]["인원"])
    tot_out_a = int(fa.iloc[0]["인원"]) - int(fa.iloc[-1]["인원"])
    need("발견 4 첫 구간 전환율", f"{_shown(fa.iloc[1]['직전 대비'])}%")
    need("발견 4 첫 구간 분자/분모",
         f"({int(fa.iloc[1]['인원']):,}건 / {int(fa.iloc[0]['인원']):,}건)")
    need("발견 4 뒤 구간 둘",
         f"{_shown(fa.iloc[2]['직전 대비'])}% · {_shown(fa.iloc[3]['직전 대비'])}%")
    need("발견 4 이 구간 이탈", f"{first_out:,}건")
    need("발견 4 전체 이탈", f"{tot_out_a:,}건")
    need("발견 4 비중", f"{_shown(first_out / tot_out_a)}%")

    # ── 발견 5 — 안 갈리는 축들 ─────────────────────────────────────────
    for axis in ("고용 형태", "과제 유무", "직무", "산업"):
        g = metrics.funnel_by(t, axis)
        v = g.loc[g["전환율"].notna(), "전환율"]
        need(f"발견 5 {axis} 격차", f"{_shown_gap(v) * 100:.1f}%p")
        need(f"발견 5 {axis} 가장 작은 칸", f"{int(g['시작'].min()):,}")
        need(f"발견 5 {axis} 흔들림", f"{1 / int(g['시작'].min()) * 100:.3f}%p")

    # ── 못 쓰는 숫자 · 정의 ─────────────────────────────────────────────
    ctx = context.build(t)
    coh = ctx["cohort"]
    for _, r in coh[coh["못 믿을 사유"].notna()].iterrows():
        need(f"감춘 코호트 {r['코호트']} 인원", f"{r['코호트']} ({int(r['인원'])}명)")
    m = metrics.monthly(t)[config.MAIN_METRIC].dropna()
    import pandas as pd
    cut = pd.Period(config.VALID_UNTIL[:7], freq="M")
    inc = float(m.mean())
    exc = float(m[[i for i in m.index if pd.Period(str(i), freq="M") <= cut]].mean())
    need("유효 구간 포함 평균", f"{_shown(inc, 2)}%")
    need("유효 구간만 평균", f"{_shown(exc, 2)}%")
    need("두 값의 차이", f"{round(_shown(inc, 2) - _shown(exc, 2), 2)}%p")

    ap = t["applications"]
    need("원본 행 수", f"{len(ap):,}")
    need("고유 키 수", f"{ap['application_id'].nunique():,}")
    need("키 중복 건수", f"중복 {len(ap) - ap['application_id'].nunique()}건")
    return out


def no_cause():
    """발견에 원인이 섞이지 않았는가.

    8주차에 만든 인과 표현 검사기를 그대로 쓴다. 도구가 남아 있으면
    새 문서에도 걸 수 있다 — 그게 도구를 만든 값이다.
    교안: «원인을 쓰지 마. 때문에가 들어가면 그건 오늘 것이 아니다.»
    """
    from report import sections as S
    hits = S.check_phrasing({"발견.md": DOC.read_text(encoding="utf-8")})
    print(f"\n인과 단정 표현 검사 — {len(hits)}건")
    for h in hits:
        print(f"  «{h['단어']}» {h['문맥'][:80]}")
    if not hits:
        print("  발견에 원인이 섞이지 않았다. 원인은 내일 데이터로 좁힌다.")
    return hits


# 「크기와 순서」 표의 한 줄. 손으로 곱해 적은 자리라 특히 잘 어긋난다.
_ROW = re.compile(
    r"^\|\s*\d+\s+(?P<축>[^|]+?)\s*\|\s*(?P<격차>[\d.]+)%p\s*"
    r"\|\s*(?P<비중>[\d.]+)%\s*\|\s*\**(?P<크기>[\d.]+)\**\s*"
    r"\|\s*\+(?P<건수>[\d,]+)(?P<단위>건|명)\s*\|")


def derived(text):
    """문서에 «곱해서 적어 둔» 값을 다시 곱해 본다.

    ★ 조회값 대조는 통과하는데 이 자리는 안 잡혔다. 조회한 값은 옮겨 적었고
      **곱한 값은 손으로 곱했기** 때문이다. 세 줄이 틀려 있었다(2.75·0.55·0.13)
      — 전부 반올림 전 값으로 곱한 것이다. 화면에 찍히는 값끼리 곱해야
      읽는 사람이 암산으로 맞춰 볼 수 있다.
    """
    t = load()
    years = metrics._period_years()
    out = []
    for ln in text.splitlines():
        m = _ROW.match(ln.strip())
        if not m:
            continue
        axis = m.group("축").strip()
        if axis not in metrics.AXES:
            continue
        g = metrics.funnel_by(t, axis)
        v = g.loc[g["전환율"].notna()]
        hi, lo = v.loc[v["전환율"].idxmax()], v.loc[v["전환율"].idxmin()]
        gap = round(_shown(hi["전환율"]) - _shown(lo["전환율"]), 1)
        share = _shown(lo["비중"])
        size = round(gap * share / 100, 2)
        cnt = round(gap / 100 * int(lo["시작"]) / years)
        for name, got, want in (("격차", float(m.group("격차")), gap),
                                ("비중", float(m.group("비중")), share),
                                ("크기", float(m.group("크기")), size),
                                ("건수", float(m.group("건수").replace(",", "")),
                                 float(cnt))):
            out.append((f"{axis} {name}", got == want, got, want))
    return out


# 축 후보 비교표가 적혀 있는 자리. 한 표가 네 곳에 **손으로 복사돼** 있다.
# 계산이 한 곳에서 나와도 «옮겨 적은 값»은 한 곳이 아니다 — 실제로 두 값이
# 어긋나 있었다 (산업 4.7 vs 4.8 · 공고 경쟁도 10.4 vs 10.3).
#
# ★ core/metrics.py 와 checks/w9d1_evidence.py 의 주석에도 원값 «10.4%p» 가 있지만
#   그 둘은 **틀린 예로** 적어 둔 것이다. 여기서 안 본다 — 규칙을 설명하는
#   문장까지 고치면 그 규칙이 왜 생겼는지가 사라진다.
GAP_DOCS = ["core/config.py", "README.md", "발표.md", "판단기준.md"]
_PP = re.compile(r"(\d+" + chr(92) + r".\d)\s*%p")


# 원값을 적어도 되는 자리가 있다 — **왜 그 값을 쓰면 안 되는지 설명하는 문장.**
# 그 자리까지 고치면 규칙만 남고 까닭이 사라진다.
#
# 파일 단위로 봐주지 않는다. 그러면 그 파일에 새로 새어 나온 값도 같이 봐준다.
# 줄 단위로 보되, 표시가 «원값» 이라는 낱말이다 — 설명하는 문장은 예외 없이
# 그 낱말을 쓴다. 낱말을 안 쓰고 값만 적었다면 그건 설명이 아니라 주장이다.
RAW_MARK = "원값"


def axis_gaps():
    """축마다 격차를 두 가지로 낸다 — 표시값끼리 뺀 것과 원값끼리 뺀 것.

    문서가 적어야 하는 것은 앞의 것이다. 뒤의 것은 **문서에 있으면 안 되는 값**이라
    같이 낸다. 둘이 같은 축은 어차피 구분이 없다.
    """
    t = load()
    shown, raw = {}, {}
    for axis in metrics.AXES:
        g = metrics.funnel_by(t, axis)
        v = g.loc[g["전환율"].notna(), "전환율"]
        if len(v) < 2:
            continue
        shown[axis] = round(round(float(v.max()) * 100, 1)
                            - round(float(v.min()) * 100, 1), 1)
        raw[axis] = round((float(v.max()) - float(v.min())) * 100, 1)
    return shown, raw


def raw_slips():
    """원값으로 뺀 격차가 저장소 어디엔가 남아 있는가.

    ★ 앞의 copied_gaps() 는 «축 이름이 같은 줄에 있는 것»만 본다. 줄글로 적힌
      원값이 줄글로 섞인 «서류에서 10.4%p 벌어지고» 같은 문장은 못 잡는다.
      그래서 한 겹 더 둔다 —
      **어느 축의 원값 격차와 똑같은 수**가 문서에 있으면 옮겨 적다 새어 나온
      것이다. 표시값과 원값이 같은 축은 애초에 후보에서 빠지므로 오탐이 없다.
      (3.3%p 같은 다른 %p 는 어느 축의 원값도 아니라 안 걸린다)
      «원값» 이라고 밝힌 줄은 뺀다 — 왜 그 값을 쓰면 안 되는지 적은 자리다.
    """
    shown, raw = axis_gaps()
    나쁜값 = {f"{raw[a]:.1f}": a for a in raw if raw[a] != shown[a]}
    if not 나쁜값:
        return [], 나쁜값
    hit = []
    for f in sorted(ROOT.rglob("*.md")) + sorted(ROOT.rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(("docs/", "outputs/", ".git")):
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if RAW_MARK in ln:      # 원값이라고 밝힌 자리는 설명이다
                continue
            for m in _PP.finditer(ln):
                if m.group(1) in 나쁜값:
                    hit.append((rel, i, m.group(1), 나쁜값[m.group(1)],
                                ln.strip()[:52]))
    return hit, 나쁜값


def copied_gaps():
    """문서 넷에 «X.X%p» 로 적힌 값이 조회로 나오는 값인가.

    어느 축의 값인지는 문장을 읽어야 알 수 있으므로, 여기서는
    **조회로 안 나오는 값이 적혀 있는가**만 본다. 그것만으로 4.7 과 10.4 가
    걸린다 — 옮겨 적다 어긋난 값은 어느 축에서도 안 나오기 때문이다.
    같은 줄에 축 이름이 있는 것만 본다. 이 문서들에는 축 격차가 아닌 %p 도 있다.
    """
    want = {f"{v:.1f}" for v in axis_gaps()[0].values()}
    names = list(metrics.AXES)
    bad = []
    for name in GAP_DOCS:
        f = ROOT / name
        if not f.exists():
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not any(a in ln for a in names):
                continue
            for m in _PP.finditer(ln):
                if m.group(1) not in want:
                    bad.append((name, i, m.group(1), ln.strip()[:58]))
    return bad, sorted(want)


def main():
    if not DOC.exists():
        print(f"{DOC.name} 가 없다.")
        return 1
    text = DOC.read_text(encoding="utf-8")
    rows = claims()
    missing = [(lab, s) for lab, s in rows if s not in text]

    print(f"\n발견.md 대조 — 조회로 만든 문자열 {len(rows)}개\n")
    for lab, s in rows:
        print(f"  {'있음' if s in text else '없음':<4} {lab:<28} «{s}»")
    print()
    if missing:
        print(f"문서에 없는 값 {len(missing)}개 — 고칠 쪽은 문서다:")
        for lab, s in missing:
            print(f"  · {lab} → «{s}»")
        return 1
    print(f"{len(rows)}개 전부 문서에 있다. 조회하지 않은 값은 없다.")

    print("\n곱해서 적어 둔 값을 다시 곱한다 — 「크기와 순서」 표\n")
    dv = derived(text)
    for label, good, got, want in dv:
        print(f"  {'같음' if good else '다름':<4} {label:<20} 문서 {got:<10} "
              f"조회 {want}")
    bad = [d for d in dv if not d[1]]
    if bad:
        print(f"\n어긋난 값 {len(bad)}개 — 고칠 쪽은 문서다.")
        return 1
    print(f"\n{len(dv)}개 전부 같다.")

    print("\n문서 넷에 손으로 옮겨 적은 축 격차\n")
    bad2, want = copied_gaps()
    print("  조회로 나오는 값: "
          + " · ".join(w + "%p" for w in want))
    for name, i, got, ln in bad2:
        print(f"  [다름] {name}:{i}  «{got}%p» — {ln}")
    if bad2:
        print(f"\n조회로 안 나오는 값 {len(bad2)}곳 — 고칠 쪽은 문서다.")
        return 1
    print(f"  문서 {len(GAP_DOCS)}개 전부 조회값과 같다.")

    hit, 나쁜값 = raw_slips()
    print("  원값으로 빼면 나오는 값: "
          + (" · ".join(f"{v}%p({a})" for v, a in 나쁜값.items()) or "없음")
          + f" — 저장소 전체에서 찾는다 («{RAW_MARK}» 이라고 밝힌 줄은 뺀다)")
    for rel, i, got, axis, ln in hit:
        print(f"  [새어 나옴] {rel}:{i}  «{got}%p» = {axis} 의 원값 — {ln}")
    if hit:
        print(f"\n원값으로 뺀 값 {len(hit)}곳 — 표시값끼리 뺀 값으로 고친다.")
        return 1
    print("  저장소 어디에도 안 남아 있다.")
    return 1 if no_cause() else 0


if __name__ == "__main__":
    raise SystemExit(main())
