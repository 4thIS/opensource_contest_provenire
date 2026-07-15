"""MockIndex 계약 테스트.

민수의 T-03(provenire scan)이 이 계약에 기대어 개발된다.
'겹치면 찾고, 안 겹치면 안 찾고, 메타를 정확히 실어 준다.'
"""
from provenire import Scanner
from provenire.index import FileIndex, FingerprintStore, Index, MockIndex

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


# ─────────────────────────── FileIndex (sqlite) ───────────────────────────


def _store_with_origin(path: str = ":memory:") -> FingerprintStore:
    store = FingerprintStore(path)
    store.add(Scanner()._fp(ORIGIN), project="acme", file="util.py",
              symbol="elide_filename", license="GPL-3.0-or-later",
              url="https://example.com/util.py")
    return store


def test_fileindex_finds_renamed_code():
    """★ 디스크 인덱스도 이름만 바꾼 코드를 찾아낸다."""
    hits = FileIndex(_store_with_origin()).search(Scanner()._fp(RENAMED))
    assert len(hits) == 1
    assert hits[0].project == "acme"
    assert hits[0].license == "GPL-3.0-or-later"
    assert hits[0].shared > 0


def test_fileindex_ignores_unrelated_code():
    assert FileIndex(_store_with_origin()).search(Scanner()._fp(UNRELATED)) == []


def test_fileindex_satisfies_index_protocol():
    assert isinstance(FileIndex(FingerprintStore()), Index)


def test_store_persists_across_reopen(tmp_path):
    """디스크에 저장하고 새 연결로 다시 열어도 검색된다."""
    db = str(tmp_path / "idx.db")
    _store_with_origin(db).close()
    hits = FileIndex(FingerprintStore(db)).search(Scanner()._fp(RENAMED))
    assert len(hits) == 1


def test_store_saves_no_source_code(tmp_path):
    """⚠️ 저작권 안전 — DB에 원본 코드가 저장되지 않는다 (지문 해시만)."""
    db = tmp_path / "idx.db"
    FingerprintStore(str(db)).add(
        Scanner()._fp(ORIGIN), project="acme", file="util.py",
        license="GPL-3.0-or-later", url="x",  # symbol(=함수명) 생략
    )
    raw = db.read_bytes()
    assert b"marker" not in raw    # 원본 코드의 지역변수명이 DB에 없다
    assert b"elidestr" not in raw
