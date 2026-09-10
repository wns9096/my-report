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
    return 1 if no_cause() else 0


if __name__ == "__main__":
    raise SystemExit(main())
