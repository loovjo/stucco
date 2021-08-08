from __future__ import annotations
from typing import List, Optional, Union

from .tokenize import LexicalElement, ProperPPToken, TokenizeException, expect
from .escape import EscapeSequence
from .identifier import is_identifier_ch
from span import Span, SourceStream


class Digit(LexicalElement):
    CHARS = "0123456789"

    def __init__(self, span: Span, value: int) -> None:
        super().__init__(span)

        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    @staticmethod
    def tokenize(inp: SourceStream) -> Digit:
        ch, span = inp.pop(1)
        if ch is not None and ch.lower() in Digit.CHARS:
            return Digit(span, Digit.CHARS.index(ch))

        raise TokenizeException("Expected hexadecimal digit", span)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        ch = inp.peek(1)
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
    def tokenize(inp: SourceStream) -> Exponent:
        exp, expspan = inp.pop(1)
        sign, signspan = inp.pop(1)

        if exp is None or exp.lower() not in "ep":
            raise TokenizeException("Expected exponent", expspan)
        if sign is None or sign not in "+-":
            raise TokenizeException("Expected plus or minus", expspan)

        return Exponent(
            expspan.combine(signspan),
            exp.lower() == "e",
            exp == exp.upper(),
            sign == "+",
        )

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        x = inp.peek(2)
        if x is None:
            return False
        return x[0].lower() in "ep" and x[1] in "+-"


class Dot(LexicalElement):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    @staticmethod
    def tokenize(inp: SourceStream) -> Dot:
        dot, span = inp.pop(1)
        if dot != ".":
            raise TokenizeException("Expected dot", span)
        return Dot(span)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return inp.peek_exact(".")


class PPNumber(ProperPPToken):
    def __init__(
        self, span: Span, number_content: List[Union[Digit, Exponent, Dot, str]]
    ) -> None:
        super().__init__(span)

        self.number_content = number_content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.number_content!r})"

    @staticmethod
    def tokenize(inp: SourceStream) -> PPNumber:
        start = inp.idx

        content: List[Union[Digit, Exponent, Dot, str]] = []

        if Dot.is_valid(inp):
            content.append(Dot.tokenize(inp))

        if not Digit.is_valid(inp):
            raise TokenizeException("Expected digit", inp.point_span())

        content.append(Digit.tokenize(inp))

        while True:
            if Digit.is_valid(inp):
                content.append(Digit.tokenize(inp))
            elif Exponent.is_valid(inp):
                content.append(Exponent.tokenize(inp))
            elif is_identifier_ch(inp.peek(1), can_be_digit=False):
                ch, _ = inp.pop(1)
                assert ch is not None
                content.append(ch)
            else:
                break

        return PPNumber(Span(inp.source, start, inp.idx), content)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        if Dot.is_valid(inp):
            ahead = inp.peek(2)
            if ahead is None:
                return False
            return ahead[1] in Digit.CHARS
        if Digit.is_valid(inp):
            return True
        return False
