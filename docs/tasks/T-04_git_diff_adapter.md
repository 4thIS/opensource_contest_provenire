# T-04 · git diff 어댑터 (`scan --diff`)

**담당**: 김민수 (`minsoo`) · **난이도**: 중 · **예상**: 2일 · **WP**: B (스캐너 & PR 게이트)

---

## 한 줄

> **PR에서 바뀐 부분(추가된 코드)만 골라 검사한다 — 빠르고, 새로 들어온 AI 코드에 집중한다.**

---

## 왜 필요한가

T-03의 `scan` 은 **파일 전체**를 검사한다. 그런데 PR 리뷰에서 중요한 건 **이번에 새로 추가된 코드**다.

```bash
provenire scan --diff main        # main 대비 이 브랜치에서 추가된 코드만 검사
provenire scan --diff HEAD~1      # 직전 커밋 이후 추가된 코드만 검사
```

왜 "추가된 줄만"인가:
- **빠르다** — 거대한 저장소 전체가 아니라 PR diff만 본다. GitHub Action(T-05)에서 매 PR마다 도니까 속도가 중요하다.
- **정확히 겨냥한다** — AI가 이번 PR에서 뱉은 코드가 표적이다. 기존 코드까지 다시 훑을 필요가 없다.

> ⭐ T-05(GitHub Action)가 이 `--diff` 모드를 쓴다. **PR 게이트의 실전 진입점**이다.

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** |
| `src/provenire/cli.py` | **네가 T-03에서 만든 `scan`** — `--diff` 를 여기에 얹는다 |
| `tests/test_cli.py` | 네 기존 scan 테스트 — diff 테스트도 같은 스타일로 |

---

## 핵심 계약 — T-03을 재사용한다

`--diff` 는 "경로를 순회"하는 대신 "git이 알려준 추가 코드"를 검사한다.
**T-03의 "코드 하나를 인덱스와 대조하는 로직"을 재사용**하면 된다.

```python
# 새로 만들 것 (adapters/git.py) — git 을 파싱해 (파일 → 추가된 코드) 를 준다
changes: dict[str, str] = changed_code(ref="main")
#   {"src/foo.py": "def bar(...):\n    ...추가된 라인들...", ...}

# 그다음은 T-03과 똑같다 — 각 코드의 지문을 떠서 index.search
for file, code in changes.items():
    fp = Scanner()._fp(code, filename=file)
    for h in index.search(fp):
        sim = h.shared / len(fp)
        if sim >= threshold: ...  # Finding
```

> **팁**: T-03의 `scan_paths` 가 파일을 읽어 검사하는 그 안쪽 로직을, "코드 문자열을 받아 검사하는" 작은 함수로 빼두면 `--diff` 와 **그대로 공유**된다. (네 코드니까 자유롭게 리팩터해도 된다)

---

## 완료 조건 (DoD)

- [ ] `provenire scan --diff <ref>` 가 동작한다 (`--diff main`, `--diff HEAD~1` 등)
- [ ] `src/provenire/adapters/git.py` 가 git diff 를 파싱해 **(파일 → 추가된 코드)** 를 돌려준다
- [ ] **diff 파싱은 순수 함수**여서 git 실행 없이 테스트된다 (가짜 diff 텍스트로)
- [ ] 지원 언어 파일만 검사한다 (`.py .java .js .ts` — `languages.extensions()` 재사용)
- [ ] 의심이 있으면 **exit 1**, 없으면 0 (T-03과 동일)
- [ ] `tests/test_git_adapter.py` 통과
  - [ ] 가짜 diff 텍스트 → 추가된 코드가 파일별로 정확히 추출된다
  - [ ] (통합) 임시 git 저장소에서 표절 코드를 커밋 → `scan --diff` 가 잡는다
- [ ] `pytest` 전체 통과 · `ruff check .` 통과 · `python benchmarks/poc_winnowing.py` 통과

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/git-diff
```

### 2) 먼저 테스트를 쓴다 (TDD) — 파싱부터

`tests/test_git_adapter.py`. **git 없이** 파싱 로직부터 테스트한다.

```python
from provenire.adapters.git import parse_added_code

DIFF = '''diff --git a/src/foo.py b/src/foo.py
index 1234..5678 100644
--- a/src/foo.py
+++ b/src/foo.py
@@ -0,0 +1,3 @@
+def elide(name, n):
+    marker = "..."
+    return name[:n] + marker
'''

def test_parse_extracts_added_lines_per_file():
    changes = parse_added_code(DIFF)
    assert "src/foo.py" in changes
    assert "def elide(name, n):" in changes["src/foo.py"]
    assert "marker" in changes["src/foo.py"]
```

**이 테스트가 실패하는 것을 먼저 확인**하고 통과시킨다.

### 3) `adapters/git.py` 를 만든다

```python
import subprocess

def run_git_diff(ref: str, cwd: str = ".") -> str:
    """git diff 를 실행해 unified diff 텍스트를 돌려준다."""
    out = subprocess.run(
        ["git", "diff", "--unified=3", ref, "--"],
        capture_output=True, text=True, cwd=cwd, check=True,
    )
    return out.stdout

def parse_added_code(diff_text: str) -> dict[str, str]:
    """unified diff → {파일경로: 추가된 코드}. (순수 함수 = 테스트 쉬움)

    - `diff --git a/… b/…` 로 파일이 바뀐다
    - `+` 로 시작하되 `+++` 가 아닌 줄이 '추가된 코드'
    """
    files: dict[str, list[str]] = {}
    current = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/")[-1]
            files[current] = []
        elif current and line.startswith("+") and not line.startswith("+++"):
            files[current].append(line[1:])
    return {f: "\n".join(v) for f, v in files.items() if v}

def changed_code(ref: str, cwd: str = ".") -> dict[str, str]:
    """git diff 를 파싱해 (파일 → 추가된 코드) 를 돌려준다."""
    return parse_added_code(run_git_diff(ref, cwd))
```
`src/provenire/adapters/__init__.py` 도 만든다(빈 파일이면 충분).

### 4) `cli.py` 의 `scan` 에 `--diff` 를 얹는다

- `--diff <ref>` 가 있으면: `changed_code(ref)` 로 (파일→코드) 를 얻어 검사
- 없으면: 기존 T-03 경로(파일/디렉터리) 검사
- **지원 언어 확장자만** 거른다 (`languages.extensions()`)
- 두 경로가 **검사 로직을 공유**하도록 리팩터한다 (팁 참조)

> ⚠️ 추가된 라인만 모으면 문법이 안 맞는 조각일 수 있다. 괜찮다 — 정규화는 **토큰 기반**(pygments lex)이라 조각도 토큰화된다. 다만 **너무 짧으면 지문이 안 나온다** (`if not fp: continue` 로 이미 걸러진다).

### 5) 자가 점검
```bash
pytest
ruff check .
python benchmarks/poc_winnowing.py
```
> 통합 테스트에서 임시 git 저장소가 필요하면 `tmp_path` 에 `git init` → `git add` → `git commit` 을
> `subprocess` 로 만들면 된다. (git 사용자 설정이 없으면 `-c user.email=... -c user.name=...` 로 준다)

### 6) PR을 올린다
```bash
git add -A
git commit -m "feat: scan --diff — PR에서 추가된 코드만 검사하는 git 어댑터"
git push origin feat/minsoo/git-diff
```
GitHub에서 **PR 생성 (base: main)** → **팀장 리뷰를 기다린다.**

---

## 브랜치

```
feat/minsoo/git-diff
```

---

## 🚫 건드리면 안 되는 파일 (팀장 영역)

```
src/provenire/core/**       ← 읽기만
src/provenire/index/**      ← 읽기만 (import 해서 쓰기만)
src/provenire/explain/**
benchmarks/**
```
`cli.py` · `adapters/**` 는 **네 영역**이다.

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 구현 | `superpowers:test-driven-development` ← **파싱을 순수 함수로 먼저** |
| 막혔을 때 | `superpowers:systematic-debugging` |
| PR 전 | `superpowers:verification-before-completion` |

**Claude에게 시작할 때:**
```
docs/tasks/T-04_git_diff_adapter.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/git-diff 브랜치에서 작업해.
index/ 와 core/ 는 읽기만 하고 import해서 써.
```

---

## 막히면

1. 무엇을 시도했는가
2. 어디서 막혔는가 (에러 메시지 그대로)
3. 무엇을 묻고 싶은가

**30분 이상 진전이 없으면 바로 묻는다.**

---

## 이 태스크가 끝나면

**T-05 (GitHub Action + PR 인라인 코멘트) ⭐** 로 이어진다 — **데모의 클라이맥스**다.
이 `scan --diff` 가 드디어 PR에 자동으로 붙어, 표절 의심에 **인라인 코멘트**를 단다.

---

<sub>배정일: 2026-07-15 · 작성: 이우진(팀장)</sub>
