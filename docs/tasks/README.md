# 작업 지시서 (tasks)

> 이 폴더에는 **각자에게 배정된 작업**이 들어 있다.
> 팀장이 태스크를 작성해 `main`에 머지하면, 담당자는 `git pull` 로 받는다.

---

## 어떻게 일을 받는가

```bash
# 1. 최신 태스크를 받는다
git checkout main
git pull origin main

# 2. docs/tasks/ 에서 자기 태스크를 확인한다
#    T-01, T-02 ... 순서대로 진행한다
```

## 어떻게 진행하는가

```bash
# 3. 태스크 문서에 적힌 브랜치를 만든다
git checkout -b feat/minsoo/java-lang

# 4. 작업한다  (AI와 협업해도 좋다 — 아래 참조)

# 5. 자기 브랜치에 커밋하고 push 한다   (main 아님!)
git add -A
git commit -m "feat: Java 언어팩 추가"
git push origin feat/minsoo/java-lang

# 6. GitHub에서 PR 생성  (base: main)

# 7. 팀장의 리뷰·머지를 기다린다.  ← 여기서 멈춘다. 직접 머지하지 않는다.
```

> 🚫 **`main`에 직접 push 하지 않는다.**
> 🚫 **자기 PR을 자기가 머지하지 않는다.**
> 자세한 규칙: [`../../CLAUDE.md`](../../CLAUDE.md)

---

## AI(Claude 등)와 협업하는 법

태스크 문서는 **AI에게 그대로 던지면 작업이 되도록** 쓰여 있다.

```
1. Claude Code를 프로젝트 루트에서 연다
   → CLAUDE.md 가 자동으로 로드된다 (협업 규칙)

2. 태스크 문서를 읽히고 시작한다:
   "docs/tasks/T-01_java_language_pack.md 를 읽고 작업해줘"

3. AI에게도 규칙이 똑같이 적용된다:
   - AI가 main에 push 하게 두지 않는다
   - AI가 팀장 영역(core/, index/, explain/, benchmarks/)을 고치게 두지 않는다
   - AI가 만든 코드도 반드시 PR을 거친다
```

### 추천 작업 흐름 (Claude 사용 시)
| 단계 | 스킬 (있으면) | 없으면 |
|---|---|---|
| 구현 | `superpowers:test-driven-development` | **테스트를 먼저 쓰고** 구현한다 |
| 막혔을 때 | `superpowers:systematic-debugging` | 추측으로 고치지 말고 원인을 찾는다 |
| 끝내기 전 | `superpowers:verification-before-completion` | **실제로 돌려보고** "됐다"고 말한다 |
| PR 전 | `superpowers:requesting-code-review` | 자기 diff를 한 번 더 읽는다 |

---

## 완료 전 자가 점검 (PR 올리기 전 반드시)

```bash
pytest                              # 테스트 통과하는가
ruff check .                        # 린트 통과하는가
python benchmarks/poc_winnowing.py  # 핵심 명제가 살아있는가  ← 이게 깨지면 절대 안 됨
```

셋 다 초록이어야 PR을 올린다.

---

## 막히면

**하루 이상 막히지 않는다.** 30분 이상 진전이 없으면 팀장에게 묻는다.
- 무엇을 시도했는지
- 어디서 막혔는지 (에러 메시지 그대로)
- 무엇을 물어보고 싶은지

이 세 가지만 정리해서 물으면 된다.

---

## 태스크 목록

| ID | 제목 | 담당 | 상태 |
|---|---|---|---|
| [T-01](T-01_java_language_pack.md) | Java 언어팩 추가 | 김민수 | ✅ 머지됨 (PR #3) |
| [T-02](T-02_javascript_typescript_language_pack.md) | JS/TS 언어팩 추가 | 김민수 | 🟢 진행 가능 |

*(태스크는 순차적으로 추가된다. `git pull` 로 새 태스크를 받는다.)*
