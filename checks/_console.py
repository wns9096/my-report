# -*- coding: utf-8 -*-
"""검사 결과를 사람이 읽을 수 있게 내보내는 자리. 여기 하나뿐이다.

검사는 «검사한 것» 때문에 죽어야 한다. «찍은 것» 때문에 죽으면 안 된다.

윈도우 기본 콘솔은 cp949 다. 한글은 나가지만 «»·— 같은 글자는 못 나가서
UnicodeEncodeError 로 프로세스가 통째로 죽는다. 검사는 다 돌았는데 결과를
찍다가 죽으니, 사람이 보기에는 «검사가 실패했다»와 구분이 안 된다.

더 나쁜 자리가 run_all 이다. 자식 프로세스의 출력은 파이프로 묶이는데,
파이프의 인코딩도 cp949 라 부모가 utf-8 로 «읽어도» 자식이 «쓰다가» 먼저
죽는다. 읽는 쪽만 고치면 안 되고 쓰는 쪽을 고쳐야 한다 — 9주차에 한 번
고쳤다고 생각했지만 읽는 쪽만 고쳐서, 열 개 중 아홉이 계속 죽고 있었다.
"""
import sys


def use_utf8():
    """이 프로세스의 출력을 utf-8 로 돌린다. 검사 스크립트 맨 앞에서 부른다.

    stderr 도 같이 돌린다. 죽을 때 나오는 추적(traceback)에도 한글이 섞이는데,
    그것마저 못 찍으면 왜 죽었는지가 안 보인다.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass    # 파이썬이 아닌 자리로 묶여 있으면 그냥 둔다
