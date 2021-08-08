from __future__ import annotations
from typing import Optional

from span import Span, SourceStream
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
    def tokenize(inp: SourceStream) -> HeaderName:
        start = inp.idx

        is_q = True
        if inp.pop_exact("<"):
            is_q = False
        elif inp.pop_exact('"'):
            is_q = True
        else:
            raise TokenizeException("Expected header name", inp.point_span())

        name = ""
        while True:
            if inp.peek_exact('"' if is_q else ">"):
                inp.pop()
                break
            ch, _ = inp.pop()
            if ch is None:
                raise TokenizeException(
                    "File ended within header name", inp.point_span()
                )
            name += ch

        return HeaderName(Span(inp.source, start, inp.idx), name, is_q)

    @staticmethod
    def is_valid(
        inp: SourceStream,
        last_token: Optional[LexicalElement] = None,
        second_last_token: Optional[LexicalElement] = None,
    ) -> bool:
        if (
            isinstance(second_last_token, Punctuator)
            and second_last_token.ty == PunctuatorType.HASH
        ):
            if (
                isinstance(last_token, Identifier)
                and last_token.identifier == "include"
            ):
                return inp.peek_exact("<") or inp.peek_exact('"')
        return False
