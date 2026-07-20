"""`provenire scan` — PR 게이트 코어 테스트.

핵심 설계: 로직(`scan_paths`)이 **인덱스를 인자로 받는 순수 함수**라서
MockIndex 를 주입해 실제 코퍼스 없이 탐지/오탐/exit code 를 검증한다.
"""
import argparse
from pathlib import Path

from provenire import Scanner
from provenire.cli import _load_index, main, scan_paths
from provenire.index import FileIndex, FingerprintStore, MockIndex

# 인덱스에 심을 "카피레프트 원본" (자체 작성 코드 — 저작권 안전)
GPL_LIKE = '''
def elide_filename(filename, length):
    marker = "..."
    if length < len(marker):
        raise ValueError("too short")
    if len(filename) <= length:
        return filename
    to_elide = len(filename) - length + len(marker)
    left = (len(filename) - to_elide) // 2
    return filename[:left] + marker
'''

# 위를 변수·함수명만 바꿔 베낀 코드 (AI가 흔히 뱉는 형태)
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

CLEAN = "def add(a, b):\n    return a + b\n"


def _index() -> MockIndex:
    idx = MockIndex()
    idx.add(
        GPL_LIKE,
        project="acme",
        file="util.py",
        symbol="elide_filename",
        license="GPL-3.0-or-later",
        url="https://example.com/util.py",
    )
    return idx


def test_scan_detects_copied_file(tmp_path):
    """이름만 바꿔 베낀 파일 → 인덱스와 대조해 잡아낸다."""
    f = tmp_path / "mycode.py"
    f.write_text(COPIED_RENAMED, encoding="utf-8")
    findings = scan_paths([str(f)], index=_index())
    assert len(findings) == 1
    assert findings[0].hit.license == "GPL-3.0-or-later"
    assert findings[0].hit.project == "acme"
    assert findings[0].similarity >= 0.30


def test_scan_passes_clean_file(tmp_path):
    """무관한 파일 → 탐지 없음."""
    f = tmp_path / "clean.py"
    f.write_text(CLEAN, encoding="utf-8")
    assert scan_paths([str(f)], index=_index()) == []


def test_scan_recurses_directory(tmp_path):
    """디렉터리를 주면 지원 언어 파일을 재귀적으로 순회한다."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "copied.py").write_text(COPIED_RENAMED, encoding="utf-8")
    (tmp_path / "clean.py").write_text(CLEAN, encoding="utf-8")
    findings = scan_paths([str(tmp_path)], index=_index())
    assert len(findings) == 1
    assert findings[0].file.endswith("copied.py")


def test_scan_ignores_unsupported_extension(tmp_path):
    """디렉터리 순회 시 지원하지 않는 확장자는 건너뛴다."""
    (tmp_path / "notes.txt").write_text(COPIED_RENAMED, encoding="utf-8")
    assert scan_paths([str(tmp_path)], index=_index()) == []


def _build_db(path) -> str:
    """FingerprintStore(sqlite) 에 원본 지문을 심어 db 파일을 만든다 (--index 용)."""
    store = FingerprintStore(str(path))
    store.add(
        Scanner()._fp(GPL_LIKE),
        project="acme",
        file="util.py",
        symbol="elide_filename",
        license="GPL-3.0-or-later",
        url="https://example.com/util.py",
    )
    store.close()
    return str(path)


def test_scan_exit_code_1_on_detection(tmp_path):
    """의심이 있으면 CLI exit code 1 (PR 게이트 실패 판정) — --index db 경유(FileIndex)."""
    f = tmp_path / "mycode.py"
    f.write_text(COPIED_RENAMED, encoding="utf-8")
    db = _build_db(tmp_path / "copyleft.db")
    assert main(["scan", str(f), "--index", db]) == 1


def test_scan_exit_code_0_when_clean(tmp_path):
    """빈 인덱스(기본) + 무관 코드 → exit 0."""
    f = tmp_path / "clean.py"
    f.write_text(CLEAN, encoding="utf-8")
    assert main(["scan", str(f)]) == 0


# ─────────────────────────── _load_index 폴백 (내장 인덱스) ───────────────────────────
#
# T-06: `pip install provenire` 후 --index 없이도 동봉 인덱스로 탐지되게 했다.
# 동봉 db 는 src/provenire/ 밑이 아니라 설치본에만 있으므로, 패키징에 의존하지 않도록
# _default_index_path 를 monkeypatch 해 _load_index 의 세 분기를 검증한다.


def _args(index=None):
    return argparse.Namespace(index=index)


def test_load_index_uses_explicit_index(tmp_path):
    """① --index 를 명시하면 그 db 를 FileIndex 로 로드한다."""
    db = _build_db(tmp_path / "explicit.db")
    assert isinstance(_load_index(_args(index=db)), FileIndex)


def test_load_index_falls_back_to_bundled(tmp_path, monkeypatch):
    """② --index 가 없으면 패키지 동봉 인덱스를 기본으로 쓴다."""
    db = _build_db(tmp_path / "bundled.db")
    monkeypatch.setattr("provenire.cli._default_index_path", lambda: Path(db))
    assert isinstance(_load_index(_args(index=None)), FileIndex)


def test_load_index_empty_when_none_available(monkeypatch):
    """③ --index 도 동봉 인덱스도 없으면 빈 MockIndex 로 동작한다."""
    monkeypatch.setattr("provenire.cli._default_index_path", lambda: None)
    assert isinstance(_load_index(_args(index=None)), MockIndex)
