from __future__ import annotations
from typing import Optional

from .tokenize import LexicalElement, TokenizeException, SpaceSequence, SpaceSequence
from span import Span, SourceCtx


class Comment(SpaceSequence):
    def __init__(self, span: Span):
        super().__init__(span, has_nl=False)

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Comment:
        start = ctx.idx
        if ctx.peek_exact("//"):
            ctx.pop(2)
            while True:
                if SpaceSequence.is_valid(ctx):
                    sp = SpaceSequence.tokenize(ctx)
                    if sp.has_nl:
                        break
                    else:
                        continue
                elif ctx.peek(1) == None:
                    break
                else:
                    ctx.pop()
            return Comment(Span(ctx.source, start, ctx.idx))

        if ctx.peek_exact("/*"):
            ctx.pop(2)
            while True:
                if ctx.pop_exact("*/") != None:
                    break
                if ctx.peek() == None:
                    raise TokenizeException("File ended in comment", Span(ctx.source, start, ctx.idx))
                ctx.pop()
            return Comment(Span(ctx.source, start, ctx.idx))
        raise TokenizeException("Expected comment", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact("//") or ctx.peek_exact("/*")
