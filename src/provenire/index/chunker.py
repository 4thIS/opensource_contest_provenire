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

__all__ = ["iter_functions", "sliding_windows", "chunk_for_scan", "MIN_CHUNK_LINES"]

MIN_CHUNK_LINES = 5    # 이보다 짧은 함수는 관용구라 청킹에서 제외
_WINDOW = 30           # 슬라이딩 윈도우 크기(줄)
_STEP = 15             # 이동 간격(줄) — 조각이 함수 경계를 걸쳐도 하나는 온전히 담기게 겹친다


def iter_functions(code: str) -> list[tuple[str, str]]:
    """Python 함수 단위 조각. `ast.parse` 실패 시 SyntaxError 를 그대로 올린다."""
    out: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.end_lineno or 0) - node.lineno + 1 < MIN_CHUNK_LINES:
                continue
            seg = ast.get_source_segment(code, node)
            if seg:
                out.append((node.name, seg))
    return out


def sliding_windows(
    code: str, window: int = _WINDOW, step: int = _STEP
) -> list[tuple[None, str]]:
    """겹치는 고정 크기 창으로 쪼갠다 — 함수 경계를 모를 때의 fallback.

    비-Python 파일이나, `--diff` 의 구문상 불완전한 조각(ast.parse 실패)에 쓴다.
    """
    lines = code.splitlines()
    if len(lines) <= window:
        return [(None, code)]
    out: list[tuple[None, str]] = []
    for i in range(0, len(lines), step):
        out.append((None, "\n".join(lines[i : i + window])))
        if i + window >= len(lines):
            break
    return out


def chunk_for_scan(code: str, lang: str = "python") -> list[tuple[str | None, str]]:
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
