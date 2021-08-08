from __future__ import annotations
from abc import ABC, abstractmethod
from span import Span, SourceStream
from enum import Enum
from typing import Optional, List

USE_TRIGRAPHS = True


class TokenizeException(Exception):
    def __init__(self, msg: str, span: Span) -> None:
        self.msg = msg
        self.span = span


def expect(value: str, inp: SourceStream) -> Span:
    v, s = inp.pop(len(value))
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
    def tokenize(inp: SourceStream) -> Tokenizable:
        pass

    # May return True even if invalid, as long as no other tokens in this position can be
    # Should ideally run in constant time / fast
    @staticmethod
    @abstractmethod
    def is_valid(inp: SourceStream) -> bool:
        pass


class LexicalElement(Tokenizable):
    @staticmethod
    def tokenize(inp: SourceStream) -> LexicalElement:
        if SpaceSequence.is_valid(inp):
            return SpaceSequence.tokenize(inp)

        if PPToken.is_valid(inp):
            return PPToken.tokenize(inp)

        raise TokenizeException(
            "Expected source elemeent (TODO: Better error)", inp.point_span()
        )

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return SpaceSequence.is_valid(inp) or PPToken.is_valid(inp)


class SpaceSequence(LexicalElement):
    def __init__(self, span: Span, has_nl: bool) -> None:
        super().__init__(span)
        self.has_nl = has_nl

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(has_nl={self.has_nl})"

    @staticmethod
    def tokenize(inp: SourceStream) -> SpaceSequence:
        from .comment import Comment

        if Comment.is_valid(inp):
            return Comment.tokenize(inp)

        start = inp.idx

        has_nl = False
        has_any = False

        while True:
            if inp.pop_exact("\\\n"):
                has_any = True
                continue
            elif inp.pop_exact("\n"):
                has_nl = True
                has_any = True
                continue
            elif inp.pop_exact(" "):
                has_any = True
                continue
            elif USE_TRIGRAPHS and inp.pop_exact("??/\n"):
                has_any = True
                continue
            else:
                break

        if not has_any:
            raise TokenizeException("Expected spaces", inp.point_span())

        return SpaceSequence(Span(inp.source, start, inp.idx), has_nl)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        from .comment import Comment

        if Comment.is_valid(inp):
            return True

        if USE_TRIGRAPHS:
            if inp.peek_exact("??/\n"):
                return True

        return inp.peek_exact("\n") or inp.peek_exact(" ") or inp.peek_exact("\\\n")


class PPToken(LexicalElement):
    @staticmethod
    def tokenize(inp: SourceStream) -> PPToken:
        if ProperPPToken.is_valid(inp):
            return ProperPPToken.tokenize(inp)

        return Other.tokenize(inp)

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return inp.peek() is not None


class Other(PPToken):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.span.contents()!r})"

    @staticmethod
    def tokenize(inp: SourceStream) -> Other:
        start = inp.idx
        while (
            inp.peek() is not None
            and not ProperPPToken.is_valid(inp)
            and not SpaceSequence.is_valid(inp)
        ):
            inp.pop()

        return Other(Span(inp.source, start, inp.idx))

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        return (
            inp.peek() is not None
            and not ProperPPToken.is_valid(inp)
            and not SpaceSequence.is_valid(inp)
        )


class ProperPPToken(PPToken):
    @staticmethod
    def tokenize(inp: SourceStream) -> ProperPPToken:
        from .string import StringLiteral
        from .character import CharacterLiteral
        from .identifier import Identifier
        from .punctuator import Punctuator
        from .number import PPNumber

        if StringLiteral.is_valid(inp):
            return StringLiteral.tokenize(inp)

        if CharacterLiteral.is_valid(inp):
            return CharacterLiteral.tokenize(inp)

        if Identifier.is_valid(inp):
            return Identifier.tokenize(inp)

        if Punctuator.is_valid(inp):
            return Punctuator.tokenize(inp)

        if PPNumber.is_valid(inp):
            return PPNumber.tokenize(inp)

        raise TokenizeException("Expected preprocessing token", inp.point_span())

    @staticmethod
    def is_valid(inp: SourceStream) -> bool:
        from .string import StringLiteral
        from .character import CharacterLiteral
        from .identifier import Identifier
        from .punctuator import Punctuator
        from .number import PPNumber

        return (
            StringLiteral.is_valid(inp)
            or CharacterLiteral.is_valid(inp)
            or Identifier.is_valid(inp)
            or Punctuator.is_valid(inp)
            or PPNumber.is_valid(inp)
        )
