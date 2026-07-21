# Provenire

**한국어** · [English](https://github.com/4thIS/opensource_contest_provenire/blob/main/README.md)

> **AI가 생성한 코드가 오픈소스 라이선스를 베꼈는지, PR에서 잡아내는 오픈소스 라이선스 게이트**

[![PyPI](https://img.shields.io/pypi/v/provenire.svg)](https://pypi.org/project/provenire/)
[![Downloads](https://img.shields.io/pypi/dm/provenire.svg)](https://pypi.org/project/provenire/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/4thIS/opensource_contest_provenire/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml/badge.svg)](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)](#로드맵)

`provenire` — 라틴어 *"기원하다"*. 코드가 **어디서 왔는지(provenance)** 를 추적합니다.

---

## 문제

Copilot·Cursor·Claude는 **GPL·AGPL 저장소로 학습**되었습니다.
이들이 원본 코드를 **출처 없이 그대로 재현**하는 일이 실제로 벌어집니다 — 이를 **"AI 라이선스 세탁"** 이라 부릅니다.

카피레프트 코드가 섞여 들어가면 **제품 소스 전체를 공개해야 할 수도** 있습니다.
실제로 이 문제로 **코드베이스를 전면 재작성한 기업 사례**가 보고되었습니다.

그런데 이를 검사하는 도구는 **FOSSA · Snyk · Black Duck — 전부 유료**입니다.
학생·개인·소규모 팀은 **무방비**입니다.

### 게다가, 대부분의 라이선스 도구는 이 문제를 **볼 수조차 없다**

"오픈소스 라이선스 검사"라 불리는 도구는 사실 **세 종류**이고, 서로 다른 일을 합니다.

| | 대표 도구 | 무엇을 보나 | AI가 베낀 코드 |
|---|---|---|:--:|
| **A. 의존성 검사 (SCA)** | FOSSA · Snyk · ORT · pip-licenses | `requirements.txt` 등 **선언된 패키지 목록** | ❌ |
| **B. 라이선스 문구 스캐너** | ScanCode · licensee · FOSSology · REUSE | 파일 헤더의 **라이선스 텍스트** | ❌ |
| **C. 코드 스니펫 매칭** | Black Duck · SCANOSS · **Provenire** | **코드 본문의 유사도** | ⭕ |

AI가 GPL 코드를 재현할 때 **의존성 목록에는 아무것도 추가되지 않고, 라이선스 헤더도 붙지 않습니다.**
A와 B는 볼 대상 자체가 없습니다. 이 문제는 **C에서만** 잡힙니다.

> 기존 도구는 **무엇을 가져왔는지**를 검사합니다.
> Provenire는 **무엇을 베꼈는지**를 검사합니다.

---

## 핵심 아이디어

GitHub Copilot의 `public code filter`는 **문자열이 거의 똑같을 때만** 걸러냅니다.
**변수명만 바꾸면 그대로 통과합니다.**

Provenire는 지문을 뜨기 전에 **식별자를 익명화**합니다.

```
원본:  def elide_filename(filename, length):  ->  def ID(ID, ID):
AI  :  def truncate_path(path_str, max_len):  ->  def ID(ID, ID):
                                                  ^ 지문이 같아진다
```

이름은 지우고 **구조(키워드·연산자·제어흐름)만 남긴 뒤** winnowing 지문을 뜹니다.
→ **이름을 아무리 바꿔도 잡힙니다.**

그리고 **C 그룹 안에서도** 식별자를 지우는 도구는 현재 Provenire뿐입니다.

| | 정규화 방식 | k-gram | 식별자 |
|---|---|---|:--:|
| MOSS (표준 설정) | 주석·공백 제거 | 5 문자 | **보존** |
| [SCANOSS](https://github.com/scanoss/wfp/blob/master/README.md) | 영숫자가 아닌 문자 제거 | 30 문자 | **보존** |
| **Provenire** | 주석 제거 + **식별자 → `ID`** | 15 토큰 | **삭제** |

지문에 이름이 남아 있으면, **이름을 바꾸는 순간 지문이 깨집니다.**

---

## 실제 동작

AI가 GPL 코드를 **변수명만 바꿔서** 뱉었다고 해봅시다.

```console
$ provenire compare ai_output.py gpl_origin.py

  모드               유사도   지문
  ------------------------------------------
  raw (baseline)     12.0%   3/25      <- Copilot 필터 수준: 임계값 미만, 놓친다
  tokens (기본)     100.0%   24/24     <- Provenire: 잡아낸다
  ------------------------------------------

  [!] 표절 의심 — 유사도 100.0% (임계값 30%)
```

종료 코드 `1` → **CI/PR 게이트로 바로 쓸 수 있습니다.**

---

## 검증 결과

실제 **GPL-3.0 코드**(`qutebrowser/utils/utils.py`)로 검증했습니다.

| 변형 시나리오 | raw (baseline) | **tokens (Provenire)** |
|---|:--:|:--:|
| 그대로 복사 | 100% | **100%** |
| 주석·독스트링 삭제 | 100% | **87.5%** |
| **변수·함수명 전부 변경** | **8.8%** (놓침) | **100.0%** (탐지) |
| 이름변경 + 주석삭제 + 재포맷 | **8.8%** (놓침) | **87.5%** (탐지) |
| 무관한 코드 (음성대조) | 0% | **0%** (오탐 없음) |

이름을 바꾸면 raw 는 **임계값(30%) 아래로 떨어져 놓치고**, 토큰 정규화는 100% 탐지·오탐 0 입니다.

### 함수 하나를 넘어서

Provenire 는 코드를 **함수 단위로 쪼개** 대조하므로, 큰 파일에 묻힌 카피레프트도 잡습니다 —
GPL 파일을 통째로 붙여넣거나, GPL 함수 하나를 **변수명만 바꿔 내 코드에 섞어도** 그 조각을
정확히 짚어냅니다. **9개 카피레프트 프로젝트** 기준 **Precision 100% · Recall 90.7% · F1 95.1% · 오탐 0**
(`python benchmarks/evaluate.py`).

> 재현: [`benchmarks/`](https://github.com/4thIS/opensource_contest_provenire/tree/main/benchmarks) · 상세: [`benchmarks/RESULTS.md`](https://github.com/4thIS/opensource_contest_provenire/blob/main/benchmarks/RESULTS.md)

### 선행 연구 속에서의 위치

LLM 생성 코드의 출처 추적은 활발한 연구 주제입니다. 최근 연구
([Gurioli et al., *Efficient and Scalable Provenance Tracking for LLM-Generated Code Snippets*, 2026](https://arxiv.org/abs/2605.28510))는
winnowing의 **확장성**을 해결했습니다 — 벡터 검색을 앞단에 붙여 1,000만 스니펫 코퍼스에서
선형 시간을 로그 시간으로 낮췄습니다. 다만 그 연구는 정규화 단계에서 **식별자를 보존**하고,
이름 변경 시나리오를 *"4글자를 넘고 3회 넘게 등장하는 단어를 20% 확률로 치환"* 으로
정의합니다 — **식별자의 대부분이 원문 그대로 남습니다.**

Provenire가 파는 축은 **직교합니다.** 규모가 아니라 **변형 내성** — 식별자가 **전부** 바뀐
조건에서의 탐지입니다. 덧붙여 같은 연구가 향후 과제로 제시한
*"함수 본문 등 의미 단위로 분할(AST 활용)"* 은 Provenire에 **이미 구현되어 있습니다**
([`index/chunker.py`](https://github.com/4thIS/opensource_contest_provenire/blob/main/src/provenire/index/chunker.py)).
반대로 그 연구가 남긴 **Type-3 클론**(문장 추가·삭제·재배열)은 우리에게도 열린 문제입니다 — [로드맵](#로드맵)에 있습니다.

---

## 설치

```bash
pip install provenire
```

카피레프트 지문 인덱스가 **패키지에 들어 있어** 설치 직후 바로 검사됩니다.

```bash
# 소스에서 개발하려면
git clone https://github.com/4thIS/opensource_contest_provenire.git
cd opensource_contest_provenire
pip install -e ".[dev]"
```

## 사용법

```bash
provenire scan <경로>                   # 파일·폴더 검사 — 내장 인덱스로 바로 동작
provenire scan --diff <ref>             # <ref> 이후 추가된 코드만 검사 (PR 게이트)
provenire compare <의심코드> <원본>      # 두 파일의 유사도
provenire fingerprint <파일>             # 지문 미리보기
provenire scan <경로> --index <db>       # ...직접 만든 지문 DB를 쓰려면
```

표절이 발견되면 **종료 코드 1** 로 끝나므로 CI 에서 그대로 게이트로 쓸 수 있습니다.

```python
from provenire import compare

m = compare(ai_generated_code, gpl_source)
if m.is_suspicious:
    print(f"표절 의심: {m.similarity:.1%}")

# 다른 언어
compare(java_a, java_b, lang="java")
```

---

## GitHub Action

PR 을 열 때마다 자동으로 검사합니다. Provenire 는 **그 PR 에서 추가된 코드만**(`scan --diff`)
훑어서, 카피레프트와 겹치면 PR 에 코멘트를 달고 체크를 실패시킵니다.

```yaml
# .github/workflows/provenire.yml
name: Provenire
on: pull_request
permissions:
  contents: read
  pull-requests: write        # PR 코멘트를 달려면 필요하다
jobs:
  license-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0       # 필수 — base 커밋이 있어야 diff 를 계산한다
      - uses: 4thIS/opensource_contest_provenire/.github/action@v0.1
        with:
          fail-on: true        # 발견 시 체크 실패 (false = 코멘트만)
```

걸리면 PR 에 이렇게 달립니다:

```
⚠️ Provenire — 카피레프트 유사 코드가 발견되었습니다

  98.2%  src/utils.py
     ↳ qutebrowser/utils.py :: sanitize_filename  [GPL-3.0-or-later]
```

**주의할 점**
- **`fetch-depth: 0` 은 필수입니다.** 기본 checkout 은 커밋 하나만 받아와 base 가 없으므로 `--diff` 가 동작하지 않습니다.
- **fork 에서 온 PR** 은 토큰이 읽기 전용이라 코멘트가 생략됩니다. 체크 실패로는 알려줍니다.
- **처음에는 `fail-on: false` 로 시작하세요.** 일주일쯤 경고만 받아보고 켜는 편이 안전합니다 — 우리도 그렇게 하다가 오탐 한 종류를 발견해 고쳤습니다.

---

## 로드맵

- [x] winnowing 핑거프린팅 엔진
- [x] 토큰 정규화 (식별자 익명화) — **핵심 차별점**
- [x] 유사도 판정 (containment)
- [x] CLI (`compare` / `fingerprint`)
- [x] 언어팩 구조 — Python · Java · JavaScript · TypeScript
- [x] **카피레프트 지문 인덱스 동봉** — 설치 즉시 검사된다
- [x] **`provenire scan`** — 파일 검사(함수 단위 청킹) 및 `--diff` PR 게이트
- [x] **GitHub Action** — PR 코멘트 + 체크 실패 ([사용법](#github-action))
- [ ] 인덱스 확장 (LSH/MinHash) — 코퍼스를 더 키우기 위해
- [ ] LLM 2차 판정 (관용구 vs 구조적 재현)
- [ ] 더 많은 언어 (Go, C++ 등) · Python 외 함수 단위 청킹
- [ ] pre-commit 훅

---

## 어떻게 동작하나

```
PR diff (추가된 줄)
   |
   |-- 1. 정규화       주석·공백 제거 -> 토큰화 -> 식별자를 ID로 익명화
   |-- 2. 핑거프린팅   k-gram 해시 -> 슬라이딩 윈도우 최소해시 (winnowing)
   |-- 3. 인덱스 검색  카피레프트 코퍼스 지문 DB 조회
   |-- 4. 유사도 판정  containment = |공유 지문| / |의심 코드 지문|
   `-- 5. 리포트       원본 링크 · 라이선스 · 위험도
```

알고리즘: Schleimer, Wilkerson, Aiken.
*"Winnowing: Local Algorithms for Document Fingerprinting"* (SIGMOD 2003) — MOSS의 기반.

---

## 기여

새 언어·새 라이선스 규칙은 **파일 하나 추가**로 확장됩니다.
[`CONTRIBUTING.md`](https://github.com/4thIS/opensource_contest_provenire/blob/main/CONTRIBUTING.md)를 봐주세요. `good first issue` 환영합니다.

## 라이선스

[Apache-2.0](https://github.com/4thIS/opensource_contest_provenire/blob/main/LICENSE) — 특허 조항 포함. 자유롭게 쓰시되 출처를 남겨주세요.

> **Provenire는 법률 자문이 아닙니다.** 의심 구간을 알려주는 도구이지 판결이 아닙니다.

---

<sub>2026 오픈소스 개발자대회 출품작 · 팀 <b>코드감식반</b> (이우진 · 김민수)</sub>
