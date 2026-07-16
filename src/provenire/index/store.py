"""지문 인덱스의 디스크 저장소 (sqlite, stdlib) — 지문 해시만 저장한다.

⚠️ 저작권 안전 (WP-A DoD): **원본 코드는 저장하지 않는다.**
   저장하는 것은 지문(정수 해시)과 라이선스 메타(project·file·symbol·SPDX·URL)뿐이다.
   지문에서 원본 코드를 복원할 수 없으므로 인덱스 파일 자체는 배포 가능하다.
   (우리가 라이선스를 지키는 도구를 만들면서 GPL 코드를 재배포하면 안 된다.)
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

__all__ = ["FingerprintStore"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id      INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    file    TEXT NOT NULL,
    symbol  TEXT,
    license TEXT NOT NULL,
    url     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fingerprints (
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    hash     INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
"""


class FingerprintStore:
    """카피레프트 코드 조각의 지문 + 메타를 sqlite 에 담는다.

        store = FingerprintStore("copyleft.db")   # 경로 생략 시 :memory:
        store.add(fp, project="qutebrowser", file="utils.py",
                  symbol="elide_filename", license="GPL-3.0-or-later", url="https://...")

    코퍼스 수집기(A-1, 다음 단계)가 이 add() 로 인덱스를 채운다.
    """

    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path)
        self._db.executescript(_SCHEMA)

    def add(
        self,
        fp: set[int],
        *,
        project: str,
        file: str,
        license: str,
        url: str,
        symbol: str | None = None,
    ) -> None:
        """지문 한 벌 + 메타를 저장한다. (원본 코드는 받지도 저장하지도 않는다)"""
        cur = self._db.execute(
            "INSERT INTO entries (project, file, symbol, license, url) VALUES (?, ?, ?, ?, ?)",
            (project, file, symbol, license, url),
        )
        self._db.executemany(
            "INSERT INTO fingerprints (entry_id, hash) VALUES (?, ?)",
            [(cur.lastrowid, h) for h in fp],
        )
        self._db.commit()

    def entries(self) -> Iterator[tuple[dict, frozenset[int]]]:
        """저장된 (메타, 지문) 쌍을 하나씩 돌려준다."""
        rows = self._db.execute(
            "SELECT id, project, file, symbol, license, url FROM entries"
        ).fetchall()
        for eid, project, file, symbol, license, url in rows:
            hashes = self._db.execute(
                "SELECT hash FROM fingerprints WHERE entry_id = ?", (eid,)
            ).fetchall()
            meta = {
                "project": project, "file": file, "symbol": symbol,
                "license": license, "url": url,
            }
            yield meta, frozenset(h for (h,) in hashes)

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

    def common_fingerprints(self, min_count: int) -> frozenset[int]:
        """min_count 개 이상의 서로 다른 조각(entry)에 나타나는 지문 = 관용구.

        여러 무관한 원본에 공통으로 나오는 지문은 표절 신호가 아니라 흔한
        관용구다(getter, 표준 루프·예외 처리 등). 검색에서 이 지문을 빼면
        보일러플레이트끼리 매칭되는 오탐이 줄어든다 (IDF 개념, WP-C).
        """
        rows = self._db.execute(
            "SELECT hash FROM fingerprints "
            "GROUP BY hash HAVING COUNT(DISTINCT entry_id) >= ?",
            (min_count,),
        ).fetchall()
        return frozenset(h for (h,) in rows)

    def close(self) -> None:
        self._db.close()
