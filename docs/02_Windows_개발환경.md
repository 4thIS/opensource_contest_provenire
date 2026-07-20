# Windows 개발 환경 주의사항

> 이 문서는 **한국어 Windows에서 이 저장소를 개발할 때 반복해서 터진 문제**를 정리한 것이다.
> 우리 팀은 같은 뿌리의 문제를 **네 번** 겪었다. 다섯 번째를 막기 위해 쓴다.

---

## 1. 모든 문제의 뿌리 — `cp949`

한국어 Windows의 기본 문자 인코딩은 **`cp949`**(≒ EUC-KR)다. 반면 우리 소스·git·PyPI·GitHub는 전부 **UTF-8**이다.

파이썬은 **인코딩을 명시하지 않으면 시스템 기본값(cp949)을 쓴다.** 그래서 한글이나 `—`, `•` 같은 문자를 만나면 죽는다.

```
UnicodeEncodeError: 'cp949' codec can't encode character '—'   ← 쓸 때
UnicodeDecodeError: 'cp949' codec can't decode byte 0xec            ← 읽을 때
```

> ⚠️ **CI(Linux)는 기본이 UTF-8이라 이 문제를 절대 못 잡는다.**
> CI가 초록이어도 Windows에서 터질 수 있다. **로컬에서 직접 돌려봐야 한다.**

---

## 2. 실제로 겪은 사례 (전부 같은 원인)

| # | 무슨 일 | 원인 | 해결 |
|---|---|---|---|
| 1 | 벤치마크 스크립트가 출력 중 죽음 | `print()` → 콘솔이 cp949 | 스크립트가 stdout을 UTF-8로 고정 (PR #20) |
| 2 | **`scan --diff` 가 한글 주석만 있어도 크래시** | `subprocess(text=True)` 에 encoding 미지정 | 이슈 #22 → PR #28 에서 해결 |
| 3 | `twine` 이 `~/.pypirc` 를 못 읽음 | 설정 파일에 한글 주석 | `.pypirc` 를 ASCII로 재작성 |
| 4 | `twine` 출력이 죽음 | rich 라이브러리가 `•` 출력 | `PYTHONIOENCODING=utf-8` |
| 5 | **`provenire scan` 이 표절을 찾으면 크래시** | CLI 리포트의 `↳`·한글 출력 | `cli.py` stdout 고정 (T-06 리뷰에서 발견) |

**2번과 5번이 특히 아프다.** 우리 타겟 사용자는 한국 개발자다. 한글 주석은 예외가 아니라 기본값이고,
CLI 는 그 사용자가 직접 실행하는 제품의 얼굴이다.

> 5번은 **PyPI 배포 직전에** 잡혔다. 그대로 올렸으면 되돌릴 수 없어 0.1.1 로 다시 배포해야 했다.

---

## 3. 코드 작성 규칙 (이것만 지키면 안 터진다)

### ① 파일을 열 때는 **항상** `encoding="utf-8"`

```python
open(path, encoding="utf-8")                  # ✅
Path(p).read_text(encoding="utf-8")           # ✅
Path(p).write_text(s, encoding="utf-8")       # ✅

open(path)                                    # ❌ cp949로 읽는다
```

### ② `subprocess` 로 출력을 읽을 때는 `encoding` 을 명시

```python
subprocess.run(cmd, capture_output=True, text=True,
               encoding="utf-8", errors="replace")   # ✅

subprocess.run(cmd, capture_output=True, text=True)  # ❌ 이슈 #22의 원인
```

> `errors="replace"` 까지 주면 깨진 바이트가 있어도 죽지 않고 넘어간다.

### ③ **사용자에게 출력하는 진입점**은 stdout을 고정

`benchmarks/*.py` 뿐 아니라 **`cli.py` 도 포함이다.** 직접 실행되어 한글·기호를 출력하는
모든 진입점의 맨 위에:

```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

이게 있어야 사용자가 환경변수 없이 그냥 실행할 수 있다. **"누구나 재현 가능"의 전제조건이다.**

> 🔴 **CLI 가 이 규칙이 가장 필요한 곳이다.** 벤치마크는 우리끼리 돌리지만,
> CLI 는 **설치한 사용자가 실행한다.** 여기서 터지면 제품이 망가진 것으로 보인다.
> 실제로 v0.1.0 준비 중 `provenire scan` 이 리포트의 `↳` 문자에서 죽는 것을 발견했다.

### ③-1 ⚠️ **조건부 출력 경로**를 조심하라

위 크래시는 **표절을 찾았을 때만** 터졌다. 아무것도 안 잡히면 `[OK]` 만 출력하고 정상 종료한다.

```
scan → 결과 없음  → "[OK] 찾지 못했습니다"   ← 여기는 ASCII 라 안전
scan → 표절 발견  → "  ↳ project/file ..."   ← 여기서 죽는다
```

**정상 경로만 실행해보면 절대 안 걸린다.** 경고·에러·발견 등 **조건부로만 출력되는 경로**는
반드시 그 조건을 실제로 만들어서 확인해야 한다.

### ④ 외부 도구가 읽는 설정 파일은 **ASCII로만**

`~/.pypirc` 같은 파일에 한글 주석을 넣지 마라. 그 도구가 UTF-8로 읽어준다는 보장이 없다.

---

## 4. 코드 리뷰 체크리스트

PR을 볼 때 이 두 가지만 grep 해도 대부분 걸러진다:

```bash
grep -rn "open(" --include="*.py" src/ | grep -v "encoding="
grep -rn "subprocess.run" --include="*.py" -A3 src/ | grep "text=True" | grep -v "encoding="
```

### 현재 저장소 상태 (2026-07-20 스캔)

| 위치 | 상태 |
|---|---|
| `benchmarks/evaluate.py`, `poc_winnowing.py` | ✅ stdout 고정됨 |
| 파일 I/O (`read_text`/`write_text`/`open`) | ✅ 전부 `encoding` 명시 |
| `src/provenire/adapters/git.py` | ✅ PR #28 에서 해결 |
| `tests/test_git_adapter.py` 의 `_git()` 헬퍼 | ✅ PR #28 에서 함께 해결 |
| **`src/provenire/cli.py`** | ⏳ **T-06(PR #30)에서 stdout 고정 예정** |

---

## 5. 실행할 때

### 외부 도구가 인코딩 에러를 뱉으면

우리가 고칠 수 없는 서드파티(twine 등)는 환경변수로 넘긴다:

```bash
PYTHONIOENCODING=utf-8 python -m twine upload dist/*
```

### 셸별 명령 문법이 다르다

| | Git Bash | PowerShell |
|---|---|---|
| 경로 | `./.venv/Scripts/python.exe` | `.\.venv\Scripts\python.exe` |
| 환경변수 | `VAR=값 명령` | `$env:VAR="값"; 명령` |

같은 명령을 다른 셸에 붙여넣으면 `command not found` 가 난다.

---

## 6. 권장 환경

```bash
# Python 3.10 (CI와 동일 버전)으로 venv 를 만든다
py -3.10 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"

# 이후 항상 venv 파이썬을 쓴다
./.venv/Scripts/python.exe -m pytest
```

> 시스템에 여러 파이썬(3.10 / 3.14 …)이 깔려 있으면 `python` 이 어느 것을 가리키는지 바뀐다.
> **venv 파이썬을 경로로 직접 지정**하면 흔들리지 않는다.

### 검증 3종 (PR 전 필수)

```bash
./.venv/Scripts/python.exe -m pytest
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe benchmarks/poc_winnowing.py
```

### ⚠️ 사용자 대면 기능은 **실제로 실행**해봐야 한다

`pytest` 는 출력을 캡처하므로 **인코딩 문제를 잡지 못한다.** CI 는 Linux 라 더더욱 못 잡는다.
CLI 처럼 사용자가 직접 쓰는 것은 **터미널에서 눈으로** 확인한다:

```bash
# 환경변수 없이, 실제 콘솔에서, "무언가 발견되는" 상황으로
./.venv/Scripts/python.exe -m provenire.cli scan <표절코드폴더> --index data/copyleft.db
```

배포 전이라면 한 단계 더 — **프로젝트 폴더 밖 새 venv 에 wheel 을 설치해서** 확인한다.
개발 환경에서 되는 것과 설치본이 되는 것은 다르다.

---

<sub>작성: 2026-07-20 · 이우진(팀장) — 실제로 겪은 문제만 적었다. 새로 겪으면 여기에 추가한다.</sub>
