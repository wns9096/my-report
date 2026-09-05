# -*- coding: utf-8 -*-
"""적재층 — data/ 의 파일을 읽어 이름:DataFrame 으로 돌려준다.

csv 는 UTF-8 / cp949 를 차례로 시도한다. 한글이 깨져 보이면 코드가 아니라
저장 형식을 먼저 확인한다 (Day1 실습 B).
"""
import pandas as pd
import streamlit as st

from core import config

_EXT = [".parquet", ".csv", ".xlsx"]
_DATE_HINT = ("date", "일자", "일시", "_dt")


def _read(path):
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".xlsx":
        return pd.read_excel(path)
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"{path.name} 인코딩을 못 읽었다")


def _cast_dates(df):
    for c in df.columns:
        if any(h in c.lower() for h in _DATE_HINT):
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_all(stamp: str = ""):
    """TABLES 에 적힌 이름을 data/ 에서 찾아 읽는다. 없으면 missing 에 담는다.

    stamp 는 data/ 폴더의 (파일명·수정시각·크기) 지문이다. 파일이 바뀌면 값이
    달라져 캐시가 버려진다. 이름 앞에 _ 를 붙이면 안 된다 — Streamlit 은
    _ 로 시작하는 인자를 캐시 키에서 빼기 때문에, 파일을 바꿔도 옛 값이 나온다.
    """
    tables, missing = {}, []
    for name in config.TABLES:
        for ext in _EXT:
            p = config.DATA / f"{name}{ext}"
            if p.exists():
                tables[name] = _cast_dates(_read(p))
                break
        else:
            missing.append(name)
    return tables, missing


def profile(tables):
    """테이블별 행 수 · 컬럼 수 · 기간 · 결측 컬럼 수. 판단은 하지 않는다."""
    rows = []
    for name, df in tables.items():
        dcols = [c for c in df.columns if str(df[c].dtype).startswith("datetime")]
        span = "—"
        if dcols:
            lo = min(df[c].min() for c in dcols)
            hi = max(df[c].max() for c in dcols)
            if pd.notna(lo) and pd.notna(hi):
                span = f"{lo:%Y-%m-%d} ~ {hi:%Y-%m-%d}"
        rows.append({
            "테이블": name,
            "행": len(df),
            "컬럼": df.shape[1],
            "기간": span,
            "결측 있는 컬럼": int((df.isna().sum() > 0).sum()),
            "메모리(MB)": round(df.memory_usage(deep=True).sum() / 1024 ** 2, 1),
        })
    return pd.DataFrame(rows)


def read_upload(f):
    """업로드된 파일 하나를 읽는다. data/ 의 파일은 건드리지 않는다.

    올린 것은 세션에만 둔다 — 배포본은 여러 사람이 같은 서버를 본다.
    한 사람이 올린 깨진 파일이 원본을 덮으면 다른 사람의 화면까지 바뀐다.
    """
    import io
    name = f.name.rsplit(".", 1)[0]
    raw = f.getvalue()
    if f.name.endswith(".parquet"):
        return name, _cast_dates(pd.read_parquet(io.BytesIO(raw)))
    if f.name.endswith(".xlsx"):
        return name, _cast_dates(pd.read_excel(io.BytesIO(raw)))
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return name, _cast_dates(pd.read_csv(io.BytesIO(raw), encoding=enc))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"{f.name} 인코딩을 못 읽었다")
