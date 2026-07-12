"""유사도 판정.

표절 탐지에서는 Jaccard보다 **포함도(containment)** 가 적합하다.
    Jaccard      = |A ∩ B| / |A ∪ B|   ← 길이 차이에 취약
    Containment  = |A ∩ B| / |A|       ← "의심 코드의 몇 %가 원본에 있나"

작은 함수 하나를 거대한 GPL 파일에서 베껴온 경우, Jaccard는 낮게 나오지만
containment는 정확히 잡아낸다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fingerprint import K_DEFAULT, W_DEFAULT, fingerprint
from .normalizer import normalize_raw, normalize_tokens

__all__ = ["Match", "jaccard", "containment", "compare", "Scanner"]


@dataclass(frozen=True)
class Match:
    """유사도 판정 결과."""

    similarity: float   # 0.0 ~ 1.0 (containment)
    shared: int         # 공유 지문 개수
    total: int          # 의심 코드의 전체 지문 개수

    @property
    def is_suspicious(self) -> bool:
        return self.similarity >= Scanner.THRESHOLD


def jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(suspect: set[int], origin: set[int]) -> float:
    """의심 코드의 지문 중 원본에 존재하는 비율."""
    if not suspect:
        return 0.0
    return len(suspect & origin) / len(suspect)


class Scanner:
    """두 코드의 유사도를 잰다.

    mode="tokens" (기본) — 식별자 익명화. 변수명을 바꿔도 잡아낸다.
    mode="raw"           — 문자 그대로. 비교/검증용 baseline.

    언어는 `lang="java"` 로 지정하거나, `filename` 확장자로 추론한다.
    지원 언어: provenire.languages.available()
    """

    THRESHOLD = 0.30   # 이 이상이면 '의심'

    def __init__(
        self,
        mode: str = "tokens",
        k: int = K_DEFAULT,
        w: int = W_DEFAULT,
        lang: str | None = None,
    ):
        if mode not in ("tokens", "raw"):
            raise ValueError("mode는 'tokens' 또는 'raw'")
        self.mode, self.k, self.w, self.lang = mode, k, w, lang

    def fingerprint_of(self, code: str, filename: str | None = None) -> set[int]:
        """코드 → 정규화 → winnowing 지문."""
        text = (
            normalize_tokens(code, filename=filename, lang=self.lang)
            if self.mode == "tokens"
            else normalize_raw(code)
        )
        return fingerprint(text, k=self.k, w=self.w)

    # 하위 호환
    _fp = fingerprint_of

    def compare(self, suspect: str, origin: str, filename: str | None = None) -> Match:
        fs = self.fingerprint_of(suspect, filename)
        fo = self.fingerprint_of(origin, filename)
        return Match(
            similarity=containment(fs, fo),
            shared=len(fs & fo),
            total=len(fs),
        )


def compare(
    suspect: str,
    origin: str,
    mode: str = "tokens",
    lang: str | None = None,
    filename: str | None = None,
) -> Match:
    """단축 함수.

        >>> compare(ai_code, gpl_code).similarity
        >>> compare(java_a, java_b, lang="java").similarity
    """
    return Scanner(mode=mode, lang=lang).compare(suspect, origin, filename=filename)
