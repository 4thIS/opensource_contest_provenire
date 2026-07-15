"""카피레프트 지문 인덱스 — 계약과 mock.

실제 인덱스(코퍼스 수집 · 지문 DB · LSH 검색)는 WP-A에서 채운다.
지금 필요한 건 두 사람이 병렬로 움직이게 하는 최소 계약뿐이다:

    Hit        검색 결과 한 건        (docs/01_구현계획.md §3 계약)
    Index      search() 계약          (Protocol)
    MockIndex  가짜 인덱스 — 실제 인덱스를 기다리지 않고 scan/PR게이트를 개발한다

⚠️ 이 시그니처는 docs/01_구현계획.md §3 에 고정된 계약이다.
   바꾸면 민수의 T-03(provenire scan)이 깨진다. 함부로 바꾸지 말 것.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..core.matcher import Scanner
from .store import FingerprintStore

__all__ = ["Hit", "Index", "MockIndex", "FileIndex", "FingerprintStore"]


@dataclass(frozen=True)
class Hit:
    """검색 결과 한 건 — '이 코드가 어떤 카피레프트 원본과 겹치나'."""

    project: str        # "qutebrowser"
    file: str           # "qutebrowser/utils/utils.py"
    symbol: str | None  # "elide_filename" (함수 단위 매칭 시), 없으면 None
    license: str        # SPDX ID, 예: "GPL-3.0-or-later"
    url: str            # 원본 코드 링크
    shared: int         # 의심 코드와 공유하는 지문 개수
    total: int          # 원본 청크의 전체 지문 개수


@runtime_checkable
class Index(Protocol):
    """지문을 받아 유사한 카피레프트 후보를 돌려주는 계약.

    실제 구현(WP-A)도 MockIndex 도 이 시그니처만 지키면 된다.
    """

    def search(self, fp: set[int], top_k: int = 10) -> list[Hit]:
        """지문을 받아 유사한 카피레프트 코드 후보를 반환한다."""
        ...


@dataclass(frozen=True)
class _Entry:
    project: str
    file: str
    symbol: str | None
    license: str
    url: str
    fp: frozenset[int]


def _rank(entries: list[_Entry], fp: set[int], top_k: int) -> list[Hit]:
    """지문과 겹치는 후보를 공유 지문이 많은 순으로 돌려준다 (선형 스캔)."""
    hits = [
        Hit(
            e.project, e.file, e.symbol, e.license, e.url,
            shared=len(fp & e.fp), total=len(e.fp),
        )
        for e in entries
        if fp & e.fp
    ]
    hits.sort(key=lambda h: h.shared, reverse=True)
    return hits[:top_k]


class MockIndex:
    """가짜 인덱스 — 심어둔 코드와 지문이 겹치면 Hit 을 돌려준다.

    실제 코퍼스/DB/LSH 없이, 민수가 `provenire scan` · PR 게이트를
    개발·테스트할 수 있게 하는 것이 목적이다.

        idx = MockIndex()
        idx.add(gpl_like_code, project="acme", file="util.py",
                symbol="elide", license="GPL-3.0-or-later", url="https://...")
        hits = idx.search(Scanner()._fp(suspect_code))

    ⚠️ 저작권 코드를 여기 하드코딩하지 않는다. 테스트는 자체 작성 코드로 심는다.
    """

    def __init__(self, scanner: Scanner | None = None):
        self._entries: list[_Entry] = []
        self._scanner = scanner or Scanner()

    def add(
        self,
        code: str,
        *,
        project: str,
        file: str,
        license: str,
        url: str,
        symbol: str | None = None,
        lang: str | None = None,
        filename: str | None = None,
    ) -> None:
        """코드 한 조각을 인덱스에 심는다 (지문은 자동으로 뜬다)."""
        scanner = Scanner(lang=lang) if lang else self._scanner
        fp = scanner.fingerprint_of(code, filename=filename)
        self._entries.append(
            _Entry(project, file, symbol, license, url, frozenset(fp))
        )

    def search(self, fp: set[int], top_k: int = 10) -> list[Hit]:
        """의심 지문과 겹치는 후보를 공유 지문이 많은 순으로 돌려준다."""
        return _rank(self._entries, fp, top_k)


class FileIndex:
    """디스크(sqlite) 지문 저장소를 로드해 검색하는 실제 인덱스.

        store = FingerprintStore("copyleft.db")   # 코퍼스가 채워둔 지문 DB
        hits = FileIndex(store).search(Scanner()._fp(suspect_code))

    # ponytail: 선형 스캔 — 코퍼스 Top-N(~30개) 규모엔 충분. 지문이 수만을
    #           넘어 느려지면 index/search.py 에 MinHash LSH(datasketch)를 얹는다.
    """

    def __init__(self, store: FingerprintStore):
        self._entries = [
            _Entry(m["project"], m["file"], m["symbol"], m["license"], m["url"], fp)
            for m, fp in store.entries()
        ]

    def search(self, fp: set[int], top_k: int = 10) -> list[Hit]:
        return _rank(self._entries, fp, top_k)
