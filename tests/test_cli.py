"""`provenire scan` — PR 게이트 코어 테스트.

핵심 설계: 로직(`scan_paths`)이 **인덱스를 인자로 받는 순수 함수**라서
MockIndex 를 주입해 실제 코퍼스 없이 탐지/오탐/exit code 를 검증한다.
"""
import argparse
from pathlib import Path

from provenire import Scanner
from provenire.cli import (
    Finding,
    _load_index,
    _print_report,
    main,
    scan_changes,
    scan_code,
    scan_paths,
)
from provenire.index import FileIndex, FingerprintStore, Hit, MockIndex

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

# §2 회귀용 — 자체 작성 함수 3개 (GPL 아님). "파일 통째 복사" 상황을 만든다.
WHOLE_FUNCS = [
    '''
def elide_filename(filename, length):
    marker = "..."
    if length < len(marker):
        raise ValueError("too short")
    if len(filename) <= length:
        return filename
    cut = len(filename) - length + len(marker)
    left = (len(filename) - cut) // 2
    return filename[:left] + marker
''',
    '''
def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda pair: pair[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged
''',
    '''
def rolling_average(samples, window):
    if window <= 0:
        raise ValueError("window must be positive")
    out, running = [], 0.0
    for i, value in enumerate(samples):
        running += value
        if i >= window:
            running -= samples[i - window]
        out.append(running / min(i + 1, window))
    return out
''',
]


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


def test_scan_detects_whole_file_copy(tmp_path):
    """★ 큰 파일에 섞인 표절 함수를 잡는다 (§2 미탐 회귀 방지).

    파일을 통째로 지문 뜨면 표절 함수의 지문이 전체 대비 소수라 containment 가
    임계값을 못 넘겨 놓치던 버그. 인덱스엔 함수 하나만 있고, 의심 파일은 그 함수 +
    무관한 대량 코드다. 청킹하면 그 함수 청크가 100% 로 잡힌다.
    """
    idx = MockIndex()
    idx.add(WHOLE_FUNCS[0], project="acme", file="lib.py", symbol="elide",
            license="GPL-3.0-or-later", url="https://example.com/lib.py")

    # 무관한 자체 코드로 파일을 크게 만든다 → 파일 단위면 분모가 폭발한다.
    # ⚠️ 이름만 다르고 구조가 같으면 정규화 후 지문이 같아져 파일이 안 커진다.
    #    연산자 조합을 함수마다 다르게 해서 지문이 다양해지게 한다.
    ops = ["+", "-", "*", "//", "%"]
    padding = "\n\n".join(
        f"def calc_{i}(x, y, z):\n    acc = x\n"
        + "\n".join(
            f"    acc = acc {ops[(i * 2 + j) % len(ops)]} (y {ops[(i + j) % len(ops)]} z)"
            for j in range(5)
        )
        + "\n    return acc"
        for i in range(25)
    )
    whole = WHOLE_FUNCS[0] + "\n\n" + padding
    f = tmp_path / "copied.py"
    f.write_text(whole, encoding="utf-8")

    findings = scan_paths([str(f)], index=idx)
    assert findings, "큰 파일에 섞인 표절 함수를 놓쳤다 (§2 회귀)"
    assert findings[0].hit.symbol == "elide"

    # 파일 통째로 한 번에 지문 떴다면(수정 전) 놓쳤을 것임을 대조로 보인다
    single_fp = Scanner()._fp(whole)
    naive_best = max((h.shared / len(single_fp) for h in idx.search(single_fp)), default=0.0)
    assert naive_best < Scanner.THRESHOLD, "이 회귀 테스트의 전제(파일단위 미탐)가 깨졌다"


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


def _store_with(code: str) -> FingerprintStore:
    """원본 지문 하나를 심은 인메모리 store (:memory: 기본값)."""
    store = FingerprintStore()
    store.add(
        Scanner()._fp(code),
        project="acme", file="util.py", symbol="elide_filename",
        license="GPL-3.0-or-later", url="https://example.com/util.py",
    )
    return store


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


def test_report_has_no_ansi_when_piped(capsys):
    """리포트에 ANSI 색상 코드가 없다 (파이프/캡처 환경).

    GitHub Action 이 리포트를 PR 코멘트에 넣으면 ANSI 코드가 깨진 글자로 보인다
    (`\\x1b[31m` → `?[31m`). 터미널이 아닐 때는 색상을 끈다. pytest 는 stdout 을
    캡처(비-tty)하므로 여기서 색상이 새어 나오면 안 된다.
    """
    hit = Hit("acme", "util.py", "elide", "GPL-3.0-or-later", "https://x", 5, 5)
    _print_report([Finding("mine.py", hit, 1.0)], ["mine.py"])
    out = capsys.readouterr().out
    assert "\x1b" not in out, "비-tty 출력에 ANSI 색상 코드가 남았다"
    assert "표절 의심" in out          # 내용은 정상 출력


def test_report_shows_line_range_and_local_symbol(capsys):
    """리포트가 '내 파일 몇 번째 줄'과 '내 쪽 함수명'까지 찍는다.

    파일명만 알려주면 큰 파일에서 어디를 봐야 할지 알 수 없다. `파일:시작-끝` 형식은
    대부분의 터미널·에디터가 눌러서 이동할 수 있다.
    """
    hit = Hit("acme", "util.py", "elide", "GPL-3.0-or-later", "https://x", 5, 5)
    _print_report([Finding("mine.py", hit, 0.9, start=41, end=58, symbol="v0")], ["mine.py"])
    out = capsys.readouterr().out
    assert "mine.py:41-58" in out
    assert "(v0)" in out              # 내 코드 쪽 함수명


def test_report_omits_line_range_when_unknown(capsys):
    """줄 위치를 모르면(start=0) 파일명만 찍는다 — 틀린 줄번호를 찍지 않는다."""
    hit = Hit("acme", "util.py", "elide", "GPL-3.0-or-later", "https://x", 5, 5)
    _print_report([Finding("mine.py", hit, 0.9)], ["mine.py"])
    out = capsys.readouterr().out
    assert "mine.py" in out
    assert ":0-" not in out and "mine.py:" not in out


def test_scan_code_reports_where_the_match_is():
    """스캔 결과가 '내 파일의 몇 번째 줄'을 담는다 — 정상 함수 뒤에 숨은 조각도 짚는다."""
    code = "def helper(a, b):\n" + "".join(f"    x{i} = a + b + {i}\n" for i in range(8))
    code += "    return x0\n\n\n" + GPL_LIKE.strip() + "\n"
    store = _store_with(GPL_LIKE)
    findings = scan_code(code, "mine.py", FileIndex(store), Scanner())
    assert findings, "GPL 함수를 찾지 못했다"
    f = findings[0]
    assert f.symbol == "elide_filename"
    # 보고된 줄 범위 안에 실제로 그 함수가 있어야 한다
    seg = code.splitlines()[f.start - 1 : f.end]
    assert seg[0].startswith("def elide_filename")


def test_scan_changes_maps_line_numbers_to_real_file():
    """`--diff` 는 추가된 줄만 이어붙여 검사하지만, 줄번호는 **원본 파일 기준**으로 찍는다."""
    added = GPL_LIKE.strip().splitlines()
    line_maps = {"mine.py": list(range(101, 101 + len(added)))}   # 실제로는 101줄부터
    store = _store_with(GPL_LIKE)
    findings = scan_changes(
        {"mine.py": "\n".join(added)}, FileIndex(store), line_maps=line_maps,
    )
    assert findings, "GPL 함수를 찾지 못했다"
    assert findings[0].start == 101      # 덩어리 기준 1 이 아니라 파일 기준 101


def test_scan_changes_omits_line_numbers_without_map():
    """줄번호 맵이 없으면 위치를 비운다 — 덩어리 기준 줄번호를 파일 줄번호인 척하지 않는다."""
    store = _store_with(GPL_LIKE)
    findings = scan_changes({"mine.py": GPL_LIKE}, FileIndex(store))
    assert findings
    assert findings[0].start == 0
    assert findings[0].location == "mine.py"
