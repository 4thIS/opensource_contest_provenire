# T-06 · PyPI 재배포 (v0.1.0) + README 마무리

**담당**: 김민수 (`minsoo`) · **난이도**: 중 · **예상**: 2일 · **WP**: F (배포 & 문서)

---

## 한 줄

> **`pip install provenire` 한 줄이면 바로 표절 검사가 되게 만든다.**

---

## 왜 필요한가 — 지금 심각한 문제가 있다

PyPI 에 `provenire` **0.0.1 이 이미 올라가 있다**(이름 선점 완료, 민수님이 배포).
그런데 그건 **아주 초기 엔진뿐**이다. 그 뒤에 만든 것이 **전혀 들어있지 않다**:

| 지금 PyPI 의 0.0.1 | 실제 main |
|---|---|
| ❌ `provenire scan` 없음 | ✅ 있음 |
| ❌ Java·JS·TS 언어팩 없음 | ✅ 있음 |
| ❌ 인덱스·코퍼스 없음 | ✅ 있음 |
| ❌ `scan --diff` 없음 | ✅ 있음 |

> **즉 지금 누가 `pip install provenire` 하면 `scan` 명령조차 없는 껍데기를 받는다.**
> 심사위원이 이걸 해볼 수도 있다. **가장 먼저 고쳐야 할 인상 문제다.**

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** |
| `pyproject.toml` | 버전·패키징 설정을 고칠 곳 |
| `src/provenire/__init__.py` | `__version__` 도 함께 올려야 한다 |
| `README.md` | 네가 T-05 에서 정비한 곳 — 설치 흐름을 마무리한다 |

---

## ⭐ 핵심 쟁점 — 인덱스를 패키지에 넣을 것인가

**넣어야 한다.** 안 넣으면 이렇게 된다:

```bash
pip install provenire
provenire scan ./src          # → 빈 인덱스라 "찾지 못했습니다". 아무것도 안 잡는다.
```

사용자는 **왜 아무것도 안 잡히는지 모른다.** 도구가 무용지물로 보인다.

`data/copyleft.db` 는 **380KB** 라 패키지에 넣어도 부담이 없다.
지문 해시 + 메타뿐이라 **저작권 문제도 없다**(§4 · WP-A DoD 확인 완료).

### 어떻게 넣나 — 저장소 구조는 그대로 두고 패키지에만 포함

`pyproject.toml` 에 hatchling 의 `force-include` 를 쓰면 된다:

```toml
[tool.hatch.build.targets.wheel.force-include]
"data/copyleft.db" = "provenire/data/copyleft.db"
```

그리고 `cli.py` 의 `_load_index()` 가 **`--index` 가 없을 때 패키지 내장 인덱스를 기본으로** 쓰게 한다:

```python
from importlib.resources import files

def _default_index_path() -> Path | None:
    """패키지에 동봉된 카피레프트 인덱스. 없으면 None."""
    try:
        p = files("provenire") / "data" / "copyleft.db"
        return Path(str(p)) if p.is_file() else None
    except (ModuleNotFoundError, FileNotFoundError):
        return None
```

> `_load_index` 는 **네 영역(`cli.py`)** 이라 자유롭게 고쳐도 된다.
> `data/copyleft.db` 파일 자체와 빌드 방식은 **팀장 영역과 걸치니, 위 `force-include` 방식대로만** 하고 다르게 가고 싶으면 먼저 말해달라.

---

## 🔴 배포 권한 — 먼저 읽어라

**PyPI 최종 업로드는 민수님이 할 수 없다.** `provenire` 프로젝트의 **소유 계정은 팀장(이우진)** 이다
(0.0.1 을 팀장이 올렸다). 다른 계정으로 `twine upload` 하면 **403 Forbidden** 이 난다.

| 단계 | 담당 |
|---|---|
| 버전 올리기 · 인덱스 동봉 · wheel 빌드 · **깨끗한 venv 검증** | **민수** |
| **TestPyPI** 업로드·설치 확인 (본인 계정으로 가능) | **민수** |
| **PyPI 정식 업로드** (`twine upload dist/*`) | **팀장(이우진)** |

> ⚠️ **팀장에게 PyPI 토큰을 요청하지 마라.** 토큰 공유는 §4(비밀 정보) 위반이다.
> 민수님은 **PR 까지** 올리고, 머지 후 **팀장이 직접 업로드**한다.
> PR 본문에 "**빌드·검증 완료, 업로드 대기**" 라고 적어주면 된다.

---

## 완료 조건 (DoD)

**민수 담당**
- [ ] `pyproject.toml` 버전 **0.1.0**, `src/provenire/__init__.py` 의 `__version__` 도 **0.1.0**
- [ ] 패키지에 **`data/copyleft.db` 포함** (`force-include`)
- [ ] `--index` 없이도 `provenire scan` 이 **내장 인덱스로 실제 탐지**한다
- [ ] **깨끗한 환경에서 검증**: 새 venv → wheel 설치 → `provenire scan` 이 표절을 잡는다
- [ ] **TestPyPI 에 올려** 설치까지 확인한다 (본인 계정으로 가능)
- [ ] `README.md` — 설치 → 사용 흐름이 처음 보는 사람에게 이어진다 (배지·따라하기 예시)
- [ ] `pytest` · `ruff check .` · `python benchmarks/poc_winnowing.py` 통과
- [ ] PR 본문에 **깨끗한 venv 설치 검증 출력**을 붙인다

**팀장 담당 (머지 후)**
- [ ] PyPI 에 **0.1.0 정식 업로드**
- [ ] `pip install --upgrade provenire` 로 실제 설치 확인

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/pypi-release
```

### 2) 버전을 올린다
`pyproject.toml` 의 `version` 과 `src/provenire/__init__.py` 의 `__version__` **둘 다** 0.1.0 으로.
(두 곳이 어긋나면 배포 후 혼란스럽다)

### 3) 인덱스를 패키지에 포함시키고 기본 경로를 연결한다
위 "핵심 쟁점" 절 참조.

### 4) 로컬에서 wheel 을 만들어 **깨끗한 환경**에 설치해본다

이게 가장 중요한 검증이다. 개발 환경에서 되는 것과 설치본이 되는 것은 다르다.

```bash
pip install build
python -m build                       # dist/provenire-0.1.0-py3-none-any.whl 생성

# 완전히 새로운 가상환경에서 설치 (프로젝트 폴더 밖에서!)
cd /tmp && python -m venv fresh && source fresh/Scripts/activate   # Windows Git Bash
pip install /경로/dist/provenire-0.1.0-py3-none-any.whl

provenire --help
provenire scan <표절코드가_있는_폴더>      # ← --index 없이 잡히는지가 핵심
```

> 💡 **프로젝트 폴더 안에서 테스트하면 안 된다.** 소스가 그대로 보여서 "설치된 패키지"를 검증하지 못한다.

### 5) TestPyPI 로 검증한다 ⚠️ (민수 담당)

TestPyPI 는 **본인 계정으로 자유롭게** 올릴 수 있다. 여기서 끝까지 확인해라.

```bash
pip install twine
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --no-deps provenire==0.1.0
provenire scan <표절코드_폴더>      # ← 내장 인덱스로 잡히는지
```

> 🔴 **PyPI 는 같은 버전을 다시 올릴 수 없다.** 0.1.0 을 잘못 올리면 **영원히 되돌릴 수 없고**
> 0.1.1 로 새로 올려야 한다. 그래서 TestPyPI 검증이 필수다.

### 6) PR 을 올리고 **여기서 멈춘다** (PyPI 업로드는 팀장이)

`dist/` 는 커밋하지 않는다(빌드 산출물). PR 에는 **설정 변경과 검증 결과**만 담는다.
PR 본문에 아래를 적어주면 팀장이 이어받는다:

- 깨끗한 venv 설치 검증 출력
- TestPyPI 설치 확인 결과
- **"빌드·검증 완료 — PyPI 업로드 대기"**

> 팀장이 머지 후 `python -m build && twine upload dist/*` 로 정식 배포하고,
> `pip install --upgrade provenire` 로 확인한다.

### 7) README 를 마무리한다
처음 보는 사람이 **위에서 아래로 읽으면 따라할 수 있게**:
설치 → 한 번 돌려보기 → GitHub Action 붙이기 → 원리(왜 이름을 바꿔도 잡나)

### 8) PR을 올린다
```bash
git add -A
git commit -m "chore: v0.1.0 PyPI 배포 — 인덱스 동봉, scan 기본 동작"
git push origin feat/minsoo/pypi-release
```
**PR 본문에 실제 설치 검증 결과**(새 venv 에서 돌린 출력)를 붙여달라.

---

## 브랜치

```
feat/minsoo/pypi-release
```

---

## 🚫 건드리면 안 되는 파일 (팀장 영역)

```
src/provenire/core/**       ← 읽기만
src/provenire/index/**      ← 읽기만
benchmarks/**
data/copyleft.db            ← 파일 자체는 건드리지 않는다 (패키징 설정만 추가)
```
`pyproject.toml` · `cli.py` · `README.md` 는 배포를 위해 **필요한 만큼 고쳐도 된다.**
단 `pyproject.toml` 의 **의존성·라이선스 메타는 바꾸지 말 것** (Apache-2.0 유지).

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 배포 전 | `superpowers:verification-before-completion` ← **깨끗한 환경 설치까지 확인하고** "됐다"고 말할 것 |
| 막혔을 때 | `superpowers:systematic-debugging` |

**Claude에게 시작할 때:**
```
docs/tasks/T-06_pypi_release.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/pypi-release 브랜치에서 작업해.
core/ index/ benchmarks/ 는 읽기만 해.
PyPI 정식 업로드는 팀장이 하니, 빌드·TestPyPI 검증·PR 까지만 진행해줘.
```

> ⚠️ **AI에게 `twine upload` 를 맡기지 마라.** 토큰이 필요하고 되돌릴 수 없다.
> **PyPI 정식 업로드는 소유 계정을 가진 팀장이 직접** 한다. TestPyPI 까지만 AI 와 진행한다.

---

## 막히면

1. 무엇을 시도했는가
2. 어디서 막혔는가 (에러 메시지 그대로)
3. 무엇을 묻고 싶은가

**특히 배포는 되돌릴 수 없으니, 조금이라도 애매하면 올리기 전에 물어봐 달라.**

---

## 이 태스크가 끝나면

민수님의 태스크 라인(T-01~T-06)이 **완료**된다. 남는 것은 팀 공동 작업이다:
**시연 영상(F-4) · 결과보고서(F-5) · 커뮤니티 씨딩(F-6)**.

---

<sub>배정일: 2026-07-20 · 작성: 이우진(팀장)</sub>
