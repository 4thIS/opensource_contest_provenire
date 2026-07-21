"""Provenire — AI가 생성한 코드가 오픈소스 라이선스를 베꼈는지 탐지한다.

    >>> from provenire import compare
    >>> compare(suspect_code, gpl_code).similarity
    1.0
    >>> compare(java_a, java_b, lang="java").similarity

핵심: 변수명을 바꿔도 잡아낸다. (benchmarks/RESULTS.md 참조)
새 언어 추가: provenire/languages/ 참조 (core를 고칠 필요 없다)
"""
from . import languages
from .core.fingerprint import fingerprint
from .core.matcher import Match, Scanner, compare, containment, jaccard
from .core.normalizer import normalize_raw, normalize_tokens

__version__ = "0.1.3"   # pyproject.toml 의 version 과 반드시 같다 (tests/test_version.py)
__all__ = [
    "Scanner", "Match", "compare",
    "fingerprint", "normalize_tokens", "normalize_raw",
    "containment", "jaccard",
    "languages",
]
