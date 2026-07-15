"""언어팩이 핵심 명제를 언어와 무관하게 지키는지 검증한다.

    "이름만 바꾼 재현은 잡고, 무관한 코드는 잡지 않는다."

Python은 test_core.py 가 지킨다. 여기서는 새로 추가한 언어를 지킨다.
"""
from provenire import compare
from provenire.languages import available

# ─────────────────────────── Java ───────────────────────────

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

# 변수·메서드·클래스명만 전부 바꾼 버전 (= AI가 흔히 뱉는 형태)
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

# 무관한 로직 (오탐 방지용)
JAVA_UNRELATED = """
public class Stats {
    public static double mean(int[] values) {
        double total = 0.0;
        int count = 0;
        for (int v : values) {
            total += v;
            count += 1;
        }
        return count == 0 ? 0.0 : total / count;
    }
}
"""


def test_java_is_registered():
    assert "java" in available()


def test_java_renamed_is_detected():
    """★ 이름만 바꾼 Java 재현을 잡아낸다."""
    m = compare(JAVA_RENAMED, JAVA_ORIGIN, lang="java")
    assert m.similarity > 0.9, f"이름 변경 Java 코드를 놓쳤다 (유사도 {m.similarity:.1%})"


def test_java_unrelated_is_not_flagged():
    """무관한 Java 코드는 잡히면 안 된다."""
    m = compare(JAVA_UNRELATED, JAVA_ORIGIN, lang="java")
    assert m.similarity < 0.3, f"무관한 Java 코드를 오탐했다 (유사도 {m.similarity:.1%})"


def test_java_tokens_beat_raw_on_renaming():
    """대조군 — raw 방식(Copilot 필터 수준)은 이름 변경에 무너진다."""
    raw = compare(JAVA_RENAMED, JAVA_ORIGIN, mode="raw", lang="java")
    tok = compare(JAVA_RENAMED, JAVA_ORIGIN, mode="tokens", lang="java")
    assert tok.similarity > raw.similarity, "토큰 정규화가 raw보다 나아야 한다"


def test_java_inferred_from_extension():
    """lang 없이 .java 확장자만으로도 언어를 추론한다."""
    m = compare(JAVA_RENAMED, JAVA_ORIGIN, filename="PathHelper.java")
    assert m.similarity > 0.9


# ─────────────────────────── JavaScript ───────────────────────────

JS_ORIGIN = """
function elideFilename(filename, length) {
    const marker = "...";
    if (length < marker.length) {
        throw new Error("too short");
    }
    if (filename.length <= length) {
        return filename;
    }
    const toElide = filename.length - length + marker.length;
    const left = Math.floor((filename.length - toElide) / 2);
    return filename.substring(0, left) + marker;
}
"""

# 변수·함수명만 전부 바꾼 버전 (= AI가 흔히 뱉는 형태)
JS_RENAMED = """
function truncatePath(pathStr, maxLen) {
    const dots = "...";
    if (maxLen < dots.length) {
        throw new Error("too short");
    }
    if (pathStr.length <= maxLen) {
        return pathStr;
    }
    const cut = pathStr.length - maxLen + dots.length;
    const head = Math.floor((pathStr.length - cut) / 2);
    return pathStr.substring(0, head) + dots;
}
"""

JS_UNRELATED = """
function mean(values) {
    let total = 0.0;
    let count = 0;
    for (const v of values) {
        total += v;
        count += 1;
    }
    return count === 0 ? 0.0 : total / count;
}
"""


def test_javascript_is_registered():
    assert "javascript" in available()


def test_javascript_renamed_is_detected():
    """★ 이름만 바꾼 JS 재현을 잡아낸다."""
    m = compare(JS_RENAMED, JS_ORIGIN, lang="javascript")
    assert m.similarity > 0.9, f"이름 변경 JS 코드를 놓쳤다 (유사도 {m.similarity:.1%})"


def test_javascript_unrelated_is_not_flagged():
    """무관한 JS 코드는 잡히면 안 된다."""
    m = compare(JS_UNRELATED, JS_ORIGIN, lang="javascript")
    assert m.similarity < 0.3, f"무관한 JS 코드를 오탐했다 (유사도 {m.similarity:.1%})"


def test_javascript_inferred_from_extension():
    """lang 없이 .js 확장자만으로도 언어를 추론한다."""
    m = compare(JS_RENAMED, JS_ORIGIN, filename="pathHelper.js")
    assert m.similarity > 0.9


# ─────────────────────────── TypeScript ───────────────────────────

TS_ORIGIN = """
function elideFilename(filename: string, length: number): string {
    const marker: string = "...";
    if (length < marker.length) {
        throw new Error("too short");
    }
    if (filename.length <= length) {
        return filename;
    }
    const toElide: number = filename.length - length + marker.length;
    const left: number = Math.floor((filename.length - toElide) / 2);
    return filename.substring(0, left) + marker;
}
"""

# 변수·함수명만 전부 바꾼 버전 (타입 애노테이션은 그대로 = 구조)
TS_RENAMED = """
function truncatePath(pathStr: string, maxLen: number): string {
    const dots: string = "...";
    if (maxLen < dots.length) {
        throw new Error("too short");
    }
    if (pathStr.length <= maxLen) {
        return pathStr;
    }
    const cut: number = pathStr.length - maxLen + dots.length;
    const head: number = Math.floor((pathStr.length - cut) / 2);
    return pathStr.substring(0, head) + dots;
}
"""

TS_UNRELATED = """
function mean(values: number[]): number {
    let total: number = 0.0;
    let count: number = 0;
    for (const v of values) {
        total += v;
        count += 1;
    }
    return count === 0 ? 0.0 : total / count;
}
"""


def test_typescript_is_registered():
    assert "typescript" in available()


def test_typescript_renamed_is_detected():
    """★ 이름만 바꾼 TS 재현을 잡아낸다 (타입 애노테이션은 구조로 보존)."""
    m = compare(TS_RENAMED, TS_ORIGIN, lang="typescript")
    assert m.similarity > 0.9, f"이름 변경 TS 코드를 놓쳤다 (유사도 {m.similarity:.1%})"


def test_typescript_unrelated_is_not_flagged():
    """무관한 TS 코드는 잡히면 안 된다."""
    m = compare(TS_UNRELATED, TS_ORIGIN, lang="typescript")
    assert m.similarity < 0.3, f"무관한 TS 코드를 오탐했다 (유사도 {m.similarity:.1%})"


def test_typescript_inferred_from_extension():
    """lang 없이 .ts 확장자만으로도 언어를 추론한다."""
    m = compare(TS_RENAMED, TS_ORIGIN, filename="pathHelper.ts")
    assert m.similarity > 0.9
