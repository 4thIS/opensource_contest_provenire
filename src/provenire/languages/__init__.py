"""언어팩 레지스트리.

새 언어를 추가하려면:

    1. `languages/<언어>.py` 를 만들고 `SPEC = LanguageSpec(...)` 을 정의한다
    2. 아래 `_MODULES` 에 모듈 이름을 추가한다
    3. 테스트를 쓴다 — "이름만 바꾼 코드가 같은 지문을 내는가"

`core/` 는 건드릴 필요가 없다.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

from .base import LanguageSpec

__all__ = ["LanguageSpec", "get", "guess", "available", "register", "extensions"]

# 새 언어를 추가하면 여기에 모듈 이름을 넣는다.
_MODULES = (
    "python",
    "java",
    "javascript",
    "typescript",
)

_REGISTRY: dict[str, LanguageSpec] = {}
_BY_EXT: dict[str, LanguageSpec] = {}


def register(spec: LanguageSpec) -> None:
    _REGISTRY[spec.name.lower()] = spec
    for ext in spec.extensions:
        _BY_EXT[ext.lower()] = spec


def _load() -> None:
    for mod in _MODULES:
        spec = import_module(f".{mod}", __package__).SPEC
        register(spec)


_load()


def available() -> list[str]:
    """지원하는 언어 목록."""
    return sorted(_REGISTRY)


def extensions() -> set[str]:
    """등록된 모든 언어의 파일 확장자 집합 (예: {".py", ".java", ".js", ".ts"}).

    `provenire scan` 이 디렉터리를 순회할 때 지원 언어 파일만 고르는 데 쓴다.
    """
    return set(_BY_EXT)


def get(name: str) -> LanguageSpec:
    """언어 이름으로 스펙을 가져온다. 없으면 python으로 폴백."""
    return _REGISTRY.get(name.lower(), _REGISTRY["python"])


def guess(filename: str | None) -> LanguageSpec:
    """파일명(확장자)으로 언어를 추론한다. 실패하면 python."""
    if filename:
        spec = _BY_EXT.get(Path(filename).suffix.lower())
        if spec:
            return spec
    return _REGISTRY["python"]
