from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum

from .tokenize import LexicalElement, TokenizeException, expect
from span import Span, SourceCtx

class HexDigit(LexicalElement):
    CHARS = '0123456789abcdef'

    def __init__(self, span: Span, value: int) -> None:
        super().__init__(span)

        self.value = value

    @staticmethod
    def tokenize(ctx: SourceCtx) -> HexDigit:
        ch, span = ctx.pop(1)
        if ch is not None and ch.lower() in HexDigit.CHARS:
            return HexDigit(span, HexDigit.CHARS.index(ch))

        raise TokenizeException("Expected hexadecimal digit", span)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        ch = ctx.peek(1)
        if ch is not None:
            return ch.lower() in HexDigit.CHARS
        return False

# TODO: Octal escape sequence and universal character name

class EscapeSequence(LexicalElement):
    @abstractmethod
    def unescape(self) -> str:
        pass

    @staticmethod
    def tokenize(ctx: SourceCtx) -> EscapeSequence:
        if SimpleEscapeSequence.is_valid(ctx):
            return SimpleEscapeSequence.tokenize(ctx)
        if HexEscapeSequence.is_valid(ctx):
            return HexEscapeSequence.tokenize(ctx)

        raise TokenizeException("Expected escape code", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact("\\")

class SimpleEscape(Enum):
    SINGLE_QUOTE = ("'", "'")
    DOUBLE_QUOTE = ('"', '"')
    QUESTION_MARK = ("?", "?")
    ALERT = ("a", "\a")
    BACKSPACE = ("b", "\b")
    FORM_FEED = ("f", "\f")
    NEW_LINE = ("n", "\n")
    CARRIAGE_RETURN = ("r", "\r")
    HORIZONTAL_TAB = ("t", "\t")
    VERTICAL_TAB = ("v", "\v")

class SimpleEscapeSequence(EscapeSequence):
    def __init__(self, span: Span, esc: SimpleEscape) -> None:
        super().__init__(span)

        self.esc = esc

    @staticmethod
    def tokenize(ctx: SourceCtx) -> SimpleEscapeSequence:
        backslash = expect("\\", ctx)
        for esc in SimpleEscape:
            if ctx.peek_exact(esc.value[0]):
                seq = expect(esc.value[0], ctx)

                return SimpleEscapeSequence(backslash.combine(seq), esc)

        raise TokenizeException("Expected simple escape sequence", backslash)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        if ctx.peek(1) != "\\":
            return False
        for esc in SimpleEscape:
            if ctx.peek_exact("\\" + esc.value[0]):
                return True
        return False

    def unescape(self) -> str:
        return self.esc.value[1]

class HexEscapeSequence(EscapeSequence):
    def __init__(self, span: Span, value: int) -> None:
        super().__init__(span)

        self.value = value

    @staticmethod
    def tokenize(ctx: SourceCtx) -> HexEscapeSequence:
        start = ctx.idx

        backslash_x = expect("\\x", ctx)

        digits = [HexDigit.tokenize(ctx)]

        while HexDigit.is_valid(ctx):
            digits.append(HexDigit.tokenize(ctx))

        value = sum(16 ** (len(digits) - i - 1) * digit.value for i, digit in enumerate(digits))
        return HexEscapeSequence(Span(ctx.source, start, ctx.idx), value)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact("\\x")

    def unescape(self) -> str:
        return chr(self.value)
