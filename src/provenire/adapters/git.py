"""git diff 어댑터 — PR에서 **추가된 코드만** 골라 스캐너에 넘긴다.

왜 추가된 줄만인가 (T-04):
    - **빠르다**: 저장소 전체가 아니라 PR diff 만 본다. GitHub Action(T-05)이 매 PR 마다 돌린다.
    - **정확히 겨냥**: 이번 PR 에서 AI 가 뱉은 코드가 표적이다. 기존 코드를 다시 훑지 않는다.

파이프라인:
    ref  ──run_git_diff──▶  unified diff 텍스트  ──parse_added_code──▶  {파일: 추가된 코드}

핵심 설계: **파싱(parse_added_code)은 순수 함수**라 git 실행 없이 테스트된다.
"""
from __future__ import annotations

import re
import subprocess

__all__ = ["parse_added", "parse_added_code", "run_git_diff", "changed_added", "changed_code"]

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def parse_added(diff_text: str) -> dict[str, list[tuple[int, str]]]:
    """unified diff → {파일경로: [(새 파일 기준 줄번호, 추가된 코드), …]}. (순수 함수)

    줄번호를 같이 들고 나오는 이유: `scan --diff` 는 추가된 줄만 이어붙여 검사하므로,
    그 이어붙인 덩어리의 3번째 줄이 **원본 파일의 몇 번째 줄인지** 알 방법이 없다.
    리포트에 엉뚱한 줄번호를 찍는 것은 아예 안 찍는 것보다 나쁘다 → hunk 헤더
    (`@@ -a,b +c,d @@`)에서 새 파일 시작 줄을 읽고, 컨텍스트/추가 줄마다 증가시킨다.

    - `diff --git a/… b/…` 로 파일이 바뀐다 (b/ 쪽 경로를 쓴다 = 새 파일명).
    - `+` 로 시작하되 `+++` 가 아닌 줄이 '추가된 코드'다.
    - 삭제 줄(-)은 새 파일에 없으므로 줄번호를 올리지 않는다.
    - `\\ No newline at end of file` 은 줄이 아니므로 세지 않는다.
    - 추가 줄이 하나도 없는 파일(순수 삭제 등)은 결과에서 뺀다.
    """
    files: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    lineno = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/")[-1]
            files[current] = []
        elif (m := _HUNK.match(line)) is not None:
            lineno = int(m.group(1))
        elif current is None or line.startswith(("+++", "---", "\\")):
            continue
        elif line.startswith("+"):
            files[current].append((lineno, line[1:]))
            lineno += 1
        elif not line.startswith("-"):
            lineno += 1   # 컨텍스트 줄 — 새 파일에도 있으므로 센다
    return {f: rows for f, rows in files.items() if rows}


def parse_added_code(diff_text: str) -> dict[str, str]:
    """unified diff → {파일경로: 추가된 코드}. parse_added 에서 줄번호만 뗀 것."""
    return {f: "\n".join(c for _, c in rows) for f, rows in parse_added(diff_text).items()}


def run_git_diff(ref: str, cwd: str = ".") -> str:
    """`git diff --unified=3 <ref> --` 를 실행해 unified diff 텍스트를 돌려준다.

    인코딩을 **UTF-8 로 고정**한다. `text=True` 만 주면 파이썬이 시스템 기본
    인코딩으로 디코딩하는데, Windows 한국어 환경은 cp949 라 UTF-8 바이트(한글
    주석·em dash 등)를 만나면 UnicodeDecodeError 로 죽는다. git diff 출력은
    UTF-8 이므로 명시적으로 맞춰준다. `errors="replace"` 로 깨진 바이트가 있어도
    크래시 대신 대체 문자로 넘어간다. (이슈 #22)
    """
    out = subprocess.run(
        ["git", "diff", "--unified=3", ref, "--"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd, check=True,
    )
    return out.stdout


def changed_added(ref: str, cwd: str = ".") -> dict[str, list[tuple[int, str]]]:
    """git diff 를 파싱해 (파일 → [(줄번호, 추가된 코드), …]) 를 돌려준다."""
    return parse_added(run_git_diff(ref, cwd))


def changed_code(ref: str, cwd: str = ".") -> dict[str, str]:
    """git diff 를 파싱해 (파일 → 추가된 코드) 를 돌려준다."""
    return parse_added_code(run_git_diff(ref, cwd))
