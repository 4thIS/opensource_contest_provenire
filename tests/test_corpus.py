"""코퍼스 수집기 테스트 — 네트워크 없이 (가짜 fetch 주입).

    "내려받은 카피레프트 코드를 함수 단위로 청킹해 지문 인덱스를 채우고,
     그 인덱스가 이름만 바꾼 재현을 잡아낸다."
"""
from provenire import Scanner
from provenire.index import FileIndex, FingerprintStore
from provenire.index.corpus import CorpusSource, build_index, chunk

# 함수 2개짜리 원본 (하나는 길고, 하나는 너무 짧아 청킹에서 빠져야 한다)
TWO_FUNCS = '''
def elide_filename(filename, length):
    marker = "..."
    if length < len(marker):
        raise ValueError("too short")
    if len(filename) <= length:
        return filename
    cut = len(filename) - length + len(marker)
    left = (len(filename) - cut) // 2
    return filename[:left] + marker


def tiny(x):
    return x + 1
'''

# elide_filename 을 변수명만 바꿔 베낀 코드
COPIED_RENAMED = '''
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


def test_chunk_splits_functions_and_skips_tiny():
    chunks = chunk(TWO_FUNCS, "python")
    names = [name for name, _ in chunks]
    assert "elide_filename" in names
    assert "tiny" not in names        # 5줄 미만 → 청킹 제외


def test_chunk_non_python_is_single_piece():
    chunks = chunk("some { js } code", "javascript")
    assert len(chunks) == 1
    assert chunks[0][0] is None       # 심볼 없음 = 파일 단위 fallback


def test_chunk_handles_syntax_error():
    chunks = chunk("def broken(:\n", "python")
    assert chunks == [(None, "def broken(:\n")]


def test_build_index_populates_and_detects():
    """★ 가짜 fetch 로 코퍼스를 만들고, 이름 바꾼 재현이 잡히는지 확인한다."""
    src = CorpusSource(
        project="acme", file="util.py",
        license="GPL-3.0-or-later", url="https://example.com/util.py",
    )
    store = build_index([src], FingerprintStore(), fetch=lambda url: TWO_FUNCS)

    assert len(store) >= 1            # 함수 청크가 인덱싱됐다
    hits = FileIndex(store).search(Scanner(lang="python")._fp(COPIED_RENAMED))
    assert hits, "이름만 바꾼 재현을 코퍼스 인덱스가 놓쳤다"
    assert hits[0].project == "acme"
    assert hits[0].symbol == "elide_filename"   # 함수 단위로 매칭됐다
    assert hits[0].license == "GPL-3.0-or-later"


def test_build_index_skips_failed_fetch():
    """한 소스가 네트워크 실패해도 건너뛰고 계속한다 (예외로 죽지 않는다)."""
    def boom(url):
        raise ConnectionError("network down")

    store = build_index(
        [CorpusSource("p", "f.py", "GPL-3.0", "https://x")],
        FingerprintStore(), fetch=boom,
    )
    assert len(store) == 0
