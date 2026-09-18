# -*- coding: utf-8 -*-
"""data/*.csv 를 만든 스크립트. **이 저장소만으로 다시 만들 수 있어야 한다.**

교안 14장 첫 줄이 「합성 데이터의 생성 스크립트가 남아 있고, 다시 돌려도 같은
결과가 나오는가」다. 여기에 없었다. 데이터는 다른 폴더에서 만들어 복사해 온
것이었고, 이 저장소를 받은 사람은 `data/*.csv` 가 어디서 왔는지 알 수 없었다.

★ 회사 이름을 어떻게 다뤘나 — 되돌릴 수 없게 했다.
    원래는 실제 회사 이름으로 만들고 **나중에** 「회사01」 로 바꿨다. 그러면
    바꾸기 전 파일과 바꾸는 표가 어딘가 남아야 다시 만들 수 있는데, 그 표가
    남아 있으면 익명화가 아니다. **되돌릴 수 있으면 가린 것이 아니다.**
    그래서 이름을 **처음부터** 「회사01」 로 두고 만든다. 뽑는 순서와 난수는
    그대로라서 나오는 파일은 전과 **바이트까지 같다**. 확인은 아래 `--확인`.

★ 표기 흔들림이 다시 보이게 됐다.
    일부러 심은 잡음 넷 중 하나가 「같은 회사가 두 가지로 적힌다」였다.
    이름을 가리고 나니 「회사11」 과 「회사01」 이 같은 회사라는 것을 아무도 알
    수 없었다 — 심어 놓고 못 찾는 잡음은 심지 않은 것과 같다. 아래 `같은회사`
    표가 그 짝을 말한다. `data/심은것.md` 가 이 표를 읽어 대조한다.

    python data/_gen.py --확인    지금 파일과 같은지만 본다 (안 덮어쓴다)
    python data/_gen.py --쓰기    실제로 다시 만든다
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from checks._console import use_utf8  # noqa: E402

# 윈도우 콘솔은 cp949 다. 「」 나 · 를 찍다가 프로세스가 죽는다 — 검사가
# 이것을 자식으로 부르면 부모는 «검사가 실패했다»로 읽는다. 찍는 쪽을 고친다.
use_utf8()

# ── 씨앗과 크기 — 이 값이 같으면 같은 파일이 나온다 ────────────────────────
SEED = 20260829
AS_OF = "2025-12-31"
OBS = ("2025-01-01", "2025-12-31")
N_APPLICANTS, N_POSTINGS = 520, 240
P_MISSING_INDUSTRY = 0.12   # 산업 미기재
P_MISSING_EDU = 0.08        # 학력 미기재
P_DUP_ROW = 0.015           # 같은 지원이 두 번 입력된 행
P_NAME_VARIANT = 0.05       # 같은 회사가 다른 표기로 적힌 행

# ── 어휘 ──────────────────────────────────────────────────────────────────
# 회사 이름은 **처음부터 가린 이름**이다. 번호는 실제 이름을 정렬해 붙였던
# 순서라서 띄엄띄엄하다. 순서를 다시 매기면 지금 파일과 안 맞는다.
COMPANIES = ["회사32", "회사27", "회사29", "회사13", "회사28", "회사15",
             "회사26", "회사30", "회사33", "회사16", "회사24", "회사19",
             "회사31", "회사25", "회사18", "회사20", "회사14", "회사17",
             "회사12", "회사11", "회사34", "회사21", "회사22", "회사23"]

# 같은 회사의 두 표기. 왼쪽이 흔히 쓰는 쪽, 오른쪽이 흔들린 쪽이다.
# 실제로는 「(주)」가 붙거나 띄어쓰기가 빠진 이름이었다.
같은회사 = {"회사11": "회사01", "회사15": "회사02", "회사18": "회사03",
            "회사19": "회사04", "회사22": "회사05", "회사26": "회사06",
            "회사28": "회사07", "회사31": "회사08", "회사33": "회사09",
            "회사34": "회사10"}

ROLES = ["DA (Data Analyst)", "BA (Business Analyst)", "Data Scientist",
         "Product Analyst", "BI Engineer", "Growth Analyst"]
INDUSTRIES = ["리테일", "모바일·APP", "금융", "배달/배송", "경영 컨설팅",
              "게임", "물류", "헬스케어", "교육", "미디어"]
EMPLOYMENT = ["신입", "경력", "인턴", "전환형 인턴", "계약직"]
EDU = ["학사", "석사", "전문학사", "비전공 부트캠프"]

TABLES = ("applicants", "postings", "applications", "application_events")


def variant(name: str) -> str:
    """표기를 흔든다. 짝이 없는 회사는 흔들려도 데이터에 안 나온다."""
    return 같은회사.get(name, name + " ")


def build() -> dict[str, pd.DataFrame]:
    """씨앗을 고정해 네 표를 만든다. 밖의 것을 읽지 않는다."""
    rng = np.random.default_rng(SEED)

    n = N_POSTINGS
    post = pd.DataFrame({
        "posting_id": [f"P{i:04d}" for i in range(1, n + 1)],
        "company": rng.choice(COMPANIES, n),
        "role": rng.choice(ROLES, n),
        "employment_type": rng.choice(EMPLOYMENT, n, p=[.34, .30, .12, .12, .12]),
        "industry": rng.choice(INDUSTRIES, n),
        # 전형의 40%만 과제·코딩테스트가 있다. 나머지는 서류 다음이 바로 면접이다.
        "has_test": rng.random(n) < 0.40,
        # 경쟁 강도 — 서류 통과 확률을 좌우한다
        "competition": rng.beta(2.2, 2.2, n).round(3),
    })
    m = rng.random(n) < P_NAME_VARIANT
    post.loc[m, "company"] = [variant(c) for c in post.loc[m, "company"]]
    m = rng.random(n) < P_MISSING_INDUSTRY
    post.loc[m, "industry"] = np.nan

    n = N_APPLICANTS
    obs0 = pd.Timestamp(OBS[0])
    # 구직 시작일은 관측창 안에 흩어진다. 늦게 시작한 사람은 관측 기간이 짧다 —
    # 그 사실이 유지·이탈 판정에서 그대로 문제가 된다.
    start = obs0 + pd.to_timedelta(rng.integers(0, 334, n), unit="D")
    app = pd.DataFrame({
        "applicant_id": [f"A{i:04d}" for i in range(1, n + 1)],
        "start_date": start,
        "education": rng.choice(EDU, n, p=[.52, .13, .11, .24]),
        "prior_years": np.clip(rng.gamma(1.3, 1.5, n), 0, 12).round(1),
        # 준비도 — 서류 통과 확률의 주된 원인. 관측되지 않는 잠재변수다.
        "readiness": np.clip(rng.normal(0.5, 0.17, n), 0.02, 0.98).round(3),
        # 끈기 — 몇 달이나 지원을 계속하는가
        "persist_days": np.clip(rng.lognormal(4.6, 0.62, n), 20, 400).round(0),
    })
    m = rng.random(n) < P_MISSING_EDU
    app.loc[m, "education"] = np.nan

    as_of = pd.Timestamp(AS_OF)
    apps, events, k = [], [], 0
    for a in app.itertuples():
        cur = a.start_date
        end = min(as_of, a.start_date + pd.Timedelta(days=int(a.persist_days)))
        while cur <= end:
            p = post.iloc[rng.integers(0, len(post))]
            k += 1
            aid = f"J{k:05d}"
            fit = float(np.clip(a.readiness + rng.normal(0, 0.18), 0.02, 0.99))

            apps.append({
                "application_id": aid, "applicant_id": a.applicant_id,
                "posting_id": p.posting_id, "company": p.company, "role": p.role,
                "industry": p.industry, "employment_type": p.employment_type,
                "applied_date": cur, "fit_score": round(fit, 3),
            })
            events.append({"application_id": aid, "applicant_id": a.applicant_id,
                           "stage": "지원", "event_date": cur})

            # 서류 — 준비도와 적합도가 올리고, 경쟁 강도가 내린다
            p_doc = 1 / (1 + np.exp(-(-2.05 + 2.3 * fit - 1.5 * p.competition)))
            if rng.random() < p_doc:
                d1 = cur + pd.Timedelta(days=int(rng.integers(7, 22)))
                if d1 > as_of:
                    cur += pd.Timedelta(days=int(rng.integers(4, 17)))
                    continue
                events.append({"application_id": aid, "applicant_id": a.applicant_id,
                               "stage": "서류 통과", "event_date": d1})

                alive, d = True, d1
                if p.has_test:               # 과제가 있는 전형만 거친다
                    if rng.random() < 0.74:
                        d = d1 + pd.Timedelta(days=int(rng.integers(5, 15)))
                        if d <= as_of:
                            events.append({"application_id": aid,
                                           "applicant_id": a.applicant_id,
                                           "stage": "과제·테스트 통과",
                                           "event_date": d})
                        else:
                            alive = False
                    else:
                        alive = False

                if alive:
                    d2 = d + pd.Timedelta(days=int(rng.integers(8, 24)))
                    if d2 <= as_of and rng.random() < 0.41:
                        events.append({"application_id": aid,
                                       "applicant_id": a.applicant_id,
                                       "stage": "면접 통과", "event_date": d2})
                        d3 = d2 + pd.Timedelta(days=int(rng.integers(5, 21)))
                        if d3 <= as_of and rng.random() < 0.38:
                            events.append({"application_id": aid,
                                           "applicant_id": a.applicant_id,
                                           "stage": "최종 합격", "event_date": d3})
                            end = d3      # 합격하면 지원을 멈춘다 — 성공 종료
            cur += pd.Timedelta(days=int(rng.integers(4, 17)))

    ap = pd.DataFrame(apps)
    ev = pd.DataFrame(events)

    # 중복 행 — 같은 지원이 두 번 입력된 경우. 고유값으로 세지 않으면 부풀려진다.
    dup = ap.sample(frac=P_DUP_ROW, random_state=SEED)
    ap = pd.concat([ap, dup], ignore_index=True).sort_values("applied_date")

    return {"applicants": app, "postings": post,
            "applications": ap, "application_events": ev}


def write(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, df in build().items():
        p = out_dir / f"{name}.csv"
        df.to_csv(p, index=False, encoding="utf-8-sig")
        paths[name] = p
    return paths


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def check() -> int:
    """지금 data/ 에 있는 파일과 **바이트까지** 같은지 본다. 안 덮어쓴다."""
    with tempfile.TemporaryDirectory() as tmp:
        made = write(Path(tmp))
        bad = []
        for name in TABLES:
            here, there = HERE / f"{name}.csv", made[name]
            a = _sha(here) if here.exists() else "없다"
            b = _sha(there)
            같다 = a == b
            print(f"  [{'지킴' if 같다 else '걸림'}] {name:<20} "
                  f"지금 {a} · 다시 만든 것 {b}")
            if not 같다:
                bad.append(name)
    print(f"\n{len(TABLES) - len(bad)}/{len(TABLES)} 바이트까지 같다")
    if bad:
        print("다시 만든 것이 지금 파일과 다르다. **데이터를 덮어쓰지 않는다** — "
              "지금 파일로 낸 숫자가 문서 곳곳에 적혀 있다. 왜 달라졌는지부터 본다.")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--쓰기" in sys.argv:
        for name, p in write(HERE).items():
            print(f"  {name:<20} {_sha(p)}  {p}")
        raise SystemExit(0)
    raise SystemExit(check())
