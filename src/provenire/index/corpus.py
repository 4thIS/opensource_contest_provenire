"""코퍼스 수집기 (WP-A: A-1 수집 + A-2 청킹) — 인덱스에 "무엇을 담을까"를 채운다.

파이프라인:
    시드 URL 목록  ──fetch──▶  카피레프트 원본  ──chunk──▶  함수 단위 조각
                                                              │
                                          Scanner 로 지문 ◀────┘
                                                              │
                                          FingerprintStore.add  ─▶  copyleft.db

⚠️ 저작권 (§4):
    - GPL 원본은 **런타임에 내려받고**, 저장소에 커밋하지 않는다. (캐시는 .gitignore)
    - DB엔 지문(해시)과 메타만 들어간다. 원본 코드는 저장하지 않는다. (store.py 참조)

지금은 착수 단계다:
    - 시드는 큐레이션된 소수의 URL (Top-N 자동 선정은 다음).
    - Python 은 ast 로 함수 단위 청킹, 그 외 언어는 파일 단위 fallback.

인덱스 빌드 (배포용 `data/copyleft.db` 를 갱신할 때):

    python -m provenire.index.corpus              # → data/copyleft.db
    python -m provenire.index.corpus 다른경로.db   # → 지정 경로

    # ponytail: 빌드된 DB를 저장소에 커밋해 배포한다(지문 해시뿐이라 저작권 안전).
    #           시드를 바꾸거나 upstream 코드가 변하면 다시 빌드해 커밋한다.
    #           DB가 수 MB를 넘어가면 그때 GitHub Release 자산으로 옮긴다.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..core.matcher import Scanner
from .chunker import Chunk, iter_functions
from .store import FingerprintStore

__all__ = ["CorpusSource", "SOURCES", "chunk", "fetch", "build_index"]

_CACHE = Path(__file__).parent / "_corpus_cache"

@dataclass(frozen=True)
class CorpusSource:
    """인덱싱할 카피레프트 소스 한 건 (메타데이터 — 코드가 아니므로 커밋 가능)."""

    project: str
    file: str
    license: str   # SPDX
    url: str       # raw 소스 URL
    lang: str = "python"


def _gh(project: str, license: str, repo: str, branch: str, path: str) -> CorpusSource:
    """GitHub raw URL 로 CorpusSource 를 만든다 (시드 목록을 짧게 유지)."""
    return CorpusSource(
        project=project, file=path, license=license,
        url=f"https://raw.githubusercontent.com/{repo}/{branch}/{path}",
    )


# 큐레이션 시드 — 실제 카피레프트 프로젝트의 파일 주소 (코드가 아니다).
#
# 라이선스(SPDX)와 파일 경로는 **GitHub API 로 실재를 확인**했다 (추측 아님).
# 카피레프트가 아닌 후보(sqlmap·fail2ban·borg·mitmproxy 등)는 탐색 단계에서 제외됐다.
# GPL-2.0 · GPL-3.0 · AGPL-3.0 을 고루 담아 라이선스 다양성을 확보한다.
_REPOS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("qutebrowser", "GPL-3.0-or-later", "qutebrowser/qutebrowser", "main", (
        "qutebrowser/utils/utils.py",
        "qutebrowser/utils/urlutils.py",
        "qutebrowser/api/cmdutils.py",
        "qutebrowser/completion/models/miscmodels.py",
        "qutebrowser/components/misccommands.py",
    )),
    ("ansible", "GPL-3.0", "ansible/ansible", "devel", (
        "lib/ansible/_internal/_errors/_error_utils.py",
        "lib/ansible/_internal/_templating/_jinja_common.py",
        "lib/ansible/cli/arguments/option_helpers.py",
    )),
    ("OctoPrint", "AGPL-3.0", "OctoPrint/OctoPrint", "dev", (
        "src/octoprint/filemanager/storage/common.py",
        "src/octoprint/filemanager/util.py",
        "src/octoprint/server/util/__init__.py",
    )),
    ("searxng", "AGPL-3.0", "searxng/searxng", "master", (
        "searx/utils.py",
        "searx/webutils.py",
        "searx/engines/wikicommons.py",
    )),
    ("Radicale", "GPL-3.0", "Kozea/Radicale", "master", (
        "radicale/httputils.py",
        "radicale/pathutils.py",
        "radicale/utils.py",
    )),
    ("ranger", "GPL-3.0", "ranger/ranger", "master", (
        "ranger/api/commands.py",
        "ranger/container/bookmarks.py",
        "ranger/ext/shutil_generatorized.py",
    )),
    ("buildbot", "GPL-2.0", "buildbot/buildbot", "master", (
        "master/buildbot/pbutil.py",
        "master/buildbot/reporters/utils.py",
        "master/buildbot/reporters/generators/utils.py",
    )),
    ("weblate", "GPL-3.0", "WeblateOrg/weblate", "main", (
        "weblate/accounts/utils.py",
        "weblate/auth/utils.py",
        "weblate/checks/fluent/utils.py",
    )),
    ("gramps", "GPL-2.0", "gramps-project/gramps", "master", (
        "gramps/gen/db/utils.py",
        "gramps/gen/lib/json_utils.py",
        "gramps/gen/db/conversion_tools/conversion_21.py",
    )),
)

SOURCES: tuple[CorpusSource, ...] = tuple(
    _gh(project, lic, repo, branch, path)
    for project, lic, repo, branch, paths in _REPOS
    for path in paths
)


def fetch(url: str) -> str:
    """URL 을 내려받는다 (캐시됨). 캐시엔 원본이 들어가므로 .gitignore 처리돼 있다."""
    key = hashlib.md5(url.encode("utf-8")).hexdigest()
    cached = _CACHE / key
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    src = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")  # noqa: S310
    _CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(src, encoding="utf-8")
    return src


def chunk(code: str, lang: str = "python") -> list[Chunk]:
    """인덱싱용 청킹 — 코드를 Chunk(심볼·조각·줄범위) 목록으로 쪼갠다.

    Python 은 함수 단위(ast). 그 외 언어는 파일 전체를 한 조각으로 (fallback).
    함수 단위 매칭이 정확도에 중요하다 — 큰 파일에서 작은 함수만 베낀 경우를 잡는다.

    스캔(의심 코드)용 청킹은 chunker.chunk_for_scan 을 쓴다 — 함수 로직은 공유하되
    fallback 이 파일 전체가 아니라 슬라이딩 윈도우다. (§2 참조)
    """
    whole = [Chunk(None, code, 1, max(len(code.splitlines()), 1))]
    if lang != "python":
        return whole   # ponytail: 비-Python 함수 청킹은 다음 단계(tree-sitter 등)
    try:
        return iter_functions(code)      # 함수가 없으면 빈 리스트 (기존 동작 유지)
    except SyntaxError:
        return whole


def build_index(
    sources: tuple[CorpusSource, ...] | list[CorpusSource],
    store: FingerprintStore,
    fetch: Callable[[str], str] = fetch,
) -> FingerprintStore:
    """시드를 내려받아 청킹하고 지문을 떠서 store 에 채운다.

    fetch 를 주입할 수 있다 → 테스트는 네트워크 없이 가짜 fetch 를 쓴다.
    한 소스가 실패해도(네트워크 등) 건너뛰고 나머지를 계속한다.
    """
    for src in sources:
        try:
            code = fetch(src.url)
        except Exception:   # noqa: BLE001 - 네트워크 실패는 건너뛴다
            continue
        scanner = Scanner(lang=src.lang)
        for c in chunk(code, src.lang):
            fp = scanner.fingerprint_of(c.code)
            if fp:   # 너무 짧아 지문이 안 나오는 조각은 버린다
                store.add(
                    fp, project=src.project, file=src.file,
                    symbol=c.symbol, license=src.license, url=src.url,
                )
    return store


if __name__ == "__main__":  # pragma: no cover - 실제 네트워크 빌드
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/copyleft.db")
    out.parent.mkdir(parents=True, exist_ok=True)
    db = FingerprintStore(str(out))
    build_index(SOURCES, db)
    print(f"인덱싱 완료: {len(db)} 청크 / {len(SOURCES)} 소스  →  {out}")
    db.close()
