# T-03 · `provenire scan` CLI (+ 인덱스 연결)

**담당**: 김민수 (`minsoo`) · **난이도**: 중 · **예상**: 3일 · **WP**: B (스캐너 & PR 게이트)

---

## 한 줄

> **파일/디렉토리를 카피레프트 인덱스와 대조해, 표절 의심을 찾아내는 `provenire scan` 을 만든다.**

---

## 왜 필요한가

지금까지(T-01·T-02)는 **언어팩** — "두 코드를 비교"하는 재료였다.
T-03부터는 **제품의 얼굴**이다. 개발자가 실제로 쓰는 명령은 이것이다:

```bash
provenire scan ./src            # 내 코드가 카피레프트를 베꼈나?
```

`compare` 는 "두 파일"을 비교했다. `scan` 은 **"내 코드 전체 vs 인덱스(수천 개 원본)"** 를 대조한다.
이게 **PR 게이트의 심장**이다 — 나중에 T-05(GitHub Action)가 이 `scan` 을 PR에서 돌린다.

> ⭐ **팀장이 인덱스를 이미 준비해뒀다.** `provenire.index` 의 `MockIndex` / `FileIndex` 를
> **가져다 쓰기만** 하면 된다. 인덱스 내부는 건드리지 않는다(팀장 영역).

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** |
| `src/provenire/cli.py` | **네가 확장할 곳** — 이미 `compare`·`fingerprint` 가 있다. `scan` 을 같은 패턴으로 추가 |
| `src/provenire/index/__init__.py` | **읽기만** — `MockIndex`·`FileIndex`·`Hit` 의 사용법 (수정 금지, 팀장 영역) |
| `src/provenire/core/matcher.py` | **읽기만** — `Scanner`·`containment`·`THRESHOLD` (재사용한다) |

---

## 핵심 계약 — 인덱스는 이렇게 쓴다 (외워둘 것)

```python
from provenire import Scanner
from provenire.index import MockIndex, Hit   # 팀장이 제공. import 만 한다.

# 1) 인덱스 준비 (테스트에서는 mock 에 직접 심는다)
idx = MockIndex()
idx.add(some_gpl_like_code, project="acme", file="util.py",
        symbol="elide", license="GPL-3.0-or-later", url="https://...")

# 2) 의심 코드의 지문을 뜬다
suspect_fp = Scanner(lang="python")._fp(my_code)     # set[int]

# 3) 인덱스에 물어본다
hits: list[Hit] = idx.search(suspect_fp)             # 겹치는 후보들

# 4) 각 Hit 으로 "얼마나 겹치나" 판정
for h in hits:
    similarity = h.shared / len(suspect_fp)          # 의심 코드의 몇 %가 원본과 겹치나
    if similarity >= Scanner.THRESHOLD:              # 0.30 재사용
        print(f"⚠️ {h.project}/{h.file} [{h.license}] {similarity:.0%}  {h.url}")
```

> 이 4단계가 `scan` 의 전부다. 나머지는 "여러 파일을 순회"하고 "예쁘게 출력"하는 것뿐.

---

## 완료 조건 (DoD)

- [ ] `provenire scan <경로>` 가 동작한다 (파일 하나 **또는** 디렉토리)
  - [ ] 디렉토리면 **지원 언어 파일**(`.py .java .js .ts` 등)을 재귀적으로 순회
- [ ] 각 파일을 인덱스와 대조해, **임계값(30%) 이상**이면 표절 의심으로 리포트
- [ ] 리포트에 **원본 project · file · license · url · 유사도** 가 나온다
- [ ] **의심이 하나라도 있으면 exit code 1**, 없으면 0 (← PR 게이트가 이걸로 실패 판정)
- [ ] `tests/test_cli.py` 에 테스트가 있고 통과한다
  - [ ] `MockIndex` 에 심은 코드를 베낀 파일 → **탐지 + exit 1**
  - [ ] 무관한 파일만 있을 때 → **통과 + exit 0**
- [ ] `pytest` 전체 통과 · `ruff check .` 통과 · `python benchmarks/poc_winnowing.py` 통과

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/scan-cli
```

### 2) 먼저 테스트를 쓴다 (TDD)

`tests/test_cli.py` 를 만든다. **핵심은 "인덱스를 주입 가능하게" 짜는 것** — 그래야 MockIndex로 테스트한다.

```python
from provenire.index import MockIndex
from provenire.cli import scan_paths     # ← 네가 만들 함수 (인덱스를 인자로 받는다)

GPL_LIKE = '''
def elide_filename(filename, length):
    marker = "..."
    if length < len(marker):
        raise ValueError("too short")
    ...
'''
COPIED_RENAMED = '''   # 위를 변수명만 바꿔 베낀 코드
def truncate_path(path_str, max_len):
    dots = "..."
    ...
'''

def _index():
    idx = MockIndex()
    idx.add(GPL_LIKE, project="acme", file="util.py", symbol="elide",
            license="GPL-3.0-or-later", url="https://example.com/util.py")
    return idx

def test_scan_detects_copied_file(tmp_path):
    f = tmp_path / "mycode.py"
    f.write_text(COPIED_RENAMED, encoding="utf-8")
    findings = scan_paths([str(f)], index=_index())
    assert len(findings) == 1
    assert findings[0].hit.license == "GPL-3.0-or-later"

def test_scan_passes_clean_file(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    assert scan_paths([str(f)], index=_index()) == []
```

**이 테스트가 실패하는 것을 먼저 확인**하고 통과시킨다.

### 3) `scan` 을 구현한다

`src/provenire/cli.py` 에 추가한다. **핵심 로직(`scan_paths`)과 CLI(`cmd_scan`)를 분리**하라 — 로직을 순수 함수로 빼야 테스트에서 인덱스를 주입할 수 있다.

```python
# 권장 시그니처 (인덱스를 인자로 받는다 = 테스트 가능)
def scan_paths(paths, index, threshold=Scanner.THRESHOLD):
    findings = []
    for path in _iter_source_files(paths):        # 디렉토리면 재귀
        code = Path(path).read_text(encoding="utf-8", errors="replace")
        fp = Scanner(lang=...)._fp(code, filename=path)   # 확장자로 언어 추론됨
        for h in index.search(fp):
            sim = h.shared / len(fp) if fp else 0.0
            if sim >= threshold:
                findings.append(Finding(file=path, hit=h, similarity=sim))
    return findings

def cmd_scan(args):
    index = _load_index(args)          # 지금은 비어있거나 mock. 실제 인덱스는 팀장이 채운다.
    findings = scan_paths(args.paths, index)
    _print_report(findings)
    return 1 if findings else 0        # ← PR 게이트가 이 코드로 실패 판정
```

- `Finding` 은 작은 dataclass(`file`, `hit`, `similarity`)면 충분하다.
- 언어 추론: `Scanner` 는 `filename=` 를 주면 확장자로 언어를 고른다(`compare` 가 이미 그렇게 쓴다).
- 순회할 확장자: `provenire.languages` 의 등록된 확장자를 참고하면 깔끔하다(하드코딩해도 무방).

> ⚠️ **실제 카피레프트 인덱스(`copyleft.db`)는 아직 없다** — 팀장이 코퍼스를 수집 중(A-1).
> 그래서 `_load_index` 는 지금은 **빈 인덱스나 mock** 을 돌려주면 된다. **scan 의 뼈대를 완성하는 게 이 태스크의 목표**이고, 실제 인덱스가 붙는 건 나중이다. (`--against copyleft` 옵션은 자리만 만들어 둬도 된다)

### 4) 자가 점검
```bash
pytest
ruff check .
python benchmarks/poc_winnowing.py
```

### 5) PR을 올린다
```bash
git add -A
git commit -m "feat: provenire scan — 인덱스와 대조하는 PR 게이트 코어"
git push origin feat/minsoo/scan-cli
```
GitHub에서 **PR 생성 (base: main)** → **팀장 리뷰를 기다린다.**

---

## 브랜치

```
feat/minsoo/scan-cli
```

---

## 🚫 건드리면 안 되는 파일 (팀장 영역)

```
src/provenire/core/**       ← 읽기만. 재사용은 하되 수정 금지
src/provenire/index/**      ← 읽기만. import 해서 쓰기만 (MockIndex/FileIndex/Hit)
src/provenire/explain/**
benchmarks/**
```
`cli.py` 는 **네 영역**이니 자유롭게 고친다.
인덱스 계약(`Hit`·`search`)이 부족하다고 느끼면 **고치지 말고 팀장에게 말한다.** (계약을 바꾸면 팀장 작업과 충돌한다)

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 구현 | `superpowers:test-driven-development` ← **테스트 먼저, 인덱스 주입 가능하게** |
| 막혔을 때 | `superpowers:systematic-debugging` |
| PR 전 | `superpowers:verification-before-completion` |

**Claude에게 시작할 때:**
```
docs/tasks/T-03_scan_cli.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/scan-cli 브랜치에서 작업해.
src/provenire/index/ 는 읽기만 하고 import해서 쓰기만 해 (팀장 영역).
```

---

## 막히면

1. 무엇을 시도했는가
2. 어디서 막혔는가 (에러 메시지 그대로)
3. 무엇을 묻고 싶은가

**30분 이상 진전이 없으면 바로 묻는다.** 특히 **인덱스 계약(`Hit`/`search`)이 애매하면 즉시 팀장에게.**

---

## 이 태스크가 끝나면

**T-04 (git diff 어댑터)** 로 이어진다 — PR에서 **추가된 줄만** 검사해 빠르게. 그 다음이 **T-05(GitHub Action ⭐)** 로, 이 `scan` 이 드디어 PR에 자동으로 붙는다. **여기가 데모의 클라이맥스다.**

---

<sub>배정일: 2026-07-15 · 작성: 이우진(팀장)</sub>
