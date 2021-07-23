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
        if Space.is_valid(ctx):
            return Space.tokenize(ctx)

        if PPToken.is_valid(ctx):
            return PPToken.tokenize(ctx)

        raise TokenizeException("Expected source elemeent (TODO: Better error)", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return Space.is_valid(ctx) or PPToken.is_valid(ctx)

def tokenize(ctx: SourceCtx) -> List[LexicalElement]:
    from .header_name import HeaderName
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

    return elements

class Space(LexicalElement):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> Space:
        from .comment import Comment

        if Comment.is_valid(ctx):
            return Comment.tokenize(ctx)

        if ctx.peek_exact("\\\n"):
            return Space(ctx.pop(2)[1])

        if ctx.peek_exact("\n"):
            return Newline(ctx.pop()[1])

        if ctx.peek_exact(" "):
            return Space(ctx.pop()[1])

        if USE_TRIGRAPHS:
            if ctx.peek_exact("??/\n"):
                return Space(ctx.pop(4)[1])

        raise TokenizeException("Expected space", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        from .comment import Comment

        if Comment.is_valid(ctx):
            return True

        if USE_TRIGRAPHS:
            if ctx.peek_exact("??/\n"):
                return True

        return ctx.peek_exact("\n") or ctx.peek_exact(" ") or ctx.peek_exact("\\\n")

class Newline(Space):
    @staticmethod
    def tokenize(ctx: SourceCtx) -> Newline:
        space = Space.tokenize(ctx)
        if isinstance(space, Newline):
            return space
        raise TokenizeException("Expected newline", ctx.point_span())

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek_exact("\n")

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
        while ctx.peek() is not None and not ProperPPToken.is_valid(ctx) and not Space.is_valid(ctx):
            ctx.pop()

        return Other(Span(ctx.source, start, ctx.idx))

    @staticmethod
    def is_valid(ctx: SourceCtx) -> bool:
        return ctx.peek() is not None and not ProperPPToken.is_valid(ctx) and not Space.is_valid(ctx)

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
