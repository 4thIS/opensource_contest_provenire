# CLAUDE.md — 협업 헌법

> ## 이 문서는 이 프로젝트에 참여하는 **모든 사람과 모든 AI**가 따르는 **협업 헌법**이다.
>
> **사람이든 AI든, 이 저장소에서 어떤 작업을 시작하기 전에 반드시 이 문서를 먼저 읽는다.**
>
> - **Claude Code**는 프로젝트 루트의 이 파일을 **세션 시작 시 자동으로 로드**한다.
> - **다른 AI 도구**(Cursor, Copilot, ChatGPT 등)를 사용할 때는 **세션 시작 시 이 파일을 컨텍스트에 직접 포함**시킨다.
> - 개인 전역 설정(`~/.claude/CLAUDE.md`)과 이 문서가 충돌하는 경우, **항상 이 문서가 우선한다.**

---

## 1. 프로젝트 개요

### 무엇을 만드는가
**Provenire** — AI가 생성한 코드가 오픈소스 라이선스를 베꼈는지 **Pull Request에서 잡아내는 오픈소스 라이선스 게이트**.

> Copilot·Cursor·Claude는 GPL·AGPL 저장소로 학습되었다.
> 이들이 원본 코드를 출처 없이 재현하면 **제품 소스 전체를 공개해야 할 수도** 있다.
> 그런데 이를 검사하는 도구는 FOSSA·Snyk·Black Duck — **전부 유료**다.
> 학생·개인·소규모 팀은 무방비다. **우리는 이것을 오픈소스로 연다.**

### 핵심 원리 (이걸 모르면 코드를 못 고친다)
GitHub Copilot의 `public code filter`는 **문자열이 거의 같을 때만** 걸러낸다.
→ **변수명만 바꾸면 그대로 통과한다.**

Provenire는 지문을 뜨기 전에 **식별자를 익명화**한다.

```
원본:  def elide_filename(filename, length):  ->  def ID(ID, ID):
AI  :  def truncate_path(path_str, max_len):  ->  def ID(ID, ID):
                                                  ^ 지문이 같아진다
```

**이름은 지우고 구조만 남긴다.** 이것이 프로젝트의 존재 이유이자 유일한 해자다.

### 검증된 명제 (CI가 매번 확인한다)
| 시나리오 | raw (Copilot 수준) | **tokens (우리)** |
|---|:--:|:--:|
| 변수·함수명 전부 변경 | **0.0%** (놓침) | **100.0%** (탐지) |
| 무관한 코드 | 0.0% | **0.0%** (오탐 없음) |

> 재현: `python benchmarks/poc_winnowing.py` · 상세: [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md)
> **이 명제가 깨지면 CI가 실패한다.** 절대 깨뜨리지 말 것.

### 기본 정보
| 항목 | 내용 |
|---|---|
| 대회 | 2026 오픈소스 개발자대회 · **학생부문** · 자유과제 · 세부과제 **보안/인증** |
| 팀 | 이우진(팀장) · 김민수 |
| 라이선스 | **Apache-2.0** (특허 조항 포함) |
| 언어 | Python 3.10+ |
| 주요 의존성 | Pygments (토큰화) · pytest · ruff |
| 배포 | PyPI (`provenire`) · GitHub Actions Marketplace |

### 저장소 구조
```
src/provenire/
├── core/
│   ├── normalizer.py    식별자 익명화 (핵심)
│   ├── fingerprint.py   winnowing 지문 (MOSS 알고리즘)
│   └── matcher.py       containment 유사도 판정
├── index/               [미구현] 카피레프트 코퍼스 지문 DB
└── cli.py               provenire compare / fingerprint
tests/                   핵심 명제를 지키는 테스트
benchmarks/              누구나 재현 가능한 검증 실험
.github/workflows/ci.yml 테스트 + 핵심 명제 검증
```

### 개발 환경
```bash
pip install -e ".[dev]"

pytest                              # 테스트
ruff check .                        # 린트
python benchmarks/poc_winnowing.py  # 핵심 명제 검증
```

---

## 2. 역할 분담

| 담당자 | 브랜치 | 영역 | 담당 파일 (**본인만 수정**) |
|---|---|---|---|
| **이우진** (팀장) | `woojin` | **엔진 · 정확도 · 평가**<br/>인덱스 · 관용구 필터 · LLM 판정 · 벤치마크 | `src/provenire/core/**`<br/>`src/provenire/index/**`<br/>`src/provenire/explain/**`<br/>`benchmarks/**` |
| **김민수** | `minsoo` | **사용자 접점 · 확장**<br/>다언어 · CLI · PR 게이트 · 배포 | `src/provenire/languages/**`<br/>`src/provenire/adapters/**`<br/>`src/provenire/report/**`<br/>`src/provenire/cli.py`<br/>`.github/action/**`<br/>`docs/**` · `README.md` |

브랜치는 `<타입>/<이름>/<주제>` 형식을 쓴다.
```
feat/woojin/copyleft-index
feat/minsoo/java-lang
```

### 규칙
- **타인의 담당 파일은 수정하지 않는다.** 고쳐야 하면 **먼저 담당자와 협의**한다. (§4)
- 두 영역을 잇는 **인터페이스는 [`docs/01_구현계획.md`](docs/01_구현계획.md) §3에 고정**되어 있다.
  → 그 계약만 지키면 서로 막히지 않고 **병렬로** 개발할 수 있다.
- 김민수의 작업 지시서: [`docs/tasks/`](docs/tasks/) — 팀장이 배정하고, `git pull` 로 받는다.

---

## 3. 작업 흐름 (Git)

### 대원칙
> ## 🚫 **main 브랜치에 직접 push 하지 않는다.**
> ## ✅ **자신의 브랜치에서 작업하고, PR을 올리고, 팀장의 머지를 기다린다.**

### 브랜치 규칙
- **모든 작업은 자신의 브랜치에서만** 한다. `main`에서 직접 작업하지 않는다.
- 브랜치 이름: `<타입>/<이름>/<주제>`
  ```
  feat/woojin/token-normalizer
  feat/minsu/copyleft-index
  fix/woojin/false-positive
  docs/minsu/readme
  ```
- 타입: `feat` (기능) · `fix` (버그) · `docs` (문서) · `test` · `refactor` · `chore`

### 작업 순서
```bash
# 1. 최신 main에서 브랜치를 딴다
git checkout main
git pull origin main
git checkout -b feat/woojin/token-normalizer

# 2. 작업하고, 자신의 브랜치에 커밋한다
git add -A
git commit -m "feat: 다언어 토큰 정규화 지원"

# 3. 자신의 브랜치를 push 한다  (main이 아니다!)
git push origin feat/woojin/token-normalizer

# 4. GitHub에서 PR을 생성한다  (base: main)

# 5. 팀장의 리뷰와 머지를 기다린다.  ← 여기서 멈춘다
```

### PR 규칙
| 규칙 | 내용 |
|---|---|
| **PR 생성자는 자기 PR을 머지하지 않는다** | 리뷰 없이 들어가는 코드를 만들지 않는다 |
| **`main`으로의 머지는 팀장(이우진)만 진행한다** | 머지 권한은 팀장에게만 있다 |
| PR 본문에 **무엇을·왜** 를 적는다 | 리뷰어가 맥락 없이 코드만 보게 하지 않는다 |
| **CI가 초록이어야 머지한다** | 테스트·린트·핵심 명제 검증 통과 필수 |

### 머지 전 자가 점검
```bash
pytest                              # 통과하는가
ruff check .                        # 린트 통과하는가
python benchmarks/poc_winnowing.py  # 핵심 명제가 살아있는가
```

### AI로 작업할 때 (Claude Code, Cursor, Copilot 등)
> **AI에게도 위 규칙이 100% 동일하게 적용된다.**

- ❌ **AI에게 `main`으로 push 시키지 않는다.**
- ❌ **AI에게 타인의 담당 영역을 수정하게 하지 않는다.**
- ✅ AI는 **자신의 브랜치에서만** 커밋한다.
- ✅ AI가 만든 코드도 **반드시 PR을 거쳐** 팀장의 리뷰를 받는다.
- ✅ AI에게 작업을 시킬 때, **이 문서를 먼저 읽게 한다.**

> AI가 규칙을 어기려 하면 **중단시킨다.** "AI가 그렇게 했다"는 변명이 되지 않는다.

---

## 4. 절대 하지 말 것

### 🔴 비밀 정보 커밋 금지
```
.env  *.pem  *.key  *.p12  credentials.json  토큰·비밀번호가 담긴 모든 파일
```
- **차단 수단**: `.gitignore` + **pre-commit hook**
- 실수로 커밋했다면 **즉시 팀장에게 알린다.** 조용히 덮지 않는다. (히스토리에 영원히 남는다)
- 대회 심사에서 **개인정보·비밀키 커밋은 치명적 감점**이다.

### 🔴 `main` 브랜치 직접 push 금지
- **차단 수단**: GitHub **Protected Branches**
- 반드시 **브랜치 → PR → 팀장 머지**를 거친다.

### 🔴 타 개발 영역 코드 임의 수정 금지
- 담당자가 정해진 영역은 **본인만 수정**한다.
- 고쳐야 한다면 **먼저 담당자와 협의**한다. 말없이 고치지 않는다.
- 급하면 **이슈를 올리거나 담당자에게 PR을 제안**한다.

### 🔴 히스토리를 파괴하는 명령 금지
```bash
git push --force        # ❌ 금지 (남의 커밋을 지운다)
git push --force-with-lease  # ❌ 팀장 승인 없이는 금지
git reset --hard        # ❌ 금지 (되돌릴 수 없다)
git rebase              # ⚠️ 공유된 브랜치에서는 금지
```
- 되돌려야 하면 **`git revert`** 를 쓴다. (되돌린 기록이 남는다)
- 실수했다면 **팀장에게 먼저 말한다.**

### 🔴 저작권 코드 커밋 금지 (이 프로젝트 특성상 중요)
- **GPL 등 타인의 코드를 저장소에 넣지 않는다.**
- 벤치마크는 **런타임에 내려받는다** (`benchmarks/poc_winnowing.py` 참조).
- 우리가 라이선스를 지키는 도구를 만들면서 라이선스를 어기면 **모든 것이 무너진다.**

---

## 5. 팀장이 해야 할 설정 (체크리스트)

- [ ] GitHub **Settings → Branches → Protected Branches** 로 `main` 보호
  - [ ] Require a pull request before merging
  - [ ] Require status checks to pass (CI)
  - [ ] Do not allow bypassing the above settings
- [ ] **pre-commit hook** 설치 (비밀키 커밋 차단)
- [ ] 역할 분담 확정 후 §2 표 채우기

---

<sub>
생성일: 2026-07-12 · 최종 수정일: 2026-07-12<br/>
팀 코드감식반 (이우진 · 김민수) — 2026 오픈소스 개발자대회
</sub>
