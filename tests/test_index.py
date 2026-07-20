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


# ─────────────────────────── 관용구 필터 (WP-C) ───────────────────────────

# 여러 원본에 흔히 나오는 관용구 (표절 신호가 아니다)
BOILERPLATE = '''
def __init__(self, name, value, parent=None):
    self.name = name
    self.value = value
    self.parent = parent
    self.children = []
    self.visible = True
    self.enabled = True
'''


def _store_with_idioms(copies: int = 4) -> FingerprintStore:
    """같은 관용구를 여러 원본에 심어 '흔한 지문'을 만든다."""
    store = FingerprintStore()
    for i in range(copies):
        store.add(Scanner()._fp(BOILERPLATE), project=f"lib{i}", file="m.py",
                  license="GPL-3.0-or-later", url="x")
    return store


def test_tiny_overlap_is_not_reported():
    """★ 작은 diff 오탐 방지 — 몇 개 안 겹치는 후보는 후보로 치지 않는다.

    containment 는 `공유/전체` 라서 지문이 적으면 무의미하게 부풀려진다
    (4개 중 2개 = 50%). scan --diff 가 PR의 추가 줄만 볼 때 실제로 오탐이
    터졌다. MIN_SHARED 미만 겹침은 검색에서 제외한다. (RESULTS.md 참조)
    """
    from provenire.index import MIN_SHARED, _Entry, _rank

    origin_fp = frozenset(range(100))
    entries = [_Entry("acme", "u.py", "f", "GPL-3.0", "x", origin_fp)]

    # MIN_SHARED 미만만 겹치는 의심 지문 → 비율은 100%지만 후보가 아니어야 한다
    tiny = set(range(MIN_SHARED - 1))
    assert _rank(entries, tiny, top_k=10) == []

    # MIN_SHARED 이상 겹치면 정상적으로 잡힌다
    enough = set(range(MIN_SHARED))
    assert len(_rank(entries, enough, top_k=10)) == 1


def test_common_fingerprints_flags_shared_idioms():
    idioms = _store_with_idioms(4).common_fingerprints(min_count=4)
    assert idioms, "4개 원본에 공통인 지문(관용구)을 찾지 못했다"


def test_idiom_filter_removes_boilerplate_false_positive():
    """★ 관용구만 공유하는 코드 → 필터 켜면 오탐이 사라진다."""
    store = _store_with_idioms(4)
    suspect = Scanner()._fp(BOILERPLATE)
    assert FileIndex(store).search(suspect)                    # 필터 없으면 오탐
    assert FileIndex(store, idiom_min=4).search(suspect) == [] # 필터 켜면 제거


def test_idiom_filter_keeps_real_plagiarism():
    """★ 관용구를 걸러도 진짜 표절(이름만 바꾼 재현)은 그대로 잡힌다."""
    store = _store_with_idioms(4)
    store.add(Scanner()._fp(ORIGIN), project="acme", file="util.py",
              symbol="elide_filename", license="GPL-3.0-or-later", url="x")
    hits = FileIndex(store, idiom_min=4).search(Scanner()._fp(RENAMED))
    assert any(h.project == "acme" for h in hits)
