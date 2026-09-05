# -*- coding: utf-8 -*-
"""앱점검 — 이번 주에 세운 규칙을 앱이 실제로 지키는지 기계로 훑는다.

규칙은 나흘치 판단 기준에서 왔다. 사람이 매번 눈으로 확인하면 빠뜨린다.
   1 임계값에 근거가 적혀 있는가        근거 없는 임계값은 남의 것이다
   2 검증 메시지에 숫자가 들어가는가     "실패"는 판단 재료가 아니다
   3 감춘 항목의 값이 어디에도 없는가    한쪽만 감추면 의미가 없다
   4 사람이 쓰는 장이 자동으로 안 채워지는가
   5 인과 단정 표현이 남아 있는가        자동 장과 사람 장 전부
   6 강조 색이 장식에 쓰이지 않는가      색을 하드코딩하면 의미가 흩어진다
   7 계산에 현재 시각이 섞이지 않는가    재현이 안 되는 코드가 된다
   8 게이트 기록에 근거가 비어 있지 않은가
   9 차단 규칙이 너무 많지 않은가        많으면 사람이 끄기 시작한다
  10 화면과 문서가 같은 계산을 쓰는가
  11 카드를 직접 쓴 HTML 로 그리지 않는가   테마가 바뀌면 그 부분만 색이 남는다
  12 근거에 «무엇에서 온 값인지»가 있는가   "적당해서"는 근거가 아니다
  13 저장소에 재배포 못 하는 파일이 없는가  폰트·비밀번호는 올리면 안 된다
  14 배포 설정 파일이 그 형식대로인가       packages.txt 는 주석을 못 읽는다
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config, context, gates, loader, validate  # noqa: E402
from report import sections as S  # noqa: E402

SRC = sorted(set(ROOT.glob("*.py")) | set(ROOT.glob("core/*.py"))
             | set(ROOT.glob("screens/*.py")) | set(ROOT.glob("viz/*.py"))
             | set(ROOT.glob("report/*.py")))

FINDINGS = []


def note(rule, ok, detail):
    FINDINGS.append({"규칙": rule, "결과": "지킴" if ok else "걸림", "내용": detail})
    return ok


def load():
    return {n: loader._cast_dates(loader._read(config.DATA / f"{n}.csv"))
            for n in config.TABLES}


def r1_threshold_reasons():
    """임계값 이름마다 근거 주석이 붙어 있는가.

    ★ 이 규칙은 처음에 «근거» 또는 «#» 중 하나만 있으면 통과시켰다.
      그래서 값의 뜻만 적어 둔 항목(«60일 무활동 → 이탈»)이 새어 나갔다.
      뜻은 정의이지 근거가 아니다 — 왜 60인지에 답하지 못한다.
      느슨한 점검은 안 하느니만 못하다. «근거»를 반드시 요구하게 바꿨다.
    """
    txt = (ROOT / "core" / "config.py").read_text(encoding="utf-8")
    missing = []
    for name in ("THRESHOLDS", "MIN_SAMPLE", "MIN_OBS_DAYS", "VALID_UNTIL",
                 "CHURN_GAP_DAYS", "JUDGE_MIN_DAYS", "DECOMP_AXIS"):
        i = txt.find(f"\n{name}")
        if i < 0:
            missing.append(f"{name} 없음")
            continue
        head = txt[max(0, i - 900):i]
        block = head.rsplit("\n\n", 1)[-1]
        if "근거" not in block:
            missing.append(name)
    from core import verdict
    for mod, names in ((verdict, ("MOVE_MIN", "GUARD_DROP")),
                       (validate, ("MIN_ROWS", "OUT_OF_PERIOD_BLOCK",
                                   "MISSING_WARN"))):
        t = Path(mod.__file__).read_text(encoding="utf-8")
        for n in names:
            i = t.find(f"\n{n}")
            if i < 0 or "근거" not in t[max(0, i - 600):i]:
                missing.append(f"{Path(mod.__file__).name}:{n}")
    return note("1 임계값에 근거", not missing,
                "근거 주석 없음: " + ", ".join(missing) if missing
                else "임계값 11개 전부 근거 주석이 붙어 있다")


def r2_messages_have_numbers(tables):
    """검증 메시지에 실제 숫자가 들어가는가."""
    bad = [r["message"] for r in validate.run_checks(tables)
           if not re.search(r"\d", r["message"])]
    return note("2 메시지에 숫자", not bad,
                f"숫자 없는 메시지 {len(bad)}건: {bad[:3]}" if bad
                else "검증 결과 전부에 실제 값이 들어 있다")


def r3_hidden_stay_hidden(ctx, sections):
    """감춘 항목의 값이 화면 데이터나 문서에 남아 있지 않은가."""
    leaks = []
    for c in ctx["cards"]:
        if c["판정"] != "무효":
            continue
        if any(c[k] is not None for k in ("이전", "이후", "변화", "가드레일")):
            leaks.append(f"카드 «{c['이름']}» 에 값이 남음")
        body = "\n".join(sections.values())
        for line in body.splitlines():
            if c["이름"] in line and "%" in line:
                leaks.append(f"문서에 «{c['이름']}» 수치 유출")
    d = ctx["decomp"]
    if "사유" in d.columns:
        hid = d[d["사유"].notna()]
        if len(hid) and hid["전환율"].notna().any():
            leaks.append("분해 표의 감춘 칸에 전환율이 남음")
    coh = ctx["cohort"]
    hidden_n = int(coh["못 믿을 사유"].notna().sum())
    return note("3 감춘 값이 남지 않음", not leaks,
                "; ".join(leaks) if leaks
                else f"감춘 항목 {len(ctx['cards']) - len([c for c in ctx['cards'] if c['판정'] != '무효'])}"
                     f"+{hidden_n}건, 값이 어디에도 없다")


def r4_human_not_autofilled(ctx):
    """사람이 안 쓴 장이 자동으로 채워지지 않는가."""
    empty = S.build(ctx, human={})
    bad = [t for t in S.HUMAN_SECTIONS if empty[t] != S.NOT_WRITTEN]
    return note("4 빈 장은 빈 채로", not bad,
                f"자동으로 채워진 장: {bad}" if bad
                else f"사람이 쓰는 {len(S.HUMAN_SECTIONS)}장은 비우면 «{S.NOT_WRITTEN}»")


def r5_no_causal(sections):
    hits = S.check_phrasing(sections)
    return note("5 인과 단정 표현", not hits,
                f"{len(hits)}건: {[h['단어'] for h in hits]}" if hits
                else f"자동·사람 장 {len(sections)}장 전부 통과")


def r6_colors_from_config():
    """색을 파일 안에서 새로 만들지 않는가 (config.COLORS 만 쓴다)."""
    allow = {"core/config.py"}
    bad = []
    for p in SRC:
        rel = p.relative_to(ROOT).as_posix()
        if rel in allow:
            continue
        txt = p.read_text(encoding="utf-8")
        for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", txt):
            line = txt[:m.start()].count("\n") + 1
            bad.append(f"{rel}:{line} {m.group()}")
        # PDF 는 색을 (r, g, b) 로 받는다. 16진수만 찾으면 여기를 놓친다 —
        # 실제로 한 번 놓쳤고, 그래서 이 줄을 더했다.
        for m in re.finditer(
                r"set_(?:text|fill|draw)_color\(\s*(\d+)\s*,\s*(\d+)\s*,"
                r"\s*(\d+)\s*\)", txt):
            line = txt[:m.start()].count("\n") + 1
            rr, gg, bb = (int(x) for x in m.groups())
            bad.append(f"{rel}:{line} #{rr:02X}{gg:02X}{bb:02X}")
    # 화면 테두리/배경 같은 무채색은 판정 색이 아니다 — 회색 계열만 허용한다
    def is_gray(h):
        r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
        return max(r, g, b) - min(r, g, b) <= 12
    real = [b for b in bad if not is_gray(b.split()[-1])]
    return note("6 강조 색은 config 에서만", not real,
                "판정 색을 파일 안에서 새로 만든 곳: " + "; ".join(real) if real
                else f"무채색 {len(bad)}곳만 인라인, 판정 색은 전부 config.COLORS")


def r7_no_wall_clock():
    """계산에 현재 시각을 쓰지 않는가 — 쓰면 재현이 안 된다."""
    pat = re.compile(r"(datetime\.now|Timestamp\.now|date\.today|time\.time"
                     r"|Timestamp\('today'\)|pd\.Timestamp\.today)")
    bad = []
    for p in SRC:
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(("screens/", "core/gates.py")):
            continue          # 기록의 타임스탬프는 계산이 아니다
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                bad.append(f"{rel}:{i}")
    return note("7 계산에 현재 시각 없음", not bad,
                "; ".join(bad) if bad
                else f"기준일은 config.AS_OF={config.AS_OF} 하나로 고정")


def r8_gate_reasons():
    rows = gates.history()
    if not rows:
        return note("8 게이트 근거", False, "통과 기록이 없다")
    thin = [r["name"] for r in rows if len(r["reason"].strip()) < 20]
    return note("8 게이트 근거", not thin,
                f"근거가 부실한 기록: {thin}" if thin
                else f"기록 {len(rows)}건 전부 근거가 20자 이상")


def r9_few_blocks(tables):
    names = {r["name"].split(" · ")[0] for r in validate.run_checks(tables)}
    block_rules = {"행 수", "필수 컬럼", "날짜 범위"}
    over = len(names) - len(block_rules | {"키 중복", "결측률"})
    return note("9 차단 규칙은 적게", over <= 0,
                f"규칙 종류가 {len(names)}개로 늘었다" if over > 0
                else "차단 3종(행 수·필수 컬럼·날짜 범위) + 경고 2종(키 중복·결측률)")


def r10_single_source():
    """화면과 문서가 각자 계산하지 않고 context 를 거치는가."""
    bad = []
    for p in sorted(ROOT.glob("screens/*.py")) + sorted(ROOT.glob("report/*.py")):
        txt = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT).as_posix()
        for fn in ("metrics.funnel(", "metrics.kpis(", "metrics.monthly(",
                   "metrics.retention_funnel(", "metrics.churn_split("):
            if fn in txt:
                bad.append(f"{rel} 가 {fn} 를 직접 부른다")
    return note("10 계산은 한 곳에서", not bad,
                "; ".join(bad) if bad
                else "화면·문서 모두 core/context.py 가 만든 값을 쓴다")


def r11_no_raw_html():
    """카드·배지를 직접 쓴 HTML 로 그리지 않는가.

    직접 쓴 HTML 은 테마를 안 따라간다. 밝은 테마용으로 박은 회색이
    어두운 테마에서 그대로 남아, 판정 색만 엉뚱하게 튄다.
    st.container(border=True) · st.badge · st.metric 이 같은 일을 한다.
    """
    bad = []
    for p in SRC:
        rel = p.relative_to(ROOT).as_posix()
        txt = p.read_text(encoding="utf-8")
        for i, line in enumerate(txt.splitlines(), 1):
            if "unsafe_allow_html" in line and not line.lstrip().startswith("#"):
                bad.append(f"{rel}:{i}")
    return note("11 직접 쓴 HTML 없음", not bad,
                "; ".join(bad) if bad
                else "카드·배지·테두리는 전부 Streamlit 요소로 그린다")


# 근거가 «무엇에서 온 값인지» 말하려면 이 중 하나는 있어야 한다.
# 교안 ③: 직전 기간인지 · 목표치인지 · 벤치마크인지 · 분석이 성립하는 최소치인지.
REASON_KINDS = ("직전", "이전 기간", "표준편차", "분포", "중앙값", "최댓값",
                "실제로", "재 보니", "목표", "벤치마크", "업계", "최소",
                "하한", "합의", "정의서", "7주차", "손계산", "관측")


def r12_reason_kind():
    """근거가 그 값의 «뜻»이 아니라 «출처»를 말하는가.

    ★ 규칙 1은 «근거»라는 낱말이 있는지만 본다. 그것만으로는
      "근거: 적당해서"도 통과한다. 어디서 온 값인지가 있어야 근거다.
      교안 ③ — 직전 기간인지 · 목표치인지 · 벤치마크인지 · 최소치인지.
    """
    txt = (ROOT / "core" / "config.py").read_text(encoding="utf-8")
    thin = []
    for name in ("THRESHOLDS", "MIN_SAMPLE", "MIN_OBS_DAYS", "VALID_UNTIL",
                 "CHURN_GAP_DAYS", "JUDGE_MIN_DAYS", "DECOMP_AXIS",
                 "HAND_BASELINE", "HAND_TOL"):
        i = txt.find("\n" + name)
        if i < 0:
            continue
        block = txt[max(0, i - 900):i].rsplit("\n\n", 1)[-1]
        if not any(k in block for k in REASON_KINDS):
            thin.append(name)
    return note("12 근거에 출처가 있음", not thin,
                "무엇에서 온 값인지 없음: " + ", ".join(thin) if thin
                else "임계값 9개가 전부 «어디서 온 값인지»를 말한다")


def r13_no_redistributable():
    """저장소에 올리면 안 되는 파일이 남아 있지 않은가.

    폰트는 눈에 안 띄게 무겁고, 라이선스가 딸려 온다.
    맑은 고딕은 Windows 에 딸려 오는 것이라 재배포할 수 없다.
    """
    bad = []
    for pat in ("fonts/*.ttf", "fonts/*.otf", ".streamlit/secrets.toml"):
        for f in ROOT.glob(pat):
            bad.append(f"{f.relative_to(ROOT).as_posix()} "
                       f"({f.stat().st_size / 1024 / 1024:.1f}MB)")
    gi = (ROOT / ".gitignore")
    if not gi.exists() or "secrets.toml" not in gi.read_text(encoding="utf-8"):
        bad.append(".gitignore 에 secrets.toml 이 없다")
    return note("13 못 올릴 파일 없음", not bad,
                "; ".join(bad) if bad
                else "폰트는 packages.txt 로 깔고, secrets 는 .gitignore 에 있다")


# apt 패키지 이름에 쓸 수 있는 글자. 데비안 정책상 소문자·숫자와 + - . 뿐이다.
APT_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


def r14_deploy_files():
    """배포 설정 파일이 그 형식이 읽을 수 있는 것만 담고 있는가.

    ★ 실제로 여기서 배포가 죽었다.
      packages.txt 에 «# 배포처(리눅스)에 한글 폰트를 깐다» 같은 주석을 달았는데,
      이 파일은 주석을 모른다 — 모든 줄을 그대로 apt-get 에 넘긴다.
      그래서 낱말 하나하나가 패키지 이름이 되어 40줄짜리 에러가 났다.

      requirements.txt(pip) 는 «#» 을 주석으로 읽는다. 둘이 나란히 있어서
      같은 규칙일 것이라고 생각했다 — 형식이 비슷하게 생겼다는 것은 근거가 아니다.
      설명은 fonts/README.md 로 옮겼다.
    """
    bad = []
    pkg = ROOT / "packages.txt"
    if pkg.exists():
        for i, line in enumerate(pkg.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s:
                continue
            if not APT_NAME.match(s):
                bad.append(f"packages.txt:{i} «{s[:30]}» 는 apt 패키지 이름이 아니다")
    return note("14 배포 설정 파일 형식", not bad,
                "; ".join(bad) if bad
                else f"packages.txt 는 패키지 이름만 담는다 "
                     f"({pkg.read_text(encoding='utf-8').split() if pkg.exists() else []})")



def main():
    tables = load()
    ctx = context.build(tables)
    sections = S.build(ctx, human=S.load_human())

    r1_threshold_reasons()
    r2_messages_have_numbers(tables)
    r3_hidden_stay_hidden(ctx, sections)
    r4_human_not_autofilled(ctx)
    r5_no_causal(sections)
    r6_colors_from_config()
    r7_no_wall_clock()
    r8_gate_reasons()
    r9_few_blocks(tables)
    r10_single_source()
    r11_no_raw_html()
    r12_reason_kind()
    r13_no_redistributable()
    r14_deploy_files()

    width = max(len(f["규칙"]) for f in FINDINGS)
    print()
    for f in FINDINGS:
        print(f"  [{f['결과']}] {f['규칙']:<{width}}  {f['내용']}")
    bad = [f for f in FINDINGS if f["결과"] == "걸림"]
    print("\n" + (f"규칙 {len(FINDINGS)}개 전부 지킴" if not bad
                  else f"걸린 규칙 {len(bad)}개"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
