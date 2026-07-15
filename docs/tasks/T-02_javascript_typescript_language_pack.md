# T-02 · JavaScript / TypeScript 언어팩 추가

**담당**: 김민수 (`minsoo`) · **난이도**: 하 · **예상**: 2일 · **WP**: D (다언어 지원)

---

## 한 줄

> **JS·TS 코드도 "변수명만 바꾼 재현"을 잡아낼 수 있게 만든다.**

---

## 왜 필요한가

T-01(Java)에서 이미 증명했다 — **언어팩 하나만 추가하면 그 언어의 재현을 잡는다.**
AI가 GPL 코드를 베끼는 일은 **웹 프론트/백엔드(JS·TS)에서 특히 잦다.**

이번엔 Java에서 익힌 패턴을 **그대로 반복**하면 된다. 두 언어를 함께 처리한다:

```
JS:  function elideFilename(name, len) { ... }   ->  function ID(ID, ID) { ... }
TS:  function elideFilename(name: string, len: number): string   ->  function ID(ID: string, ID: number): string
                                                                                      ^ 타입은 구조로 남긴다
```

> ⭐ **T-01을 참고 구현으로 쓴다.** `src/provenire/languages/java.py` 가 정확히 이 태스크의 본보기다.

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** — 브랜치·PR·금지사항 |
| `src/provenire/languages/java.py` | **이번 작업의 본보기** — 이 구조를 그대로 따른다 |
| `src/provenire/languages/__init__.py` | `_MODULES` 에 언어를 등록하는 곳 |
| `src/provenire/core/normalizer.py` | 정규화가 어떻게 돌아가는지 (**읽기만**, 수정 금지) |
| `tests/test_languages.py` | Java 테스트가 본보기 — 여기에 JS·TS 테스트를 **추가**한다 |

---

## 완료 조건 (DoD)

- [ ] `src/provenire/languages/javascript.py` 가 존재한다
- [ ] `src/provenire/languages/typescript.py` 가 존재한다
- [ ] `_MODULES` 에 `"javascript"`, `"typescript"` 가 등록됐다
- [ ] `tests/test_languages.py` 에 JS·TS 테스트를 **추가**하고 **통과**한다
  - [ ] 이름만 바꾼 JS 코드 → **유사도 90% 이상** (탐지)
  - [ ] 이름만 바꾼 TS 코드 → **유사도 90% 이상** (탐지)
  - [ ] 무관한 JS/TS 코드 → **유사도 30% 미만** (오탐 없음)
  - [ ] `.js` / `.ts` 확장자만으로도 언어가 추론된다
- [ ] `pytest` 전체 통과
- [ ] `ruff check .` 통과
- [ ] `python benchmarks/poc_winnowing.py` 통과 (**Python·Java 동작을 깨뜨리지 않았는가**)

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/js-ts-lang
```

### 2) 먼저 테스트를 쓴다 (TDD)
`tests/test_languages.py` **맨 아래에** JS·TS 블록을 추가한다. Java 블록이 본보기다.

```python
# ─────────────────────────── JavaScript ───────────────────────────

JS_ORIGIN = """
function elideFilename(filename, length) {
    const marker = "...";
    if (length < marker.length) {
        throw new Error("too short");
    }
    if (filename.length <= length) {
        return filename;
    }
    const toElide = filename.length - length + marker.length;
    const left = Math.floor((filename.length - toElide) / 2);
    return filename.substring(0, left) + marker;
}
"""

# 변수·함수명만 전부 바꾼 버전
JS_RENAMED = """
function truncatePath(pathStr, maxLen) {
    const dots = "...";
    if (maxLen < dots.length) {
        throw new Error("too short");
    }
    if (pathStr.length <= maxLen) {
        return pathStr;
    }
    const cut = pathStr.length - maxLen + dots.length;
    const head = Math.floor((pathStr.length - cut) / 2);
    return pathStr.substring(0, head) + dots;
}
"""

JS_UNRELATED = """
function mean(values) {
    let total = 0.0;
    let count = 0;
    for (const v of values) {
        total += v;
        count += 1;
    }
    return count === 0 ? 0.0 : total / count;
}
"""


def test_javascript_is_registered():
    assert "javascript" in available()


def test_javascript_renamed_is_detected():
    m = compare(JS_RENAMED, JS_ORIGIN, lang="javascript")
    assert m.similarity > 0.9, f"이름 변경 JS 코드를 놓쳤다 ({m.similarity:.1%})"


def test_javascript_unrelated_is_not_flagged():
    m = compare(JS_UNRELATED, JS_ORIGIN, lang="javascript")
    assert m.similarity < 0.3


def test_javascript_inferred_from_extension():
    m = compare(JS_RENAMED, JS_ORIGIN, filename="pathHelper.js")
    assert m.similarity > 0.9
```

TypeScript도 **같은 방식**으로 작성한다. TS 예제는 타입 애노테이션(`: string`, `: number`)을 넣는다.

**이 테스트가 실패하는 것을 먼저 확인한다.** 그 다음 통과시킨다.

### 3) 언어팩을 만든다

Pygments가 각 언어를 토큰화하면 어떤 토큰이 나오는지 **직접 찍어본다** (java.py가 이렇게 만들어졌다):

```python
from pygments import lex
from pygments.lexers import get_lexer_by_name

for tok, val in lex(JS_ORIGIN, get_lexer_by_name("javascript")):
    print(tok, repr(val))
# TS 는 get_lexer_by_name("typescript") 로 똑같이 찍어본다
```

그리고 java.py와 **같은 원칙**으로 `keep` 을 정한다:

| 토큰 종류 | 어떻게 | 왜 |
|---|---|---|
| 키워드 (`function`, `if`, `return`, `const`, `new`, `throw`) | **그대로 둔다** | 구조 |
| TS 타입 (`string`, `number`, `boolean`) | **직접 찍어보고** 판단 | 구조일 가능성 높음 |
| 변수·함수·클래스명 | **`ID` 로 익명화** (자동) | ← 핵심 |
| 문자열·숫자 | `STR`·`NUM` (자동) | |
| 주석 | 버린다 (자동) | |

`javascript.py`:
```python
from pygments.token import Token
from .base import LanguageSpec

SPEC = LanguageSpec(
    name="javascript",
    lexer="javascript",
    extensions=(".js", ".mjs", ".cjs", ".jsx"),
    keep=(Token.Keyword,),   # ← 직접 찍어보고 필요한 것만. java.py 참고
)
```

`typescript.py` 도 같은 틀. `lexer="typescript"`, `extensions=(".ts", ".tsx")`.

> ⚠️ **추측하지 말 것.** TS의 `string`·`number` 같은 타입명이 Pygments에서
> `Token.Keyword.Type` 로 나오는지 `Token.Name` 으로 나오는지 **직접 lex 해서 확인**하고,
> java.py 처럼 **왜 그렇게 정했는지 독스트링에 적는다.**

### 4) 두 언어를 등록한다
`src/provenire/languages/__init__.py` 의 `_MODULES`:
```python
_MODULES = (
    "python",
    "java",
    "javascript",   # ← 추가
    "typescript",   # ← 추가
)
```

### 5) 자가 점검
```bash
pytest
ruff check .
python benchmarks/poc_winnowing.py   # Python·Java 동작이 안 깨졌는지
```

### 6) PR을 올린다
```bash
git add -A
git commit -m "feat: JS/TS 언어팩 추가 — 이름 변경 재현 탐지"
git push origin feat/minsoo/js-ts-lang
```
GitHub에서 **PR 생성 (base: main)** → **팀장 리뷰를 기다린다.**

---

## 브랜치

```
feat/minsoo/js-ts-lang
```

---

## 🚫 건드리면 안 되는 파일 (팀장 영역)

```
src/provenire/core/**       ← 읽기만. 수정 금지
src/provenire/index/**
src/provenire/explain/**
benchmarks/**
```
`core/normalizer.py` 를 고쳐야 할 것 같으면 **먼저 팀장에게 말한다.**
(언어팩은 `languages/` 안에서만 끝나도록 설계되어 있다 — Java가 그걸 증명했다)

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 구현 | `superpowers:test-driven-development` ← **테스트 먼저** |
| 막혔을 때 | `superpowers:systematic-debugging` |
| PR 전 | `superpowers:verification-before-completion` |

**Claude에게 시작할 때:**
```
docs/tasks/T-02_javascript_typescript_language_pack.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/js-ts-lang 브랜치에서 작업해.
src/provenire/languages/java.py 를 본보기로 삼아.
```

---

## 막히면

이 세 가지를 정리해서 팀장에게 묻는다.
1. 무엇을 시도했는가
2. 어디서 막혔는가 (에러 메시지 그대로)
3. 무엇을 묻고 싶은가

**30분 이상 진전이 없으면 바로 묻는다.** 혼자 붙잡고 있지 않는다.

---

## 이 태스크가 끝나면

**T-03 (`provenire scan` CLI + mock Index)** 로 이어진다.
여기서부터 언어팩을 벗어나 **제품의 얼굴(PR 게이트)** 을 만들기 시작한다.
팀장이 이미 `MockIndex` 를 준비해뒀으니(`src/provenire/index/`) 인덱스 완성을 기다릴 필요가 없다.

---

<sub>배정일: 2026-07-15 · 작성: 이우진(팀장)</sub>
