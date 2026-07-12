"""Python 언어팩 — 다른 언어팩을 만들 때의 참고 구현.

Python에서 "구조"로 볼 것:
    - 키워드      def, if, return, for ...
    - 빌트인      len, str, int, range ...  (이름을 바꾸지 않으므로 구조에 가깝다)

나머지 이름(변수·함수·클래스)은 전부 ID로 익명화된다.
"""
from pygments.token import Token

from .base import LanguageSpec

SPEC = LanguageSpec(
    name="python",
    lexer="python",
    extensions=(".py", ".pyi"),
    keep=(
        Token.Keyword,
        Token.Name.Builtin,
        Token.Name.Builtin.Pseudo,   # self, cls, True, False, None
    ),
)
