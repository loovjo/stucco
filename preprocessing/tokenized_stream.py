from __future__ import annotations
from typing import List, Optional, NewType, Dict, Tuple
import random

from span import Span, SourceStream, Source, PseudoFilename
from .tokenizer.tokenize import (
    TokenizeException,
    PPToken,
    ProperPPToken,
    LexicalElement,
)


class _EOFElement(LexicalElement):
    @staticmethod
    def tokenize(inp: SourceStream) -> LexicalElement:
        raise TokenizeException(
            "_EOFElement should never be tokenized", inp.point_span()
        )

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return False


ElementKey = NewType("ElementKey", int)
def make_key() -> ElementKey:
    return ElementKey(random.getrandbits(128))

# TokenizedStream iterates using an internal doubly linked list. The linked list
# is shared among subctxs.
# Internally, the linked list is circular, but the TokenizedStream.end represents
# the first member of the list that is not part of the ctx


class Entry:
    def __init__(self, element: LexicalElement, previous: ElementKey, next: ElementKey):
        self.element = element
        self.previous = previous
        self.next = next


class TokenizedStream:
    @staticmethod
    def from_list(elements: List[LexicalElement]) -> TokenizedStream:
        element_list: Dict[ElementKey, Entry] = dict()

        idx2key = [make_key() for _ in range(len(elements) + 1)]


        first = idx2key[0]
        last = idx2key[len(elements) - 1]
        end = idx2key[len(elements)]

        nullSpan = Span(Source(PseudoFilename.NULL, ""), 0, 0)
        element_list[end] = Entry(_EOFElement(nullSpan), last, first)

        for i, e in enumerate(elements):
            last = idx2key[i - 1] if i > 0 else end
            next = idx2key[i + 1] if i < end else 0

            element_list[idx2key[i]] = Entry(e, idx2key[i - 1], idx2key[i + 1])

        return TokenizedStream(
            element_list,
            first,
            end,
        )

    def __init__(
        self,
        element_list: Dict[ElementKey, Entry],  # {id: (token, from, to)}
        idx: ElementKey,
        end: ElementKey,
    ) -> None:

        self.entries = element_list
        self.idx = idx
        self.end = end  # Reference to the first element outisde the list

    def collect(self) -> List[LexicalElement]:
        out = []

        idx = self.idx
        while idx != self.end:
            out.append(self.entries[idx].element)
            idx = self.entries[idx].next

        return out

    def _check_coherence(self) -> None:
        for key in self.entries:
            before = self.entries[key].previous
            after = self.entries[key].next
            assert(self.entries[before].next == key)
            assert(self.entries[after].previous == key)

    # start is inclusive, end is not. invalidates data
    def replace_range(self, start: ElementKey, end: ElementKey, data: TokenizedStream) -> None:

        before_start = self.entries[start].previous
        before_end = self.entries[end].previous

        before_data_end = data.entries[data.end].previous

        to_add = data.idx
        while to_add != data.end:
            assert(to_add not in self.entries)
            self.entries[to_add] = data.entries[to_add]
            to_add = data.entries[to_add].next

        self.entries[before_start].next = data.idx
        self.entries[data.idx].previous = before_start

        self.entries[before_data_end].next = end
        self.entries[end].previous = before_data_end

        to_delete = start
        while to_delete != end:
            next = self.entries[to_delete].next
            del self.entries[to_delete]
            to_delete = next

        # self._check_coherence()

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
    def tokenize(inp: SourceStream) -> TokenizedStream:
        from .tokenizer.header_name import HeaderName

        elements: List[LexicalElement] = []

        last_token = None
        second_last_token = None

        while True:
            tok: Optional[LexicalElement] = None
            if len(elements) >= 2 and HeaderName.is_valid(
                inp, last_token, second_last_token
            ):
                tok = HeaderName.tokenize(inp)
            elif LexicalElement.is_valid(inp):
                tok = LexicalElement.tokenize(inp)
            else:
                break
            elements.append(tok)
            if isinstance(tok, ProperPPToken):
                second_last_token = last_token
                last_token = tok

        return TokenizedStream.from_list(elements)

# Renders stream into a graphviz object
def render_stream(stream: TokenizedStream) -> None:
    import graphviz # type: ignore # no stubs sadge

    graph = graphviz.Digraph()

    for k, v in stream.entries.items():
        print(k, v)
        graph.node("N" + str(k), str(v.element), color="blue" if k == stream.idx else "red" if k == stream.end else None)
        graph.edge("N" + str(k), "N" + str(v.next), color="blue")
        graph.edge("N" + str(v.previous), "N" + str(k), color="red")

    graph.render("/tmp/grap", view=True)

