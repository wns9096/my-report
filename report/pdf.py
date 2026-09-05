# -*- coding: utf-8 -*-
"""PDF — Day4 실습 D.

한글 폰트는 fonts/ 에서 임베드한다. 그리스 문자는 쓰지 않는다
(α 대신 "유의수준"). 폰트에 그 글자가 없으면 네모로 나온다.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from fpdf import FPDF  # noqa: E402

from core import config  # noqa: E402
from report import sections as S  # noqa: E402

# 한글 폰트를 찾는 순서. 저장소에는 폰트 파일을 넣지 않는다 —
# 맑은 고딕은 Windows 에 딸려 오는 것이라 재배포할 수 없고, 두 파일이 25MB다.
# 배포처(리눅스)에는 packages.txt 가 나눔고딕(OFL)을 깔아 준다.
FONT_CANDIDATES = [
    (config.FONTS / "NanumGothic.ttf", config.FONTS / "NanumGothicBold.ttf"),
    (config.FONTS / "malgun.ttf", config.FONTS / "malgunbd.ttf"),
    (pathlib.Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
     pathlib.Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")),
    (pathlib.Path("C:/Windows/Fonts/malgun.ttf"),
     pathlib.Path("C:/Windows/Fonts/malgunbd.ttf")),
]


def _pick_font():
    """찾은 첫 짝을 쓴다. 하나도 없으면 조용히 네모로 찍지 말고 여기서 멈춘다.

    폰트가 없으면 한글이 전부 네모로 나오는데, 그건 PDF 를 열어 보기 전에는
    모른다. 만들어진 파일이 있으면 사람은 됐다고 생각한다.
    """
    for reg, bold in FONT_CANDIDATES:
        if reg.exists():
            return reg, (bold if bold.exists() else reg)
    raise FileNotFoundError(
        "한글 폰트를 못 찾았다. fonts/ 에 NanumGothic.ttf 를 넣거나, "
        "리눅스면 packages.txt 의 fonts-nanum 이 설치됐는지 보십시오. "
        f"찾아본 곳: {[str(r) for r, _ in FONT_CANDIDATES]}")


FONT_REG, FONT_BOLD = _pick_font()


def _rgb(key):
    """판정 색은 config.COLORS 에서만 가져온다. PDF 는 (r, g, b) 로 받는다."""
    h = config.COLORS[key].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _setup_mpl():
    fm.fontManager.addfont(str(FONT_REG))
    name = fm.FontProperties(fname=str(FONT_REG)).get_name()
    plt.rcParams["font.family"] = name
    plt.rcParams["axes.unicode_minus"] = False
    return name


def _finish(fig, ax_list, path):
    for ax in ax_list:
        ax.tick_params(labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _funnel_png(funnel_df, path, worst_idx=None):
    """획득 퍼널 — 병목 한 칸만 강조색을 쓰고 기호를 붙인다. 화면과 같게."""
    _setup_mpl()
    d = funnel_df.iloc[::-1].reset_index(drop=True)
    n = len(funnel_df)
    colors = [config.COLORS["warn"] if (n - 1 - i) == worst_idx
              else config.COLORS["neutral"] for i in range(n)]
    fig, ax = plt.subplots(figsize=(6.2, 2.6), dpi=150)
    ax.barh(d["단계"], d["인원"], color=colors, height=0.55)
    for y, (v, r) in enumerate(zip(d["인원"], d["직전 대비"])):
        tail = ""
        if r == r and r is not None:
            tail = (f"  {config.MARKS['warn']} 병목 {r:.1%}"
                    if (n - 1 - y) == worst_idx else f"  {r:.1%}")
        ax.text(v, y, f" {v:,}{tail}", va="center", fontsize=8)
    ax.set_xlabel("인원", fontsize=8)
    ax.set_xlim(0, float(d["인원"].max()) * 1.35)
    return _finish(fig, [ax], path)


def _decomp_png(decomp, axis, path):
    """분해 — 전환율과 비중을 나란히. 감춘 칸은 막대를 그리지 않는다.

    전환율 순으로 세운다. 격차가 어디서 나는지가 먼저 보여야 한다.
    감춘 칸은 값이 없으므로 맨 아래로 내린다.
    """
    _setup_mpl()
    d = decomp.copy()
    d["_hidden"] = [isinstance(r, str) and bool(r)
                    for r in (d["사유"] if "사유" in d.columns else [None] * len(d))]
    d = d.sort_values(["_hidden", "전환율"], ascending=[True, True],
                      na_position="first").reset_index(drop=True)
    hidden = list(d["_hidden"])
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 0.46 * len(d) + 1.2), dpi=150,
                             gridspec_kw={"width_ratios": [3, 1]})
    a, b = axes
    vals = [0 if h else float(v) for h, v in zip(hidden, d["전환율"].fillna(0))]
    a.barh(d["칸"], vals, height=0.5,
           color=[config.COLORS["none"] if h else config.COLORS["neutral"]
                  for h in hidden])
    for y, (h, v, n) in enumerate(zip(hidden, d["전환율"], d["시작"])):
        a.text(0.002, y, f"  {config.MARKS['none']} 판정 보류 (표본 {int(n):,})"
               if h else f"  {v:.1%}   n={int(n):,}", va="center", fontsize=7.5)
    a.set_xlabel(f"{axis}별 전환율", fontsize=8)
    a.set_xlim(0, max(max(vals) * 1.95, 0.05))
    a.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")

    b.barh(d["칸"], d["비중"], height=0.5, color=config.COLORS["muted"])
    for y, w in enumerate(d["비중"]):
        b.text(w, y, f" {w:.0%}", va="center", fontsize=7.5, color="#555")
    b.set_yticks([])
    b.set_xlabel("비중", fontsize=8)
    b.set_xlim(0, float(d["비중"].max()) * 1.45)
    b.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    return _finish(fig, [a, b], path)


def _cohort_png(cohort, path):
    """코호트 — 못 믿을 칸은 값을 그리지 않는다. 문서에서도 감춘다."""
    _setup_mpl()
    hidden = [isinstance(r, str) and bool(r) for r in cohort["못 믿을 사유"]]
    vals = [0 if h else v for h, v in zip(hidden, cohort["서류통과율"])]
    fig, ax = plt.subplots(figsize=(6.2, 2.1), dpi=150)
    ax.bar(cohort["코호트"], vals,
           color=[config.COLORS["none"] if h else config.COLORS["neutral"]
                  for h in hidden])
    for x, (h, v) in enumerate(zip(hidden, vals)):
        if h:
            ax.text(x, 0.01, f"{config.MARKS['none']} 판정 보류", rotation=90,
                    fontsize=7, va="bottom", ha="center",
                    color=config.COLORS["none"])
        else:
            ax.text(x, v, f"{v:.0%}", fontsize=7, va="bottom", ha="center")
    ax.set_ylabel("서류 통과율", fontsize=8)
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0%}")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return _finish(fig, [ax], path)


class Doc(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("KO", "", 8)
        self.set_text_color(*_rgb("none"))
        self.cell(0, 6, config.DATASET, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)

    def footer(self):
        self.set_y(-12)
        self.set_font("KO", "", 8)
        self.set_text_color(*_rgb("none"))
        self.cell(0, 6, f"{self.page_no()}", align="C")
        self.set_text_color(0)


def build_pdf(sections: dict, ctx, out_path=None, warnings_=None):
    out_path = out_path or (config.OUT / "report.pdf")
    charts_ = {
        "4. 결과": [
            _funnel_png(ctx["funnel"], config.OUT / "_c_funnel.png",
                        worst_idx=ctx.get("worst")),
            _decomp_png(ctx["decomp"], ctx["axis"], config.OUT / "_c_decomp.png"),
        ],
        "5. 전후 비교": [
            _cohort_png(ctx["cohort"], config.OUT / "_c_cohort.png"),
        ],
    }

    pdf = Doc()
    pdf.add_font("KO", "", str(FONT_REG))
    pdf.add_font("KO", "B", str(FONT_BOLD))
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

    pdf.set_font("KO", "B", 18)
    pdf.multi_cell(0, 10, config.DATASET, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("KO", "", 10)
    pdf.set_text_color(*_rgb("none"))
    pdf.multi_cell(0, 6, f"{config.PERIOD[0]} ~ {config.PERIOD[1]}  ·  "
                         f"분석 단위 {ctx['grain_ko']}  ·  기준일 {config.AS_OF}",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(4)

    if warnings_:
        pdf.set_font("KO", "B", 10)
        pdf.set_text_color(*_rgb("block"))
        pdf.multi_cell(0, 6, f"인과 단정 표현 {len(warnings_)}건이 남아 있다 — "
                             f"발송 전에 고쳐야 한다", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.ln(2)

    for title in S.ORDER:
        body = sections.get(title, S.NOT_WRITTEN)
        pdf.set_font("KO", "B", 13)
        pdf.ln(3)
        pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("KO", "", 9.5)
        if body == S.NOT_WRITTEN:
            pdf.set_text_color(*_rgb("muted"))
            pdf.multi_cell(0, 6, S.NOT_WRITTEN, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0)
        else:
            pdf.multi_cell(0, 5.4, body.replace("**", ""),
                           new_x="LMARGIN", new_y="NEXT")
        for img in charts_.get(title, []):
            pdf.ln(2)
            pdf.image(str(img), w=150)
            pdf.ln(2)

    pdf.output(str(out_path))
    return out_path
