"""코드 정규화 — 지문을 뜨기 전에 '무엇을 지울지' 정하는 단계.

핵심 아이디어:
    AI가 오픈소스를 베낄 때 가장 흔히 하는 변형은 **변수·함수명 바꾸기**다.
    식별자를 익명 토큰(ID)으로 치환하면 이름을 아무리 바꿔도 지문이 동일해진다.
    → 이것이 raw 문자열 비교(GitHub Copilot의 public code filter 수준)와의 결정적 차이다.

    검증 결과: benchmarks/RESULTS.md
    변수명 전부 변경 시 → raw 0.0% / 토큰 정규화 100.0%
"""
from __future__ import annotations

import re

from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound

__all__ = ["normalize_raw", "normalize_tokens", "lexer_for"]


def lexer_for(filename: str | None = None, code: str = "", lang: str | None = None):
    """파일명/언어로 Pygments 렉서를 고른다. 실패 시 Python으로 폴백."""
    if lang:
        try:
            return get_lexer_by_name(lang)
        except ClassNotFound:
            pass
    if filename:
        try:
            return guess_lexer_for_filename(filename, code)
        except ClassNotFound:
            pass
    return get_lexer_by_name("python")


def normalize_raw(code: str) -> str:
    """주석·공백만 제거하는 단순 정규화 (비교용 baseline).

    이름을 바꾸면 그대로 무너진다 — Copilot 필터가 놓치는 이유.
    """
    code = re.sub(r"#.*", "", code)
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    code = re.sub(r"'''[\s\S]*?'''", "", code)
    return re.sub(r"\s+", "", code)


def normalize_tokens(code: str, filename: str | None = None, lang: str | None = None) -> str:
    """토큰 정규화 — 식별자/문자열/숫자를 익명 토큰으로 치환한다.

    보존하는 것: 키워드 · 빌트인 · 연산자 · 구두점  → **코드의 구조**
    지우는 것:   변수명 · 함수명 · 문자열 · 숫자     → **표면적 차이**
    """
    lexer = lexer_for(filename, code, lang)
    out: list[str] = []
    for tok, val in lex(code, lexer):
        if val.strip() == "":
            continue
        if tok in Token.Comment:
            continue
        if tok in Token.Keyword or tok in Token.Name.Builtin:
            out.append(val)          # 구조 정보 — 보존
        elif tok in Token.Name:
            out.append("ID")         # ← 핵심: 이름을 지운다
        elif tok in Token.Literal.String:
            out.append("STR")
        elif tok in Token.Literal.Number:
            out.append("NUM")
        else:
            out.append(val)          # 연산자·구두점 = 구조
    return "".join(out)
