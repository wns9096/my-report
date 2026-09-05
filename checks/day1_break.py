# -*- coding: utf-8 -*-
"""Day1 실습 E — 깨뜨려 봅니다.

검증을 만들었다고 끝이 아니다. 실제로 막히는지 봐야 한다.
경고만 띄우고 진행되는 검증은 없는 것과 같다.

보아야 할 것 셋
  1 검증 카드에 빨간 차단이 뜬다
  2 차단 개수가 카드에 세어진다
  3 [통과시키기] 버튼이 잠긴다          ← 가장 중요

원본은 건드리지 않는다. 사본을 만들어 넣었다가 되돌린다.
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import config  # noqa: E402
from checks.ui_smoke import run  # noqa: E402

CARD_BLOCK = f":red-badge[{config.MARKS['block']} {config.LABELS_KO['block']}]"

TARGET = config.DATA / "applications.csv"
BACKUP = config.DATA.parent / "_applications.orig.csv"

# 앱에 넣기 전에 먼저 말한다 — 예상과 실제가 다르면 그 차이가 배울 거리다.
EXPECT = {
    "필수 컬럼 하나를 지운 사본": "차단 — applied_date 가 없으면 어떤 비율도 못 낸다",
    "날짜를 1년 옮긴 사본": "차단 — 기간 밖이 100%다. 20% 하한을 넘으므로 파일이 잘못 온 것",
}


def gate_state():
    """실행 화면을 실제로 열어 차단 수와 통과 버튼 상태를 읽는다.

    근거를 안 적으면 버튼은 어차피 잠긴다. 그래서 근거를 채운 뒤에 본다 —
    그래야 "차단 때문에 잠겼는가"를 가릴 수 있다.
    """
    at = run("실행")
    if at.exception:
        return {"에러": str(at.exception[0].value), "에러화면": True}
    ta = [t for t in at.text_area if t.key == "g1_reason"]
    if ta:
        ta[0].set_value("검증 결과를 확인했다 (자동 점검)")
        at.run()
    if at.exception:
        return {"에러": str(at.exception[0].value), "에러화면": True}
    txt = "\n".join(str(m.value) for m in at.markdown)
    btn = [b for b in at.button if b.label == "통과시키기"]
    # 차단 카드를 센다. 카드 배지는 «✕ 차단», 위쪽 요약 배지는 «✕ 차단 N» 이라
    # 정확히 일치하는 것만 세면 요약 줄이 안 섞인다.
    # (직접 쓴 HTML 을 걷어내고 st.badge 로 바꾸면서 여기도 같이 바꿨다.
    #  화면 표현을 바꾸면 그 화면을 읽는 검사도 같이 바뀌어야 한다.)
    cards = len([1 for m in at.markdown
                 if str(m.value).strip() == CARD_BLOCK])
    return {
        "차단 카드": cards,
        "카드에 세어진 차단 수": _counted(txt),
        "통과 버튼": ("잠김" if (btn and btn[0].disabled) else
                      "눌림 가능" if btn else "없음"),
        "에러화면": False,
    }


def _counted(txt):
    import re
    m = re.search(r"차단 (\d+)\]", txt)
    return int(m.group(1)) if m else None


def show(label, st_):
    print(f"  {label}")
    for k, v in st_.items():
        print(f"      {k:<18} {v}")


def main():
    shutil.copy2(TARGET, BACKUP)
    orig = pd.read_csv(TARGET)
    try:
        print("\n먼저 예상을 말한다")
        for k, v in EXPECT.items():
            print(f"  · {k} → {v}")

        print("\n[0] 원본")
        base = gate_state()
        show("원본 그대로", base)

        print("\n[1] 필수 컬럼 하나를 지운 사본")
        orig.drop(columns=["applied_date"]).to_csv(TARGET, index=False,
                                                   encoding="utf-8")
        s1 = gate_state()
        show("applied_date 삭제", s1)

        print("\n[2] 날짜를 1년 옮긴 사본")
        d = orig.copy()
        d["applied_date"] = (pd.to_datetime(d["applied_date"])
                             + pd.DateOffset(years=1)).dt.strftime("%Y-%m-%d")
        d.to_csv(TARGET, index=False, encoding="utf-8")
        s2 = gate_state()
        show("applied_date +1년", s2)
    finally:
        shutil.copy2(BACKUP, TARGET)
        BACKUP.unlink()

    print("\n[3] 원상복구")
    s3 = gate_state()
    show("되돌린 뒤", s3)

    ok = (
        base["차단 카드"] == 0 and base["통과 버튼"] == "눌림 가능"
        and s1["차단 카드"] >= 1 and s1["통과 버튼"] == "잠김"
        and s2["차단 카드"] >= 1 and s2["통과 버튼"] == "잠김"
        and s3["차단 카드"] == 0 and s3["통과 버튼"] == "눌림 가능"
        and not any(x.get("에러화면") for x in (base, s1, s2, s3))
    )
    print("\n" + ("깨진 파일에서 차단이 뜨고 통과 버튼이 잠겼다. 되돌리니 풀렸다."
                  if ok else "기대와 다르다 — 판정 레벨이 block 인지 확인하십시오."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
