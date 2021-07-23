from __future__ import annotations
from enum import Enum

from .tokenize import LexicalElement, PPToken, TokenizeException, expect
from .escape import EscapeSequence
from span import Span, SourceCtx
from typing import Optional

class CharacterPrefix(Enum):
    U = "u"
    BIG_U = "U"
    L = "L"
    NONE = ""

# Represents both the string-literal and the second variant of header-name
class CharacterLiteral(PPToken):
    def __init__(self, span: Span, prefix: CharacterPrefix, contents: str) -> None:
        super().__init__(span)

        self.prefix = prefix
        self.contents = contents # Escape sequences escaped

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix={self.prefix.name},contents={self.contents!r})"

    # May throw TokenizeException
    @staticmethod
    def tokenize(ctx: SourceCtx) -> PPToken:
        start = ctx.idx
        prefix: Optional[CharacterPrefix] = None

        for pref in CharacterPrefix:
            if ctx.peek_exact(pref.value + "'"):
                prefix = pref
                break

        if prefix is None:
            raise TokenizeException("Expected character", ctx.point_span())

        expect(prefix.value + "'", ctx)

        contents = ""
        while True:
            if ctx.peek_exact("'"):
                ctx.pop(1)
                break

            if EscapeSequence.is_valid(ctx):
                esc = EscapeSequence.tokenize(ctx)
                contents += esc.unescape()
            else:
                ch, _ = ctx.pop(1)
                if ch is None:
                    raise TokenizeException("EOF in string literal", ctx.point_span())

                contents += ch

        return CharacterLiteral(Span(ctx.source, start, ctx.idx), prefix, contents)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        for pref in CharacterPrefix:
            if ctx.peek_exact(pref.value + "'"):
                return True
        return False

