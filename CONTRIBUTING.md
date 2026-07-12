# 기여 가이드

Provenire에 기여해 주셔서 감사합니다.
**오픈소스를 지키는 도구를, 오픈소스로** 만듭니다.

## 빠른 시작

```bash
git clone https://github.com/4thIS/opensource_contest_provenire.git
cd opensource_contest_provenire
pip install -e ".[dev]"

pytest                              # 테스트
python benchmarks/poc_winnowing.py  # 핵심 명제 검증
ruff check .                        # 린트
```

## 가장 도움이 되는 기여

### 1. 새 언어 지원 추가 (`good first issue`)
현재 정규화는 Pygments 토크나이저를 씁니다. **500개 이상 언어**를 이미 인식할 수 있습니다.
`src/provenire/core/normalizer.py`의 `normalize_tokens()`에서
해당 언어의 토큰 타입 매핑만 맞춰주면 됩니다.

- Java / C / C++ / Go / Rust / JavaScript ... 환영합니다
- 테스트: 같은 로직을 이름만 바꾼 두 코드가 **동일한 정규화 결과**를 내면 성공

### 2. 오탐 사례 제보
보일러플레이트(getter/setter, 표준 관용구)가 잘못 매칭되는 케이스를 찾으면
**이슈로 올려주세요.** 정밀도(Precision)를 올리는 데 가장 중요합니다.

### 3. 벤치마크 확장
`benchmarks/`에 새 시나리오를 추가해 주세요.
특히 **실제 LLM에게 재생성시킨 코드**로 검증하면 큰 도움이 됩니다.

## 규칙

- **실제 저작권 코드를 저장소에 커밋하지 마세요.** 벤치마크는 런타임에 내려받습니다.
- 테스트 없는 PR은 머지하지 않습니다. 핵심 명제(`tests/test_core.py`)를 깨면 안 됩니다.
- 커밋 메시지는 자유. 한국어/영어 모두 좋습니다.
- 라이선스: Apache-2.0에 동의하는 것으로 간주합니다.

## 행동 강령
서로 존중합시다. 그게 전부입니다.
