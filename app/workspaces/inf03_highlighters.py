"""Syntax highlighters used by the INF.03 code editors."""

from __future__ import annotations

from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat


class _SimpleHighlighter(QSyntaxHighlighter):
    """Highlight keywords, strings, and line comments for one language."""

    comment_markers: tuple[str, ...] = ("//", "#", "--")

    def __init__(self, document, keywords: tuple[str, ...]) -> None:
        super().__init__(document)
        self._keywords = keywords

    @staticmethod
    def _keyword_format() -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#af52de"))
        fmt.setFontWeight(600)
        return fmt

    @staticmethod
    def _string_format() -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#34c759"))
        return fmt

    @staticmethod
    def _comment_format() -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#8e8e93"))
        fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt API name
        self._highlight(text)

    def _highlight(self, text: str) -> None:
        self._set_format_for_delimited(text, '"', self._string_format())
        self._set_format_for_delimited(text, "'", self._string_format())

        for marker in self.comment_markers:
            idx = text.find(marker)
            if idx >= 0:
                self.setFormat(idx, len(text) - idx, self._comment_format())

        lowered = text.lower()
        for keyword in self._keywords:
            start = 0
            keyword_lower = keyword.lower()
            while True:
                pos = lowered.find(keyword_lower, start)
                if pos < 0:
                    break
                left_ok = pos == 0 or not text[pos - 1].isalnum()
                right = pos + len(keyword_lower)
                right_ok = right >= len(text) or not text[right].isalnum()
                if left_ok and right_ok:
                    self.setFormat(pos, len(keyword_lower), self._keyword_format())
                start = right

    def _set_format_for_delimited(
        self, text: str, quote: str, fmt: QTextCharFormat
    ) -> None:
        pos = 0
        while True:
            start = text.find(quote, pos)
            if start < 0:
                return
            end = text.find(quote, start + 1)
            if end < 0:
                self.setFormat(start, len(text) - start, fmt)
                return
            self.setFormat(start, end - start + 1, fmt)
            pos = end + 1


class SqlHighlighter(_SimpleHighlighter):
    """SQL keyword set covering MySQL 8 and standard SQL."""

    comment_markers = ("--",)

    def __init__(self, document) -> None:
        super().__init__(
            document,
            (
                "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES",
                "UPDATE", "SET", "DELETE", "JOIN", "INNER", "LEFT",
                "RIGHT", "OUTER", "ON", "AS", "AND", "OR", "NOT", "NULL",
                "CREATE", "TABLE", "DROP", "ALTER", "INDEX", "PRIMARY",
                "KEY", "FOREIGN", "REFERENCES", "DISTINCT", "ORDER",
                "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "UNION",
                "ALL", "CASE", "WHEN", "THEN", "ELSE", "END", "IN",
                "IS", "LIKE", "BETWEEN", "EXISTS", "COUNT", "SUM",
                "AVG", "MIN", "MAX",
            ),
        )


class PhpHighlighter(_SimpleHighlighter):
    """PHP keyword set covering the INF.03 syllabus."""

    comment_markers = ("//", "#")

    def __init__(self, document) -> None:
        super().__init__(
            document,
            (
                "echo", "if", "else", "elseif", "while", "for", "foreach",
                "function", "return", "class", "public", "private",
                "protected", "static", "new", "use", "namespace",
                "require", "require_once", "include", "include_once",
                "true", "false", "null", "and", "or", "xor",
                "try", "catch", "finally", "throw", "match",
                "switch", "case", "default", "break", "continue",
            ),
        )


class HtmlHighlighter(_SimpleHighlighter):
    """HTML tag highlighter."""

    comment_markers = ()

    def __init__(self, document) -> None:
        super().__init__(document, ())
        self._tag_format = QTextCharFormat()
        self._tag_format.setForeground(QColor("#ff9500"))

    def _highlight(self, text: str) -> None:
        super()._highlight(text)
        pos = 0
        while True:
            start = text.find("<", pos)
            if start < 0:
                return
            end = text.find(">", start)
            if end < 0:
                self.setFormat(start, len(text) - start, self._tag_format)
                return
            self.setFormat(start, end - start + 1, self._tag_format)
            pos = end + 1


class CssHighlighter(_SimpleHighlighter):
    """CSS selector, property, and value highlighter."""

    comment_markers = ()

    def __init__(self, document) -> None:
        super().__init__(document, ())
        self._selector_format = QTextCharFormat()
        self._selector_format.setForeground(QColor("#ff9500"))
        self._property_format = QTextCharFormat()
        self._property_format.setForeground(QColor("#5e5ce6"))

    def _highlight(self, text: str) -> None:
        super()._highlight(text)
        stripped = text.lstrip()
        offset = len(text) - len(stripped)
        if stripped.startswith("/*"):
            end = stripped.find("*/", 2)
            length = len(stripped) if end < 0 else end + 2
            self.setFormat(offset, length, self._comment_format())
            return

        if "{" in text and not text.lstrip().startswith("@"):
            selector_end = text.find("{")
            self.setFormat(0, selector_end, self._selector_format)

        property_start = text.find("{") + 1 if "{" in text else 0
        while True:
            colon = text.find(":", property_start)
            if colon < 0:
                return
            property_name = text[property_start:colon].strip()
            property_offset = text.find(property_name, property_start, colon)
            if property_name and property_offset >= 0:
                self.setFormat(
                    property_offset,
                    len(property_name),
                    self._property_format,
                )
            property_start = colon + 1
