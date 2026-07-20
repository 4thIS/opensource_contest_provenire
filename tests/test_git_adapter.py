"""git diff 어댑터 (`scan --diff`) 테스트.

핵심 설계: **diff 파싱은 순수 함수**(`parse_added_code`)라서 git 실행 없이 테스트한다.
검사 로직(`scan_changes`)도 인덱스를 주입받아 실제 코퍼스 없이 검증한다.
통합 테스트만 진짜 git 임시 저장소를 만들어 end-to-end 를 확인한다.
"""
import subprocess

from provenire import Scanner
from provenire.adapters.git import changed_code, parse_added_code
from provenire.cli import main, scan_changes
from provenire.index import FingerprintStore, MockIndex

# tests/test_cli.py 와 같은 픽스처 — 자체 작성 코드(저작권 안전)
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


# ─────────────────────────── 순수 파싱 (git 없이) ───────────────────────────

DIFF_ONE = '''diff --git a/src/foo.py b/src/foo.py
index 1234..5678 100644
--- a/src/foo.py
+++ b/src/foo.py
@@ -0,0 +1,3 @@
+def elide(name, n):
+    marker = "..."
+    return name[:n] + marker
'''


def test_parse_extracts_added_lines_per_file():
    changes = parse_added_code(DIFF_ONE)
    assert "src/foo.py" in changes
    assert "def elide(name, n):" in changes["src/foo.py"]
    assert "marker" in changes["src/foo.py"]


def test_parse_ignores_headers_context_and_deletions():
    """+++ 헤더, 컨텍스트 줄, 삭제(-) 줄은 '추가된 코드'가 아니다."""
    diff = '''diff --git a/a.py b/a.py
index 1..2 100644
--- a/a.py
+++ b/a.py
@@ -1,4 +1,4 @@
 keep_this = 1
-removed = 2
+added = 3
'''
    changes = parse_added_code(diff)
    assert changes["a.py"] == "added = 3"
    # 헤더/컨텍스트/삭제 줄은 포함되지 않는다
    assert "+++" not in changes["a.py"]
    assert "keep_this" not in changes["a.py"]
    assert "removed" not in changes["a.py"]


def test_parse_separates_multiple_files():
    diff = '''diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -0,0 +1 @@
+alpha = 1
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -0,0 +1 @@
+beta = 2
'''
    changes = parse_added_code(diff)
    assert changes == {"a.py": "alpha = 1", "b.py": "beta = 2"}


def test_parse_drops_files_with_no_additions():
    """추가 줄이 없는 파일(순수 삭제)은 결과에서 빠진다."""
    diff = '''diff --git a/gone.py b/gone.py
--- a/gone.py
+++ b/gone.py
@@ -1,2 +0,0 @@
-x = 1
-y = 2
'''
    assert parse_added_code(diff) == {}


def test_parse_empty_diff():
    assert parse_added_code("") == {}


# ─────────────────────────── scan_changes 단위 (인덱스 주입) ───────────────────────────


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


def test_scan_changes_detects_copied_code():
    """이름만 바꿔 베낀 추가 코드 → 인덱스와 대조해 잡는다."""
    findings = scan_changes({"mycode.py": COPIED_RENAMED}, index=_index())
    assert len(findings) == 1
    assert findings[0].file == "mycode.py"
    assert findings[0].hit.license == "GPL-3.0-or-later"
    assert findings[0].similarity >= 0.30


def test_scan_changes_passes_clean_code():
    assert scan_changes({"clean.py": CLEAN}, index=_index()) == []


def test_scan_changes_skips_unsupported_extension():
    """지원하지 않는 확장자는 검사하지 않는다 (베낀 코드여도)."""
    assert scan_changes({"notes.txt": COPIED_RENAMED}, index=_index()) == []


# ─────────────────────────── 통합 (진짜 git 저장소) ───────────────────────────


def _git(cwd, *args):
    # encoding="utf-8" 고정: 한글 커밋 메시지 등 비ASCII 출력을 Windows 기본
    # cp949 로 읽다 리더 스레드에서 UnicodeDecodeError 가 나는 것을 막는다 (이슈 #22)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


def _build_db(path) -> str:
    store = FingerprintStore(str(path))
    store.add(
        Scanner()._fp(GPL_LIKE),
        project="acme", file="util.py", symbol="elide_filename",
        license="GPL-3.0-or-later", url="https://example.com/util.py",
    )
    store.close()
    return str(path)


def test_changed_code_returns_only_added_files(tmp_path):
    """임시 git 저장소: 두 번째 커밋에서 추가한 파일만 changed_code 에 나온다."""
    _git(tmp_path, "init")
    (tmp_path / "base.py").write_text(CLEAN, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")

    (tmp_path / "new.py").write_text(COPIED_RENAMED, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "add copied")

    changes = changed_code("HEAD~1", cwd=str(tmp_path))
    assert "new.py" in changes
    assert "base.py" not in changes
    assert "truncate_path" in changes["new.py"]


def test_scan_diff_exit_code_1_on_detection(tmp_path, monkeypatch):
    """scan --diff <ref> 가 추가된 표절 코드를 잡아 exit 1."""
    _git(tmp_path, "init")
    (tmp_path / "base.py").write_text(CLEAN, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")

    (tmp_path / "copied.py").write_text(COPIED_RENAMED, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "add copied")

    db = _build_db(tmp_path / "copyleft.db")
    monkeypatch.chdir(tmp_path)
    assert main(["scan", "--diff", "HEAD~1", "--index", db]) == 1


def test_changed_code_handles_korean_comments(tmp_path):
    """한글/유니코드 주석이 있어도 diff 를 정상 파싱한다 (이슈 #22 회귀 방지).

    Windows 한국어 환경(cp949)에서 run_git_diff 가 UTF-8 한글 주석을 디코딩하다
    UnicodeDecodeError 로 크래시하던 버그. encoding="utf-8" 명시로 플랫폼 무관하게
    동작해야 한다. em dash(—) 같은 비ASCII 문자도 포함해 검증한다.
    """
    korean = (
        "# 사용자 이름을 정리한다 — 앞뒤 공백 제거\n"
        "def clean(name):\n"
        "    return name.strip()\n"
    )
    _git(tmp_path, "init")
    (tmp_path / "base.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")

    (tmp_path / "korean.py").write_text(korean, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "한글 주석 추가")

    changes = changed_code("HEAD~1", cwd=str(tmp_path))
    assert "korean.py" in changes
    assert "def clean(name):" in changes["korean.py"]


def test_scan_diff_exit_code_0_when_clean(tmp_path, monkeypatch):
    """추가 코드가 무관하면 exit 0 (빈 인덱스)."""
    _git(tmp_path, "init")
    (tmp_path / "base.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")

    (tmp_path / "clean.py").write_text(CLEAN, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "add clean")

    monkeypatch.chdir(tmp_path)
    assert main(["scan", "--diff", "HEAD~1"]) == 0
