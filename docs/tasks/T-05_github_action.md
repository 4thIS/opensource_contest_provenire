# T-05 · GitHub Action + PR 코멘트 ⭐

**담당**: 김민수 (`minsoo`) · **난이도**: 중 · **예상**: 4~5일 · **WP**: B (스캐너 & PR 게이트)

---

## 한 줄

> **PR을 열면 Provenire가 자동으로 돌아, 표절 의심 코드에 경고 코멘트를 달고 체크를 실패시킨다.**

---

## 왜 이게 제일 중요한가

지금까지 만든 건 **터미널에서 사람이 직접 쳐야** 동작한다.
T-05는 그걸 **PR에 자동으로 붙인다.** 개발자는 설정 파일 몇 줄만 넣고 잊으면 된다.

```yaml
# 사용자가 자기 저장소에 넣을 전부
- uses: 4thIS/provenire-action@v1
  with:
    fail-on: true
```

그 뒤로는 **PR 열 때마다 자동으로**:
```
❌ Provenire / license-gate — Failing

⚠️ 표절 의심 1건
  100.0%  src/utils.py
     ↳ qutebrowser/utils.py :: elide_filename  [GPL-3.0-or-later]
```

> ⭐ **이게 시연 영상의 클라이맥스다.** "AI가 뱉은 코드 → PR → 경고" 장면 전체가 이 태스크에 달려 있다.
> 심사위원이 실제로 보게 될 유일한 화면이기도 하다.

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** |
| `src/provenire/cli.py` | **네가 만든 `scan --diff`** — Action이 이걸 호출한다 |
| `src/provenire/adapters/git.py` | diff 파싱 (인라인 코멘트로 확장할 때 필요) |
| `.github/workflows/ci.yml` | 우리 CI 구조 참고 |

---

## 완료 조건 (DoD)

**필수 (여기까지만 해도 태스크 완료)**
- [ ] `.github/action/action.yml` — composite action 으로 동작
- [ ] PR 이벤트에서 **base 대비 추가된 코드만** 검사 (`scan --diff`)
- [ ] 표절 의심 시 **PR에 코멘트**가 달린다 (원본 project·file·license·url·유사도 포함)
- [ ] `fail-on: true` 면 **체크가 실패**(빨간 X), `false` 면 경고만
- [ ] 의심이 없으면 **코멘트를 달지 않는다** (조용히 통과 — 소음 방지)
- [ ] **우리 저장소에서 실제로 동작 확인** (dogfooding — 아래 참조)
- [ ] `README.md` 에 **사용법 5줄** 추가

**여유 되면 (선택)**
- [ ] 코멘트를 **인라인**(해당 코드 줄 옆)으로 — 아래 "인라인 코멘트" 절 참조

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/github-action
```

### 2) action.yml 을 만든다

**composite action** 이 가장 간단하다 (Docker 불필요, 빠름).

```yaml
# .github/action/action.yml
name: "Provenire License Gate"
description: "AI가 생성한 코드가 카피레프트 오픈소스를 베꼈는지 PR에서 검사한다"
branding: { icon: "shield", color: "purple" }

inputs:
  index:
    description: "카피레프트 지문 DB(sqlite) 경로. 없으면 빈 인덱스로 동작"
    required: false
  base:
    description: "비교 기준 ref (기본: PR의 base 커밋)"
    required: false
  fail-on:
    description: "의심 발견 시 체크를 실패시킬지"
    default: "true"

runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: provenire 설치
      shell: bash
      run: pip install -e "${{ github.action_path }}/../.."   # 개발 중엔 저장소에서 설치

    - name: 스캔
      id: scan
      shell: bash
      run: |
        BASE="${{ inputs.base }}"
        [ -z "$BASE" ] && BASE="${{ github.event.pull_request.base.sha }}"
        set +e
        provenire scan --diff "$BASE" ${{ inputs.index && format('--index {0}', inputs.index) || '' }} > report.txt 2>&1
        echo "exit=$?" >> "$GITHUB_OUTPUT"
        set -e
        cat report.txt
```

> ⚠️ **`git fetch` 주의**: Actions의 기본 checkout은 얕은 복제(depth=1)라 **base 커밋이 없을 수 있다.**
> 사용자 워크플로에 `actions/checkout@v4` + `fetch-depth: 0` 을 요구하거나, action 안에서 `git fetch --depth=...` 를 해야 한다. **이거 안 하면 `--diff` 가 실패한다. 반드시 확인할 것.**

### 3) PR 코멘트를 단다

가장 간단한 방법은 **러너에 기본 설치된 `gh` CLI** 를 쓰는 것이다.

```yaml
    - name: PR 코멘트
      if: steps.scan.outputs.exit == '1'      # 의심이 있을 때만
      shell: bash
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        {
          echo "## ⚠️ Provenire — 카피레프트 유사 코드가 발견되었습니다"
          echo
          echo '```'
          cat report.txt
          echo '```'
          echo
          echo "그대로 머지하면 **소스 공개 의무**가 발생할 수 있습니다. 다시 작성하거나 라이선스를 검토하세요."
        } > comment.md
        gh pr comment ${{ github.event.pull_request.number }} --body-file comment.md

    - name: 체크 실패 처리
      if: steps.scan.outputs.exit == '1' && inputs.fail-on == 'true'
      shell: bash
      run: exit 1
```

**권한이 필요하다.** 사용자 워크플로에 이게 있어야 코멘트가 달린다:
```yaml
permissions:
  contents: read
  pull-requests: write
```

> ⚠️ **fork PR 함정**: 외부 fork에서 온 PR은 토큰 권한이 읽기 전용이라 **코멘트가 실패한다.**
> 그때는 조용히 넘어가게 처리하고(`continue-on-error`), 체크 실패만으로 알리는 게 안전하다. README에 명시할 것.

### 4) 우리 저장소에서 실제로 돌려본다 (dogfooding ⭐)

**이게 가장 중요한 검증이다.** 남의 저장소가 아니라 **우리 PR에서 진짜로 동작하는지** 봐야 한다.

`.github/workflows/provenire.yml` 를 만든다:
```yaml
name: Provenire
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  license-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }     # ← base 커밋이 필요하다
      - uses: ./.github/action
        with:
          fail-on: false             # 처음엔 경고만 (우리 PR을 막지 않게)
```

그리고 **일부러 표절 코드를 넣은 테스트 PR** 을 하나 열어 경고가 뜨는지 확인한다.
(그 PR 은 확인 후 닫는다. 머지하지 않는다.)

> 💡 팀장이 만든 코퍼스 DB(`copyleft.db`)는 아직 배포되지 않았다.
> **인덱스 없이도 Action 자체는 동작해야 한다**(빈 인덱스 = 항상 통과).
> 실제 DB 연결은 팀장이 배포한 뒤 `index:` 입력으로 붙인다.

### 5) README 에 사용법을 쓴다

```markdown
## GitHub Action 으로 쓰기
\```yaml
permissions: { contents: read, pull-requests: write }
steps:
  - uses: actions/checkout@v4
    with: { fetch-depth: 0 }
  - uses: 4thIS/provenire-action@v1
\```
\```
```

### 6) 자가 점검
```bash
pytest
ruff check .
python benchmarks/poc_winnowing.py
```
(Action 은 파이썬 테스트로 검증이 안 되므로 **실제 PR 실행 결과 스크린샷/링크**를 PR 본문에 붙일 것)

### 7) PR을 올린다
```bash
git add -A
git commit -m "feat: GitHub Action — PR에서 카피레프트 유사 코드 자동 검사"
git push origin feat/minsoo/github-action
```

---

## 인라인 코멘트 (선택 과제)

"코드 줄 옆에 코멘트"를 하려면 **줄 번호**가 필요한데, 현재 `parse_added_code` 는 줄 번호를 버린다.

하려면:
1. `adapters/git.py` 에서 hunk 헤더 `@@ -a,b +c,d @@` 의 **c(새 파일 시작 줄)** 를 읽어
   추가된 줄마다 실제 줄 번호를 함께 보존한다 (`{파일: [(줄번호, 코드)]}`)
2. GitHub API 로 인라인 코멘트를 단다:
   `POST /repos/{owner}/{repo}/pulls/{n}/comments` (`path`, `line`, `side: RIGHT`, `commit_id`)

**무리하지 마라.** 요약 코멘트만으로도 데모는 충분히 강력하다.
필수 항목을 먼저 완성하고, 시간이 남을 때 손대는 게 맞다.

---

## 브랜치

```
feat/minsoo/github-action
```

---

## 🚫 건드리면 안 되는 파일 (팀장 영역)

```
src/provenire/core/**       ← 읽기만
src/provenire/index/**      ← 읽기만
src/provenire/explain/**
benchmarks/**
```
`.github/action/**` · `.github/workflows/provenire.yml` · `cli.py` · `README.md` 는 **네 영역**이다.

> ⚠️ `.github/workflows/ci.yml`(기존 CI)은 **건드리지 말고**, 새 워크플로 파일을 따로 만들어라.
> CI가 깨지면 팀 전체가 막힌다.

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 막혔을 때 | `superpowers:systematic-debugging` |
| PR 전 | `superpowers:verification-before-completion` ← **실제 PR에서 돌려보고** "됐다"고 말할 것 |

**Claude에게 시작할 때:**
```
docs/tasks/T-05_github_action.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/github-action 브랜치에서 작업해.
core/ 와 index/ 는 읽기만 해. 기존 .github/workflows/ci.yml 은 건드리지 마.
```

---

## 막히면

Action 은 **로컬에서 디버깅이 어렵다.** 다음 순서로 접근하면 빠르다.

1. 먼저 **로컬에서** `provenire scan --diff main` 이 되는지 확인 (Action 문제인지 CLI 문제인지 분리)
2. Action 로그를 그대로 읽는다 — 대부분 `fetch-depth` 나 권한(`permissions`) 문제다
3. 30분 이상 진전이 없으면 **로그 전문과 함께** 팀장에게 묻는다

---

## 이 태스크가 끝나면

**T-06 (PyPI 재배포 + README 정비)** 으로 마무리된다.

> 참고: PyPI 의 `provenire` **0.0.1 은 이미 배포돼 있다**(이름 선점 완료).
> 다만 초기 엔진뿐이라 `scan`·언어팩·인덱스가 **빠져 있다.** T-06 에서 `0.1.0` 으로 올린다.

---

<sub>배정일: 2026-07-16 · 작성: 이우진(팀장)</sub>
