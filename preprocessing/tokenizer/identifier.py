from __future__ import annotations
from typing import Optional
import unicodedata
from enum import Enum

from .tokenize import LexicalElement, ProperPPToken, TokenizeException
from .escape import HexDigit
from span import Span, SourceCtx

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
    def tokenize(ctx: SourceCtx) -> UniversalCharacterName:
        esc = ctx.pop_exact("\\u")
        Esc = ctx.pop_exact("\\U")

        if esc is not None:
            _, escspan = esc
            hd1 = HexDigit.tokenize(ctx)
            hd2 = HexDigit.tokenize(ctx)
            return UniversalCharacterName(escspan.combine(hd2.span), (hd1.value << 4) + hd2.value)

        if Esc is not None:
            _, escspan = Esc
            hd1 = HexDigit.tokenize(ctx)
            hd2 = HexDigit.tokenize(ctx)
            hd3 = HexDigit.tokenize(ctx)
            hd4 = HexDigit.tokenize(ctx)
            return UniversalCharacterName(escspan.combine(hd2.span), (hd1.value << 12) + (hd2.value << 8) + (hd3.value << 4) + hd4.value)

        raise TokenizeException("Expected UCN (\\u__ or \\U____)", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact("\\u") or ctx.peek_exact("\\U")

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
    def __init__(self, span: Span, identifier: str): # identifier has universal names expanded
        super().__init__(span)

        self.identifier = identifier

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.identifier})"

    # May return a Keyword if appropriate
    @staticmethod
    def tokenize(ctx: SourceCtx) -> ProperPPToken:
        start = ctx.idx

        identifier = ""
        if is_identifier_ch(ctx.peek(1), False):
            identifier, _ = ctx.pop(1) # type: ignore # we know ctx.pop(1) must be valid
        elif UniversalCharacterName.is_valid(ctx):
            identifier += chr(UniversalCharacterName.tokenize(ctx).value)
        else:
            raise TokenizeException("Expected identifier", ctx.point_span())

        while True:
            if is_identifier_ch(ctx.peek(1), True):
                ch, _ = ctx.pop(1)
                identifier += ch # type: ignore # we know ctx.pop(1) must be valid
            elif UniversalCharacterName.is_valid(ctx):
                identifier += chr(UniversalCharacterName.tokenize(ctx).value)
            else:
                break

        span = Span(ctx.source, start, ctx.idx)

        for kw in KeywordType:
            if kw.value == identifier:
                return Keyword(span, kw)

        return Identifier(span, identifier)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return is_identifier_ch(ctx.peek(1), False) or UniversalCharacterName.is_valid(ctx)

class Keyword(Identifier):
    def __init__(self, span: Span, ty: KeywordType) -> None:
        super().__init__(span, ty.value)

        self.ty = ty

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.ty})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Keyword:
        x = Identifier.tokenize(ctx)
        if isinstance(x, Keyword):
            return x

        raise TokenizeException("Expected keyword", x.span)

    # Not very efficient, but will never be called in practice
    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        if Identifier.is_valid(ctx):
            i = Identifier.tokenize(ctx)
            return isinstance(i, Keyword)
        return False
