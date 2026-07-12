"""언어팩의 계약 — 새 언어를 추가하려면 이 스펙 하나만 채우면 된다.

정규화의 원칙은 **모든 언어에서 동일**하다.

    이름은 지운다 (변수·함수·클래스명 -> ID)
    구조는 남긴다 (키워드·타입·연산자·구두점)

언어마다 다른 것은 **"무엇을 구조로 볼 것인가"** 뿐이다.
    Python: 키워드 + 빌트인(len, str...)
    Java  : 키워드 + 타입(String, int...)

그래서 언어팩은 `keep` 하나만 정하면 된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pygments.token import _TokenType

__all__ = ["LanguageSpec"]


@dataclass(frozen=True)
class LanguageSpec:
    """한 언어의 정규화 규칙.

    Attributes:
        name:       언어 이름. `compare(..., lang="java")` 로 쓰인다.
        lexer:      Pygments 렉서 별칭 (예: "python", "java", "javascript")
        extensions: 파일 확장자 — 파일명으로 언어를 추론할 때 쓴다.
        keep:       **원문 그대로 보존할 토큰 타입.** = 코드의 구조 정보.
                    여기 없는 Name 토큰은 전부 `ID` 로 익명화된다.

    예시 — Java 언어팩:
        LanguageSpec(
            name="java",
            lexer="java",
            extensions=(".java",),
            keep=(Token.Keyword, Token.Keyword.Type),   # 타입도 구조다
        )
    """

    name: str
    lexer: str
    extensions: tuple[str, ...] = ()
    keep: tuple[_TokenType, ...] = field(default_factory=tuple)

    def keeps(self, tok: _TokenType) -> bool:
        """이 토큰을 원문 그대로 남길 것인가 (= 구조 정보인가)."""
        return any(tok in k for k in self.keep)
