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

__all__ = ["normalize_raw", "normalize_tokens", "resolve_spec", "LITERAL_RUN_MAX"]

# 연속된 STR/NUM 을 몇 개까지 남길 것인가.
#
# Pygments 는 문자열 하나를 여러 토큰(따옴표·본문·이스케이프…)으로 쪼갠다. 토큰마다
# STR 을 붙이면 **리터럴의 길이가 곧 구조**가 되어, 긴 정규식을 쓰는 짧은 함수끼리
# 아무 관계가 없는데도 `STRSTRSTR…` 런만으로 지문이 겹친다.
# 실제로 dogfooding 이 우리 PR #42 에서 이 오탐을 잡았다(41.2%, tests/test_version.py).
#
# 2 인 이유 (2026-07-21 실측, benchmarks/RESULTS.md "문자열 리터럴 런" 절):
#   1(완전히 접기) → recall 90.7%→88.9%, F1 −1.0%p. 리터럴이 **나열된** 구조는
#                     개수 자체가 신호였다. 하나로 뭉개면 그 신호가 사라진다.
#   2             → F1 95.1% 그대로, 저장소 자체 스캔 오탐 4건 → 0건  ← 채택
#   3~5           → F1 은 같지만 오탐이 2~3건 남는다
# 즉 "하나냐 여럿이냐"는 남기고 "얼마나 긴가"만 버리는 값이 2 다.
LITERAL_RUN_MAX = 2


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
    run = 0                          # 같은 리터럴 자리표시자가 연속으로 몇 개 나왔나
    for tok, val in lex(code, lexer):
        if not val.strip():
            continue
        if tok in Token.Comment:
            continue
        if spec.keeps(tok):
            placeholder = val        # 구조 정보 — 보존
        elif tok in Token.Name:
            placeholder = "ID"       # ← 핵심: 이름을 지운다
        elif tok in Token.Literal.String:
            placeholder = "STR"
        elif tok in Token.Literal.Number:
            placeholder = "NUM"
        else:
            placeholder = val        # 연산자·구두점 = 구조

        # 리터럴의 **길이**는 구조가 아니다 — 연속 STR/NUM 을 최대 LITERAL_RUN_MAX 개로 자른다.
        if placeholder in ("STR", "NUM") and out and out[-1] == placeholder:
            run += 1
            if run >= LITERAL_RUN_MAX:
                continue
        else:
            run = 0
        out.append(placeholder)
    return "".join(out)
