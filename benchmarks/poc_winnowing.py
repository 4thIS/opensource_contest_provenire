"""검증 실험 — Provenire의 존재 이유를 증명한다.

명제:
    "AI가 GPL 코드를 변수명만 바꿔 재현했을 때, 우리는 잡아내는가?"

비교:
    raw    — 문자 그대로 비교 (GitHub Copilot의 public code filter 수준)
    tokens — 식별자 익명화 후 비교 (Provenire)

실행:
    python benchmarks/poc_winnowing.py

주의:
    실제 GPL-3.0 코드를 런타임에 내려받아 검증한다.
    저장소에는 GPL 코드를 포함하지 않는다. (NOTICE 참조)
"""
from __future__ import annotations

import ast
import builtins
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from provenire import Scanner  # noqa: E402

# 실제 GPL-3.0 프로젝트 — qutebrowser (SPDX: GPL-3.0-or-later)
GPL_URL = (
    "https://raw.githubusercontent.com/qutebrowser/qutebrowser/main/"
    "qutebrowser/utils/utils.py"
)
CACHE = Path(__file__).parent / "_cache" / "qutebrowser_utils.py"
THRESHOLD = Scanner.THRESHOLD
BUILTINS = set(dir(builtins)) | {"self", "cls"}


def fetch_gpl_source() -> str:
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    print(f"내려받는 중: {GPL_URL}")
    src = urllib.request.urlopen(GPL_URL, timeout=20).read().decode("utf-8")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(src, encoding="utf-8")
    return src


def pick_function(src: str, prefer: str = "elide_filename") -> tuple[str, str]:
    """파일에서 실험용 함수 하나를 뽑는다."""
    lines = src.split("\n")
    funcs: dict[str, str] = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.end_lineno - node.lineno > 8:
            funcs[node.name] = "\n".join(lines[node.lineno - 1 : node.end_lineno])
    name = prefer if prefer in funcs else next(iter(funcs))
    return name, funcs[name]


def rename_identifiers(code: str) -> str:
    """AI가 가장 흔히 하는 변형: 변수·함수명만 바꿔서 뱉기.

    빌트인(str, len, int...)은 건드리지 않는다 — 실제 AI도 그렇다.
    """
    names: set[str] = set()
    for n in ast.walk(ast.parse(code)):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.FunctionDef):
            names.add(n.name)
    names -= BUILTINS
    out = code
    for i, old in enumerate(sorted(n for n in names if len(n) > 2)):
        out = re.sub(rf"\b{re.escape(old)}\b", f"var_{i}", out)
    return out


def strip_comments(code: str) -> str:
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    return re.sub(r"#.*", "", code)


UNRELATED = '''
def compute_statistics(dataset, weights=None):
    total, count = 0.0, 0
    for row in dataset:
        total += row.value * (weights.get(row.key, 1.0) if weights else 1.0)
        count += 1
    mean = total / count if count else 0.0
    variance = sum((r.value - mean) ** 2 for r in dataset) / count if count else 0.0
    return {"mean": mean, "variance": variance, "n": count}
'''


def main() -> int:
    src = fetch_gpl_source()
    name, origin = pick_function(src)

    print("=" * 76)
    print(f"원본(GPL-3.0): qutebrowser/utils/utils.py :: {name}()   [{len(origin)} chars]")
    print("=" * 76)

    variants = {
        "1) 그대로 복사": origin,
        "2) 주석·독스트링 삭제": strip_comments(origin),
        "3) 변수·함수명 전부 변경": rename_identifiers(origin),
        "4) 이름변경+주석삭제+재포맷": re.sub(
            r"\n\s*\n", "\n", strip_comments(rename_identifiers(origin))
        ),
        "5) 무관한 코드 (음성대조)": UNRELATED,
    }

    raw_s, tok_s = Scanner(mode="raw"), Scanner(mode="tokens")

    print(f"\n  {'변형 시나리오':<26}{'raw':>8}{'tokens':>10}   판정")
    print("  " + "-" * 66)
    failures = 0
    for label, code in variants.items():
        a = raw_s.compare(code, origin).similarity
        b = tok_s.compare(code, origin).similarity
        negative = "음성" in label

        if negative:
            ok = b < THRESHOLD
            verdict = "OK (오탐 없음)" if ok else "!! 오탐 발생"
        else:
            ok = b >= THRESHOLD
            if ok and a < THRESHOLD:
                verdict = "*** tokens만 탐지 (핵심 차별점)"
            elif ok:
                verdict = "둘 다 탐지"
            else:
                verdict = "!! 놓침"
        failures += 0 if ok else 1
        print(f"  {label:<26}{a*100:7.1f}%{b*100:9.1f}%   {verdict}")

    print("  " + "-" * 66)
    print(f"  임계값 {THRESHOLD*100:.0f}% 이상 = 표절 의심\n")

    print("[ k-gram 길이(k)별 민감도 — 시나리오 3 '변수명 전부 변경' ]")
    print("  " + "-" * 56)
    print(f"  {'k':>4}{'raw':>10}{'tokens':>10}{'음성대조 오탐':>16}")
    print("  " + "-" * 56)
    renamed = variants["3) 변수·함수명 전부 변경"]
    for k in (10, 15, 20, 25, 30):
        a = Scanner(mode="raw", k=k).compare(renamed, origin).similarity
        b = Scanner(mode="tokens", k=k).compare(renamed, origin).similarity
        fp = Scanner(mode="tokens", k=k).compare(UNRELATED, origin).similarity
        print(f"  {k:>4}{a*100:9.1f}%{b*100:9.1f}%{fp*100:14.1f}%")
    print("  " + "-" * 56)

    if failures:
        print(f"\n!! 검증 실패: {failures}건\n")
        return 1
    print("\n검증 통과 — 이름을 바꿔도 잡아내고, 무관한 코드는 잡지 않는다.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
