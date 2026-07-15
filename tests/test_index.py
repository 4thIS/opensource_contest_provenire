"""MockIndex 계약 테스트.

민수의 T-03(provenire scan)이 이 계약에 기대어 개발된다.
'겹치면 찾고, 안 겹치면 안 찾고, 메타를 정확히 실어 준다.'
"""
from provenire import Scanner
from provenire.index import Index, MockIndex

ORIGIN = '''
def elide_filename(filename, length):
    marker = "..."
    if length < len(marker):
        raise ValueError("too short")
    if len(filename) <= length:
        return filename
    cut = len(filename) - length + len(marker)
    left = (len(filename) - cut) // 2
    return filename[:left] + marker
'''

# 이름만 바꾼 버전 — AI가 흔히 뱉는 형태
RENAMED = '''
def truncate_path(path_str, max_len):
    dots = "..."
    if max_len < len(dots):
        raise ValueError("too short")
    if len(path_str) <= max_len:
        return path_str
    cut = len(path_str) - max_len + len(dots)
    head = (len(path_str) - cut) // 2
    return path_str[:head] + dots
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


def _index_with_origin() -> MockIndex:
    idx = MockIndex()
    idx.add(ORIGIN, project="acme", file="util.py", symbol="elide_filename",
            license="GPL-3.0-or-later", url="https://example.com/util.py")
    return idx


def test_empty_index_finds_nothing():
    assert MockIndex().search(Scanner()._fp(ORIGIN)) == []


def test_renamed_code_is_found():
    """★ 인덱스에 심은 원본을 '이름만 바꾼 코드'로도 찾아낸다."""
    hits = _index_with_origin().search(Scanner()._fp(RENAMED))
    assert len(hits) == 1
    h = hits[0]
    assert h.project == "acme"
    assert h.symbol == "elide_filename"
    assert h.license == "GPL-3.0-or-later"
    assert h.shared > 0
    assert h.total > 0


def test_unrelated_code_is_not_found():
    assert _index_with_origin().search(Scanner()._fp(UNRELATED)) == []


def test_top_k_limits_results():
    idx = MockIndex()
    for i in range(5):
        idx.add(ORIGIN, project=f"p{i}", file="util.py",
                license="GPL-3.0-or-later", url="x")
    assert len(idx.search(Scanner()._fp(RENAMED), top_k=3)) == 3


def test_results_sorted_by_shared_desc():
    hits = _index_with_origin().search(Scanner()._fp(RENAMED))
    assert hits == sorted(hits, key=lambda h: h.shared, reverse=True)


def test_mockindex_satisfies_index_protocol():
    assert isinstance(MockIndex(), Index)
