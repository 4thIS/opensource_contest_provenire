"""코드 정규화 — 지문을 뜨기 전에 '무엇을 지울지' 정하는 단계.

핵심 아이디어:
    AI가 오픈소스를 베낄 때 가장 흔히 하는 변형은 **변수·함수명 바꾸기**다.
    식별자를 익명 토큰(ID)으로 치환하면 이름을 아무리 바꿔도 지문이 동일해진다.
    → 이것이 raw 문자열 비교(GitHub Copilot의 public code filter 수준)와의 결정적 차이다.

    검증 결과: benchmarks/RESULTS.md
    변수명 전부 변경 시 → raw 0.0% / 토큰 정규화 100.0%

언어별 규칙은 여기 없다:
    "무엇을 구조로 볼 것인가"는 `provenire/languages/` 의 언어팩이 정한다.
    새 언어를 추가할 때 이 파일을 고칠 필요는 없다.
"""
from __future__ import annotations

import re

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
from pygments.util import ClassNotFound

from ..languages import LanguageSpec, get, guess

__all__ = ["normalize_raw", "normalize_tokens", "resolve_spec"]


def resolve_spec(filename: str | None = None, lang: str | None = None) -> LanguageSpec:
    """언어 이름 > 파일 확장자 > python 순으로 언어팩을 정한다."""
    return get(lang) if lang else guess(filename)


def normalize_raw(code: str) -> str:
    """주석·공백만 제거하는 단순 정규화 (비교용 baseline).

    이름을 바꾸면 그대로 무너진다 — Copilot 필터가 놓치는 이유.
    """
    code = re.sub(r"//.*", "", code)                  # C 계열 한 줄 주석
    code = re.sub(r"#.*", "", code)                   # Python·셸 주석
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)        # C 계열 블록 주석
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    code = re.sub(r"'''[\s\S]*?'''", "", code)
    return re.sub(r"\s+", "", code)


def normalize_tokens(
    code: str,
    filename: str | None = None,
    lang: str | None = None,
) -> str:
    """토큰 정규화 — 식별자/문자열/숫자를 익명 토큰으로 치환한다.

    보존하는 것: 언어팩의 `keep` (키워드·타입 등) + 연산자 · 구두점  → **구조**
    지우는 것:   변수명 · 함수명 · 문자열 · 숫자                      → **표면**
    """
    spec = resolve_spec(filename, lang)
    try:
        lexer = get_lexer_by_name(spec.lexer)
    except ClassNotFound:  # pragma: no cover - 언어팩 설정 오류
        lexer = get_lexer_by_name("python")

    out: list[str] = []
    for tok, val in lex(code, lexer):
        if not val.strip():
            continue
        if tok in Token.Comment:
            continue
        if spec.keeps(tok):
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
