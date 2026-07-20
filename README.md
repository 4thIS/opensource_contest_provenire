# Provenire

**English** · [한국어](README.ko.md)

> **Catch AI-generated code that copied open-source licenses — right in the pull request.**

[![PyPI](https://img.shields.io/pypi/v/provenire.svg)](https://pypi.org/project/provenire/)
[![Downloads](https://img.shields.io/pypi/dm/provenire.svg)](https://pypi.org/project/provenire/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml/badge.svg)](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#roadmap)

*provenire* — Latin, *"to originate."* It traces where your code **came from**.

---

## The problem

Copilot, Cursor, and Claude were **trained on GPL and AGPL repositories**.

They reproduce that code — sometimes verbatim, **without attribution**. The industry now calls this
**"AI license laundering."**

If copyleft code slips into your codebase, you may be obligated to **open-source your entire product.**
Companies have already had to **rewrite whole codebases** because of this.

And yet every tool that detects it — **FOSSA, Snyk, Black Duck** — is **commercial**.
Students, individuals, and small teams are left **defenseless**.

**Provenire opens that door.**

---

## The key insight

GitHub Copilot's `public code filter` only blocks matches that are **nearly character-identical**.

**Rename the variables, and it sails right through.**

Provenire **anonymizes identifiers before fingerprinting**:

```
original:  def elide_filename(filename, length):  ->  def ID(ID, ID):
AI output: def truncate_path(path_str, max_len):  ->  def ID(ID, ID):
                                                       ^ the fingerprints become identical
```

**Erase the names. Keep the structure** (keywords, operators, control flow). Then fingerprint it.

→ **No matter how the names change, we still catch it.**

---

## It actually works

Suppose an AI reproduced GPL code with **only the variable names changed**:

```console
$ provenire compare ai_output.py gpl_origin.py

  mode              similarity   fingerprints
  ---------------------------------------------
  raw (baseline)         2.1%    1/48      <- Copilot-filter level: MISSED
  tokens (default)     100.0%    21/21     <- Provenire: CAUGHT
  ---------------------------------------------

  [!] Suspected copy — 100.0% similarity (threshold 30%)
```

Exit code `1` → **drop it straight into CI as a PR gate.**

---

## Verified results

Benchmarked against **real GPL-3.0 code** (`qutebrowser/utils/utils.py`).

| Transformation | raw (baseline) | **tokens (Provenire)** |
|---|:--:|:--:|
| Verbatim copy | 100% | **100%** |
| Comments & docstrings stripped | 100% | **86.4%** |
| **All variable & function names renamed** | **0.0%** (missed) | **100.0%** (caught) |
| Renamed + stripped + reformatted | **0.0%** (missed) | **86.4%** (caught) |
| Unrelated code (negative control) | 0% | **0%** (no false positive) |

Across `k = 10…30`, the token engine catches **100%** with **0% false positives**,
while the raw engine **collapses to 0%**.

> Reproduce it yourself: [`benchmarks/`](benchmarks/) · Details: [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md)

---

## Install

```bash
pip install provenire
```

## Usage

```bash
provenire compare <suspect> <origin>   # similarity between two files
provenire fingerprint <file>           # preview the fingerprint
provenire scan <path>                  # scan files — bundled copyleft index, works out of the box
provenire scan --diff <ref>            # scan only the code added since <ref> (PR gate)
provenire scan <path> --index <db>     # ...or point at your own fingerprint DB
```

```python
from provenire import compare

m = compare(ai_generated_code, gpl_source)
if m.is_suspicious:
    print(f"Suspected copy: {m.similarity:.1%}")

# other languages
compare(java_a, java_b, lang="java")
```

---

## GitHub Action

Gate every pull request automatically. Provenire scans **only the code added in the PR**
(`scan --diff`), comments on the PR when a copyleft match is found, and can fail the check.

```yaml
# .github/workflows/provenire.yml
name: Provenire
on: pull_request
permissions:
  contents: read
  pull-requests: write        # required to comment on the PR
jobs:
  license-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0       # required — the base commit must exist for the diff
      - uses: 4thIS/opensource_contest_provenire/.github/action@main
        with:
          fail-on: true        # fail the check on a match (false = comment only)
```

The copyleft fingerprint index ships **inside the package**, so it works with no extra setup.
Point at your own DB with `index: path/to/your.db` if you build one.

Notes:
- **`fetch-depth: 0` is required.** The default shallow checkout has no base commit, so `--diff` cannot compute the added lines.
- **Fork PRs** run with a read-only token, so the comment step is skipped; the failing check still signals the problem.
- **Start with `fail-on: false`.** Let it comment for a week before it blocks anyone — that is how we found (and fixed) a false-positive class in our own repo.

---

## Roadmap

- [x] Winnowing fingerprint engine
- [x] Token normalization (identifier anonymization) — **the core moat**
- [x] Similarity judgment (containment)
- [x] CLI (`compare` / `fingerprint`)
- [x] Pluggable language packs
- [x] **Bundled copyleft index** — ships with the package; `scan` works out of the box
- [ ] Scale the index (LSH / MinHash) for larger corpora
- [x] **`provenire scan`** — file scan & `--diff` PR gate
- [x] **GitHub Action** — PR comment + failing check ([usage](#github-action))
- [ ] LLM second-pass judgment (idiom vs. structural reproduction)
- [ ] More languages (Java, JS/TS, Go, C++)
- [ ] pre-commit hook

---

## How it works

```
PR diff (added lines)
   |
   |-- 1. Normalize     strip comments -> tokenize -> anonymize identifiers to ID
   |-- 2. Fingerprint   k-gram hashes -> sliding-window minimum (winnowing)
   |-- 3. Index lookup  query the copyleft fingerprint database
   |-- 4. Judge         containment = |shared fingerprints| / |suspect fingerprints|
   `-- 5. Report        origin link · license · risk level
```

Algorithm: Schleimer, Wilkerson & Aiken,
*"Winnowing: Local Algorithms for Document Fingerprinting"* (SIGMOD 2003) — the basis of MOSS.

---

## Adding a language

Language packs are **one file**. You never touch the core.

```python
# src/provenire/languages/java.py
from pygments.token import Token
from .base import LanguageSpec

SPEC = LanguageSpec(
    name="java",
    lexer="java",
    extensions=(".java",),
    keep=(Token.Keyword, Token.Keyword.Type),   # types are structure
)
```

Register it in `languages/__init__.py`, add a test, done.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) — `good first issue` welcome.

---

## Contributing

The most valuable contributions right now:

1. **New language packs** (Java, Go, Rust, JS/TS) — `good first issue`
2. **False-positive reports** — boilerplate that gets wrongly flagged
3. **Benchmark cases** — especially code an LLM actually regenerated

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

[Apache-2.0](LICENSE) — patent grant included. Use it freely; keep the attribution.

> **Provenire is not legal advice.** It flags suspicious regions. It does not render a verdict.

---

<sub>Built for the 2026 Open Source Developer Contest (Korea) · Team <b>코드감식반</b> (Lee Woojin · Kim Minsu)</sub>
