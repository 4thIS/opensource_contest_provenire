# T-01 · Java 언어팩 추가

**담당**: 김민수 (`minsoo`) · **난이도**: 하 · **예상**: 2~3일 · **WP**: D (다언어 지원)

---

## 한 줄

> **Java 코드도 "변수명만 바꾼 재현"을 잡아낼 수 있게 만든다.**

---

## 왜 필요한가

지금 Provenire는 **Python만** 제대로 정규화한다.
하지만 AI가 GPL 코드를 베끼는 일은 **Java·JS·C++ 어디서나** 일어난다.

우리의 핵심 원리는 언어와 무관하다:

```
Python:  def elide_filename(filename, length):   ->  def ID(ID, ID):
Java  :  String elideFilename(String name, int len)  ->  String ID(String ID, int ID)
                                                          ^ 이름을 지우고 구조만 남긴다
```

Pygments가 **500개 이상 언어**를 이미 토큰화해준다.
**언어별 매핑만 맞춰주면 된다.** → 이게 이 태스크다.

---

## 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | **협업 규칙 (필수)** — 브랜치·PR·금지사항 |
| `src/provenire/languages/` | 이번에 작업할 곳 (팀장이 구조를 만들어 둠) |
| `src/provenire/core/normalizer.py` | 정규화가 어떻게 돌아가는지 (**읽기만**, 수정 금지) |
| `tests/test_core.py` | 기존 테스트가 무엇을 지키는지 |
| `benchmarks/RESULTS.md` | 우리가 증명한 것이 무엇인지 |

---

## 완료 조건 (DoD)

- [ ] `src/provenire/languages/java.py` 가 존재한다
- [ ] **같은 로직 · 다른 이름**인 두 Java 코드가 **동일한 정규화 결과**를 낸다
- [ ] `tests/test_languages.py` 에 Java 테스트가 있고 **통과**한다
  - [ ] 이름만 바꾼 Java 코드 → **유사도 90% 이상** (탐지)
  - [ ] 무관한 Java 코드 → **유사도 30% 미만** (오탐 없음)
- [ ] `pytest` 전체 통과
- [ ] `ruff check .` 통과
- [ ] `python benchmarks/poc_winnowing.py` 통과 (**Python 동작을 깨뜨리지 않았는가**)

---

## 작업 순서

### 1) 브랜치를 딴다
```bash
git checkout main
git pull origin main
git checkout -b feat/minsoo/java-lang
```

### 2) 먼저 테스트를 쓴다 (TDD)
`tests/test_languages.py` 를 만들고, **실패하는 테스트**부터 쓴다.

```python
JAVA_ORIGIN = """
public class FileUtil {
    public static String elideFilename(String filename, int length) {
        String marker = "...";
        if (length < marker.length()) {
            throw new IllegalArgumentException("too short");
        }
        if (filename.length() <= length) {
            return filename;
        }
        int toElide = filename.length() - length + marker.length();
        int left = (filename.length() - toElide) / 2;
        return filename.substring(0, left) + marker;
    }
}
"""

# 이름만 바꾼 버전 (AI가 흔히 뱉는 형태)
JAVA_RENAMED = """
public class PathHelper {
    public static String truncatePath(String pathStr, int maxLen) {
        String dots = "...";
        if (maxLen < dots.length()) {
            throw new IllegalArgumentException("too short");
        }
        if (pathStr.length() <= maxLen) {
            return pathStr;
        }
        int cut = pathStr.length() - maxLen + dots.length();
        int head = (pathStr.length() - cut) / 2;
        return pathStr.substring(0, head) + dots;
    }
}
"""

def test_java_renamed_is_detected():
    m = compare(JAVA_RENAMED, JAVA_ORIGIN, lang="java")
    assert m.similarity > 0.9   # 이름을 바꿔도 잡아낸다
```

**이 테스트가 실패하는 것을 먼저 확인한다.** 그 다음 통과시킨다.

### 3) 언어팩을 만든다
`src/provenire/languages/java.py`

Pygments가 Java를 토큰화하면 어떤 토큰이 나오는지 **먼저 찍어본다**:

```python
from pygments import lex
from pygments.lexers import JavaLexer

for tok, val in lex(JAVA_ORIGIN, JavaLexer()):
    print(tok, repr(val))
```

그리고 Python 매핑(`core/normalizer.py`의 `normalize_tokens`)과 **같은 원칙**으로 규칙을 정한다.

| 토큰 종류 | 어떻게 | 왜 |
|---|---|---|
| 키워드 (`public`, `if`, `return`) | **그대로 둔다** | 구조 정보 |
| 타입 (`String`, `int`) | **그대로 둔다** | 구조 정보 |
| 변수·메서드·클래스명 | **`ID` 로 치환** | ← **핵심**. 이름을 지운다 |
| 문자열 리터럴 | `STR` 로 치환 | |
| 숫자 | `NUM` 로 치환 | |
| 연산자·구두점 (`{`, `;`, `+`) | **그대로 둔다** | 구조 정보 |
| 주석 | **버린다** | |

> ⚠️ **어려운 부분**: Java는 `String`·`int` 같은 타입명이 Pygments에서
> `Token.Keyword.Type` 으로 나올 수도, `Token.Name` 으로 나올 수도 있다.
> **직접 찍어보고** 확인해야 한다. 추측하지 말 것.

### 4) 자가 점검
```bash
pytest
ruff check .
python benchmarks/poc_winnowing.py   # Python 동작이 안 깨졌는지
```

### 5) PR을 올린다
```bash
git add -A
git commit -m "feat: Java 언어팩 추가 — 이름 변경 재현 탐지"
git push origin feat/minsoo/java-lang
```
GitHub에서 **PR 생성 (base: main)** → **팀장 리뷰를 기다린다.**

---

## 브랜치

```
feat/minsoo/java-lang
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
(언어팩은 `languages/` 안에서만 끝나도록 설계되어 있다)

---

## 추천 Claude 스킬

| 단계 | 스킬 |
|---|---|
| 구현 | `superpowers:test-driven-development` ← **테스트 먼저** |
| 막혔을 때 | `superpowers:systematic-debugging` |
| PR 전 | `superpowers:verification-before-completion` |

**Claude에게 시작할 때:**
```
docs/tasks/T-01_java_language_pack.md 를 읽고 작업해줘.
CLAUDE.md의 규칙을 지켜. main에 push하지 말고 feat/minsoo/java-lang 브랜치에서 작업해.
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

**T-02 (JavaScript/TypeScript 언어팩)** 으로 이어진다.
Java에서 익힌 패턴을 그대로 반복하면 되므로 훨씬 빠르다.

---

<sub>배정일: 2026-07-12 · 작성: 이우진(팀장)</sub>
