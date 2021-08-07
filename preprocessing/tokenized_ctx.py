from __future__ import annotations
from typing import List, Optional

from span import Span, SourceCtx, Source
from .tokenizer.tokenize import TokenizeException, PPToken, ProperPPToken, LexicalElement

class TokenizedCtx:
    def __init__(self, elements: List[LexicalElement], idx: int = 0) -> None:
        self.elements = elements
        self.idx = idx

    def current_span(self) -> Span:
        if self.idx >= len(self.elements):
            last = self.elements[-1].span
            return Span(last.source, last.end, last.end)

        return self.elements[self.idx].span

    def peek_element(self, offset: int = 0) -> Optional[LexicalElement]:
        if 0 <= self.idx + offset < len(self.elements):
            return self.elements[self.idx + offset]
        return None

    def peek_token(self) -> Optional[LexicalElement]:
        i = self.idx
        while i < len(self.elements):
            if isinstance(self.elements[i], PPToken):
                return self.elements[i]
            i += 1
        return None

    def pop_element(self) -> Optional[LexicalElement]:
        if self.idx >= len(self.elements):
            return None
        else:
            e = self.elements[self.idx]
            self.idx += 1
            return e

    def pop_token(self) -> Optional[LexicalElement]:
        while self.idx < len(self.elements):
            el = self.elements[self.idx]
            self.idx += 1
            if isinstance(el, PPToken):
                return el
        return None

    @staticmethod
    def tokenize(ctx: SourceCtx) -> TokenizedCtx:
        from .tokenizer.header_name import HeaderName
        elements: List[LexicalElement] = []

        last_token = None
        second_last_token = None

        while True:
            if len(elements) >= 2 and HeaderName.is_valid(ctx, last_token, second_last_token):
                elements.append(HeaderName.tokenize(ctx))
            elif LexicalElement.is_valid(ctx):
                tok = LexicalElement.tokenize(ctx)
                elements.append(tok)
                if isinstance(tok, ProperPPToken):
                    second_last_token = last_token
                    last_token = tok
            else:
                break

        return TokenizedCtx(elements)

