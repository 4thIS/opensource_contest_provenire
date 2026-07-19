"""git diff 어댑터 — PR에서 **추가된 코드만** 골라 스캐너에 넘긴다.

왜 추가된 줄만인가 (T-04):
    - **빠르다**: 저장소 전체가 아니라 PR diff 만 본다. GitHub Action(T-05)이 매 PR 마다 돌린다.
    - **정확히 겨냥**: 이번 PR 에서 AI 가 뱉은 코드가 표적이다. 기존 코드를 다시 훑지 않는다.

파이프라인:
    ref  ──run_git_diff──▶  unified diff 텍스트  ──parse_added_code──▶  {파일: 추가된 코드}

핵심 설계: **파싱(parse_added_code)은 순수 함수**라 git 실행 없이 테스트된다.
"""
from __future__ import annotations

import subprocess

__all__ = ["parse_added_code", "run_git_diff", "changed_code"]


def parse_added_code(diff_text: str) -> dict[str, str]:
    """unified diff → {파일경로: 추가된 코드}. (순수 함수 = 테스트 쉬움)

    - `diff --git a/… b/…` 로 파일이 바뀐다 (b/ 쪽 경로를 쓴다 = 새 파일명).
    - `+` 로 시작하되 `+++` 가 아닌 줄이 '추가된 코드'다.
    - 컨텍스트 줄( ), 삭제 줄(-), 헤더(---/+++/@@)는 무시한다.
    - 추가 줄이 하나도 없는 파일(순수 삭제 등)은 결과에서 뺀다.
    """
    files: dict[str, list[str]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/")[-1]
            files[current] = []
        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            files[current].append(line[1:])
    return {f: "\n".join(lines) for f, lines in files.items() if lines}


def run_git_diff(ref: str, cwd: str = ".") -> str:
    """`git diff --unified=3 <ref> --` 를 실행해 unified diff 텍스트를 돌려준다."""
    out = subprocess.run(
        ["git", "diff", "--unified=3", ref, "--"],
        capture_output=True, text=True, cwd=cwd, check=True,
    )
    return out.stdout


def changed_code(ref: str, cwd: str = ".") -> dict[str, str]:
    """git diff 를 파싱해 (파일 → 추가된 코드) 를 돌려준다."""
    return parse_added_code(run_git_diff(ref, cwd))
