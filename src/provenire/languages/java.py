"""Java 언어팩 — 이름만 바꾼 재현을 잡아낸다.

정규화 원칙은 Python과 동일하다: 이름은 지우고 구조는 남긴다.
Java에서 "구조"로 볼 것:
    - 키워드          public, class, static, if, return, new, throw ...
                      (Pygments 는 이들을 Token.Keyword / Token.Keyword.Declaration 로 낸다)
    - 기본형 타입     int, long, double, boolean ...  (Token.Keyword.Type)

⚠️ Pygments 실측 결과 (추측이 아니라 직접 lex 해서 확인함):
    - `int` 등 기본형   -> Token.Keyword.Type   (여기서 keep 으로 보존)
    - `String`·`List` 등 참조 타입 -> Token.Name  (변수명과 구분 불가 -> ID 로 익명화)
    - 메서드 호출 `.length()` -> Token.Name.Attribute (Token.Name 하위 -> ID)
    - 클래스·메서드명   -> Token.Name.Class / Token.Name.Function (Token.Name 하위 -> ID)

참조 타입(String 등)이 ID 가 되어도, 이름만 바꾼 재현은 양쪽이 동일하게
정규화되므로 탐지에 문제가 없다. (검증: tests/test_languages.py)
"""
from pygments.token import Token

from .base import LanguageSpec

SPEC = LanguageSpec(
    name="java",
    lexer="java",
    extensions=(".java",),
    keep=(
        Token.Keyword,        # public, class, static, if, return, new, throw ...
        Token.Keyword.Type,   # int, long, double, boolean ... (기본형 = 구조)
    ),
)
