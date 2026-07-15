"""TypeScript 언어팩 — 이름만 바꾼 재현을 잡아낸다.

정규화 원칙은 Python·Java·JS와 동일하다: 이름은 지우고 구조는 남긴다.

⚠️ Pygments 실측 결과 (추측이 아니라 직접 lex 해서 확인함):
    - `function`·`const` 등 키워드   -> Token.Keyword(.Declaration)  (keep 으로 보존)
    - `string`·`number`·`boolean`   -> Token.Keyword.Type            (keep 으로 보존)
      ★ Java 의 `String` 이 Token.Name(→ID) 이던 것과 **정반대**다.
        TS 는 원시 타입명을 Keyword.Type 로 분류하므로 타입을 구조로 남길 수 있다.
        타입 애노테이션(`: string`, `: number`)이 구조로 보존되면 재현 판별이 더 정확해진다.
    - 변수·함수명                    -> Token.Name.Other             (-> ID 로 익명화)

그래서 JS(키워드만) 와 달리 TS 는 Keyword.Type 을 함께 keep 한다.
"""
from pygments.token import Token

from .base import LanguageSpec

SPEC = LanguageSpec(
    name="typescript",
    lexer="typescript",
    extensions=(".ts", ".tsx"),
    keep=(
        Token.Keyword,        # function, const, if, return ... (Declaration 포함)
        Token.Keyword.Type,   # string, number, boolean (TS 는 타입이 구조로 잡힌다)
    ),
)
