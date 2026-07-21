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


def test_literal_length_is_not_structure():
    """긴 문자열 리터럴이 `STR` 런을 만들지 않는다.

    Pygments 는 문자열 하나를 여러 토큰으로 쪼개므로, 토큰마다 STR 을 붙이면
    **리터럴의 길이가 곧 구조**가 된다. 그러면 아무 관계 없는 두 함수가
    `STRSTRSTR…` 런만으로 지문이 겹친다 (PR #42 에서 dogfooding 이 잡은 오탐).
    """
    long_regex = normalize_tokens(r"""x = re.search(r'^version\s*=\s*"([^"]+)"', t)""")
    short = normalize_tokens("""x = re.search('a', t)""")
    assert long_regex == short, "리터럴 길이가 지문에 남았다"
    assert "STRSTRSTR" not in long_regex


def test_literal_presence_survives():
    """길이는 버려도 '리터럴이 있다/없다'는 남아야 한다.

    오탐을 없애려고 리터럴을 **아예 지우고 싶은 유혹**이 있는데, 그러면 `f(a, 'x')` 와
    `f(a, b)` 가 같아져 구조 정보를 잃는다. 여기서 막는다.

    주의: 이 테스트는 `LITERAL_RUN_MAX` 가 **1 이냐 2 냐**를 가르지 못한다(둘 다 통과).
    그 선택의 근거는 단위테스트가 아니라 측정이다 — `benchmarks/evaluate.py`
    (1로 접으면 F1 95.1%→94.1%). RESULTS.md "문자열 리터럴 런" 절 참조.
    """
    with_str = normalize_tokens("x = 'a'")
    without = normalize_tokens("x = y")
    assert with_str != without, "리터럴 유무가 구분되지 않는다"


def test_unrelated_string_heavy_code_does_not_match():
    """문자열이 많다는 이유만으로 무관한 코드가 겹치지 않는다 (오탐 회귀 방지).

    실제로 tests/test_version.py 의 8줄짜리 함수가 qutebrowser 의 parse_duration 과
    41.2% 로 걸렸다. 둘 다 정규식을 쓴다는 것 말고는 공통점이 없었다.
    """
    mine = """
def check_version(text):
    found = re.search(r'^version\\s*=\\s*"([^"]+)"', text, re.MULTILINE).group(1)
    assert found == expected, f"{found} != {expected} 이다. 확인이 필요하다."
"""
    theirs = """
def parse_duration(duration):
    match = re.fullmatch(r'(?P<h>[0-9]+h)?\\s*(?P<m>[0-9]+m)?\\s*(?P<s>[0-9]+s)?', duration)
    if not match or not match.group(0):
        raise ValueError(f"Invalid duration: {duration} - expected XhYmZs")
    return int(match.group('s') or 0) * 1000
"""
    m = compare(mine, theirs)
    assert not m.is_suspicious, f"무관한 코드가 {m.similarity:.1%} 로 잡혔다"


def test_fingerprint_is_empty_for_short_text():
    assert fingerprint("ab", k=25) == set()


def test_scanner_rejects_bad_mode():
    with pytest.raises(ValueError):
        Scanner(mode="nope")
