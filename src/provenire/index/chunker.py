"""코드를 검색 단위 조각으로 쪼갠다.

인덱스(corpus)와 스캔(cli)은 **같은 기준으로 쪼개야 매칭**된다.
    - Python: ast 함수 단위 (인덱스도 이렇게 저장한다)
    - 그 외 / 파싱 실패 / 함수 없음: 슬라이딩 윈도우

왜 파일 전체를 한 조각으로 쓰면 안 되나 (§2 미탐의 원인):
    인덱스는 함수 단위인데 의심 코드를 파일 통째로 지문 뜨면 containment 의 분모가
    폭발한다. 543지문짜리 파일에서 함수 하나가 76개 겹쳐도 14% 라 임계값(30%)을
    못 넘긴다. → "GPL 파일 통째 복사"가 통과됐다. 의심 코드도 같은 크기로 쪼갠다.
"""
from __future__ import annotations

import ast
from typing import NamedTuple

__all__ = [
    "Chunk", "iter_functions", "sliding_windows", "chunk_for_scan", "MIN_CHUNK_LINES",
]

MIN_CHUNK_LINES = 5    # 이보다 짧은 함수는 관용구라 청킹에서 제외
_WINDOW = 30           # 슬라이딩 윈도우 크기(줄)
_STEP = 15             # 이동 간격(줄) — 조각이 함수 경계를 걸쳐도 하나는 온전히 담기게 겹친다


class Chunk(NamedTuple):
    """검색 단위 조각 하나.

    start·end 는 **넘겨준 code 기준 1-indexed 줄 번호**(양끝 포함)다.
    리포트에서 "몇 번째 줄이 걸렸는지"를 찍으려면 이게 있어야 한다 — 조각을
    뜬 뒤에는 원래 위치를 복원할 방법이 없으므로 쪼갤 때 같이 들고 나온다.
    """

    symbol: str | None
    code: str
    start: int
    end: int


def _line_count(code: str) -> int:
    return max(len(code.splitlines()), 1)


def iter_functions(code: str) -> list[Chunk]:
    """Python 함수 단위 조각. `ast.parse` 실패 시 SyntaxError 를 그대로 올린다."""
    out: list[Chunk] = []
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            if end - node.lineno + 1 < MIN_CHUNK_LINES:
                continue
            seg = ast.get_source_segment(code, node)
            if seg:
                # get_source_segment 는 데코레이터를 뺀 def…끝 구간을 준다.
                # node.lineno 도 def 줄이라 둘이 정확히 대응한다.
                out.append(Chunk(node.name, seg, node.lineno, end))
    return out


def sliding_windows(code: str, window: int = _WINDOW, step: int = _STEP) -> list[Chunk]:
    """겹치는 고정 크기 창으로 쪼갠다 — 함수 경계를 모를 때의 fallback.

    비-Python 파일이나, `--diff` 의 구문상 불완전한 조각(ast.parse 실패)에 쓴다.
    """
    lines = code.splitlines()
    if len(lines) <= window:
        return [Chunk(None, code, 1, _line_count(code))]
    out: list[Chunk] = []
    for i in range(0, len(lines), step):
        piece = lines[i : i + window]
        out.append(Chunk(None, "\n".join(piece), i + 1, i + len(piece)))
        if i + window >= len(lines):
            break
    return out


def chunk_for_scan(code: str, lang: str = "python") -> list[Chunk]:
    """스캔용 청킹 — 인덱스와 같은 크기로 의심 코드를 쪼갠다.

    Python 이고 함수가 있으면 함수 단위. 아니면(비Python·파싱 실패·함수 없음)
    슬라이딩 윈도우. **파일 전체를 한 조각으로 쓰지 않는다.**
    """
    if lang == "python":
        try:
            fns = iter_functions(code)
            if fns:
                return fns
        except SyntaxError:
            pass
    return sliding_windows(code)
