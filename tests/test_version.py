"""버전이 한 곳만 바뀌는 사고를 막는다.

버전은 `pyproject.toml` 과 `src/provenire/__init__.py` **두 군데**에 있다.
한쪽만 올리면 PyPI 에는 새 버전으로 올라가는데 `provenire.__version__` 은 옛 값을
말하게 된다 — 사용자가 버전으로 버그를 특정할 수 없게 되고, 되돌릴 수도 없다.
(T-06 지시서가 사람에게 "둘 다 바꾸세요"라고 당부해 왔지만 당부는 잊힌다)

tomllib 은 3.11+ 라서 못 쓴다(우리는 3.10 지원). 정규식으로 충분하다.
"""
import re
from pathlib import Path

import provenire

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_matches_pyproject():
    text = _PYPROJECT.read_text(encoding="utf-8")
    # [project] 의 version — 다른 섹션의 version 키에 걸리지 않게 앞부분에서만 찾는다
    declared = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)
    assert provenire.__version__ == declared, (
        f"pyproject.toml={declared} 인데 provenire.__version__={provenire.__version__} 이다. "
        "배포 전에 두 곳을 함께 올려야 한다."
    )
