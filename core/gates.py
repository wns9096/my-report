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
        "at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "context": context or {},
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
    """가장 최근 통과 기록. 없으면 None."""
    rows = [r for r in history() if r["gate"] == gate]
    return rows[-1] if rows else None
