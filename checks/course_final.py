# -*- coding: utf-8 -*-
"""교안 14장 완주 체크리스트를 기계가 도는 데까지 돈다.

  python checks/course_final.py

★ 이미 보는 검사가 있으면 **여기서 새로 세지 않는다.** 같은 것을 두 곳에서
  세면 언젠가 두 값이 갈리고, 갈린 뒤에는 어느 쪽이 맞는지 아무도 모른다.
  그런 항목은 [맡김] 으로 찍고 **어느 검사가 보는지** 이름을 댄다. 이름을
  못 대면 그것은 안 보고 있는 것이다.

★ [해당 없음] 은 «안 했다»가 아니라 «이 앱에 그것이 없다»다. 없는 것을
  «있다»로 적지 않는다 — 체크리스트를 채우려고 없는 기능을 만들면, 남는 것은
  체크 표시뿐이다.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checks._console import use_utf8  # noqa: E402

use_utf8()

from core import config, gates, loader, metrics, validate  # noqa: E402
from report import proposal as P  # noqa: E402

results = []


def ok(cond, label, detail=""):
    results.append((bool(cond), label))
    print(f"  [{'지킴' if cond else '걸림'}] {label}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def 맡김(label, who):
    print(f"  [맡김] {label}  — {who} 가 본다")


def 없음(label, why):
    print(f"  [해당 없음] {label}  — {why}")


def _gen():
    spec = importlib.util.spec_from_file_location("_gen", ROOT / "data" / "_gen.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():  # noqa: C901
    print("교안 14장 완주 체크리스트\n")
    tables, missing = loader.load_all()
    if missing:
        return ok(False, "데이터를 읽었다", f"없는 표 {missing}") or 1

    # ── 데이터 · 구조 ────────────────────────────────────────────────────
    print("── 데이터 · 구조 ──")
    g = _gen()
    r = subprocess.run([sys.executable, str(ROOT / "data" / "_gen.py")],
                       capture_output=True, text=True, encoding="utf-8")
    같음 = r.returncode == 0
    ok(같음, "생성 스크립트가 남아 있고 다시 돌리면 같은 파일이 나온다",
       f"{len(g.TABLES)}개 표가 바이트까지 같다" if 같음
       else "다시 만든 것이 지금 파일과 다르다 — data/_gen.py 를 돌려 본다")

    # 심은 것 — 표에 적힌 값이 아니라 **데이터에서 다시 센 값**으로 본다.
    key = ROOT / "data" / "심은것.md"
    ok(key.exists(), "심은 것 목록이 있다", key.name if key.exists() else "없다")
    po, ap, apl = tables["postings"], tables["applications"], tables["applicants"]
    res = validate.run_checks(tables)
    경고이름 = " ".join(x["name"] for x in validate.warnings(res))
    심은것 = [
        ("산업 미기재", po["industry"].isna().mean() > 0.05, "결측률" in 경고이름),
        ("학력 미기재", apl["education"].isna().mean() > 0.05, "결측률" in 경고이름),
        ("같은 지원이 두 번", len(ap) > ap["application_id"].nunique(),
         "키 중복" in 경고이름),
        # ★ 이 하나는 «심었는데 앱이 못 잡는다». 가린 이름에는 표기 흔들림이
        #   안 남아서 데이터만 보고는 찾을 수 없다. data/심은것.md 4번 참고.
        ("같은 회사의 다른 표기", len(g.같은회사) > 0,
         po["company"].astype(str).str.replace(r"^\(주\)|\s", "", regex=True).nunique()
         < po["company"].nunique()),
        ("과제 있는 전형과 없는 전형", bool(po["has_test"].any() and (~po["has_test"]).any()),
         "과제·테스트 통과" in config.NON_FUNNEL),
        # ★ 목록에는 일곱을 적어 두고 검사는 다섯만 세고 있었다. 적어 둔 것과
        #   세는 것이 다르면 그것은 정답지가 아니다 — 읽는 사람은 일곱 다
        #   확인된 줄로 안다. 나머지 둘을 여기서 센다.
        ("경쟁 강도가 서류 통과를 내린다",
         any(t["키"] == "축:공고 경쟁도" and (t.get("격차") or 0) > 0
             for t in metrics.proposal_topics(tables)),
         config.DECOMP_AXIS == "공고 경쟁도"),
        # ★ 이 둘을 같은 식으로 재면 늘 같이 참이라 아무것도 안 본다.
        #   심은 것은 «시작일이 관측창 안에 흩어져 있다»(데이터의 모양),
        #   잡는 것은 «관측이 덜 찬 코호트를 못 믿을 것으로 판정한다»(앱의 일).
        ("늦게 시작한 사람은 관측이 짧다",
         (apl["start_date"].max() - apl["start_date"].min()).days > 300,
         bool(metrics.cohort_by_start_month(tables)["못 믿을 사유"].notna().any())),
    ]
    심음 = [n for n, s, _ in 심은것 if s]
    잡음 = [n for n, s, c in 심은것 if s and c]
    ok(len(심음) == len(심은것), "심은 것이 데이터에 실제로 있다",
       f"{len(심음)}/{len(심은것)}개")
    # 못 잡는 것이 있어도 **걸림이 아니다.** 목록에 적혀 있으면 그것도 결과다.
    #
    # ★ 처음에는 못 잡는 항목의 **이름이 목록에 있는지**로 봤다. 검사의 이름은
    #   「같은 회사의 다른 표기」인데 목록에는 「같은 회사가 다른 표기로 적힌
    #   행」이라 적혀 있어서, 멀쩡한 문서가 걸렸다. 낱말을 열쇠로 걸면 문장을
    #   다듬는 것만으로 검사가 깨진다 — 이 저장소가 이미 여러 번 당한 자리다.
    #   그래서 **수로만** 견준다: 앱이 못 잡는 것이 몇 개인지와, 목록이 ✕ 로
    #   표시한 것이 몇 개인지.
    못잡음 = [n for n, s, c in 심은것 if s and not c]
    md = key.read_text(encoding="utf-8")
    못잡음표시 = sum(1 for ln in md.splitlines()
                     if ln.startswith("|") and "✕" in ln)
    ok(못잡음표시 == len(못잡음), "앱이 못 잡는 것이 목록에 그만큼 적혀 있다",
       f"잡는 것 {len(잡음)}/{len(심음)} · 못 잡는 것 {len(못잡음)}개 · "
       f"목록의 ✕ {못잡음표시}개")

    화면 = sorted((ROOT / "screens").glob("*.py"))
    바 = [p.name for p in 화면 if "shell.topbar()" in p.read_text(encoding="utf-8")]
    ok(len(바) == len(화면), "컨텍스트 바가 모든 화면에 있다",
       f"{len(바)}/{len(화면)} 화면")

    ok((ROOT / "core" / "config.py").exists()
       and "THRESHOLDS" in (ROOT / "core" / "config.py").read_text(encoding="utf-8"),
       "지표 정의가 앱 코드 밖에 있다",
       "core/config.py 가 설정층이다 (교안 1-4 — 규모가 작으면 한 파일로 둔다)")

    적재 = [p.relative_to(ROOT).as_posix() for p in ROOT.glob("core/*.py")
            if "read_csv" in p.read_text(encoding="utf-8")]
    ok(len(적재) == 1, "계산 로직이 한 벌이다 (갈리는 것은 적재뿐)",
       f"파일을 읽는 곳 {적재}")

    # ── 게이트 · 숫자 ────────────────────────────────────────────────────
    print("\n── 게이트 · 숫자 ──")
    # 교안 11-2 — 「되돌림 불가는 주석이 아니라 분기 조건이어야 합니다」.
    # 글자로 적혀 있는지가 아니라 **실제로 거부하는지** 불러서 본다.
    막혔나 = False
    try:
        gates.revoke(3, "검사가 되돌려 본다")
    except PermissionError:
        막혔나 = True
    except Exception:
        pass
    ok(막혔나, "게이트 3이 코드에서 되돌림을 거부한다",
       "gates.revoke(3) 이 PermissionError 를 낸다" if 막혔나
       else "거부하지 않았다 — 표에 «되돌릴 수 없음»이라 적혀 있어도 막히지 않는다")
    되나 = False
    try:
        gates.revoke(1, "")
    except ValueError:
        되나 = True          # 근거가 비면 거부한다 — 되돌리기도 근거가 필요하다
    except PermissionError:
        되나 = False
    ok(되나, "게이트 1·2는 되돌릴 수 있고, 근거 없이는 안 된다",
       "근거가 비면 ValueError")

    # ★ 위 둘은 함수를 직접 부른 것이다. **버튼은 아직 안 눌러 봤다.**
    #   화면이 그 함수를 안 부르고 있어도 위 둘은 통과한다 — 그래서 실제
    #   Streamlit 런타임을 띄워 누른다. 기록 파일은 반드시 되돌려 놓는다:
    #   검사가 남긴 줄이 그대로 남으면 게이트 1이 되돌려진 채로 배포된다.
    from checks.ui_smoke import run as _화면
    원래 = gates.LOG.read_text(encoding="utf-8") if gates.LOG.exists() else ""
    눌렀다 = 되돌렸다 = False
    try:
        at = _화면("아카이브")
        키 = [w.key for w in at.button if str(w.key).startswith("undo_")]
        눌렀다 = "undo_1" in 키 and "undo_3" not in 키
        if "undo_1" in 키:
            at.text_input(key="undo_reason_1").set_value("검사가 눌러 본다").run()
            at.button(key="undo_1").click().run()
            되돌렸다 = gates.passed(1) is None and not at.exception
    finally:
        gates.LOG.write_text(원래, encoding="utf-8")
    ok(눌렀다, "되돌리기 버튼이 게이트 1·2 에만 있다",
       "게이트 3 에는 버튼 대신 «이미 나간 뒤» 안내만 있다" if 눌렀다
       else f"버튼 키 {키}")
    ok(되돌렸다, "버튼을 누르면 실제로 되돌아간다 (AppTest)",
       "누른 뒤 gates.passed(1) 이 None · 기록 파일은 되돌려 놓았다" if 되돌렸다
       else "버튼을 못 눌렀거나 눌러도 상태가 안 바뀌었다 — "
            "화면이 gates.revoke() 를 안 부르고 있을 수 있다")

    맡김("차단일 때 통과 버튼이 잠긴다", "checks/day1_break.py · sandbox_break.py")
    맡김("게이트 통과 기록에 근거가 있다", "checks/app_audit.py 8")
    맡김("단계별 숫자를 손계산으로 대조했다", "checks/day2_crosscheck.py")
    맡김("못 믿을 값은 계산조차 하지 않는다", "checks/day3_trust.py")

    # 두 번 돌려서 같은 값이 나오는가 — 같은 프로세스에서 두 번 부른다.
    a = metrics.funnel(tables, config.GRAIN)
    b = metrics.funnel(tables, config.GRAIN)
    같다 = a.equals(b)
    ok(같다, "두 번 돌려서 같은 값이 나온다",
       f"퍼널 {len(a)}행이 두 번 다 같다" if 같다 else "두 값이 다르다")

    # ── 문서 · 제안 ──────────────────────────────────────────────────────
    print("\n── 문서 · 제안 ──")
    맡김("자동 생성 문장에 인과 단정 표현이 없다", "checks/day4_phrasing.py")
    맡김("검증 경고가 리포트 한계로 이어진다", "checks/app_audit.py 5 · 리포트 7장")
    맡김("해석·제안이 비면 «작성되지 않음»이 찍힌다", "checks/app_audit.py 4")
    맡김("제안에 «하지 말 것»이 있다", "checks/w9d3_proposal.py")
    맡김("제안 근거를 앱에서 조회했다 (분자·분모·비교·비중)", "checks/w9d1_verify.py")

    # ★ 교안 9-4 — 「Noto Sans KR 에 그리스 문자가 없다. α=0.05 는 PDF 에서
    #   사라진다」. 지워지는 글자는 오류를 안 낸다. 그래서 **나가는 글**을
    #   훑는다. 주석·코드가 아니라 실제로 종이에 얹히는 글만 본다.
    없는글자 = re.compile(r"[Ͱ-Ͽἀ-῿]")
    나가는글 = []
    for f in (config.OUT / "제출본_제안서.html", config.OUT / "제안서.html"):
        if f.exists():
            나가는글 += [(f.name, c) for c in
                         set(없는글자.findall(f.read_text(encoding="utf-8")))]
    ok(not 나가는글, "문서에 폰트가 못 그리는 글자가 없다",
       f"{나가는글}" if 나가는글
       else "그리스 문자 0개 — σ·α 는 주석에만 있고 문서로 안 나간다")

    # ★ 교안 10-4 — 제안 문서를 **만들지 않는** 조건 넷. 앞의 셋은 카드 검사가
    #   보고 있어서 맡긴다. 넷째만 여기서 본다 — 「근거가 화면에서 감춘
    #   항목이면 제안에 쓰지 않는다」. 감춘 것을 근거로 쓰면 감춘 의미가 없다.
    붙은카드 = {c.get("주제키") for c in P.load_cards()}
    감춘근거 = [t["키"] for t in metrics.proposal_topics(tables)
                if t["키"] in 붙은카드 and t.get("감춘칸")]
    ok(not 감춘근거, "감춘 항목을 근거로 쓴 제안이 없다",
       f"감춘 칸이 있는 주제에 카드가 붙어 있다: {감춘근거}" if 감춘근거
       else f"카드가 붙은 주제 {len(붙은카드 & {t['키'] for t in metrics.proposal_topics(tables)})}개 전부 감춘 칸 0")

    # ── 화면 · 배포 ──────────────────────────────────────────────────────
    print("\n── 화면 · 배포 ──")
    shell = (ROOT / "core" / "shell.py").read_text(encoding="utf-8")
    ok("tabular-nums" in shell, "화면 지표 숫자에 tabular-nums 가 걸려 있다",
       "core/shell.py 가 모든 화면에 건다")
    없음("신뢰구간에 0 기준선이 있다",
        "이 앱은 신뢰구간을 안 그린다. 표본이 모자란 칸은 값을 아예 안 낸다")
    맡김("판정 색과 장식 색이 갈려 있다", "checks/app_audit.py 6")

    mb = sum(df.memory_usage(deep=True).sum() for df in tables.values()) / 1024 ** 2
    ok(mb < 200, "배포본 메모리가 한도 안이다",
       f"표 {len(tables)}개가 {mb:.1f}MB (무료 한도 1,024MB)")

    ign = (ROOT / ".gitignore").read_text(encoding="utf-8")
    빠진 = [p for p in ("secrets.toml", "fonts/*.ttf", "*credentials*.json")
            if p not in ign]
    ok(not 빠진, "비밀·못 올릴 파일이 .gitignore 에 있다",
       f"빠진 것 {빠진}" if 빠진 else "secrets.toml · fonts/*.ttf · 인증 키")

    # 공개 저장소에 업무 데이터가 섞이지 않았는가 — **찾기만 한다.**
    # 지우는 것은 사람이 정한다. 검사가 지우면 무엇이 지워졌는지 아무도 모른다.
    실명 = []
    for f in list(ROOT.glob("data/*.csv")):
        head = f.read_text(encoding="utf-8-sig").splitlines()[:400]
        if any(re.search(r"\(주\)|주식회사", ln) for ln in head):
            실명.append(f.name)
    ok(not 실명, "공개 저장소에 회사 실명이 없다",
       f"{실명} 에 회사 표기가 보인다 — 지우는 것은 사람이 정한다" if 실명
       else "회사는 전부 「회사NN」 · 사람 이름 열이 없다")
    없음("공개 URL 에서 웨어하우스를 직결하지 않는다",
        "이 앱은 저장소 안의 CSV 만 읽는다. 연결할 웨어하우스가 없다")
    맡김("PDF 한글이 안 깨진다", "checks/doc_print.py")
    맡김("AppTest 로 버튼을 눌러 확인했다", "checks/run_gates.py")

    # ★ 교안 13-2 — use_container_width 는 사용 중단 예정이고 width="stretch"
    #   로 바뀐다. 지금 깔린 판에는 새 이름이 아직 없어서 **지금 바꾸면 깨진다.**
    #   그렇다고 알림만 찍어 두면 판이 올라간 날 아무도 안 본다 — 배포처가
    #   알아서 올려 주기 때문에 «올린 날»이 내가 고르는 날이 아니다.
    #   그래서 **문지기**로 둔다: 새 이름을 쓸 수 있게 된 순간부터 걸린다.
    쓴곳 = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.py")
            if ".git" not in p.parts
            and "use_container_width" in p.read_text(encoding="utf-8")]
    import streamlit as st
    판 = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
    새이름가능 = 판 >= (1, 49)
    ok(not (쓴곳 and 새이름가능),
       "화면 인자가 지금 깔린 streamlit 과 맞는다",
       f"streamlit {st.__version__} 은 width=\"stretch\" 를 받는다. "
       f"use_container_width 가 {len(쓴곳)}개 파일에 남아 있다 — 바꿀 때다"
       if (쓴곳 and 새이름가능) else
       f"streamlit {st.__version__} · use_container_width {len(쓴곳)}개 파일. "
       f"새 이름 width=\"stretch\" 는 1.49 부터라 아직 못 바꾼다 — "
       f"판이 올라가면 이 검사가 그날 말한다")

    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)}/{len(results)} 지킴")
    if bad:
        print("걸린 것이 다음에 할 일이다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
