# -*- coding: utf-8 -*-
"""게이트 — 사람이 누르는 자리. 근거가 없으면 통과시키지 않는다.

  게이트 1 입구  이 데이터로 분석을 시작해도 되는가      되돌릴 수 있다
  게이트 2 출구  계산 결과가 말이 되는가                되돌릴 수 있다
  게이트 3 발송  이대로 내보내도 되는가                 되돌릴 수 없다
"""
import json
from datetime import datetime

from core import config

LOG = config.OUT / "gates.jsonl"

GATES = {
    1: {"name": "게이트 1 · 입구", "q": "이 데이터로 분석을 시작해도 되는가",
        "reversible": True},
    2: {"name": "게이트 2 · 출구", "q": "계산 결과가 말이 되는가",
        "reversible": True},
    3: {"name": "게이트 3 · 발송", "q": "이대로 내보내도 되는가",
        "reversible": False},
}

CONFIRM_PHRASE = "발송합니다"   # 게이트 3만 확인 문구를 한 번 더 받는다


def record(gate: int, reason: str, context: dict | None = None) -> dict:
    """통과 기록을 파일로 남긴다. 근거가 비면 남기지 않는다."""
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("근거 없이 통과시킬 수 없다")
    row = {
        "gate": gate,
        "name": GATES[gate]["name"],
        "kind": "pass",
        "at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "context": context or {},
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def revoke(gate: int, reason: str) -> dict:
    """게이트를 되돌린다. **게이트 3은 거부한다.**

    ★ 교안 11-2 — 「되돌림 불가는 주석이 아니라 분기 조건이어야 합니다.
      문구로만 적어두면 언젠가 되돌려집니다.」 여기가 딱 그 자리였다.
      `reversible` 이 표에 있었는데 **화면에 글자로 찍히기만 했다.** 아무것도
      막지 않는 값은 지켜지는 것처럼 보일 뿐이다.

    지우지 않는다. 「되돌렸다」를 한 줄 더 쌓는다 — 지우면 되돌린 일 자체가
    기록에서 사라지고, 거버넌스 기록이 「무슨 일이 있었나」에 답하지 못한다.
    """
    if not GATES[gate]["reversible"]:
        raise PermissionError(
            f"{GATES[gate]['name']} 은 되돌릴 수 없다. 이미 나간 뒤다 — "
            f"되돌릴 수 있으면 「발송」이 아니다. 다시 내보내려면 새로 통과시킨다.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("근거 없이 되돌릴 수 없다")
    row = {
        "gate": gate,
        "name": GATES[gate]["name"],
        "kind": "revoke",
        "at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "context": {},
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def history() -> list[dict]:
    if not LOG.exists():
        return []
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def passed(gate: int) -> dict | None:
    """가장 최근 통과 기록. 없거나 되돌린 뒤면 None.

    ★ 마지막 줄이 「되돌림」이면 통과가 아니다. 예전 기록에는 kind 가 없는데
      그때는 통과만 쌓았으므로 없으면 통과로 본다.
    """
    rows = [r for r in history() if r["gate"] == gate]
    if not rows:
        return None
    last = rows[-1]
    return None if last.get("kind") == "revoke" else last


def is_ephemeral():
    """이 기록이 재부팅하면 사라지는 자리에 있는가.

    Streamlit Community Cloud 는 저장소를 /mount/src 아래에 풀고, 그 파일계는
    앱이 다시 뜰 때 초기화된다. 게이트 기록은 «사람이 판단한 것»이라 이 앱의
    핵심 산출물인데, 배포본에서 남긴 기록은 남지 않는다.

    말하지 않으면 사람은 저장됐다고 생각한다. 그래서 화면에 적는다.
    9주차에 진짜 보관처(DB·시트)로 옮길 자리이기도 하다.
    """
    return str(config.ROOT).startswith("/mount/src")
