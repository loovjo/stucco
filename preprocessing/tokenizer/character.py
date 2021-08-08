from __future__ import annotations
from enum import Enum

from .tokenize import LexicalElement, ProperPPToken, TokenizeException, expect
from .escape import EscapeSequence
from span import Span, SourceStream
from typing import Optional


class CharacterPrefix(Enum):
    U = "u"
    BIG_U = "U"
    L = "L"
    NONE = ""


# Represents both the string-literal and the second variant of header-name
class CharacterLiteral(ProperPPToken):
    def __init__(self, span: Span, prefix: CharacterPrefix, contents: str) -> None:
        super().__init__(span)

        self.prefix = prefix
        self.contents = contents  # Escape sequences escaped

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(prefix={self.prefix.name},contents={self.contents!r})"

    # May throw TokenizeException
    @staticmethod
    def tokenize(inp: SourceStream) -> ProperPPToken:
        start = inp.idx
        prefix: Optional[CharacterPrefix] = None

        for pref in CharacterPrefix:
            if inp.peek_exact(pref.value + "'"):
                prefix = pref
                break

        if prefix is None:
            raise TokenizeException("Expected character", inp.point_span())

        expect(prefix.value + "'", inp)

        contents = ""
        while True:
            if inp.peek_exact("'"):
                inp.pop(1)
                break

            if EscapeSequence.is_valid(inp):
                esc = EscapeSequence.tokenize(inp)
                contents += esc.unescape()
            else:
                ch, _ = inp.pop(1)
                if ch is None:
                    raise TokenizeException("EOF in string literal", inp.point_span())

                contents += ch

        return CharacterLiteral(Span(inp.source, start, inp.idx), prefix, contents)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        for pref in CharacterPrefix:
            if inp.peek_exact(pref.value + "'"):
                return True
        return False
