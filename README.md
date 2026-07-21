# Provenire

**English** · [한국어](https://github.com/4thIS/opensource_contest_provenire/blob/main/README.ko.md)

> **Catch AI-generated code that copied open-source licenses — right in the pull request.**

[![PyPI](https://img.shields.io/pypi/v/provenire.svg)](https://pypi.org/project/provenire/)
[![Downloads](https://img.shields.io/pypi/dm/provenire.svg)](https://pypi.org/project/provenire/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/4thIS/opensource_contest_provenire/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml/badge.svg)](https://github.com/4thIS/opensource_contest_provenire/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)](#roadmap)

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

### Worse: most license tools **cannot even see** this problem

What people call "open-source license scanning" is really **three different jobs**:

| | Representative tools | What it inspects | Catches AI-copied code |
|---|---|---|:--:|
| **A. Dependency scanning (SCA)** | FOSSA · Snyk · ORT · pip-licenses | the **declared package list** (`requirements.txt`, …) | ❌ |
| **B. License-text scanners** | ScanCode · licensee · FOSSology · REUSE | the **license header** in each file | ❌ |
| **C. Code snippet matching** | Black Duck · SCANOSS · **Provenire** | the **similarity of the code itself** | ⭕ |

When an LLM reproduces GPL code, **nothing is added to your dependency list and no license header comes with it.**
A and B have nothing to look at. Only **C** can catch this.

> Existing tools check **what you pulled in.**
> Provenire checks **what you copied.**

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

And **even within group C**, Provenire is currently the only tool that erases identifiers:

| | Normalization | k-gram | Identifiers |
|---|---|---|:--:|
| MOSS (standard config) | strip comments & whitespace | 5 characters | **kept** |
| [SCANOSS](https://github.com/scanoss/wfp/blob/master/README.md) | strip non-alphanumeric characters | 30 characters | **kept** |
| **Provenire** | strip comments + **identifiers → `ID`** | 15 tokens | **erased** |

If names survive into the fingerprint, **renaming breaks the fingerprint.**

---

## It actually works

Suppose an AI reproduced GPL code with **only the variable names changed**:

```console
$ provenire compare ai_output.py gpl_origin.py

  mode              similarity   fingerprints
  ---------------------------------------------
  raw (baseline)        12.0%    3/25      <- Copilot-filter level: below threshold, MISSED
  tokens (default)     100.0%    24/24     <- Provenire: CAUGHT
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
| Comments & docstrings stripped | 100% | **87.5%** |
| **All variable & function names renamed** | **8.8%** (missed) | **100.0%** (caught) |
| Renamed + stripped + reformatted | **8.8%** (missed) | **87.5%** (caught) |
| Unrelated code (negative control) | 0% | **0%** (no false positive) |

The raw engine stays **well under the 30% threshold** once names change (missed), while the token
engine catches **100%** with **0% false positives**.

### Beyond single functions

Provenire chunks code **function by function**, so it catches copyleft even when it is buried in a
larger file — a whole GPL file pasted in, or a single GPL function renamed and mixed into your own
code. On a **9-project copyleft corpus**: **Precision 100% · Recall 90.7% · F1 95.1% · 0 false positives**
(`python benchmarks/evaluate.py`).

> Reproduce it yourself: [`benchmarks/`](https://github.com/4thIS/opensource_contest_provenire/tree/main/benchmarks) · Details: [`benchmarks/RESULTS.md`](https://github.com/4thIS/opensource_contest_provenire/blob/main/benchmarks/RESULTS.md)

### Where this sits in the research

Provenance tracking for LLM-generated code is an active research area. Recent work
([Gurioli et al., *Efficient and Scalable Provenance Tracking for LLM-Generated Code Snippets*, 2026](https://arxiv.org/abs/2605.28510))
solves winnowing's **scalability** problem — a vector-search first stage takes a 10M-snippet corpus
from linear- to logarithmic-time retrieval. That work, however, **keeps identifiers** during
normalization, and models renaming as *"a 20% probability of replacing words longer than three
characters that appear more than twice"* — so **most identifiers survive verbatim.**

Provenire pushes on an **orthogonal axis**: not scale, but **robustness to transformation** —
detection when **every** identifier has been changed. Notably, the semantic chunking that paper
lists as future work (*"semantically meaningful units, such as function bodies … via AST analysis"*)
is **already implemented** here
([`index/chunker.py`](https://github.com/4thIS/opensource_contest_provenire/blob/main/src/provenire/index/chunker.py)).
Conversely, the **Type-3 clones** it leaves open (inserted, deleted, or reordered statements) remain
open for us too — see the [roadmap](#roadmap).

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
      - uses: 4thIS/opensource_contest_provenire/.github/action@v0.1
        with:
          fail-on: true        # fail the check on a match (false = comment only)
```

A match is reported as `file:start-end` plus the name of **your** enclosing function, so you know
exactly which lines to look at:

```
⚠️ Provenire — copyleft-similar code found

  98.2%  src/utils.py:41-70  (sanitize_path)
     ↳ qutebrowser/utils.py :: sanitize_filename  [GPL-3.0-or-later]
```

Line numbers refer to the **original file** even under `--diff`, which only scans added lines.

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
- [x] Language packs — Python · Java · JavaScript · TypeScript
- [x] **Bundled copyleft index** — ships with the package; `scan` works out of the box
- [x] **`provenire scan`** — file scan (function-level chunking) & `--diff` PR gate
- [x] **GitHub Action** — PR comment + failing check ([usage](#github-action))
- [ ] Scale the index (LSH / MinHash) for larger corpora
- [ ] LLM second-pass judgment (idiom vs. structural reproduction)
- [ ] More languages (Go, C++, …) & function-level chunking beyond Python
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
See [`CONTRIBUTING.md`](https://github.com/4thIS/opensource_contest_provenire/blob/main/CONTRIBUTING.md) — `good first issue` welcome.

---

## Contributing

The most valuable contributions right now:

1. **New language packs** (Java, Go, Rust, JS/TS) — `good first issue`
2. **False-positive reports** — boilerplate that gets wrongly flagged
3. **Benchmark cases** — especially code an LLM actually regenerated

See [`CONTRIBUTING.md`](https://github.com/4thIS/opensource_contest_provenire/blob/main/CONTRIBUTING.md).

## License

[Apache-2.0](https://github.com/4thIS/opensource_contest_provenire/blob/main/LICENSE) — patent grant included. Use it freely; keep the attribution.

> **Provenire is not legal advice.** It flags suspicious regions. It does not render a verdict.

---

<sub>Built for the 2026 Open Source Developer Contest (Korea) · Team <b>코드감식반</b> (Lee Woojin · Kim Minsu)</sub>
