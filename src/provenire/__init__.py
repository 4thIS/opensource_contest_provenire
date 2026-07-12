"""Provenire — AI가 생성한 코드가 오픈소스 라이선스를 베꼈는지 탐지한다.

    >>> from provenire import compare
    >>> compare(suspect_code, gpl_code).similarity
    1.0

핵심: 변수명을 바꿔도 잡아낸다. (benchmarks/RESULTS.md 참조)
"""
from .core.fingerprint import fingerprint
from .core.matcher import Match, Scanner, compare, containment, jaccard
from .core.normalizer import normalize_raw, normalize_tokens

__version__ = "0.0.1"
__all__ = [
    "Scanner", "Match", "compare",
    "fingerprint", "normalize_tokens", "normalize_raw",
    "containment", "jaccard",
]
