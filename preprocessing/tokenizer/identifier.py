from __future__ import annotations
from typing import Optional
import unicodedata
from enum import Enum

from .tokenize import LexicalElement, ProperPPToken, TokenizeException
from .escape import HexDigit
from span import Span, SourceStream


class KeywordType(Enum):
    ALIGNOF = "alignof"
    AUTO = "auto"
    BREAK = "break"
    CASE = "case"
    CHAR = "char"
    CONST = "const"
    CONTINUE = "continue"
    DEFAULT = "default"
    DO = "do"
    DOUBLE = "double"
    ELSE = "else"
    ENUM = "enum"
    EXTERN = "extern"
    FLOAT = "float"
    FOR = "for"
    GOTO = "goto"
    IF = "if"
    INLINE = "inline"
    INT = "int"
    LONG = "long"
    REGISTER = "register"
    RESTRICT = "restrict"
    RETURN = "return"
    SHORT = "short"
    SIGNED = "signed"
    SIZEOF = "sizeof"
    STATIC = "static"
    STRUCT = "struct"
    SWITCH = "switch"
    TYPEDEF = "typedef"
    UNION = "union"
    UNSIGNED = "unsigned"
    VOID = "void"
    VOLATILE = "volatile"
    WHILE = "while"
    ALIGNAS = "_Alignas"
    ATOMIC = "_Atomic"
    BOOL = "_Bool"
    COMPLEX = "_Complex"
    GENERIC = "_Generic"
    IMAGINARY = "_Imaginary"
    NORETURN = "_Noreturn"
    STATIC_ASSERT = "_Static_assert"
    THREAD_LOCAL = "_Thread_local"


class UniversalCharacterName(LexicalElement):
    def __init__(self, span: Span, value: int):
        super().__init__(span)
        self.value = value

    @staticmethod
    def tokenize(inp: SourceStream) -> UniversalCharacterName:
        esc = inp.pop_exact("\\u")
        Esc = inp.pop_exact("\\U")

        if esc is not None:
            _, escspan = esc
            hd1 = HexDigit.tokenize(inp)
            hd2 = HexDigit.tokenize(inp)
            return UniversalCharacterName(
                escspan.combine(hd2.span), (hd1.value << 4) + hd2.value
            )

        if Esc is not None:
            _, escspan = Esc
            hd1 = HexDigit.tokenize(inp)
            hd2 = HexDigit.tokenize(inp)
            hd3 = HexDigit.tokenize(inp)
            hd4 = HexDigit.tokenize(inp)
            return UniversalCharacterName(
                escspan.combine(hd2.span),
                (hd1.value << 12) + (hd2.value << 8) + (hd3.value << 4) + hd4.value,
            )

        raise TokenizeException("Expected UCN (\\u__ or \\U____)", inp.point_span())

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return inp.peek_exact("\\u") or inp.peek_exact("\\U")


def is_identifier_ch(ch: Optional[str], can_be_digit: bool) -> bool:
    if ch is None:
        return False

    if ch == "_":
        return True

    cat = unicodedata.category(ch)
    if cat[0] == "L":
        return True

    if can_be_digit:
        if cat[0] == "N":
            return True

    return False


class Identifier(ProperPPToken):
    def __init__(
        self, span: Span, identifier: str
    ):  # identifier has universal names expanded
        super().__init__(span)

        self.identifier = identifier

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.identifier})"

    # May return a Keyword if appropriate
    @staticmethod
    def tokenize(inp: SourceStream) -> ProperPPToken:
        start = inp.idx

        identifier = ""
        if is_identifier_ch(inp.peek(1), False):
            identifier, _ = inp.pop(1)  # type: ignore # we know ctx.pop(1) must be valid
        elif UniversalCharacterName.is_valid(inp):
            identifier += chr(UniversalCharacterName.tokenize(inp).value)
        else:
            raise TokenizeException("Expected identifier", inp.point_span())

        while True:
            if is_identifier_ch(inp.peek(1), True):
                ch, _ = inp.pop(1)
                identifier += ch  # type: ignore # we know ctx.pop(1) must be valid
            elif UniversalCharacterName.is_valid(inp):
                identifier += chr(UniversalCharacterName.tokenize(inp).value)
            else:
                break

        span = Span(inp.source, start, inp.idx)

        for kw in sorted(list(KeywordType), key=lambda x: len(x.value), reverse=True):
            if kw.value == identifier:
                return Keyword(span, kw)

        return Identifier(span, identifier)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return is_identifier_ch(inp.peek(1), False) or UniversalCharacterName.is_valid(
            inp
        )


class Keyword(Identifier):
    def __init__(self, span: Span, ty: KeywordType) -> None:
        super().__init__(span, ty.value)

        self.ty = ty

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.ty})"

    @staticmethod
    def tokenize(inp: SourceStream) -> Keyword:
        x = Identifier.tokenize(inp)
        if isinstance(x, Keyword):
            return x

        raise TokenizeException("Expected keyword", x.span)

    # Not very efficient, but will never be called in practice
    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        if Identifier.is_valid(inp):
            i = Identifier.tokenize(inp)
            return isinstance(i, Keyword)
        return False
