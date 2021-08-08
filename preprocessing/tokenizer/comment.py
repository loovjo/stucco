from __future__ import annotations
from typing import Optional

from .tokenize import LexicalElement, TokenizeException, SpaceSequence, SpaceSequence
from span import Span, SourceStream


class Comment(SpaceSequence):
    def __init__(self, span: Span):
        super().__init__(span, has_nl=False)

    @staticmethod
    def tokenize(inp: SourceStream) -> Comment:
        start = inp.idx
        if inp.peek_exact("//"):
            inp.pop(2)
            while True:
                if inp.peek_exact("\n"):
                    break
                if SpaceSequence.is_valid(inp):
                    SpaceSequence.tokenize(inp)
                    continue
                elif inp.peek(1) == None:
                    break
                else:
                    inp.pop()
            return Comment(Span(inp.source, start, inp.idx))

        if inp.peek_exact("/*"):
            inp.pop(2)
            while True:
                if inp.pop_exact("*/") != None:
                    break
                if inp.peek() == None:
                    raise TokenizeException(
                        "File ended in comment", Span(inp.source, start, inp.idx)
                    )
                inp.pop()
            return Comment(Span(inp.source, start, inp.idx))
        raise TokenizeException("Expected comment", inp.point_span())

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return inp.peek_exact("//") or inp.peek_exact("/*")
