from __future__ import annotations
from abc import ABC, abstractmethod
from span import Span, SourceCtx
from enum import Enum
from typing import Optional, List

USE_TRIGRAPHS = True

class TokenizeException(Exception):
    def __init__(self, msg: str, span: Span) -> None:
        self.msg = msg
        self.span = span

def expect(value: str, ctx: SourceCtx) -> Span:
    v, s = ctx.pop(len(value))
    if v != value:
        raise TokenizeException(f"Expected {value!r}", s)
    return s


class Tokenizable(ABC):
    def __init__(self, span: Span) -> None:
        self.span = span

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.span.contents()!r})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    # May throw TokenizeException
    @staticmethod
    @abstractmethod
    def tokenize(ctx: SourceCtx) -> Tokenizable:
        pass

    # May return True even if invalid, as long as no other tokens in this position can be
    # Should ideally run in constant time / fast
    @staticmethod
    @abstractmethod
    def is_valid(ctx: SourceCtx) -> bool:
        pass

class LexicalElement(Tokenizable):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> LexicalElement:
        if SpaceSequence.is_valid(ctx):
            return SpaceSequence.tokenize(ctx)

        if PPToken.is_valid(ctx):
            return PPToken.tokenize(ctx)

        raise TokenizeException("Expected source elemeent (TODO: Better error)", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return SpaceSequence.is_valid(ctx) or PPToken.is_valid(ctx)

class SpaceSequence(LexicalElement):
    def __init__(self, span: Span, has_nl: bool) -> None:
        super().__init__(span)
        self.has_nl = has_nl

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(has_nl={self.has_nl})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> SpaceSequence:
        from .comment import Comment

        if Comment.is_valid(ctx):
            return Comment.tokenize(ctx)

        start = ctx.idx

        has_nl = False
        has_any = False

        while True:
            if ctx.pop_exact("\\\n"):
                has_any = True
                continue
            elif ctx.pop_exact("\n"):
                has_nl = True
                has_any = True
                continue
            elif ctx.pop_exact(" "):
                has_any = True
                continue
            elif USE_TRIGRAPHS and ctx.pop_exact("??/\n"):
                has_any = True
                continue
            else:
                break

        if not has_any:
            raise TokenizeException("Expected spaces", ctx.point_span())

        return SpaceSequence(Span(ctx.source, start, ctx.idx), has_nl)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        from .comment import Comment

        if Comment.is_valid(ctx):
            return True

        if USE_TRIGRAPHS:
            if ctx.peek_exact("??/\n"):
                return True

        return ctx.peek_exact("\n") or ctx.peek_exact(" ") or ctx.peek_exact("\\\n")

class PPToken(LexicalElement):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> PPToken:
        if ProperPPToken.is_valid(ctx):
            return ProperPPToken.tokenize(ctx)

        return Other.tokenize(ctx)

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek() is not None

class Other(PPToken):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.span.contents()!r})"

    @staticmethod
    def tokenize(ctx: SourceCtx) -> Other:
        start = ctx.idx
        while ctx.peek() is not None and not ProperPPToken.is_valid(ctx) and not SpaceSequence.is_valid(ctx):
            ctx.pop()

        return Other(Span(ctx.source, start, ctx.idx))

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek() is not None and not ProperPPToken.is_valid(ctx) and not SpaceSequence.is_valid(ctx)

class ProperPPToken(PPToken):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> ProperPPToken:
        from .string import StringLiteral
        from .character import CharacterLiteral
        from .identifier import Identifier
        from .punctuator import Punctuator
        from .number import PPNumber

        if StringLiteral.is_valid(ctx):
            return StringLiteral.tokenize(ctx)

        if CharacterLiteral.is_valid(ctx):
            return CharacterLiteral.tokenize(ctx)

        if Identifier.is_valid(ctx):
            return Identifier.tokenize(ctx)

        if Punctuator.is_valid(ctx):
            return Punctuator.tokenize(ctx)

        if PPNumber.is_valid(ctx):
            return PPNumber.tokenize(ctx)

        raise TokenizeException("Expected preprocessing teken", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        from .string import StringLiteral
        from .character import CharacterLiteral
        from .identifier import Identifier
        from .punctuator import Punctuator
        from .number import PPNumber

        return StringLiteral.is_valid(ctx) or CharacterLiteral.is_valid(ctx) or Identifier.is_valid(ctx) or Punctuator.is_valid(ctx) or PPNumber.is_valid(ctx)
