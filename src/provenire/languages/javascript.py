"""JavaScript 언어팩 — 이름만 바꾼 재현을 잡아낸다.

정규화 원칙은 Python·Java와 동일하다: 이름은 지우고 구조는 남긴다.

⚠️ Pygments 실측 결과 (추측이 아니라 직접 lex 해서 확인함):
    - `function`·`const`·`let`·`var`  -> Token.Keyword.Declaration (Keyword 하위 -> 보존)
    - `if`·`return`·`for` 등          -> Token.Keyword            (keep 으로 보존)
    - `new`                           -> Token.Operator.Word      (연산자 -> 자동 보존)
    - 변수·함수·메서드명               -> Token.Name.Other         (Token.Name 하위 -> ID)
    - `Error` 등 내장 예외             -> Token.Name.Exception     (Token.Name 하위 -> ID)

JS 는 타입 애노테이션이 없으므로 keep 은 키워드만으로 충분하다.
(TS 는 `string`·`number` 가 Token.Keyword.Type 라 typescript.py 에서 추가로 보존한다.)
"""
from pygments.token import Token

from .base import LanguageSpec

SPEC = LanguageSpec(
    name="javascript",
    lexer="javascript",
    extensions=(".js", ".mjs", ".cjs", ".jsx"),
    keep=(
        Token.Keyword,   # function, const, let, if, return, for ... (Declaration 포함)
    ),
)
