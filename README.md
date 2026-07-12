# Provenire

> **AI가 생성한 코드가 오픈소스 라이선스를 베꼈는지, PR에서 잡아내는 오픈소스 라이선스 게이트**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml/badge.svg)](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#로드맵)

`provenire` — 라틴어 *"기원하다"*. 코드가 **어디서 왔는지(provenance)** 를 추적합니다.

---

## 문제

Copilot·Cursor·Claude는 **GPL·AGPL 저장소로 학습**되었습니다.
이들이 원본 코드를 **출처 없이 그대로 재현**하는 일이 실제로 벌어집니다 — 이를 **"AI 라이선스 세탁"** 이라 부릅니다.

카피레프트 코드가 섞여 들어가면 **제품 소스 전체를 공개해야 할 수도** 있습니다.
실제로 이 문제로 **코드베이스를 전면 재작성한 기업 사례**가 보고되었습니다.

그런데 이를 검사하는 도구는 **FOSSA · Snyk · Black Duck — 전부 유료**입니다.
학생·개인·소규모 팀은 **무방비**입니다.

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

---

## 실제 동작

AI가 GPL 코드를 **변수명만 바꿔서** 뱉었다고 해봅시다.

```console
$ provenire compare ai_output.py gpl_origin.py

  모드               유사도   지문
  ------------------------------------------
  raw (baseline)      2.1%   1/48      <- Copilot 필터 수준: 놓친다
  tokens (기본)     100.0%   21/21     <- Provenire: 잡아낸다
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
| 주석·독스트링 삭제 | 100% | **86.4%** |
| **변수·함수명 전부 변경** | **0.0%** (놓침) | **100.0%** (탐지) |
| 이름변경 + 주석삭제 + 재포맷 | **0.0%** (놓침) | **86.4%** (탐지) |
| 무관한 코드 (음성대조) | 0% | **0%** (오탐 없음) |

> 재현: [`benchmarks/`](benchmarks/) · 상세: [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md)

---

## 설치

```bash
pip install provenire        # (배포 예정)
```

```bash
# 지금은 소스에서
git clone https://github.com/4thIS/opensource_contest_provenire.git
cd opensource_contest_provenire
pip install -e ".[dev]"
```

## 사용법

```bash
provenire compare <의심코드> <원본>     # 두 파일의 유사도
provenire fingerprint <파일>            # 지문 미리보기
```

```python
from provenire import compare

m = compare(ai_generated_code, gpl_source)
if m.is_suspicious:
    print(f"표절 의심: {m.similarity:.1%}")
```

---

## 로드맵

- [x] winnowing 핑거프린팅 엔진
- [x] 토큰 정규화 (식별자 익명화) — **핵심 차별점**
- [x] 유사도 판정 (containment)
- [x] CLI (`compare` / `fingerprint`)
- [ ] **카피레프트 코퍼스 인덱스** (LSH/MinHash)
- [ ] **`provenire scan --against copyleft`** — 인덱스 대조
- [ ] **GitHub Action** — PR 인라인 코멘트
- [ ] LLM 2차 판정 (관용구 vs 구조적 재현)
- [ ] 다언어 지원 (Pygments 500+ 언어)
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
[`CONTRIBUTING.md`](CONTRIBUTING.md)를 봐주세요. `good first issue` 환영합니다.

## 라이선스

[Apache-2.0](LICENSE) — 특허 조항 포함. 자유롭게 쓰시되 출처를 남겨주세요.

> **Provenire는 법률 자문이 아닙니다.** 의심 구간을 알려주는 도구이지 판결이 아닙니다.

---

<sub>2026 오픈소스 개발자대회 출품작 · 팀 <b>코드감식반</b> (이우진 · 김민수)</sub>
