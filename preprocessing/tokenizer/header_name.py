from __future__ import annotations
from typing import Optional

from span import Span, SourceCtx
from .tokenize import LexicalElement, ProperPPToken, TokenizeException, SpaceSequence
from .punctuator import Punctuator, PunctuatorType
from .identifier import Identifier

class HeaderName(ProperPPToken):
    def __init__(self, span: Span, name: str, is_q: bool) -> None:
        self.span = span
        self.name = name
        self.is_q = is_q

    # Note: Can only follow a #include directive, has to be externally checked!
    @staticmethod
    def tokenize(ctx: SourceCtx) -> HeaderName:
        start = ctx.idx

        is_q = True
        if ctx.peek_exact("<"):
            is_q = False
        elif ctx.peek_exact('"'):
            is_q = True
        else:
            raise TokenizeException("Expected header name", ctx.point_span())

        name = ""
        while True:
            if ctx.peek_exact('"' if is_q else ">"):
                ctx.pop()
                break
            ch, _ = ctx.pop()
            if ch is None:
                raise TokenizeException("File ended within header name", ctx.point_span())
            name += ch

        return HeaderName(Span(ctx.source, start, ctx.idx), name, is_q)

    @staticmethod
    def is_valid(ctx: SourceCtx, last_token: Optional[LexicalElement]=None, second_last_token: Optional[LexicalElement]=None) -> bool:
        if isinstance(second_last_token, Punctuator) and second_last_token.ty == PunctuatorType.HASH:
            if isinstance(last_token, Identifier) and last_token.identifier == "include":
                return ctx.peek_exact("<") or ctx.peek_exact('"')
        return False
