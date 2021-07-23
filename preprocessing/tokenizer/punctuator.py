from __future__ import annotations
from typing import Dict, Any
from enum import Enum

from .tokenize import LexicalElement, ProperPPToken, TokenizeException, USE_TRIGRAPHS
from span import Span, SourceCtx

class PunctuatorType(Enum):
    OPEN_BRACKET = ["[", "<:"] + USE_TRIGRAPHS * ["??("]
    CLOSE_BRACKET = ["]", ":>"] + USE_TRIGRAPHS * ["??)"]
    OPEN_PAREN = ["("]
    CLOSE_PAREN = [")"]
    OPEN_BRACE = ["{", "<%"] + USE_TRIGRAPHS * ["??<"]
    CLOSE_BRACE = ["}", "%>"] + USE_TRIGRAPHS * ["??>"]

    DOT = ["."]
    ARROW = ["->"]

    PLUS_PLUS = ["++"]
    MINUS_MINUS = ["--"]

    AMPERSAND = ["&"]
    ASTERISK = ["*"]
    PLUS = ["+"]
    MINUS = ["-"]
    TILDE = ["~"] + USE_TRIGRAPHS * ["??-"]
    EXCLAMATION_MARK = ["!"]
    SLASH = ["/"]
    PERCENT = ["%"]
    SHIFT_LEFT = ["<<"]
    SHIFT_RIGHT = [">>"]
    LESS_THAN = ["<"]
    GREATER_THAN = [">"]
    LESS_THAN_EQUAL = ["<="]
    GREATER_THAN_EQUAL = [">="]
    DOUBLE_EQUAL = ["=="]
    BANG_EQUAL = ["!="]
    CARET = ["^"] + USE_TRIGRAPHS * ["??'"]
    BAR = ["|"]
    DOUBLE_AMPERSAND = ["&&"]
    DOUBLE_BAR = ["||"]
    QUESTION_MARK = ["?"]
    COLON = [":"]
    SEMICOLON = [";"]
    TRIPLE_DOT = ["..."]
    EQUAL = ["="]

    ASTERISK_EQUAL = ["*="]
    SLASH_EQUAL = ["/="]
    PERCENT_EQUAL = ["%="]
    PLUS_EQUAL = ["+="]
    MINUS_EQUAL = ["-="]
    SHIFT_LEFT_EQUAL = ["<<="]
    SHIFT_RIGHT_EQUAL = [">>="]
    AMPERSAND_EQUAL = ["&="]
    CARET_EQUAL = ["^="]
    BAR_EQUAL = ["|="]

    COMMA = [","]
    HASH = ["#", "%:"] + USE_TRIGRAPHS * ["??="]
    DOUBLE_HASH = ["##", "%:%:"] + USE_TRIGRAPHS * ["??=??="]

    @staticmethod
    def lookup() -> Dict[str, PunctuatorType]:
        table = {}
        for punct in PunctuatorType:
            for val in punct.value:
                table[val] = punct

        return table

class Punctuator(ProperPPToken):
    def __init__(self, span: Span, ty: PunctuatorType) -> None:
        super().__init__(span)

        self.ty = ty

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.ty})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Punctuator:
        for name, punct in PunctuatorType.lookup().items():
            if ctx.peek_exact(name):
                _, span = ctx.pop(len(name))
                return Punctuator(span, punct)
        raise TokenizeException("Expected punctuator", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        for name in PunctuatorType.lookup().keys():
            if ctx.peek_exact(name):
                return True
        return False

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Punctuator) and self.ty == other.ty
