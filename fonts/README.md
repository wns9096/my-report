# 폰트는 저장소에 넣지 않는다

맑은 고딕(`malgun.ttf`)은 Windows 에 딸려 오는 폰트다. 재배포할 수 없고,
두 파일이 25MB라 저장소도 무거워진다. 그래서 여기 두지 않는다.

찾는 순서는 `report/pdf.py` 의 `FONT_CANDIDATES` 에 있다.

| 어디서 도는가 | 무엇을 쓰는가 |
| --- | --- |
| 내 Windows | `C:/Windows/Fonts/malgun.ttf` (설치돼 있다) |
| 배포처 리눅스 | `packages.txt` 의 `fonts-nanum` 이 깔아 준 나눔고딕 (OFL) |
| 그 밖 | 이 폴더에 `NanumGothic.ttf` 를 직접 넣으면 그것을 먼저 쓴다 |

하나도 못 찾으면 PDF 를 만들지 않고 멈춘다.
폰트가 없으면 한글이 전부 네모로 나오는데, 그건 파일을 열어 보기 전에는
모른다 — 파일이 만들어졌다는 사실이 사람을 안심시킨다.
