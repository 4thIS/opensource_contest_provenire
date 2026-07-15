"""Provenire CLI.

오늘 동작하는 것:
    provenire compare <의심코드> <원본>     두 파일의 유사도
    provenire fingerprint <파일>            지문 미리보기
    provenire scan <경로>                   코드를 카피레프트 인덱스와 대조 (PR 게이트)

scan 은 PR 게이트의 심장이다 — 나중에 GitHub Action(T-05)이 이 명령을 PR 에서 돌린다.
실제 카피레프트 인덱스(copyleft.db)는 팀장이 코퍼스를 수집해 채운다. 없으면 빈 인덱스로 동작한다.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from . import languages
from .core.fingerprint import K_DEFAULT, W_DEFAULT
from .core.matcher import Scanner
from .core.normalizer import normalize_tokens
from .index import FileIndex, FingerprintStore, Hit, Index, MockIndex

RED, YEL, GRN, DIM, RST = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[0m"


def _read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")


def cmd_compare(args) -> int:
    sus, org = _read(args.suspect), _read(args.origin)
    rows = []
    for mode in ("raw", "tokens"):
        m = Scanner(mode=mode, k=args.k, w=args.w).compare(sus, org, filename=args.suspect)
        rows.append((mode, m))

    print(f"\n  의심: {args.suspect}\n  원본: {args.origin}\n")
    print(f"  {'모드':<10}{'유사도':>10}   지문")
    print("  " + "-" * 42)
    for mode, m in rows:
        label = "raw (baseline)" if mode == "raw" else "tokens (기본)"
        col = RED if m.is_suspicious else DIM
        print(f"  {label:<16}{col}{m.similarity*100:7.1f}%{RST}   {m.shared}/{m.total}")
    print("  " + "-" * 42)

    final = rows[1][1]
    if final.is_suspicious:
        print(f"\n  {RED}[!] 표절 의심{RST} — 유사도 {final.similarity*100:.1f}%"
              f" (임계값 {Scanner.THRESHOLD*100:.0f}%)\n")
        return 1
    print(f"\n  {GRN}[OK]{RST} 유의미한 유사도 없음\n")
    return 0


def cmd_fingerprint(args) -> int:
    code = _read(args.file)
    norm = normalize_tokens(code, filename=args.file)
    fp = Scanner(k=args.k, w=args.w)._fp(code, filename=args.file)
    print(f"\n  파일:        {args.file}")
    print(f"  정규화 길이: {len(norm)} chars")
    print(f"  지문 개수:   {len(fp)}")
    print(f"\n  {DIM}정규화 미리보기:{RST}\n  {norm[:160]}{'...' if len(norm) > 160 else ''}\n")
    return 0


# ─────────────────────────── scan (PR 게이트 코어) ───────────────────────────


@dataclass(frozen=True)
class Finding:
    """스캔 결과 한 건 — '이 파일이 어떤 카피레프트 원본과 겹치나'."""

    file: str          # 검사한 내 파일
    hit: Hit           # 겹친 원본 (project·file·license·url ...)
    similarity: float  # 내 코드 지문 중 원본과 겹치는 비율 (0.0 ~ 1.0)


def _iter_source_files(paths: list[str]):
    """경로들을 순회하며 검사할 소스 파일 경로를 하나씩 내놓는다.

    - 파일이면 확장자와 무관하게 그대로 (사용자가 명시했으므로)
    - 디렉터리면 **지원 언어 확장자**만 재귀적으로 (languages.extensions())
    """
    exts = languages.extensions()
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts:
                    yield str(f)
        elif path.is_file():
            yield str(path)


def scan_paths(
    paths: list[str],
    index: Index,
    threshold: float = Scanner.THRESHOLD,
    k: int = K_DEFAULT,
    w: int = W_DEFAULT,
) -> list[Finding]:
    """파일/디렉터리를 인덱스와 대조해 표절 의심(Finding)을 모은다.

    핵심 설계: **인덱스를 인자로 받는 순수 함수** — MockIndex 를 주입해 테스트한다.
    """
    findings: list[Finding] = []
    scanner = Scanner(k=k, w=w)
    for path in _iter_source_files(paths):
        code = _read(path)
        fp = scanner.fingerprint_of(code, filename=path)
        if not fp:
            continue
        for h in index.search(fp):
            sim = h.shared / len(fp)
            if sim >= threshold:
                findings.append(Finding(file=path, hit=h, similarity=sim))
    return findings


def _load_index(args) -> Index:
    """스캔에 쓸 인덱스를 준비한다.

    --index <db> 가 주어지고 파일이 있으면 실제 sqlite 지문 DB(FileIndex)를,
    없으면 빈 MockIndex 를 돌려준다. (실제 카피레프트 DB 는 팀장이 코퍼스로 채운다)
    """
    db = getattr(args, "index", None)
    if db and Path(db).exists():
        return FileIndex(FingerprintStore(db))
    return MockIndex()


def _print_report(findings: list[Finding], paths: list[str]) -> None:
    if not findings:
        print(f"\n  {GRN}[OK]{RST} 카피레프트 유사 코드를 찾지 못했습니다.\n")
        return
    print(f"\n  {RED}[!] 표절 의심 {len(findings)}건{RST}"
          f" (임계값 {Scanner.THRESHOLD*100:.0f}%)\n")
    for f in findings:
        h = f.hit
        sym = f" :: {h.symbol}" if h.symbol else ""
        print(f"  {RED}{f.similarity*100:5.1f}%{RST}  {f.file}")
        print(f"         ↳ {h.project}/{h.file}{sym}  [{YEL}{h.license}{RST}]")
        print(f"           {DIM}{h.url}{RST}")
    print()


def cmd_scan(args) -> int:
    index = _load_index(args)
    findings = scan_paths(
        args.paths, index, threshold=args.threshold, k=args.k, w=args.w
    )
    _print_report(findings, args.paths)
    return 1 if findings else 0   # ← PR 게이트가 이 코드로 실패 판정


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="provenire",
        description="AI가 생성한 코드가 오픈소스를 베꼈는지 탐지합니다.",
    )
    p.add_argument("-k", type=int, default=25, help="k-gram 길이 (기본 25)")
    p.add_argument("-w", type=int, default=12, help="winnowing 윈도우 (기본 12)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="두 파일의 유사도를 잰다")
    c.add_argument("suspect")
    c.add_argument("origin")
    c.set_defaults(func=cmd_compare)

    f = sub.add_parser("fingerprint", help="파일의 지문을 미리본다")
    f.add_argument("file")
    f.set_defaults(func=cmd_fingerprint)

    s = sub.add_parser("scan", help="코드를 카피레프트 인덱스와 대조한다 (PR 게이트)")
    s.add_argument("paths", nargs="+", help="검사할 파일 또는 디렉터리")
    s.add_argument("--index", help="지문 DB(sqlite) 경로. 없으면 빈 인덱스로 동작")
    s.add_argument("--against", default="copyleft",
                   help="대조 대상 (현재는 copyleft 자리표시)")
    s.add_argument("--threshold", type=float, default=Scanner.THRESHOLD,
                   help=f"표절 의심 임계값 (기본 {Scanner.THRESHOLD})")
    s.set_defaults(func=cmd_scan)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
