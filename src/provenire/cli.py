"""Provenire CLI.

오늘 동작하는 것:
    provenire compare <의심코드> <원본>     두 파일의 유사도
    provenire fingerprint <파일>            지문 미리보기

로드맵 (MVP):
    provenire scan <경로> --against copyleft   카피레프트 인덱스와 대조
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.matcher import Scanner
from .core.normalizer import normalize_tokens

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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
