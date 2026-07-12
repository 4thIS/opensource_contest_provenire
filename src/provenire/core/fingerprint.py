"""Winnowing 지문 — MOSS(표절탐지 표준)가 쓰는 문서 핑거프린팅 알고리즘.

    Schleimer, Wilkerson, Aiken. "Winnowing: Local Algorithms for Document
    Fingerprinting" (SIGMOD 2003)

동작:
    1. 정규화된 텍스트를 길이 k의 k-gram으로 쪼갠다
    2. 각 k-gram을 해시한다
    3. 크기 w의 슬라이딩 윈도우마다 **최소 해시**를 지문으로 채택

왜 최소값인가:
    삽입·삭제가 있어도 같은 구간에서는 같은 최소값이 뽑힐 확률이 높다.
    → 부분 복사·순서 변경에 강인하다.
"""
from __future__ import annotations

import hashlib

__all__ = ["Fingerprint", "fingerprint", "K_DEFAULT", "W_DEFAULT"]

K_DEFAULT = 25   # k-gram 길이
W_DEFAULT = 12   # winnowing 윈도우 크기

Fingerprint = set  # set[int]


def _hash(chunk: str) -> int:
    return int(hashlib.md5(chunk.encode("utf-8")).hexdigest()[:8], 16)


def fingerprint(text: str, k: int = K_DEFAULT, w: int = W_DEFAULT) -> set[int]:
    """정규화된 텍스트 → winnowing 지문 집합."""
    if k <= 0 or w <= 0:
        raise ValueError("k와 w는 양수여야 합니다")
    if len(text) < k:
        return set()

    hashes = [_hash(text[i : i + k]) for i in range(len(text) - k + 1)]
    if len(hashes) < w:
        return {min(hashes)}

    fps: set[int] = set()
    for i in range(len(hashes) - w + 1):
        fps.add(min(hashes[i : i + w]))
    return fps
