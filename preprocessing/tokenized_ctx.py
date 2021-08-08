from __future__ import annotations
from typing import List, Optional, NewType, Dict, Tuple

from span import Span, SourceCtx, Source, PseudoFilename
from .tokenizer.tokenize import TokenizeException, PPToken, ProperPPToken, LexicalElement

class _EOFElement(LexicalElement):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> LexicalElement:
        raise TokenizeException("_EOFElement should never be tokenized", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return False

ElementKey = NewType("ElementKey", int)
START: ElementKey = ElementKey(0)

# TokenizedCtx iterates using an internal doubly linked list. The linked list
# is shared among subctxs.
# Internally, the linked list is circular, but the TokenizedCtx.end represents
# the first member of the list that is not part of the ctx

class Entry:
    def __init__(self, element: LexicalElement, previous: ElementKey, next: ElementKey):
        self.element = element
        self.previous = previous
        self.next = next

class TokenizedCtx:
    @staticmethod
    def from_list(elements: List[LexicalElement]) -> TokenizedCtx:
        element_list: Dict[ElementKey, Entry] = dict()

        first = ElementKey(0)
        last = ElementKey(len(elements) - 1)
        end = ElementKey(len(elements))

        nullSpan = Span(Source(PseudoFilename.NULL, ""), 0, 0)
        element_list[end] = Entry(_EOFElement(nullSpan), last, first)

        for i, e in enumerate(elements):
            last = ElementKey(i - 1) if i > 0 else end
            next = ElementKey(i + 1) if i < end else 0

            element_list[ElementKey(i)] = Entry(e, ElementKey(i - 1), ElementKey(i + 1))

        return TokenizedCtx(
            element_list,
            ElementKey(0),
            end,
        )

    def __init__(
        self,
        element_list: Dict[ElementKey, Entry], # {id: (token, from, to)}
        idx: ElementKey,
        end: ElementKey,
    ) -> None:

        self.entries = element_list
        self.idx = idx
        self.end = end # Reference to the first element outisde the list


    def current_span(self) -> Span:
        if self.idx == self.end:
            last_id = self.entries[self.end].previous
            last_span = self.entries[last_id].element.span

            return Span(last_span.source, last_span.end, last_span.end)

        return self.entries[self.idx].element.span

    def peek_element(self, offset: int = 0) -> Optional[LexicalElement]:
        if offset < 0:
            current = self.idx
            for _ in range(-offset):
                if current == self.end:
                    return None

                current = self.entries[current].previous
            if current == self.end:
                return None
            return self.entries[current].element
        else:
            current = self.idx
            for _ in range(offset):
                if current == self.end:
                    return None

                current = self.entries[current].next
            if current == self.end:
                return None
            return self.entries[current].element

    def peek_token(self) -> Optional[LexicalElement]:
        current = self.idx
        while current != self.end:
            if isinstance(self.entries[current].element, PPToken):
                return self.entries[current].element

            current = self.entries[current].next
        return None

    def pop_element(self) -> Optional[LexicalElement]:
        if self.idx == self.end:
            return None

        el = self.entries[self.idx].element
        self.idx = self.entries[self.idx].next
        return el

    def pop_token(self) -> Optional[LexicalElement]:
        while self.idx != self.end:
            el = self.entries[self.idx].element

            self.idx = self.entries[self.idx].next

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

        return TokenizedCtx.from_list(elements)

