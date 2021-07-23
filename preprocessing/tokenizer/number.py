from __future__ import annotations
from typing import List, Optional, Union

from .tokenize import LexicalElement, ProperPPToken, TokenizeException, expect
from .escape import EscapeSequence
from .identifier import is_identifier_ch
from span import Span, SourceCtx

class Digit(LexicalElement):
    CHARS = '0123456789'

    def __init__(self, span: Span, value: int) -> None:
        super().__init__(span)

        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Digit:
        ch, span = ctx.pop(1)
        if ch is not None and ch.lower() in Digit.CHARS:
            return Digit(span, Digit.CHARS.index(ch))

        raise TokenizeException("Expected hexadecimal digit", span)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        ch = ctx.peek(1)
        if ch is not None:
            return ch.lower() in Digit.CHARS
        return False

class Exponent(LexicalElement):
    def __init__(self, span: Span, is_e: bool, is_capital: bool, is_plus: bool) -> None:
        super().__init__(span)

        self.is_e = is_e
        self.is_capital = is_capital
        self.is_plus = is_plus

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.span.contents()})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Exponent:
        exp, expspan = ctx.pop(1)
        sign, signspan = ctx.pop(1)

        if exp is None or exp.lower() not in 'ep':
            raise TokenizeException("Expected exponent", expspan)
        if sign is None or sign not in '+-':
            raise TokenizeException("Expected plus or minus", expspan)

        return Exponent(expspan.combine(signspan), exp.lower() == "e", exp == exp.upper(), sign == '+')

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        x = ctx.peek(2)
        if x is None:
            return False
        return x[0].lower() in "ep" and x[1] in '+-'

class Dot(LexicalElement):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Dot:
        dot, span = ctx.pop(1)
        if dot != ".":
            raise TokenizeException("Expected dot", span)
        return Dot(span)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact(".")


class PPNumber(ProperPPToken):
    def __init__(self, span: Span, number_content: List[Union[Digit, Exponent, Dot, str]]) -> None:
        super().__init__(span)

        self.number_content = number_content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.number_content!r})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> PPNumber:
        start = ctx.idx

        content: List[Union[Digit, Exponent, Dot, str]] = []

        if Dot.is_valid(ctx):
            content.append(Dot.tokenize(ctx))

        if not Digit.is_valid(ctx):
            raise TokenizeException("Expected digit", ctx.point_span())

        content.append(Digit.tokenize(ctx))

        while True:
            if Digit.is_valid(ctx):
                content.append(Digit.tokenize(ctx))
            elif Exponent.is_valid(ctx):
                content.append(Exponent.tokenize(ctx))
            elif is_identifier_ch(ctx.peek(1), can_be_digit=False):
                ch, _ = ctx.pop(1)
                assert(ch is not None)
                content.append(ch)
            else:
                break

        return PPNumber(Span(ctx.source, start, ctx.idx), content)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        if Dot.is_valid(ctx):
            ahead = ctx.peek(2)
            if ahead is None:
                return False
            return ahead[1] in Digit.CHARS
        if Digit.is_valid(ctx):
            return True
        return False
