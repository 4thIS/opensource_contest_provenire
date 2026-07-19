"""정확도·속도 평가 (WP-E · E-3) — Precision / Recall / F1.

    python benchmarks/evaluate.py            측정만 한다
    python benchmarks/evaluate.py --check    기준 미달이면 exit 1 (CI 회귀 방지)

무엇을 재는가:
    Recall     실제 카피레프트 코드를 변형한 '표절 코드'를 잡아내는가
    Precision  우리가 직접 쓴 코드를 표절이라 잘못 판정하지 않는가
    속도       인덱스 로드 · 코드 조각당 스캔 시간

데이터 출처 (§4 저작권 안전):
    인덱스     `data/copyleft.db` — 저장소에 포함. **지문 해시와 메타뿐**이라 원본 복원 불가.
    정탐 원본  런타임에 내려받는다. GPL 코드는 저장소에 넣지 않는다.
    오탐 세트  아래 `OURS` — 우리가 직접 쓴 코드라 커밋해도 안전하다.

왜 이 평가가 공정한가:
    "AI가 카피레프트 코드를 학습해 변형 재현한다"는 실제 시나리오를 그대로 흉내낸다.
    원본이 인덱스에 있고, 그 변형본을 검사한다 — 실전과 같은 조건이다.

여기서 raw(Copilot 필터 수준)와 비교하지 않는 이유:
    인덱스는 **tokens 정규화로 뜬 지문**이라, raw 스캐너로 조회하면 정규화 방식이 달라
    항상 0%가 나온다 — 공정한 비교가 아니다(거짓 우위가 된다).
    raw 대비 우위는 **같은 두 코드를 직접 비교**하는 `poc_winnowing.py` 가 측정한다.

한계 (정직하게):
    변형은 **스크립트로 생성**한다. 실제 LLM 재생성(로직 순서·API까지 바뀜)은
    이 수치보다 훨씬 어렵다 — 그 측정은 `RESULTS.md` 의 E-1 절을 참조.
    즉 이 스크립트는 **"쉬운 변형을 놓치지 않는지" 지키는 회귀 테스트**이고,
    어려운 케이스의 실력은 E-1 이 보여준다.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Windows 콘솔 기본 인코딩(cp949)에서 한글·기호 출력이 깨지지 않게 고정한다.
# 이게 없으면 Windows 사용자는 UnicodeEncodeError 로 재현 자체가 불가능하다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from provenire import Scanner  # noqa: E402
from provenire.index import FileIndex, FingerprintStore  # noqa: E402
from provenire.index.corpus import SOURCES, chunk, fetch  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "data" / "copyleft.db"
BUILTINS = set(dir(builtins)) | {"self", "cls"}

# 정탐 세트를 만들 때 쓸 원본 소스 수 (다운로드 최소화)
N_SOURCES = 4
# 소스당 뽑을 함수 수
N_FUNCS = 6

# 합격 기준 (--check). 핵심 명제가 무너지면 CI를 실패시킨다.
MIN_RECALL_RENAMED = 0.90   # 이름 전부 변경을 90% 이상 잡아야 한다
MAX_FALSE_POSITIVES = 0     # 우리가 쓴 코드는 하나도 잡히면 안 된다


# ─────────────────────────── 오탐 세트 (우리가 직접 쓴 코드) ───────────────────────────
# 카피레프트 코퍼스와 무관한 자체 작성 코드. 하나라도 잡히면 오탐이다.
OURS: list[str] = [
    '''
def compute_statistics(dataset, weights=None):
    total, count = 0.0, 0
    for row in dataset:
        total += row.value * (weights.get(row.key, 1.0) if weights else 1.0)
        count += 1
    mean = total / count if count else 0.0
    variance = sum((r.value - mean) ** 2 for r in dataset) / count if count else 0.0
    return {"mean": mean, "variance": variance, "n": count}
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
class RetryPolicy:
    def __init__(self, attempts=3, backoff=0.5, jitter=0.1):
        self.attempts = attempts
        self.backoff = backoff
        self.jitter = jitter
        self.history = []

    def delay_for(self, attempt):
        base = self.backoff * (2 ** attempt)
        self.history.append(base)
        return base + self.jitter
''',
    '''
def parse_config_line(line, separator="="):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if separator not in stripped:
        raise ValueError(f"malformed line: {line!r}")
    key, _, value = stripped.partition(separator)
    return key.strip().lower(), value.strip()
''',
    '''
def build_summary(records, limit=5):
    buckets = {}
    for record in records:
        buckets.setdefault(record.category, []).append(record)
    summary = []
    for category, items in sorted(buckets.items()):
        items.sort(key=lambda r: r.score, reverse=True)
        summary.append({"category": category, "top": items[:limit], "count": len(items)})
    return summary
''',
    '''
def chunked(iterable, size):
    if size <= 0:
        raise ValueError("size must be positive")
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
''',
    '''
class LruBudget:
    def __init__(self, capacity):
        self.capacity = capacity
        self.spent = {}
        self.order = []

    def charge(self, key, amount):
        if key in self.spent:
            self.order.remove(key)
        self.spent[key] = self.spent.get(key, 0) + amount
        self.order.append(key)
        while len(self.order) > self.capacity:
            evicted = self.order.pop(0)
            self.spent.pop(evicted, None)
        return self.spent[key]
''',
    '''
def normalize_phone(number, country="KR"):
    digits = "".join(ch for ch in number if ch.isdigit())
    if country == "KR" and digits.startswith("82"):
        digits = "0" + digits[2:]
    if len(digits) < 9:
        raise ValueError("too short")
    head, mid, tail = digits[:-8], digits[-8:-4], digits[-4:]
    return f"{head}-{mid}-{tail}"
''',
    '''
def diff_counts(before, after):
    added = {k: after[k] for k in after if k not in before}
    removed = {k: before[k] for k in before if k not in after}
    changed = {}
    for key in before:
        if key in after and before[key] != after[key]:
            changed[key] = (before[key], after[key])
    return {"added": added, "removed": removed, "changed": changed}
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
    '''
class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.stamp = 0.0

    def allow(self, now, cost=1):
        self.tokens = min(self.capacity, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True
''',
    '''
def flatten_tree(node, depth=0, out=None):
    if out is None:
        out = []
    out.append((depth, node.label))
    for child in getattr(node, "children", []):
        flatten_tree(child, depth + 1, out)
    return out
''',
]


# ─────────────────────────── 변형 시나리오 (= AI가 흔히 하는 재현) ───────────────────────────


def rename_identifiers(code: str) -> str:
    """식별자만 전부 바꾼다 — AI가 가장 흔히 하는 변형."""
    names: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(n.name)
    names -= BUILTINS
    out = code
    for i, old in enumerate(sorted(n for n in names if len(n) > 2)):
        out = re.sub(rf"\b{re.escape(old)}\b", f"var_{i}", out)
    return out


def strip_comments(code: str) -> str:
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    code = re.sub(r"'''[\s\S]*?'''", "", code)
    return re.sub(r"#.*", "", code)


def reformat(code: str) -> str:
    return re.sub(r"\n\s*\n", "\n", code)


SCENARIOS: list[tuple[str, callable]] = [
    ("1) 그대로 복사", lambda c: c),
    ("2) 주석·독스트링 삭제", strip_comments),
    ("3) 이름 전부 변경", rename_identifiers),
    ("4) 이름변경+주석삭제+재포맷", lambda c: reformat(strip_comments(rename_identifiers(c)))),
]


def load_positives() -> list[tuple[str, str]]:
    """정탐 원본 — 인덱스에 들어있는 실제 카피레프트 함수들을 런타임에 가져온다."""
    out: list[tuple[str, str]] = []
    for src in SOURCES[:N_SOURCES]:
        try:
            code = fetch(src.url)
        except Exception as exc:  # noqa: BLE001 - 네트워크 실패는 건너뛴다
            print(f"  (건너뜀: {src.project}/{Path(src.file).name} — {type(exc).__name__})")
            continue
        for symbol, piece in chunk(code, src.lang)[:N_FUNCS]:
            out.append((f"{src.project}::{symbol}", piece))
    return out


def detected(index: FileIndex, scanner: Scanner, code: str) -> bool:
    """이 코드가 '표절 의심'으로 판정되는가."""
    fp = scanner.fingerprint_of(code)
    if not fp:
        return False
    return any(h.shared / len(fp) >= Scanner.THRESHOLD for h in index.search(fp))


def main() -> int:
    ap = argparse.ArgumentParser(description="Provenire 정확도·속도 평가")
    ap.add_argument("--check", action="store_true",
                    help="기준 미달이면 exit 1 (CI 회귀 방지)")
    args = ap.parse_args()

    if not DB.exists():
        print(f"인덱스가 없습니다: {DB}")
        print("먼저 빌드하세요:  python -m provenire.index.corpus")
        return 2

    t0 = time.perf_counter()
    store = FingerprintStore(str(DB))
    index = FileIndex(store)
    load_s = time.perf_counter() - t0
    projects = {m["project"] for m, _ in store.entries()}

    print("=" * 72)
    print("Provenire 정확도 평가 (WP-E · E-3)")
    print("=" * 72)
    print(f"  인덱스: {len(store)} 청크 / {len(projects)} 프로젝트   (로드 {load_s:.2f}s)")

    positives = load_positives()
    if not positives:
        print("\n정탐 원본을 가져오지 못했습니다 (네트워크 확인). 평가를 중단합니다.")
        return 2
    print(f"  정탐 원본: {len(positives)} 함수  ·  오탐 세트: {len(OURS)} 자체작성 코드\n")

    scanner = Scanner(lang="python")

    # ── 시나리오별 Recall ──
    print("[ 정탐 — 변형 시나리오별 Recall ]")
    print(f"  {'시나리오':<30}{'Recall':>10}{'놓침':>8}")
    print("  " + "-" * 48)
    recalls: dict[str, float] = {}
    scan_times: list[float] = []
    for label, transform in SCENARIOS:
        hits = 0
        for _, piece in positives:
            variant = transform(piece)
            t = time.perf_counter()
            ok = detected(index, scanner, variant)
            scan_times.append(time.perf_counter() - t)
            hits += ok
        recalls[label] = hits / len(positives)
        print(f"  {label:<30}{recalls[label]:>9.1%}{len(positives) - hits:>8}")
    print()

    # ── 오탐 ──
    print("[ 오탐 — 우리가 직접 쓴 코드 ]")
    false_positives = sum(detected(index, scanner, code) for code in OURS)
    print(f"  {false_positives}/{len(OURS)} 오탐")
    print()

    # ── 종합 지표 (전체 시나리오 합산) ──
    total_positive = len(positives) * len(SCENARIOS)
    tp = round(sum(recalls[label] for label, _ in SCENARIOS) * len(positives))
    fn = total_positive - tp
    precision = tp / (tp + false_positives) if (tp + false_positives) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print("[ 종합 — Precision / Recall / F1 ]")
    print(f"  {'Precision':>11}{'Recall':>10}{'F1':>10}")
    print("  " + "-" * 31)
    print(f"  {precision:>10.1%}{recall:>10.1%}{f1:>10.1%}")
    print(f"  (TP {tp} · FN {fn} · FP {false_positives})")
    print()

    # ── 속도 ──
    avg_ms = sum(scan_times) / len(scan_times) * 1000
    print("[ 속도 ]")
    print(f"  인덱스 로드 {load_s:.2f}s  ·  코드 조각당 스캔 {avg_ms:.1f}ms  "
          f"({len(scan_times)}회 평균)")
    print()

    # ── 합격 판정 ──
    renamed_recall = recalls["3) 이름 전부 변경"]
    ok = renamed_recall >= MIN_RECALL_RENAMED and false_positives <= MAX_FALSE_POSITIVES
    print("=" * 72)
    print(f"  이름 변경 Recall {renamed_recall:.1%} (기준 {MIN_RECALL_RENAMED:.0%} 이상)"
          f"  ·  오탐 {false_positives}건 (기준 {MAX_FALSE_POSITIVES}건 이하)")
    print(f"  → {'통과' if ok else '미달'}")
    print("=" * 72)

    if args.check and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
