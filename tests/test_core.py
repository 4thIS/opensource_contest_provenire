"""핵심 명제를 지키는 테스트.

    "변수명을 바꿔도 탐지되어야 한다. 무관한 코드는 잡히면 안 된다."

이 두 줄이 무너지면 프로젝트의 존재 이유가 사라진다.
"""
import pytest

from provenire import Scanner, compare, fingerprint, normalize_tokens

ORIGIN = '''
def elide_filename(filename: str, length: int) -> str:
    """Elide a filename to the given length."""
    elidestr = "..."
    if length < len(elidestr):
        raise ValueError("length must be greater or equal to 3")
    if len(filename) <= length:
        return filename
    to_elide = len(filename) - length + len(elidestr)
    left = (len(filename) - to_elide) // 2
    right = len(filename) - to_elide - left
    return filename[:left] + elidestr + filename[len(filename) - right:]
'''

# 변수·함수명만 전부 바꾼 버전 (= AI가 흔히 뱉는 형태)
RENAMED = '''
def truncate_path(path_str: str, max_len: int) -> str:
    """Truncate a path to the given length."""
    marker = "..."
    if max_len < len(marker):
        raise ValueError("max_len must be greater or equal to 3")
    if len(path_str) <= max_len:
        return path_str
    cut = len(path_str) - max_len + len(marker)
    head = (len(path_str) - cut) // 2
    tail = len(path_str) - cut - head
    return path_str[:head] + marker + path_str[len(path_str) - tail:]
'''

UNRELATED = '''
def compute_statistics(dataset, weights=None):
    total = 0.0
    count = 0
    for row in dataset:
        total += row.value * (weights.get(row.key, 1.0) if weights else 1.0)
        count += 1
    mean = total / count if count else 0.0
    return {"mean": mean, "n": count}
'''


def test_identical_code_is_detected():
    assert compare(ORIGIN, ORIGIN).similarity == pytest.approx(1.0)


def test_renamed_identifiers_are_still_detected():
    """★ 프로젝트의 존재 이유 — 이름을 바꿔도 잡아낸다."""
    m = compare(RENAMED, ORIGIN, mode="tokens")
    assert m.is_suspicious, f"변수명 변경 코드를 놓쳤다 (유사도 {m.similarity:.1%})"


def test_raw_mode_fails_on_renaming():
    """대조군 — raw 방식(Copilot 필터 수준)은 이름 변경에 무너진다."""
    raw = compare(RENAMED, ORIGIN, mode="raw")
    tok = compare(RENAMED, ORIGIN, mode="tokens")
    assert tok.similarity > raw.similarity, "토큰 정규화가 raw보다 나아야 한다"


def test_unrelated_code_is_not_flagged():
    """오탐 방지 — 무관한 코드는 잡히면 안 된다."""
    assert not compare(UNRELATED, ORIGIN).is_suspicious


def test_normalize_erases_identifier_names():
    a = normalize_tokens("def foo(bar):\n    return bar + 1\n")
    b = normalize_tokens("def qux(zap):\n    return zap + 1\n")
    assert a == b, "식별자가 익명화되지 않았다"


def test_fingerprint_is_empty_for_short_text():
    assert fingerprint("ab", k=25) == set()


def test_scanner_rejects_bad_mode():
    with pytest.raises(ValueError):
        Scanner(mode="nope")
